"""Gemini AI Video Analysis with robust error handling and fallback."""
import os
import json
import time

GEMINI_PROMPT = """
You are an expert social media content strategist. Watch the provided video completely.
Analyze what is happening in the video (topic, mood, action, meme, gameplay, facts, etc.).
Generate fresh, engaging and viral metadata for YouTube Shorts and Instagram Reels.

Return ONLY a valid JSON object with EXACTLY these fields:
{
    "youtube_title": "Engaging click-worthy title with emojis (max 90 chars)",
    "youtube_description": "SEO description with natural keywords and call to action (3-5 lines)",
    "youtube_tags": ["tag1", "tag2", "up to 12 tags"],
    "youtube_category_id": "22",
    "instagram_caption": "Engaging Instagram caption with emojis and hook",
    "instagram_hashtags": ["viral", "trending", "up to 20 hashtags without # symbol"],
    "content_summary": "1 line summary of video"
}
Return ONLY JSON. Do not include markdown or backticks.
"""

def analyze_video(video_path, api_key):
    api_key = (api_key or "").strip()
    if not api_key:
        print("   ⚠️ No Gemini API key provided. Using fallback metadata.")
        return get_fallback_metadata()

    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)

        print("   📤 Uploading video to Gemini...")
        video_file = genai.upload_file(path=video_path)

        waited = 0
        while video_file.state.name == "PROCESSING" and waited < 120:
            time.sleep(5)
            waited += 5
            video_file = genai.get_file(video_file.name)

        if video_file.state.name == "FAILED":
            raise Exception("Gemini video processing state returned FAILED")

        print("   🧠 Asking Gemini 2.0 Flash to generate title & tags...")
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content([video_file, GEMINI_PROMPT])

        try:
            genai.delete_file(video_file.name)
        except Exception:
            pass

        text = response.text.strip()
        if text.startswith('```'):
            lines = [l for l in text.split('\n') if not l.strip().startswith('```')]
            text = '\n'.join(lines)

        data = json.loads(text)
        print("   ✅ Gemini analysis complete!")
        return data

    except Exception as e:
        print(f"   ⚠️ Gemini AI failed ({e}). Switching to Smart Fallback metadata so upload continues!")
        return get_fallback_metadata()

def get_fallback_metadata():
    return {
        "youtube_title": "Wait for the End! 🤯🔥 #Shorts",
        "youtube_description": "Watch till the end! Like, share and subscribe for more daily viral shorts. 🔥\n\n#Shorts #Viral #Trending #Reels",
        "youtube_tags": ["Shorts", "Viral", "Trending", "Reels", "Explore", "ForYou"],
        "youtube_category_id": "22",
        "instagram_caption": "Wait for it... 🤯🔥 Follow for more daily reels!\n.",
        "instagram_hashtags": ["reels", "viral", "trending", "explore", "reelsinstagram", "fyp", "viralreels"],
        "content_summary": "Daily Viral Video"
    }
