"""
Dynamic Multi-Model AI Rotation & Load Balancing Engine.
Features:
- Dynamic Round-Robin Rotation across runs (no single model gets burned by rate limits)
- State persistence in `src/state/ai_rotation.json` (cached across GitHub Actions runs)
- Cascading Multi-Tier Fallback: if selected provider fails, immediately tries next until success
- 15 Supported AI Providers (Groq, Gemini, OpenRouter, Cerebras, SambaNova, Together, DeepInfra,
  Fireworks, Mistral, GitHub Models, Hugging Face, Cohere, Cloudflare, Pollinations, Smart Fallback)
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
   - If gaming highlight/gameplay -> "gaming"
   - If science, tech, curious facts, AI, education -> "tech_facts"
   - If funny, prank, meme, comedy, relatable reel -> "comedy"
   - Otherwise -> "general"

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
- If Hindi speech, text, or context is detected, write Title, Spoken Summary & Description in energetic HINGLISH.
- If in English, write in punchy modern American English.
- Return ONLY the raw JSON object. Do NOT wrap in markdown, backticks or commentary.
"""

ROTATION_STATE_FILE = os.path.join(os.path.dirname(__file__), "state", "ai_rotation.json")

def _load_video_context(video_path):
    """Loads companion metadata file saved by downloader if present."""
    base_dir = os.path.dirname(video_path)
    base_name = os.path.basename(video_path)
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
    raw_text = re.sub(r'<think>.*?</think>', '', raw_text, flags=re.DOTALL).strip()
    if raw_text.startswith('```'):
        lines = [l for l in raw_text.split('\n') if not l.strip().startswith('```')]
        raw_text = '\n'.join(lines).strip()
    match = re.search(r'\{.*\}', raw_text, re.DOTALL)
    if match:
        raw_text = match.group(0)
    try:
        return json.loads(raw_text)
    except Exception:
        return None

