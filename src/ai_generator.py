"""
Multi-Model AI Intelligence Engine with Cascading Fallback.
Supported Providers:
1. Google Gemini 2.0 Flash (Multimodal Video & Audio Understanding)
2. Groq Cloud (Llama-3.3-70B - Lightning Fast 500 T/s)
3. OpenRouter Free Models (DeepSeek R1, Llama 3.3, Mistral 7B)
4. Hugging Face Inference API (Qwen 2.5 72B / Llama 3.2)
5. Mistral AI (Mistral Small)
6. Together AI (Llama 3.3 Turbo)
7. Smart Dynamic Fallback (Context-Aware)
"""
import os
import json
import re
import time
import requests

VIRAL_PROMPT_TEMPLATE = """
You are an ELITE viral social media strategist specializing in YouTube Shorts and Instagram Reels.
Analyze the video content and context provided below:

{context}

TASKS:
1. Determine the EXACT content category: one of ["gaming", "tech_facts", "comedy", "general"].
2. If gaming highlight/gameplay -> "gaming"
3. If science, tech, curious facts, AI, education -> "tech_facts"
4. If funny, prank, meme, comedy, relatable reel -> "comedy"
5. Otherwise -> "general"

Generate an ultra-engaging metadata package in valid JSON:
{{
    "detected_category": "gaming" | "tech_facts" | "comedy" | "general",
    "spoken_summary": "1-3 sentences capturing what was spoken/done in the video",
    "youtube_title": "Extreme curiosity-hook title with 1-2 emojis (under 85 chars, no fake clickbait, maximum intrigue)",
    "youtube_description": "First line is a magnetic hook. Middle section explains the story or spoken dialogue. End has Call to Action and keywords.",
    "youtube_tags": ["Shorts", "Viral", "Trending", "tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10"],
    "youtube_category_id": "20 for gaming, 28 for tech_facts, 23 for comedy, 22 for general",
    "instagram_caption": "First line hook with dialogue points and follow CTA. Clean line breaks.",
    "instagram_hashtags": ["reels", "viral", "trending", "explore", "tag1", "tag2", "tag3", "tag4", "tag5", "tag6", "tag7", "tag8", "tag9", "tag10", "tag11", "tag12"],
    "content_summary": "One line summary of the video"
}}

LANGUAGE RULES:
- If video has Hindi speech, text, or context, write Title, Spoken Summary & Description in energetic HINGLISH.
- If in English, write in punchy modern American English.
- Return ONLY the raw JSON object. Do NOT wrap in markdown or backticks.
"""

