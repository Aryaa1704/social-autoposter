"""Instagram Reel video downloader using yt-dlp."""
import os
import re
import uuid
import yt_dlp

def extract_reel_url(text):
    patterns = [
        r'https?://(?:www\.)?instagram\.com/reel/[\w-]+/?[^\s]*',
        r'https?://(?:www\.)?instagram\.com/reels/[\w-]+/?[^\s]*',
        r'https?://(?:www\.)?instagram\.com/p/[\w-]+/?[^\s]*',
        r'https?://(?:www\.)?instagram\.com/share/[\w-]+/?[^\s]*',
        r'https?://(?:www\.)?youtube\.com/shorts/[\w-]+[^\s]*',
        r'https?://youtu\.be/[\w-]+[^\s]*',
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0).split('?')[0].rstrip('/')
    return None

def download_video(url, output_dir="downloads"):
    os.makedirs(output_dir, exist_ok=True)
    filename = uuid.uuid4().hex
    output_template = os.path.join(output_dir, f"{filename}.%(ext)s")

    ydl_opts = {
        'outtmpl': output_template,
        'format': 'best[ext=mp4]/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'socket_timeout': 30,
        'retries': 3,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        downloaded_file = ydl.prepare_filename(info)

    if not os.path.exists(downloaded_file):
        mp4_path = os.path.join(output_dir, f"{filename}.mp4")
        if os.path.exists(mp4_path):
            downloaded_file = mp4_path
        else:
            raise FileNotFoundError(f"Download failed: {downloaded_file}")

    return downloaded_file

