"""Main Orchestrator."""
import os
import sys
from downloader import download_video
from ai_generator import analyze_video
from youtube_uploader import upload_to_youtube
from instagram_uploader import upload_to_instagram
from listeners.telegram_listener import get_new_links, send_notification
from listeners.insta_dm_listener import get_new_links_from_dm

def process_reel(url, source):
    result = {"url": url, "source": source, "success": False}
    try:
        video_path = download_video(url)
        meta = analyze_video(video_path, os.environ['GEMINI_API_KEY'])
        yt = upload_to_youtube(video_path, meta['youtube_title'], meta['youtube_description'], meta['youtube_tags'])
        ig = upload_to_instagram(video_path, meta['instagram_caption'], meta['instagram_hashtags'])
        try: os.remove(video_path)
        except Exception: pass
        result.update({"youtube": yt, "instagram": ig, "success": True, "metadata": meta})
    except Exception as e:
        result["error"] = str(e)
    return result

def main():
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')
    if not token or not chat_id:
        print("Missing Telegram keys")
        return

    links = [{"url": l, "source": "Telegram"} for l in get_new_links(token, chat_id)]
    links += [{"url": l, "source": "Instagram DM"} for l in get_new_links_from_dm()]

    if not links:
        print("No new links found.")
        return

    for item in links:
        res = process_reel(item['url'], item['source'])
        msg = f"Done! Uploaded to YT & Insta.\nURL: {res.get('url')}" if res['success'] else f"Failed: {res.get('error')}"
        send_notification(token, chat_id, msg)

if __name__ == "__main__":
    main()
