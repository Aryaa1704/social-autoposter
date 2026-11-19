"""Instagram DM listener for dummy account - captures reels from ANY user."""
import os
import json
import re

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'state', 'insta_dm_state.json')
SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'state', 'insta_session.json')

def _get_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"processed_urls": []}

def _save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)

def extract_url_from_text(text):
    if not text:
        return None
    patterns = [
        r'https?://(?:www\.)?instagram\.com/reel/[\w-]+/?',
        r'https?://(?:www\.)?instagram\.com/reels/[\w-]+/?',
        r'https?://(?:www\.)?instagram\.com/p/[\w-]+/?',
        r'https?://(?:www\.)?instagram\.com/share/[\w-]+/?',
        r'https?://(?:www\.)?youtube\.com/shorts/[\w-]+',
        r'https?://youtu\.be/[\w-]+',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            return m.group(0).rstrip('/')
    return None

def get_new_links_from_dm():
    """
    Check all DMs on the dummy account.
    Captures any reel or short sent by ANY user (you, friends, or anyone).
    """
    username = os.environ.get('INSTA_DM_USERNAME')
    password = os.environ.get('INSTA_DM_PASSWORD')
    if not username or not password:
        return []

    state = _get_state()
    processed = set(state.get("processed_urls", []))
    new_links = []

    try:
        from instagrapi import Client
        cl = Client()

        session_path = os.path.abspath(SESSION_FILE)
        if os.path.exists(session_path):
            try:
                cl.load_settings(session_path)
                cl.login(username, password)
            except Exception:
                cl = Client()
                cl.login(username, password)
        else:
            cl.login(username, password)

        os.makedirs(os.path.dirname(session_path), exist_ok=True)
        cl.dump_settings(session_path)

        # Check latest 20 conversations from ANYONE
        threads = cl.direct_threads(amount=20)

        for thread in threads:
            messages = cl.direct_messages(thread.id, amount=10)
            for msg in messages:
                reel_url = None

                # 1. Instagram Reel Clip Share
                if msg.item_type == 'clip' and msg.clip:
                    code = getattr(msg.clip, 'code', None)
                    if code:
                        reel_url = f"https://www.instagram.com/reel/{code}/"

                # 2. Media Share / Post Share
                elif msg.item_type in ('media_share', 'xma_media_share') and hasattr(msg, 'media_share') and msg.media_share:
                    code = getattr(msg.media_share, 'code', None)
                    if code:
                        reel_url = f"https://www.instagram.com/reel/{code}/"

                # 3. Direct URL in message text
                elif msg.item_type == 'text' and msg.text:
                    reel_url = extract_url_from_text(msg.text)

                # Check if it is a fresh un-processed reel
                if reel_url and reel_url not in processed:
                    new_links.append(reel_url)
                    processed.add(reel_url)

        # Save state (keep last 500 processed URLs)
        state["processed_urls"] = list(processed)[-500:]
        _save_state(state)

        return new_links

    except Exception as e:
        print(f"Instagram DM listener error: {e}")
        return []
