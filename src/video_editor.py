"""
Video Editor & Optimizer Module
Cleans metadata, applies subtle anti-copyright speed shift (1.02x),
and extracts the best high-contrast thumbnail frame using FFmpeg.
"""
import os
import subprocess
import uuid

def is_ffmpeg_available():
    try:
        res = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return res.returncode == 0
    except Exception:
        return False

def optimize_video(input_path):
    """
    Cleans metadata and applies slight 1.02x speed adjustment
    to make the digital footprint unique.
    """
    if not is_ffmpeg_available():
        print("   ⚠️ FFmpeg not found, skipping video re-encoding.")
        return input_path

    out_dir = os.path.dirname(input_path)
    output_path = os.path.join(out_dir, f"opt_{os.path.basename(input_path)}")

    # FFmpeg command:
    # 1. Clean metadata (-map_metadata -1)
    # 2. 1.02x speed shift (video setpts + audio atempo)
    # 3. Fast encode H.264 + AAC with Instagram & YouTube compliance (yuv420p + faststart)
    cmd = [
        "ffmpeg", "-y",
        "-i", input_path,
        "-filter:v", "setpts=PTS/1.02",
        "-filter:a", "atempo=1.02",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-movflags", "+faststart",
        "-map_metadata", "-1",
        output_path
    ]

    try:
        print("   🎬 FFmpeg: Stripping metadata & applying 1.02x anti-fingerprint filter...")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
        if res.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            print("   ✅ Video optimized and fresh footprint generated.")
            try:
                import shutil
                orig_meta = f"{input_path}.meta.json"
                if os.path.exists(orig_meta):
                    shutil.copyfile(orig_meta, f"{output_path}.meta.json")
            except Exception:
                pass
            try:
                os.remove(input_path)
            except Exception:
                pass
            return output_path
        else:
            print(f"   ⚠️ FFmpeg optimization failed, using original: {res.stderr.decode()[:150]}")
            return input_path
    except Exception as e:
        print(f"   ⚠️ Video optimization error ({e}), proceeding with original.")
        return input_path

def extract_thumbnail_frame(video_path, timestamp_sec=1.5):
    """Extracts a sharp frame at given timestamp as thumbnail."""
    if not is_ffmpeg_available():
        return None

    out_dir = os.path.dirname(video_path)
    thumb_path = os.path.join(out_dir, f"thumb_{uuid.uuid4().hex[:8]}.jpg")

    cmd = [
        "ffmpeg", "-y",
        "-ss", str(timestamp_sec),
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        thumb_path
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30)
        if res.returncode == 0 and os.path.exists(thumb_path) and os.path.getsize(thumb_path) > 0:
            return thumb_path
    except Exception:
        pass
    return None
