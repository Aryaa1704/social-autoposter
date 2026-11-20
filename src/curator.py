"""
Autonomous Multi-Channel Content Curator & Auto-Poster v2.0.
Features:
- Ultra-Fast Parallel Scanning of 100+ channels simultaneously (ThreadPoolExecutor)
- Strict Freshness Filter: Only picks videos uploaded recently (within last 3-7 days max)
- Ranks candidate videos by newest first (descending timestamp)
- Zero duplicates: Persists history in `src/state/curated_history.json`
- Cleans metadata, optimizes video (1.02x + unsharp), generates fresh AI hooks & uploads
"""
import os
import sys
import time
import json
import random
import traceback
import concurrent.futures
import yt_dlp

from main import process_reel, build_telegram_message
from listeners.telegram_listener import send_notification

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'state', 'curated_history.json')
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config', 'curator_sources.json')

# Maximum allowed video age in days (Videos older than this will NEVER be picked)
MAX_AGE_DAYS = 3
FALLBACK_MAX_AGE_DAYS = 7

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except Exception:
            pass
    return set()

def save_history(history):
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    try:
        with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(history)[-1000:], f, indent=2)
    except Exception as e:
        print(f"   ⚠️ Could not save history: {e}")

def load_sources():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"   ⚠️ Could not read curator_sources.json: {e}")
    return {}

class SilentLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): pass

def scan_single_channel(target_url, limit=2):
    """Scans a single channel for its latest 1-2 videos in ~1 second."""
    ydl_opts = {
        'extract_flat': True,
        'playlist_items': f'1-{limit}',
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'socket_timeout': 10,
        'logger': SilentLogger(),
    }
    videos = []
    urls_to_try = [target_url]
    if '/shorts' in target_url:
        urls_to_try.append(target_url.replace('/shorts', ''))

    for u in urls_to_try:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(u, download=False)
                if not info:
                    continue
                entries = info.get('entries') or []
                for entry in entries:
                    if not entry:
                        continue
                    v_url = entry.get('url') or entry.get('webpage_url')
                    v_id = entry.get('id')
                    if v_url and ('youtube.com' in v_url or 'youtu.be' in v_url):
                        videos.append((v_id or v_url, v_url))
                    elif v_id:
                        videos.append((v_id, f"https://www.youtube.com/shorts/{v_id}"))
                if videos:
                    break
        except Exception:
            pass
    return videos

def check_video_freshness(video_tuple):
    """Fetches video upload date and verifies how fresh it is using mobile player client to bypass bot check."""
    vid_id, vid_url = video_tuple
    opts = {
        'quiet': True,
        'no_warnings': True,
        'ignoreerrors': True,
        'socket_timeout': 10,
        'logger': SilentLogger(),
        'extractor_args': {
            'youtube': {
                'player_client': ['android']
            }
        }
    }

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(vid_url, download=False)
            if not info:
                return None
            ts = info.get('timestamp') or 0
            if not ts:
                # Fallback to upload_date (YYYYMMDD) if timestamp not returned
                ud = info.get('upload_date')
                if ud and len(ud) == 8:
                    try:
                        import datetime
                        dt = datetime.datetime.strptime(ud, '%Y%m%d')
                        ts = dt.timestamp()
                    except Exception:
                        pass
            title = info.get('title', 'Unknown Title')
            now = time.time()
            age_days = (now - ts) / 86400.0 if ts else 999.0
            return {
                'id': vid_id,
                'url': vid_url,
                'title': title,
                'timestamp': ts,
                'age_days': age_days
            }
    except Exception:
        return None

