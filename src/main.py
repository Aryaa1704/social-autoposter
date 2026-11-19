"""
Social Media Auto-Poster - Main Orchestrator
Independent upload handlers for YouTube and Instagram with full logging.
"""
import os
import sys
import traceback

from downloader import download_video
from ai_generator import analyze_video
from youtube_uploader import upload_to_youtube
from instagram_uploader import upload_to_instagram
from listeners.telegram_listener import get_new_links, send_notification
from listeners.insta_dm_listener import get_new_links_from_dm


def process_reel(url, source):
    print("\n" + "=" * 60)
    print(f"🎬 [START] Processing: {url}")
    print(f"   Source: {source}")
    print("=" * 60)

    result = {
        "url": url,
        "source": source,
        "youtube": None,
        "instagram": None,
        "success": False,
        "error": None
    }
    video_path = None

    try:
        # Step 1: Download
        print("\n📥 [1/4] Downloading video...")
        video_path = download_video(url)
        print(f"   ✅ Video downloaded: {video_path}")

        # Step 2: Gemini AI Analysis
        print("\n🤖 [2/4] Analyzing video with Gemini AI...")
        gemini_key = os.environ.get('GEMINI_API_KEY', '').strip()
        if not gemini_key:
            raise ValueError("GEMINI_API_KEY is not set in GitHub Secrets!")

        meta = analyze_video(video_path, gemini_key)
        result["metadata"] = meta
        print(f"   ✅ Title: {meta.get('youtube_title')}")
        print(f"   ✅ Summary: {meta.get('content_summary')}")

        # Step 3: YouTube Upload
        yt_refresh = os.environ.get('YOUTUBE_REFRESH_TOKEN', '').strip()
        if yt_refresh:
            print("\n🔴 [3/4] Uploading to YouTube Shorts...")
            try:
                yt = upload_to_youtube(
                    video_path,
                    meta.get('youtube_title', 'Awesome Short #Shorts'),
                    meta.get('youtube_description', ''),
                    meta.get('youtube_tags', ['Shorts']),
                    meta.get('youtube_category_id', '22')
                )
                result["youtube"] = yt
                print(f"   ✅ YouTube Upload SUCCESS: {yt.get('url')}")
            except Exception as e:
                print(f"   ❌ YouTube Upload FAILED: {e}")
                traceback.print_exc()
                result["youtube_error"] = str(e)
        else:
            print("\n🔴 [3/4] YouTube skipped (YOUTUBE_REFRESH_TOKEN not set)")

        # Step 4: Instagram Upload (Only if credentials provided)
        ig_token = os.environ.get('INSTAGRAM_ACCESS_TOKEN', '').strip()
        ig_user = os.environ.get('INSTAGRAM_USER_ID', '').strip()
        if ig_token and ig_user:
            print("\n🟣 [4/4] Uploading to Instagram Reels...")
            try:
                ig = upload_to_instagram(
                    video_path,
                    meta.get('instagram_caption', ''),
                    meta.get('instagram_hashtags', [])
                )
                result["instagram"] = ig
                print(f"   ✅ Instagram Upload SUCCESS: {ig.get('url')}")
            except Exception as e:
                print(f"   ❌ Instagram Upload FAILED: {e}")
                traceback.print_exc()
                result["instagram_error"] = str(e)
        else:
            print("\n🟣 [4/4] Instagram upload skipped (INSTAGRAM_ACCESS_TOKEN not configured)")

        # Success if at least one platform succeeded
        if result.get("youtube") or result.get("instagram"):
            result["success"] = True

    except Exception as e:
        print(f"\n💥 [PIPELINE ERROR]: {e}")
        traceback.print_exc()
        result["error"] = str(e)

    finally:
        # Cleanup temp video file
        if video_path and os.path.exists(video_path):
            try:
                os.remove(video_path)
                print("   🧹 Cleaned up temporary video file.")
            except Exception:
                pass

    return result


def build_telegram_message(result):
    if result.get("success"):
        meta = result.get("metadata", {})
        title = meta.get("youtube_title", "Viral Short")
        summary = meta.get("content_summary", "")

        msg = f"🚀 <b>Video Uploaded Successfully!</b>\n\n"
        msg += f"🎬 <b>Title:</b> {title}\n"
        if summary:
            msg += f"📝 <b>About:</b> {summary}\n"
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
            f"⚠️ <b>Error:</b> {err[:200]}"
        )


def main():
    print("=" * 60)
    print("🚀 Social Media Auto-Poster Starting...")
    print("=" * 60)

    token = os.environ.get('TELEGRAM_BOT_TOKEN', '').strip()
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '').strip()

    if not token:
        print("❌ TELEGRAM_BOT_TOKEN is missing!")
        return

    # Check Telegram
    print("\n[TELEGRAM] Checking for links...")
    raw_tg = get_new_links(token, chat_id)
    links = [{"url": l, "source": "Telegram"} for l in raw_tg]

    # Check Instagram DMs if configured
    if os.environ.get('INSTA_DM_USERNAME', '').strip():
        print("\n[INSTAGRAM DM] Checking dummy account DMs...")
        raw_dm = get_new_links_from_dm()
        links += [{"url": l, "source": "Instagram DM"} for l in raw_dm]

    print(f"\n📊 Total new links to process: {len(links)}")

    if not links:
        print("No new links found. Exiting.")
        return

    for item in links:
        res = process_reel(item['url'], item['source'])
        msg = build_telegram_message(res)
        send_notification(token, chat_id, msg)
        print("   📬 Sent status notification to Telegram.")

    print("\n" + "=" * 60)
    print("🏁 All processing finished successfully.")
    print("=" * 60)


if __name__ == "__main__":
    main()
