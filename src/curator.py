"""
Autonomous Multi-Channel Content Curator & Auto-Poster.
Monitors target YouTube channels and Instagram profiles, picks new viral shorts/reels,
cleans metadata, generates new viral hooks/captions, and uploads directly.
"""
import os
import sys
import json
import traceback
import yt_dlp

from main import process_reel, build_telegram_message
from listeners.telegram_listener import send_notification

HISTORY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'state', 'curated_history.json')
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config', 'curator_sources.json')

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

def get_latest_shorts_from_channel(channel_url, limit=2):
    """Fetches latest video URLs from a channel using fast flat extraction."""
    ydl_opts = {
        'extract_flat': True,
        'playlist_items': f'1-{limit}',
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 15,
    }
    videos = []
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(channel_url, download=False)
            entries = info.get('entries') or []
            for entry in entries:
                if not entry:
                    continue
                v_url = entry.get('url') or entry.get('webpage_url')
                v_id = entry.get('id')
                if v_url and ('youtube.com' in v_url or 'youtu.be' in v_url or 'instagram.com' in v_url):
                    videos.append((v_id or v_url, v_url))
                elif v_id:
                    videos.append((v_id, f"https://www.youtube.com/shorts/{v_id}"))
    except Exception as e:
        print(f"   ⚠️ Failed to inspect channel {channel_url}: {e}")
    return videos

def run_curator():
    print("=" * 65)
    print("🎬 Autonomous Content Curator v1.0 Starting...")
    print("=" * 65)

    token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '').strip()

    sources = load_sources()
    history = load_history()

    if not sources:
        print("❌ No sources configured in config/curator_sources.json!")
        return

    print(f"📋 Loaded {len(sources)} categories from curator_sources.json")
    print(f"📜 Already processed videos in history: {len(history)}")

    total_curated = 0

    for category, feeds in sources.items():
        print(f"\n🔍 [Category: {category.upper()}] Checking target channels...")
        yt_channels = feeds.get('youtube_channels', [])
        ig_accounts = feeds.get('instagram_accounts', [])
        all_targets = yt_channels + ig_accounts

        picked_video = None

        for target in all_targets:
            if not target.strip():
                continue
            print(f"   🔎 Scanning target: {target}")
            recent_videos = get_latest_shorts_from_channel(target.strip(), limit=2)
            for vid_id, vid_url in recent_videos:
                if vid_id not in history and vid_url not in history:
                    picked_video = (vid_id, vid_url)
                    break
            if picked_video:
                break

        if not picked_video:
            print(f"   ✅ No new videos found for category '{category}' (All caught up).")
            continue

        vid_id, vid_url = picked_video
        print(f"\n🎯 [FOUND NEW VIDEO] Category: {category.upper()} -> {vid_url}")
        
        try:
            res = process_reel(vid_url, f"Auto-Curator ({category.upper()})", forced_category=category)
            history.add(vid_id)
            history.add(vid_url)
            save_history(history)
            total_curated += 1

            if token and chat_id:
                msg = build_telegram_message(res)
                send_notification(token, chat_id, f"🤖 <b>[Auto-Curator Repost]</b>\nCategory: <b>{category.upper()}</b>\n\n{msg}")
                print("   📬 Sent curation report to Telegram.")

        except Exception as e:
            print(f"   💥 Curation failed for {vid_url}: {e}")
            traceback.print_exc()

    print("\n" + "=" * 65)
    print(f"🏁 Auto-Curator finished. Total videos reposted this run: {total_curated}")
    print("=" * 65)

if __name__ == "__main__":
    run_curator()