def run_curator():
    print("=" * 65)
    print("🚀 Autonomous Multi-Channel Content Curator v2.0 Starting...")
    print("=" * 65)

    token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '').strip()

    sources = load_sources()
    history = load_history()

    if not sources:
        print("❌ No sources configured in config/curator_sources.json!")
        return

    total_channels = sum(len(v.get('youtube_channels', [])) + len(v.get('instagram_accounts', [])) for v in sources.values())
    print(f"📋 Loaded {len(sources)} categories across {total_channels} channels!")
    print(f"📜 Already processed videos in history: {len(history)}")
    print(f"⏱️ Freshness Gate: Max {MAX_AGE_DAYS} days old (Strict Filter)\n")

    total_curated = 0

    for category, feeds in sources.items():
        print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        print(f"🔍 [Category: {category.upper()}] Scanning channels in parallel...")
        yt_channels = feeds.get('youtube_channels', [])
        ig_accounts = feeds.get('instagram_accounts', [])
        all_targets = [t.strip() for t in (yt_channels + ig_accounts) if t.strip()]

        if not all_targets:
            continue

        # Step 1: Scan all channels of this category concurrently
        t0 = time.time()
        candidate_tuples = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            channel_results = executor.map(scan_single_channel, all_targets)
            for res_list in channel_results:
                for vid_id, vid_url in res_list:
                    if vid_id not in history and vid_url not in history:
                        candidate_tuples.append((vid_id, vid_url))

        print(f"   ⚡ Scanned {len(all_targets)} channels in {time.time()-t0:.2f}s | Found {len(candidate_tuples)} unposted candidates.")

        if not candidate_tuples:
            print(f"   ✅ All channels caught up for '{category}'.")
            continue

        # Step 2: Check timestamps in parallel to enforce Freshness Filter
        print(f"   ⏳ Checking video upload dates to reject old videos...")
        t1 = time.time()
        fresh_candidates = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            details = executor.map(check_video_freshness, candidate_tuples[:25])
            for d in details:
                if d and d['timestamp'] > 0:
                    fresh_candidates.append(d)

        print(f"   ⏱️ Verified freshness in {time.time()-t1:.2f}s.")

        # Filter by strict freshness: <= MAX_AGE_DAYS (3 days)
        valid_fresh = [v for v in fresh_candidates if v['age_days'] <= MAX_AGE_DAYS]

        # If none within 3 days, fallback to 7 days
        if not valid_fresh:
            valid_fresh = [v for v in fresh_candidates if v['age_days'] <= FALLBACK_MAX_AGE_DAYS]
            if valid_fresh:
                print(f"   ℹ️ No videos under {MAX_AGE_DAYS} days, using fresh candidate under {FALLBACK_MAX_AGE_DAYS} days.")

        if not valid_fresh:
            print(f"   ⚠️ All candidates are older than {FALLBACK_MAX_AGE_DAYS} days. Skipping to avoid posting outdated content.")
            continue

        # Sort by timestamp DESCENDING (Absolute freshest / newest video first!)
        valid_fresh.sort(key=lambda x: x['timestamp'], reverse=True)

        chosen = valid_fresh[0]
        print(f"\n🎯 [SELECTED FRESHEST VIDEO]")
        print(f"   📌 Title: {chosen['title']}")
        print(f"   📅 Uploaded: {chosen['age_days']:.1f} days ago ({round(chosen['age_days']*24)} hours ago)")
        print(f"   🔗 URL: {chosen['url']}")

        try:
            res = process_reel(chosen['url'], f"Auto-Curator ({category.upper()})", forced_category=category)
            history.add(chosen['id'])
            history.add(chosen['url'])
            save_history(history)
            total_curated += 1

            if token and chat_id:
                msg = build_telegram_message(res)
                send_notification(
                    token,
                    chat_id,
                    f"🤖 <b>[Auto-Curator Repost]</b>\n"
                    f"🏷️ Category: <b>{category.upper()}</b>\n"
                    f"⏰ Freshness: <b>{chosen['age_days']:.1f} days old</b>\n\n"
                    f"{msg}"
                )
                print("   📬 Sent curation report to Telegram.")

        except Exception as e:
            print(f"   💥 Curation failed for {chosen['url']}: {e}")
            traceback.print_exc()

    print("\n" + "=" * 65)
    print(f"🏁 Auto-Curator finished. Total fresh videos reposted this run: {total_curated}")
    print("=" * 65)

if __name__ == "__main__":
    run_curator()