def _get_configured_providers(video_path):
    """Returns list of all providers that have keys or require no key."""
    providers = []

    # 1. Google Gemini
    if os.environ.get('GEMINI_API_KEY', '').strip():
        providers.append(('gemini', 'Google Gemini 2.0 Flash', lambda ctx: _call_gemini(video_path, ctx)))

    # 2. Groq Cloud
    if os.environ.get('GROQ_API_KEY', '').strip():
        providers.append(('groq', 'Groq (Llama-3.1-8B)', lambda ctx: _call_openai_compatible(
            'Groq', 'https://api.groq.com/openai/v1/chat/completions',
            os.environ.get('GROQ_API_KEY').strip(), 'llama-3.1-8b-instant', ctx
        )))

    # 3. OpenRouter Free
    if os.environ.get('OPENROUTER_API_KEY', '').strip():
        providers.append(('openrouter', 'OpenRouter Free Models', lambda ctx: _call_openrouter(ctx)))

    # 4. Cerebras Cloud
    if os.environ.get('CEREBRAS_API_KEY', '').strip():
        providers.append(('cerebras', 'Cerebras (Llama-3.1-70B)', lambda ctx: _call_openai_compatible(
            'Cerebras', 'https://api.cerebras.ai/v1/chat/completions',
            os.environ.get('CEREBRAS_API_KEY').strip(), 'llama3.1-70b', ctx
        )))

    # 5. SambaNova Cloud
    if os.environ.get('SAMBANOVA_API_KEY', '').strip():
        providers.append(('sambanova', 'SambaNova (Llama-3.3-70B)', lambda ctx: _call_openai_compatible(
            'SambaNova', 'https://api.sambanova.ai/v1/chat/completions',
            os.environ.get('SAMBANOVA_API_KEY').strip(), 'Meta-Llama-3.3-70B-Instruct', ctx
        )))

    # 6. Hugging Face Inference
    hf_tok = os.environ.get('HF_TOKEN', '').strip() or os.environ.get('HUGGINGFACE_API_KEY', '').strip()
    if hf_tok:
        providers.append(('huggingface', 'Hugging Face (Qwen 2.5 72B)', lambda ctx: _call_huggingface(hf_tok, ctx)))

    # 7. Mistral AI
    if os.environ.get('MISTRAL_API_KEY', '').strip():
        providers.append(('mistral', 'Mistral AI (Mistral Small)', lambda ctx: _call_openai_compatible(
            'Mistral', 'https://api.mistral.ai/v1/chat/completions',
            os.environ.get('MISTRAL_API_KEY').strip(), 'mistral-small-latest', ctx
        )))

    # 8. Together AI
    if os.environ.get('TOGETHER_API_KEY', '').strip():
        providers.append(('together', 'Together AI (Llama 3.3 Turbo)', lambda ctx: _call_openai_compatible(
            'Together AI', 'https://api.together.xyz/v1/chat/completions',
            os.environ.get('TOGETHER_API_KEY').strip(), 'meta-llama/Llama-3.3-70B-Instruct-Turbo', ctx
        )))

    # 9. DeepInfra
    if os.environ.get('DEEPINFRA_API_KEY', '').strip():
        providers.append(('deepinfra', 'DeepInfra (Llama 3.3 70B)', lambda ctx: _call_openai_compatible(
            'DeepInfra', 'https://api.deepinfra.com/v1/openai/chat/completions',
            os.environ.get('DEEPINFRA_API_KEY').strip(), 'meta-llama/Llama-3.3-70B-Instruct', ctx
        )))

    # 10. Fireworks AI
    if os.environ.get('FIREWORKS_API_KEY', '').strip():
        providers.append(('fireworks', 'Fireworks AI (Llama 3.3 70B)', lambda ctx: _call_openai_compatible(
            'Fireworks', 'https://api.fireworks.ai/inference/v1/chat/completions',
            os.environ.get('FIREWORKS_API_KEY').strip(), 'accounts/fireworks/models/llama-v3p3-70b-instruct', ctx
        )))

    # 11. GitHub Models
    gh_tok = os.environ.get('GITHUB_MODELS_TOKEN', '').strip() or os.environ.get('GITHUB_TOKEN', '').strip()
    if gh_tok:
        providers.append(('github_models', 'GitHub Models (GPT-4o-mini)', lambda ctx: _call_openai_compatible(
            'GitHub Models', 'https://models.inference.ai.azure.com/chat/completions',
            gh_tok, 'gpt-4o-mini', ctx
        )))

    # 12. Cohere
    if os.environ.get('COHERE_API_KEY', '').strip():
        providers.append(('cohere', 'Cohere (Command-R)', lambda ctx: _call_cohere(os.environ.get('COHERE_API_KEY').strip(), ctx)))

    # 13. Cloudflare Workers AI
    cf_token = os.environ.get('CLOUDFLARE_API_TOKEN', '').strip()
    cf_acc = os.environ.get('CLOUDFLARE_ACCOUNT_ID', '').strip()
    if cf_token and cf_acc:
        providers.append(('cloudflare', 'Cloudflare Workers AI', lambda ctx: _call_cloudflare(cf_token, cf_acc, ctx)))

    # 14. Pollinations AI (100% Free Public AI, No API key needed)
    providers.append(('pollinations', 'Pollinations Public AI', lambda ctx: _call_pollinations(ctx)))

    return providers

