"""
Social Media Auto-Poster - Main Orchestrator v2.0
Features:
- 1080p Full HD Video Downloader
- Anti-copyright metadata stripping & 1.02x speed optimizer
- Multi-AI (Gemini 2.0 Flash + Groq Llama-3.3 fallback)
- Voice & spoken dialogue transcription breakdown
- Smart Multi-Channel Category Routing (Gaming/Facts/Comedy/Main)
- YouTube Shorts & Instagram Creator Reels uploader
- Telegram notifications with live links & stats
"""
import os
import sys
import traceback

from downloader import download_video
from video_editor import optimize_video, extract_thumbnail_frame
from ai_generator import analyze_video
from youtube_uploader import upload_to_youtube
from instagram_uploader import upload_to_instagram
from listeners.telegram_listener import get_new_links, send_notification
from listeners.insta_dm_listener import get_new_links_from_dm

def process_reel(url, source):
    print("\n" + "=" * 65)
    print(f"🎬 [START] Processing: {url}")
    print(f"   Source: {source}")
    print("=" * 65)

    result = {
        "url": url,
        "source": source,
        "youtube": None,
        "instagram": None,
        "success": False,
        "error": None
    }
    video_path = None
    thumb_path = None

    try:
        # Step 1: 1080p Download
        print("\n📥 [1/5] Downloading video in 1080p Full HD...")
        video_path = download_video(url)

        # Step 2: Video Optimization & Metadata Stripping
        print("\n⚙️ [2/5] Cleaning video metadata & optimizing...")
        video_path = optimize_video(video_path)
        thumb_path = extract_thumbnail_frame(video_path)

        # Step 3: Multi-AI Analysis (Gemini + Groq)
        print("\n🤖 [3/5] Multi-AI analysis (visuals, speech, category, hook)...")
        meta = analyze_video(video_path)
        result["metadata"] = meta
        category = meta.get("detected_category", "general")
        print(f"   🏷️ Detected Category: {category.upper()}")
        print(f"   🎯 Hook Title: {meta.get('youtube_title')}")
        if meta.get("spoken_summary"):
            print(f"   🎙️ Spoken Words: {meta.get('spoken_summary')}")

        # Step 4: YouTube Shorts Upload (with category routing)
        yt_refresh = os.environ.get('YOUTUBE_REFRESH_TOKEN', '').strip()
        if yt_refresh:
            print(f"\n🔴 [4/5] Uploading to YouTube Shorts (Category: {category})...")
            try:
                yt = upload_to_youtube(
                    video_path=video_path,
                    title=meta.get('youtube_title'),
                    description=meta.get('youtube_description'),
                    tags=meta.get('youtube_tags', ['Shorts']),
                    category_id=meta.get('youtube_category_id', '22'),
                    category=category,
                    thumbnail_path=thumb_path
                )
                result["youtube"] = yt
                print(f"   ✅ YouTube Upload SUCCESS: {yt.get('url')}")
            except Exception as e:
                print(f"   ❌ YouTube Upload FAILED: {e}")
                traceback.print_exc()
                result["youtube_error"] = str(e)
        else:
            print("\n🔴 [4/5] YouTube skipped (YOUTUBE_REFRESH_TOKEN not set)")

        # Step 5: Instagram Upload (to Main Creator Account)
        has_ig = any(k.startswith('INSTAGRAM_ACCESS_TOKEN') and v.strip() for k, v in os.environ.items())
        if has_ig:
            print(f"\n🟣 [5/5] Uploading to Instagram Reels (Category: {category})...")
            try:
                ig = upload_to_instagram(
                    video_path=video_path,
                    caption=meta.get('instagram_caption', ''),
                    hashtags=meta.get('instagram_hashtags', []),
                    category=category
                )
                result["instagram"] = ig
                print(f"   ✅ Instagram Upload SUCCESS: {ig.get('url')}")
            except Exception as e:
                print(f"   ❌ Instagram Upload FAILED: {e}")
                traceback.print_exc()
                result["instagram_error"] = str(e)
        else:
            print("\n🟣 [5/5] Instagram upload skipped (INSTAGRAM_ACCESS_TOKEN not set)")

        if result.get("youtube") or result.get("instagram"):
            result["success"] = True

    except Exception as e:
        print(f"\n💥 [PIPELINE ERROR]: {e}")
        traceback.print_exc()
        result["error"] = str(e)

    finally:
        # Cleanup
        for p in [video_path, thumb_path]:
            if p and os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass
                try:
                    if os.path.exists(f"{p}.meta.json"):
                        os.remove(f"{p}.meta.json")
                except Exception:
                    pass

    return result

def build_telegram_message(result):
    if result.get("success"):
        meta = result.get("metadata", {})
        title = meta.get("youtube_title", "Viral Short")
        cat = meta.get("detected_category", "general").upper()
        spoken = meta.get("spoken_summary", "")

        msg = f"🚀 <b>Video Uploaded Successfully!</b>\n\n"
        msg += f"🎬 <b>Title:</b> {title}\n"
        msg += f"🏷️ <b>Category:</b> #{cat}\n"
        if spoken:
            msg += f"🎙️ <b>Spoken Audio:</b> <i>{spoken}</i>\n"
        msg += f"🔗 <b>Source:</b> {result.get('url')}\n\n"

        if result.get("youtube"):
            msg += f"🔴 <b>YouTube Shorts:</b>\n{result['youtube'].get('url')}\n\n"
        elif result.get("youtube_error"):
            msg += f"🔴 <b>YouTube:</b> ❌ Failed ({result.get('youtube_error')[:100]})\n\n"

        if result.get("instagram"):
            msg += f"🟣 <b>Instagram Reel:</b>\n{result['instagram'].get('url')}\n\n"

        return msg
    else:
        err = result.get('error') or result.get('youtube_error') or "Unknown error"
        return (
            f"❌ <b>Upload Failed</b>\n\n"
            f"🔗 <b>Link:</b> {result.get('url')}\n"
            f"⚠️ <b>Error:</b> {err[:250]}"
        )

def main():
    print("=" * 65)
    print("🚀 Social Media Auto-Poster v2.0 Starting...")
    print("=" * 65)

    token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '').strip()

    if not token:
        print("❌ TELEGRAM_BOT_TOKEN is missing!")
        return

    # 1. Listen from Telegram Bot
    print("\n[TELEGRAM] Checking for links...")
    raw_tg = get_new_links(token, chat_id)
    links = [{"url": l, "source": "Telegram"} for l in raw_tg]

    # 2. Listen from Instagram Dummy Account DMs (if configured)
    if os.environ.get('INSTA_DM_USERNAME', '').strip():
        print("\n[INSTAGRAM DM] Checking dummy account DMs...")
        raw_dm = get_new_links_from_dm()
        links += [{"url": l, "source": "Instagram DM (Dummy Box)"} for l in raw_dm]

    print(f"\n📊 Total new links to process: {len(links)}")

    if not links:
        print("No new links found. Exiting.")
        return

    for item in links:
        res = process_reel(item['url'], item['source'])
        msg = build_telegram_message(res)
        send_notification(token, chat_id, msg)
        print("   📬 Sent status notification to Telegram.")

    print("\n" + "=" * 65)
    print("🏁 All processing finished successfully.")
    print("=" * 65)

if __name__ == "__main__":
    main()
