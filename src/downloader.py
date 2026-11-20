"""High-Quality Video Downloader using yt-dlp with anti-bot bypass."""
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
    Download video in highest available single stream MP4 (1080p).
    Bypasses datacenter anti-bot verification using mobile/embedded player clients,
    TLS browser impersonation, and optional cookies.
    """
    os.makedirs(output_dir, exist_ok=True)
    filename = uuid.uuid4().hex
    output_template = os.path.join(output_dir, f"{filename}.%(ext)s")

    # Setup optional cookies if passed via secret
    cookie_file = None
    yt_cookies = os.environ.get('YOUTUBE_COOKIES', '').strip()
    if yt_cookies:
        cookie_file = os.path.join(output_dir, f"yt_cookies_{filename}.txt")
        try:
            with open(cookie_file, 'w', encoding='utf-8') as f:
                f.write(yt_cookies)
            print("   🍪 Using YouTube cookies for authentication.")
        except Exception:
            cookie_file = None

    # Player client strategies to rotate through if datacenter IP is challenged
    client_strategies = [
        ['mweb', 'android'],
        ['ios'],
        ['tv_embedded', 'android'],
        ['android', 'ios', 'web_creator']
    ]

    last_error = None
    downloaded_file = None
    info = {}

    for attempt, client_list in enumerate(client_strategies, 1):
        try:
            ydl_opts = {
                'outtmpl': output_template,
                'format': 'best',
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'socket_timeout': 30,
                'retries': 5,
                'extractor_args': {
                    'youtube': {
                        'player_client': client_list,
                        'player_skip': ['webpage', 'configs']
                    }
                },
                'http_headers': {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
                    'Accept-Language': 'en-US,en;q=0.9',
                }
            }

            if cookie_file and os.path.exists(cookie_file):
                ydl_opts['cookiefile'] = cookie_file

            # Enable browser impersonation if curl-cffi is available
            try:
                import curl_cffi  # noqa: F401
                ydl_opts['impersonate'] = 'chrome'
            except Exception:
                pass

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                downloaded_file = ydl.prepare_filename(info)

            if downloaded_file and os.path.exists(downloaded_file):
                break

            # Search in directory if filename differs
            matches = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith(filename) and not f.endswith('.txt') and not f.endswith('.json')]
            if matches:
                downloaded_file = matches[0]
                break

        except Exception as e:
            last_error = e
            err_str = str(e).lower()
            if "confirm you’re not a bot" in err_str or "sign in" in err_str:
                print(f"   ⚠️ Client strategy {client_list} hit bot check, trying next client strategy ({attempt}/{len(client_strategies)})...")
                continue
            else:
                # If it's not a bot error, retry or raise
                continue

    # Cleanup temp cookie file
    if cookie_file and os.path.exists(cookie_file):
        try:
            os.remove(cookie_file)
        except Exception:
            pass

    if not downloaded_file or not os.path.exists(downloaded_file):
        matches = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith(filename) and not f.endswith('.txt') and not f.endswith('.json')]
        if matches:
            downloaded_file = matches[0]
        else:
            raise Exception(f"Download failed after all anti-bot strategies: {last_error}")

    size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)
    print(f"   📦 Downloaded high quality video: {size_mb:.2f} MB")

    # Save metadata companion file for text LLMs
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
