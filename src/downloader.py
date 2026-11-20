"""High-Quality Video Downloader using yt-dlp with 1080p Full HD preference."""
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
    Download video in highest available quality (up to 1080p Full HD)
    with audio merged into MP4 format.
    """
    os.makedirs(output_dir, exist_ok=True)
    filename = uuid.uuid4().hex
    output_template = os.path.join(output_dir, f"{filename}.%(ext)s")

    ydl_opts = {
        'outtmpl': output_template,
        'format': 'best[ext=mp4]/bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'socket_timeout': 30,
        'retries': 5,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
        }
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        downloaded_file = ydl.prepare_filename(info)

    # In case format merger renamed to .mp4
    if not os.path.exists(downloaded_file):
        mp4_path = os.path.join(output_dir, f"{filename}.mp4")
        if os.path.exists(mp4_path):
            downloaded_file = mp4_path
        else:
            # Fallback to any file starting with filename
            matches = [os.path.join(output_dir, f) for f in os.listdir(output_dir) if f.startswith(filename)]
            if matches:
                downloaded_file = matches[0]
            else:
                raise FileNotFoundError(f"Download failed: file not found for {url}")

    size_mb = os.path.getsize(downloaded_file) / (1024 * 1024)
    print(f"   📦 Downloaded high quality video: {size_mb:.2f} MB")
    return downloaded_file

