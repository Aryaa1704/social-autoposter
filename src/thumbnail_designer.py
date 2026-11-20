"""
Professional YouTube Shorts & Reels Thumbnail Designer.
Mimics viral top-tier creators (SuperSuper, PJ Explained, Alex Hormozi):
- 9:16 Vertical High-Contrast Frame
- Subtle Top Vignette Gradient Overlay
- Punchy 2-4 Word Curiosity Hook in Ultra-Bold Typography (Impact/Arial Black)
- Multi-color High-Contrast Stacking (Line 1: Pure White, Line 2: Vivid Red / Electric Yellow)
- Heavy 6px Black Stroke & 3D Drop Shadow
- Visual Color Vibrance & Sharpness Boost (+20%)
"""
import os
import subprocess
import uuid
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

SYSTEM_FONTS = [
    # Windows
    r"C:\Windows\Fonts\impact.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    r"C:\Windows\Fonts\ariblk.ttf",
    # Linux (GitHub Actions runners)
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]

def get_bold_font(size=86):
    """Finds the best bold font across Windows and Linux environments."""
    for path in SYSTEM_FONTS:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    try:
        return ImageFont.load_default()
    except Exception:
        return None

def extract_best_frame(video_path, timestamp_sec=1.5):
    """Extracts a high-resolution frame from the video using FFmpeg."""
    out_dir = os.path.dirname(video_path)
    temp_frame = os.path.join(out_dir, f"frame_{uuid.uuid4().hex[:8]}.jpg")
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(timestamp_sec),
        "-i", video_path,
        "-vframes", "1",
        "-q:v", "2",
        temp_frame
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
        if res.returncode == 0 and os.path.exists(temp_frame) and os.path.getsize(temp_frame) > 0:
            return temp_frame
    except Exception:
        pass
    return None

def split_hook_into_lines(hook_text, max_words_per_line=3):
    """Formats 2-5 words hook into 1 or 2 high-impact lines."""
    text = (hook_text or "").strip().upper()
    # Strip quotes
    text = text.replace('"', '').replace("'", "").strip()
    words = text.split()
    if not words:
        return ["VIRAL REVEAL!"]
    if len(words) <= 2:
        return [" ".join(words)]
    if len(words) == 3:
        return [" ".join(words[:2]), words[2]]
    # 4 or more words: split into two balanced lines
    mid = len(words) // 2
    return [" ".join(words[:mid]), " ".join(words[mid:])]

def create_pro_thumbnail(video_path, hook_text, output_path=None):
    """
    Creates a top-tier viral thumbnail with bold text overlay.
    """
    raw_frame = extract_best_frame(video_path, timestamp_sec=1.5)
    if not raw_frame or not os.path.exists(raw_frame):
        return None

    if not output_path:
        out_dir = os.path.dirname(video_path)
        output_path = os.path.join(out_dir, f"pro_thumb_{uuid.uuid4().hex[:8]}.jpg")

    try:
        img = Image.open(raw_frame).convert("RGB")
        target_w, target_h = 1080, 1920

        # Resize & crop to 9:16 vertical canvas
        img_ratio = img.width / float(img.height)
        target_ratio = target_w / float(target_h)

        if img_ratio > target_ratio:
            # Wider than 9:16 -> crop sides
            new_w = int(img.height * target_ratio)
            left = (img.width - new_w) // 2
            img = img.crop((left, 0, left + new_w, img.height))
        else:
            # Taller -> crop top/bottom
            new_h = int(img.width / target_ratio)
            top = (img.height - new_h) // 2
            img = img.crop((0, top, img.width, top + new_h))

        img = img.resize((target_w, target_h), Image.Resampling.LANCZOS)

        # 1. Image Enhancement: Boost Contrast (+15%) and Color Vibrance (+20%)
        contrast_enhancer = ImageEnhance.Contrast(img)
        img = contrast_enhancer.enhance(1.15)
        color_enhancer = ImageEnhance.Color(img)
        img = color_enhancer.enhance(1.20)
        sharp_enhancer = ImageEnhance.Sharpness(img)
        img = sharp_enhancer.enhance(1.25)

        # 2. Add Top Dark Gradient Overlay (so text pops regardless of background)
        overlay = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
        d_overlay = ImageDraw.Draw(overlay)
        gradient_h = 500
        for y in range(gradient_h):
            # Smooth cubic fade out
            alpha = int(220 * (1.0 - (y / float(gradient_h)) ** 1.4))
            d_overlay.line([(0, y), (target_w, y)], fill=(0, 0, 0, alpha))

        # Bottom slight vignette
        for y in range(target_h - 250, target_h):
            prog = (y - (target_h - 250)) / 250.0
            alpha = int(160 * prog)
            d_overlay.line([(0, y), (target_w, y)], fill=(0, 0, 0, alpha))

        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        # 3. Typography Hook Layout
        font = get_bold_font(size=86)
        lines = split_hook_into_lines(hook_text)

        colors = ["#FFFFFF", "#FF2A2A"]  # Line 1: Pure White, Line 2: Vivid Crimson Red
        if len(lines) == 1:
            colors = ["#FFFFFF"]

        y_start = 140 if len(lines) > 1 else 160
        line_spacing = 115

        for i, line in enumerate(lines):
            y = y_start + (i * line_spacing)
            col = colors[i % len(colors)]

            # 3D Drop Shadow (offset +6px)
            draw.text((target_w // 2 + 5, y + 6), line, font=font, fill="#000000", anchor="mm")

            # Heavy Black Outline / Stroke (6px) + Bright Text
            draw.text(
                (target_w // 2, y),
                line,
                font=font,
                fill=col,
                anchor="mm",
                stroke_width=6,
                stroke_fill="#000000"
            )

        img.save(output_path, "JPEG", quality=95)
        print(f"   🖼️ [Pro Thumbnail Designer] Rendered viral poster hook: '{' '.join(lines)}'")
        return output_path

    except Exception as e:
        print(f"   ⚠️ Pro Thumbnail generation error ({e}), using raw frame.")
        return raw_frame
    finally:
        if raw_frame and os.path.exists(raw_frame) and raw_frame != output_path:
            try:
                os.remove(raw_frame)
            except Exception:
                pass