def _get_rotated_providers(configured_providers):
    """Rotates providers round-robin based on state file so different model leads each run."""
    if not configured_providers:
        return []

    os.makedirs(os.path.dirname(ROTATION_STATE_FILE), exist_ok=True)
    last_index = 0
    if os.path.exists(ROTATION_STATE_FILE):
        try:
            with open(ROTATION_STATE_FILE, 'r', encoding='utf-8') as f:
                last_index = json.load(f).get('last_index', 0)
        except Exception:
            pass

    start_index = (last_index + 1) % len(configured_providers)
    rotated = configured_providers[start_index:] + configured_providers[:start_index]

    try:
        with open(ROTATION_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump({'last_index': start_index, 'leading_provider': rotated[0][0]}, f)
    except Exception:
        pass

    return rotated

def analyze_video(video_path):
    """
    Main Entrypoint:
    Rotates active AI models dynamically across runs,
    cascading through candidates until an AI produces valid viral metadata.
    """
    context = _load_video_context(video_path)
    configured = _get_configured_providers(video_path)
    rotated_chain = _get_rotated_providers(configured)

    print(f"\n🔄 [AI Orchestrator] {len(configured)} AI provider(s) active in rotation pool.")
    if rotated_chain:
        lead_name = rotated_chain[0][1]
        print(f"   🎲 Round-Robin Lead Model for this run: 🌟 {lead_name}")

    for idx, (p_id, p_name, runner) in enumerate(rotated_chain, 1):
        print(f"   👉 [Tier {idx}/{len(rotated_chain)}] Attempting: {p_name}...")
        try:
            res = runner(context)
            if res and isinstance(res, dict) and res.get('youtube_title'):
                print(f"   🎉 SUCCESS: {p_name} generated viral package!")
                return _enrich_metadata(res)
            print(f"   ⚠️ {p_name} returned incomplete result, falling back...")
        except Exception as e:
            print(f"   ⚠️ {p_name} failed ({e}), falling back...")

    print("   🛡️ [Final Fallback] Using Smart Dynamic Metadata Engine...")
    return _enrich_metadata(get_fallback_metadata(context))

def _enrich_metadata(res):
    """Guarantees full set of high-ranking viral hashtags and SEO search tags."""
    if not isinstance(res, dict):
        return res
    cat = res.get('detected_category', 'general').lower()
    default_tags = {
        'gaming': ['gaming', 'gamer', 'gameplay', 'clutch', 'bgmi', 'gta5', 'viralgaming', 'reels', 'fyp', 'trending', 'shorts'],
        'tech_facts': ['facts', 'tech', 'science', 'mindblown', 'didyouknow', 'ai', 'education', 'reels', 'fyp', 'trending', 'shorts'],
        'comedy': ['comedy', 'funny', 'meme', 'jokes', 'laugh', 'relatable', 'viralreels', 'reels', 'fyp', 'trending', 'shorts'],
        'general': ['viral', 'trending', 'explore', 'foryou', 'reels', 'fyp', 'instagram', 'shorts', 'daily']
    }
    cur_tags = res.get('instagram_hashtags', [])
    if not cur_tags or len(cur_tags) < 10:
        res['instagram_hashtags'] = list(dict.fromkeys(cur_tags + default_tags.get(cat, default_tags['general'])))[:25]

    cur_yt = res.get('youtube_tags', [])
    if not cur_yt or len(cur_yt) < 10:
        res['youtube_tags'] = list(dict.fromkeys(cur_yt + default_tags.get(cat, default_tags['general'])))[:15]
    return res

# -------------------------------------------------------------
# Provider Implementation Callers
# -------------------------------------------------------------

def _call_openai_compatible(provider_name, url, api_key, model, context, extra_headers=None):
    headers = {
        "Authorization": f"Bearer {api_key}" if api_key else "",
        "Content-Type": "application/json"
    }
    if extra_headers:
        headers.update(extra_headers)

    prompt = VIRAL_PROMPT_TEMPLATE.format(context=context)
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    res = requests.post(url, headers=headers, json=payload, timeout=35)
    if res.status_code == 200:
        data = res.json()
        content = data["choices"][0]["message"]["content"]
        return _clean_json_response(content)
    else:
        raise Exception(f"HTTP {res.status_code}: {res.text[:120]}")

def _call_gemini(video_path, context):
    api_key = os.environ.get('GEMINI_API_KEY', '').strip()
    import google.generativeai as genai
    genai.configure(api_key=api_key)

    prompt = VIRAL_PROMPT_TEMPLATE.format(context=context)
    video_file = None
    try:
        print("      📤 Uploading video to Gemini File API...")
        video_file = genai.upload_file(path=video_path)
        waited = 0
        while video_file.state.name == "PROCESSING" and waited < 120:
            time.sleep(5)
            waited += 5
            video_file = genai.get_file(video_file.name)
        if video_file.state.name == "FAILED":
            video_file = None
    except Exception as e:
        print(f"      ⚠️ Gemini File API upload note: {e}")
        video_file = None

    model = genai.GenerativeModel('gemini-2.0-flash')
    inputs = [video_file, prompt] if video_file else [prompt]
    response = model.generate_content(inputs)

    if video_file:
        try:
            genai.delete_file(video_file.name)
        except Exception:
            pass

    return _clean_json_response(response.text)

def _call_openrouter(context):
    api_key = os.environ.get('OPENROUTER_API_KEY', '').strip()
    headers = {
        "Authorization": f"Bearer {api_key}",
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
            r = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=35)
            if r.status_code == 200:
                parsed = _clean_json_response(r.json()["choices"][0]["message"]["content"])
                if parsed:
                    return parsed
        except Exception:
            continue
    raise Exception("All OpenRouter free models exhausted or unavailable.")

def _call_huggingface(hf_token, context):
    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": "application/json"
    }
    prompt = f"Return strictly JSON with social media metadata.\n{VIRAL_PROMPT_TEMPLATE.format(context=context)}"
    url = "https://router.huggingface.co/hf-inference/models/Qwen/Qwen2.5-72B-Instruct"
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 800, "return_full_text": False}
    }
    r = requests.post(url, headers=headers, json=payload, timeout=40)
    if r.status_code == 200:
        res_data = r.json()
        raw = res_data[0]["generated_text"] if isinstance(res_data, list) else str(res_data)
        return _clean_json_response(raw)
    raise Exception(f"HF status {r.status_code}: {r.text[:100]}")

