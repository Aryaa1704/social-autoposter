"""Telegram listener."""
import os
import json
import re
import requests

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'state', 'telegram_state.json')

def _get_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {"offset": 0, "processed_urls": []}

def _save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def extract_url(text):
    patterns = [r'https?://(?:www\.)?instagram\.com/reel/[\w-]+/?', r'https?://(?:www\.)?instagram\.com/p/[\w-]+/?', r'https?://(?:www\.)?instagram\.com/share/[\w-]+/?']
    for p in patterns:
        m = re.search(p, text)
        if m: return m.group(0).rstrip('/')
    return None

def get_new_links(token, chat_id):
    state = _get_state()
    try:
        r = requests.get(f"https://api.telegram.org/bot{token}/getUpdates", params={"offset": state["offset"], "timeout": 10}, timeout=15).json()
    except Exception:
        return []

    new_links = []
    for u in r.get("result", []):
        state["offset"] = u["update_id"] + 1
        msg = u.get("message", {})
        if str(msg.get("chat", {}).get("id", "")) != str(chat_id):
            continue
        url = extract_url(msg.get("text", ""))
        if url and url not in state["processed_urls"]:
            new_links.append(url)
            state["processed_urls"].append(url)

    state["processed_urls"] = state["processed_urls"][-200:]
    _save_state(state)
    return new_links

def send_notification(token, chat_id, text):
    try:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}, timeout=15)
    except Exception:
        pass