def _load_video_context(video_path):
    """Loads companion metadata file saved by downloader if present."""
    base_dir = os.path.dirname(video_path)
    base_name = os.path.basename(video_path)
    # Check for direct meta file or original name meta file
    for candidate in [
        f"{video_path}.meta.json",
        os.path.join(base_dir, f"{base_name.replace('opt_', '')}.meta.json")
    ]:
        if os.path.exists(candidate):
            try:
                with open(candidate, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return f"Title: {data.get('title', '')}\nDescription: {data.get('description', '')[:500]}\nTags: {', '.join(data.get('tags', []))}"
            except Exception:
                pass
    return f"File: {base_name}"

def _clean_json_response(raw_text):
    """Strips markdown code blocks, think tags, and extracts valid JSON."""
    if not raw_text:
        return None
    # Remove DeepSeek <think>...</think> blocks if present
    raw_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()
    if raw_text.startswith('```'):
        lines = [l for l in raw_text.split('\n') if not l.strip().startswith('```')]
        raw_text = '\n'.join(lines).strip()
    # Find outer JSON braces
    match = re.search(r'\{.*\}', raw_text, re.DOTALL)
    if match:
        raw_text = match.group(0)
    try:
        return json.loads(raw_text)
    except Exception:
        return None

def analyze_video(video_path):
    """
    Multi-model cascade:
    1. Google Gemini 2.0 Flash
    2. Groq Cloud (Llama-3.3-70B)
    3. OpenRouter Free Models
    4. Hugging Face Inference
    5. Mistral AI
    6. Together AI
    7. Smart Dynamic Fallback
    """
    context = _load_video_context(video_path)

    # Tier 1: Google Gemini 2.0 Flash
    gemini_key = os.environ.get('GEMINI_API_KEY', '').strip()
    if gemini_key:
        print("   🧠 [AI Tier 1] Trying Google Gemini 2.0 Flash...")
        res = _try_gemini(video_path, gemini_key, context)
        if res:
            return res
        print("   ⚠️ Gemini Tier failed. Cascading to next AI provider...")

    # Tier 2: Groq Cloud (Llama-3.3-70B)
    groq_key = os.environ.get('GROQ_API_KEY', '').strip()
    if groq_key:
        print("   ⚡ [AI Tier 2] Trying Groq Cloud (Llama-3.3-70B)...")
        res = _try_groq(groq_key, context)
        if res:
            return res
        print("   ⚠️ Groq Tier failed. Cascading to next AI provider...")

    # Tier 3: OpenRouter (Free models)
    openrouter_key = os.environ.get('OPENROUTER_API_KEY', '').strip()
    if openrouter_key:
        print("   🌐 [AI Tier 3] Trying OpenRouter Free Models...")
        res = _try_openrouter(openrouter_key, context)
        if res:
            return res
        print("   ⚠️ OpenRouter Tier failed. Cascading to next AI provider...")

    # Tier 4: Hugging Face Inference
    hf_token = os.environ.get('HF_TOKEN', '').strip() or os.environ.get('HUGGINGFACE_API_KEY', '').strip()
    if hf_token:
        print("   🤗 [AI Tier 4] Trying Hugging Face Inference API...")
        res = _try_huggingface(hf_token, context)
        if res:
            return res
        print("   ⚠️ Hugging Face Tier failed. Cascading to next AI provider...")

    # Tier 5: Mistral AI
    mistral_key = os.environ.get('MISTRAL_API_KEY', '').strip()
    if mistral_key:
        print("   🌪️ [AI Tier 5] Trying Mistral AI...")
        res = _try_mistral(mistral_key, context)
        if res:
            return res
        print("   ⚠️ Mistral Tier failed.")

    # Tier 6: Together AI
    together_key = os.environ.get('TOGETHER_API_KEY', '').strip()
    if together_key:
        print("   🤝 [AI Tier 6] Trying Together AI...")
        res = _try_together(together_key, context)
        if res:
            return res
        print("   ⚠️ Together AI Tier failed.")

    # Tier 7: Smart Dynamic Fallback
    print("   🛡️ [AI Fallback] Using Smart Dynamic Metadata Engine...")
    return get_fallback_metadata(context)

def _try_gemini(video_path, api_key, context):
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)

        prompt = VIRAL_PROMPT_TEMPLATE.format(context=context)

        # Upload video to Gemini File API for real audiovisual analysis
        video_file = None
        try:
            print("   📤 Uploading video to Gemini File API...")
            video_file = genai.upload_file(path=video_path)
            waited = 0
            while video_file.state.name == "PROCESSING" and waited < 120:
                time.sleep(5)
                waited += 5
                video_file = genai.get_file(video_file.name)
            if video_file.state.name == "FAILED":
                video_file = None
        except Exception as e:
            print(f"   ⚠️ Gemini File API upload note: {e}")
            video_file = None

        model = genai.GenerativeModel('gemini-2.0-flash')
        inputs = [video_file, prompt] if video_file else [prompt]
        response = model.generate_content(inputs)

        if video_file:
            try:
                genai.delete_file(video_file.name)
            except Exception:
                pass

        parsed = _clean_json_response(response.text)
        if parsed:
            print("   ✅ Google Gemini 2.0 Flash generated viral package successfully!")
            return parsed
    except Exception as e:
        print(f"   ⚠️ Gemini exception: {e}")
    return None

def _try_groq(groq_key, context):
    try:
        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }
        prompt = VIRAL_PROMPT_TEMPLATE.format(context=context)
        payload = {
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "response_format": {"type": "json_object"}
        }
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=35)
        if r.status_code == 200:
            content = r.json()["choices"][0]["message"]["content"]
            parsed = _clean_json_response(content)
            if parsed:
                print("   ✅ Groq (Llama-3.3-70B) generated viral package successfully!")
                return parsed
        else:
            print(f"   ⚠️ Groq status {r.status_code}: {r.text[:120]}")
    except Exception as e:
        print(f"   ⚠️ Groq exception: {e}")
    return None

def _try_openrouter(openrouter_key, context):
    try:
        headers = {
            "Authorization": f"Bearer {openrouter_key}",
            "HTTP-Referer": "https://github.com/Aryaa1704/social-autoposter",
            "X-Title": "Social Auto-Poster",
            "Content-Type": "application/json"
        }
        prompt = VIRAL_PROMPT_TEMPLATE.format(context=context)
        free_models = [
            "meta-llama/llama-3.3-70b-instruct:free",
            "deepseek/deepseek-r1:free",
            "mistralai/mistral-7b-instruct:free",
            "google/gemini-2.0-flash-exp:free"
        ]
        for model in free_models:
            try:
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7
                }
                r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=40)
                if r.status_code == 200:
                    content = r.json()["choices"][0]["message"]["content"]
                    parsed = _clean_json_response(content)
                    if parsed:
                        print(f"   ✅ OpenRouter ({model}) generated viral package successfully!")
                        return parsed
            except Exception:
                continue
    except Exception as e:
        print(f"   ⚠️ OpenRouter exception: {e}")
    return None