def _call_cohere(api_key, context):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    prompt = VIRAL_PROMPT_TEMPLATE.format(context=context)
    payload = {
        "model": "command-r",
        "messages": [{"role": "user", "content": prompt}]
    }
    r = requests.post("https://api.cohere.com/v2/chat", headers=headers, json=payload, timeout=35)
    if r.status_code == 200:
        data = r.json()
        content = data.get("message", {}).get("content", [{}])[0].get("text", "")
        return _clean_json_response(content)
    raise Exception(f"Cohere status {r.status_code}: {r.text[:100]}")

def _call_cloudflare(token, account_id, context):
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    prompt = VIRAL_PROMPT_TEMPLATE.format(context=context)
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-3.1-70b-instruct"
    payload = {
        "messages": [{"role": "user", "content": prompt}]
    }
    r = requests.post(url, headers=headers, json=payload, timeout=40)
    if r.status_code == 200:
        data = r.json()
        res_text = data.get("result", {}).get("response", "")
        return _clean_json_response(res_text)
    raise Exception(f"Cloudflare status {r.status_code}: {r.text[:100]}")

def _call_pollinations(context):
    prompt = VIRAL_PROMPT_TEMPLATE.format(context=context)
    payload = {
        "model": "openai",
        "messages": [{"role": "user", "content": prompt}],
        "jsonMode": True
    }
    r = requests.post("https://text.pollinations.ai/openai/chat/completions", json=payload, timeout=35)
    if r.status_code == 200:
        content = r.json()["choices"][0]["message"]["content"]
        return _clean_json_response(content)
    raise Exception(f"Pollinations status {r.status_code}")

def get_fallback_metadata(context=""):
    """Context-Aware Smart Fallback Engine."""
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
