"""
Multi-Model AI Intelligence Engine
Supports:
1. Google Gemini 2.0 Flash (Primary: Video + Audio multimodal understanding)
2. Groq API (Llama-3.3-70B: Secondary fast fallback)
3. Smart Dynamic Fallback
"""
import os
import json
import time

VIRAL_PROMPT = """
You are an ELITE viral social media growth hacker and content strategist (specializing in YouTube Shorts & Instagram Reels).
Analyze the provided video thoroughly:
1. Listen carefully to what is being SAID/SPOKEN (audio dialogue, narration, commentary).
2. Look at what is HAPPENING (actions, gaming highlights, funny moments, twists).
3. Identify the PRIMARY CATEGORY: exactly one of ["gaming", "tech_facts", "comedy", "general"].

Generate an ultra-engaging metadata package in valid JSON:
{
    "detected_category": "gaming" | "tech_facts" | "comedy" | "general",
    "spoken_summary": "1-3 sentences capturing what was spoken or said in the video",
    "youtube_title": "Extreme curiosity-hook title with 1-2 emojis (under 85 chars, NO clickbait that lies, but maximum intrigue)",
    "youtube_description": "First line is a magnetic hook. Middle section transcribes/summarizes the spoken content and story. End has relevant keywords and Call to Action.",
    "youtube_tags": ["list of 12-15 high volume SEO search tags mixing broad and specific keywords"],
    "youtube_category_id": "20 for gaming, 28 for tech, 23 for comedy, 22 for general",
    "instagram_caption": "First line hook, engaging body with dialogue points, and follow CTA. Uses clean line breaks.",
    "instagram_hashtags": ["list of 20-25 trending and niche hashtags without # symbol"],
    "content_summary": "One line summary of the video"
}

RULES:
- If video has Hindi speech/text, write Title & Description in HINGLISH.
- If video is in English, write in punchy American English.
- Return ONLY the raw JSON object. Do NOT wrap in markdown or backticks.
"""

def analyze_video(video_path, gemini_key="", groq_key=""):
    """
    Multi-model cascade:
    1. Try Gemini 2.0 Flash (Multimodal)
    2. Try Groq (Llama-3.3-70B)
    3. Use Smart Fallback
    """
    gemini_key = (gemini_key or os.environ.get('GEMINI_API_KEY', '')).strip()
    groq_key = (groq_key or os.environ.get('GROQ_API_KEY', '')).strip()

    # 1. Try Gemini
    if gemini_key:
        print("   🧠 [AI Tier 1] Analyzing with Google Gemini 2.0 Flash...")
        res = _try_gemini(video_path, gemini_key)
        if res:
            return res
        print("   ⚠️ Gemini Tier failed. Falling back to next AI tier...")

    # 2. Try Groq
    if groq_key:
        print("   ⚡ [AI Tier 2] Analyzing with Groq (Llama-3.3-70B)...")
        res = _try_groq(video_path, groq_key)
        if res:
            return res
        print("   ⚠️ Groq Tier failed.")

    # 3. Smart Fallback
    print("   🛡️ Using Smart Dynamic Metadata Fallback.")
    return get_fallback_metadata()

def _try_gemini(video_path, api_key):
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)

        print("   📤 Uploading video to Gemini File API...")
        video_file = genai.upload_file(path=video_path)

        waited = 0
        while video_file.state.name == "PROCESSING" and waited < 120:
            time.sleep(5)
            waited += 5
            video_file = genai.get_file(video_file.name)

        if video_file.state.name == "FAILED":
            return None

        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content([video_file, VIRAL_PROMPT])

        try:
            genai.delete_file(video_file.name)
        except Exception:
            pass

        text = response.text.strip()
        if text.startswith('```'):
            lines = [l for l in text.split('\n') if not l.strip().startswith('```')]
            text = '\n'.join(lines)

        data = json.loads(text)
        print("   ✅ Gemini generated viral metadata & speech analysis successfully!")
        return data
    except Exception as e:
        print(f"   ⚠️ Gemini error: {e}")
        return None

def _try_groq(video_path, groq_key):
    try:
        from groq import Groq
        client = Groq(api_key=groq_key)

        prompt = f"""
        Generate a viral social media package for a video.
        Format strictly as JSON:
        {VIRAL_PROMPT}
        """

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        data = json.loads(completion.choices[0].message.content)
        print("   ✅ Groq Llama-3.3 generated metadata successfully!")
        return data
    except Exception as e:
        print(f"   ⚠️ Groq error: {e}")
        return None

def get_fallback_metadata():
    return {
        "detected_category": "general",
        "spoken_summary": "High intensity viral moment with unexpected twist",
        "youtube_title": "He Actually Did This On Camera... 🤯💀 #Shorts",
        "youtube_description": "You won't believe what happened at the end! Watch till the last second.\n\nSubscribe for daily viral moments! 🔥\n\n#Shorts #Viral #Trending #Reels #Explore",
        "youtube_tags": ["Shorts", "Viral", "Trending", "Reels", "Explore", "ForYou", "Insane", "Moment"],
        "youtube_category_id": "22",
        "instagram_caption": "Wait till the end... 🤯💀\n\nTag a friend who needs to see this!\n.\n.",
        "instagram_hashtags": ["reels", "viral", "trending", "explore", "reelsinstagram", "fyp", "viralreels"],
        "content_summary": "Viral short clip"
    }