def _try_huggingface(hf_token, context):
    try:
        headers = {
            "Authorization": f"Bearer {hf_token}",
            "Content-Type": "application/json"
        }
        prompt = f"Return strictly JSON with social media metadata.\n{VIRAL_PROMPT_TEMPLATE.format(context=context)}"
        url = "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-72B-Instruct"
        payload = {
            "inputs": prompt,
            "parameters": {"max_new_tokens": 800, "return_full_text": False}
        }
        r = requests.post(url, headers=headers, json=payload, timeout=40)
        if r.status_code == 200:
            res_data = r.json()
            raw_text = res_data[0]["generated_text"] if isinstance(res_data, list) else str(res_data)
            parsed = _clean_json_response(raw_text)
            if parsed:
                print("   ✅ Hugging Face generated viral package successfully!")
                return parsed
    except Exception as e:
        print(f"   ⚠️ Hugging Face exception: {e}")
    return None

def _try_mistral(mistral_key, context):
    try:
        headers = {
            "Authorization": f"Bearer {mistral_key}",
            "Content-Type": "application/json"
        }
        prompt = VIRAL_PROMPT_TEMPLATE.format(context=context)
        payload = {
            "model": "mistral-small-latest",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        r = requests.post("https://api.mistral.ai/v1/chat/completions", headers=headers, json=payload, timeout=35)
        if r.status_code == 200:
            content = r.json()["choices"][0]["message"]["content"]
            parsed = _clean_json_response(content)
            if parsed:
                print("   ✅ Mistral AI generated viral package successfully!")
                return parsed
        else:
            print(f"   ⚠️ Mistral status {r.status_code}: {r.text[:120]}")
    except Exception as e:
        print(f"   ⚠️ Mistral exception: {e}")
    return None

def _try_together(together_key, context):
    try:
        headers = {
            "Authorization": f"Bearer {together_key}",
            "Content-Type": "application/json"
        }
        prompt = VIRAL_PROMPT_TEMPLATE.format(context=context)
        payload = {
            "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        r = requests.post("https://api.together.xyz/v1/chat/completions", headers=headers, json=payload, timeout=35)
        if r.status_code == 200:
            content = r.json()["choices"][0]["message"]["content"]
            parsed = _clean_json_response(content)
            if parsed:
                print("   ✅ Together AI generated viral package successfully!")
                return parsed
    except Exception as e:
        print(f"   ⚠️ Together AI exception: {e}")
    return None

def get_fallback_metadata(context=""):
    """Smart Dynamic Fallback that infers category and hooks from context."""
    text_lower = (context or "").lower()

    if any(k in text_lower for k in ["game", "gaming", "gta", "minecraft", "free fire", "bgmi", "pubg", "clutch", "headshot"]):
        category = "gaming"
        cat_id = "20"
        title = "Level 999 IQ Gaming Moment... No Way! 😱🎮 #Shorts"
        caption = "Wait for the impossible clutch at the end! 🎮🔥\n\nDrop your IGN in comments!\n.\n."
        tags = ["Shorts", "Gaming", "Gameplay", "Clutch", "Gamer", "BGMI", "GTA5", "Viral"]
    elif any(k in text_lower for k in ["fact", "science", "ai", "tech", "iphone", "did you know", "mind blowing", "space"]):
        category = "tech_facts"
        cat_id = "28"
        title = "99% People Don't Know This Mindblowing Fact! 🤯🧠 #Shorts"
        caption = "You won't believe how this works in real life! 🧠⚡\n\nDid you already know this?\n.\n."
        tags = ["Shorts", "Facts", "Tech", "Mindblown", "DidYouKnow", "Science", "Knowledge"]
    elif any(k in text_lower for k in ["funny", "comedy", "prank", "laugh", "meme", "relatable", "joke"]):
        category = "comedy"
        cat_id = "23"
        title = "Bro Thought Nobody Was Looking... 😂💀 #Shorts"
        caption = "I can't stop laughing at this! 😂💀\n\nTag that one friend!\n.\n."
        tags = ["Shorts", "Comedy", "Funny", "Meme", "Laugh", "Relatable", "Trending"]
    else:
        category = "general"
        cat_id = "22"
        title = "He Actually Did This On Camera... 🤯💀 #Shorts"
        caption = "Wait till the end... 🤯💀\n\nTag a friend who needs to see this!\n.\n."
        tags = ["Shorts", "Viral", "Trending", "Reels", "Explore", "ForYou", "Insane", "Moment"]

    return {
        "detected_category": category,
        "spoken_summary": "High intensity viral moment with unexpected twist",
        "youtube_title": title,
        "youtube_description": f"You won't believe what happened at the end! Watch till the last second.\n\nSubscribe for daily viral moments! 🔥\n\n#{category.capitalize()} #Shorts #Viral #Trending",
        "youtube_tags": tags,
        "youtube_category_id": cat_id,
        "instagram_caption": caption,
        "instagram_hashtags": ["reels", "viral", "trending", "explore", "reelsinstagram", "fyp", category],
        "content_summary": "Viral short clip"
    }
