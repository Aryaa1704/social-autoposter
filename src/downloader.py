"""High-Quality Video Downloader using yt-dlp."""
import os
import re
import uuid
import yt_dlp

def extract_reel_url(text):
    if not text:
        return None
    patterns = [
        r'https?://[^\s]*instagram\.com/(?:reel|reels|p|share)/[^\s]+',
        r'https?://[^\s]*instagram\.com/[^\s]+',
        r'https?://[^\s]*youtube\.com/shorts/[^\s]+',
        r'https?://youtu\.be/[^\s]+',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0).split('?')[0].rstrip('/')
    return None

def download_video(url, output_dir="downloads"):
    """
    Download video in highest available single stream or merged MP4 (1080p).
    Includes anti-bot evasion for YouTube and fallback client rotation.
    """
    os.makedirs(output_dir, exist_ok=True)
    filename = uuid.uuid4().hex
    output_template = os.path.join(output_dir, f"{filename}.%(ext)s")

    # Check for YOUTUBE_COOKIES env
    cookie_path = None
    youtube_cookies = os.environ.get('YOUTUBE_COOKIES', '').strip()
    if youtube_cookies:
        cookie_path = os.path.join(output_dir, 'yt_cookies.txt')
        try:
            with open(cookie_path, 'w', encoding='utf-8') as f:
                f.write(youtube_cookies)
        except Exception as e:
            print(f"   ⚠️ Could not write cookies file: {e}")
            cookie_path = None

    is_youtube = ('youtube.com' in url or 'youtu.be' in url)

    # Multi-client fallback strategies for YouTube to bypass bot checks on datacenter IPs
    if is_youtube:
        strategies = [
            # Strategy 1: Default modern clients (uses visionos/web, handles separate video+audio streams)
            {
                'outtmpl': output_template,
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best',
                'merge_output_format': 'mp4',
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 30,
                'retries': 5,
            },
            # Strategy 2: Android client (reliable on datacenter IPs)
            {
                'outtmpl': output_template,
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best',
                'merge_output_format': 'mp4',
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 30,
                'retries': 3,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['android']
                    }
                }
            },
            # Strategy 3: iOS client
            {
                'outtmpl': output_template,
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best[ext=mp4]/best',
                'merge_output_format': 'mp4',
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 30,
                'retries': 3,
                'extractor_args': {
                    'youtube': {
                        'player_client': ['ios']
                    }
                }
            },
            # Strategy 4: Universal stream fallback (any single or merged format)
            {
                'outtmpl': output_template,
                'format': 'b/bv*+ba/best',
                'merge_output_format': 'mp4',
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 30,
                'retries': 3,
            }
        ]
    else:
        # Instagram or other platforms
        strategies = [
            {
                'outtmpl': output_template,
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 30,
                'retries': 5,
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
                    'Accept-Language': 'en-US,en;q=0.9',
                }
            },
            {
                'outtmpl': output_template,
                'format': 'best[ext=mp4]/best',
                'quiet': True,
                'no_warnings': True,
                'socket_timeout': 30,
                'retries': 3,
            }
        ]

    # Attach cookies if available to all strategies
    if cookie_path and os.path.exists(cookie_path):
        for s in strategies:
            s['cookiefile'] = cookie_path

    last_error = None
    info = None
    downloaded_file = None

    for idx, ydl_opts in enumerate(strategies, 1):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_file = ydl.prepare_filename(info)
                if os.path.exists(downloaded_file):
                    break
                # Search for file starting with filename in case extension differs
                matches = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith(filename)]
                if matches and os.path.exists(matches[0]):
                    downloaded_file = matches[0]
                    break
        except Exception as e:
            last_error = e
            print(f"   ⚠️ Download attempt {idx}/{len(strategies)} failed: {e}. Trying next strategy...")

    # Verify downloaded file
    if not downloaded_file or not os.path.exists(downloaded_file):
        matches = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith(filename)]
        if matches and os.path.exists(matches[0]):
            downloaded_file = matches[0]
        else:
            raise FileNotFoundError(f"Download failed after all anti-bot strategies: {last_error or 'file not found for ' + url}")

    size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)
    print(f"   📦 Downloaded high quality video: {size_mb:.2f} MB")

    if info:
        try:
            import json
            meta_file = f"{downloaded_file}.meta.json"
            with open(meta_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'title': info.get('title', ''),
                    'description': info.get('description', ''),
                    'tags': info.get('tags', []) or [],
                    'categories': info.get('categories', []) or []
                }, f)
        except Exception:
            pass

    return downloaded_file
