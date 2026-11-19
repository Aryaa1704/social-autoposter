"""Telegram listener with robust extraction and debug logs."""
import os
import json
import re
import requests

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'state', 'telegram_state.json')

def _get_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {"offset": 0, "processed_urls": []}

def _save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)

def extract_url(text):
    if not text:
        return None
    patterns = [
        r'https?://[^\s]*instagram\.com/(?:reel|reels|p|share)/[^\s]+',
        r'https?://[^\s]*instagram\.com/[^\s]+',
        r'https?://[^\s]*youtube\.com/shorts/[^\s]+',
        r'https?://youtu\.be/[^\s]+',
    ]
    for p in patterns:
        m = re.search(p, text)
        if m:
            clean = m.group(0).split('?')[0].rstrip('/')
            return clean
    return None

def get_new_links(token, chat_id):
    token = token.strip()
    target_chat_id = str(chat_id).strip()
    state = _get_state()

    print(f"Connecting to Telegram Bot API (configured chat_id: {target_chat_id})...")
    try:
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        r = requests.get(url, params={"offset": state["offset"], "timeout": 10}, timeout=15).json()
    except Exception as e:
        print(f"Telegram API request failed: {e}")
        return []

    if not r.get("ok"):
        print(f"Telegram API error response: {r}")
        return []

    updates = r.get("result", [])
    print(f"Telegram returned {len(updates)} update(s).")

    new_links = []
    for u in updates:
        state["offset"] = u["update_id"] + 1
        msg = u.get("message") or u.get("channel_post") or u.get("edited_message") or {}
        
        # Check text or caption
        text = msg.get("text") or msg.get("caption") or ""
        sender_chat_id = str(msg.get("chat", {}).get("id", "")).strip()
        sender_username = msg.get("chat", {}).get("username", "unknown")

        print(f"Processing message from chat_id: '{sender_chat_id}' (@{sender_username})")

        # Verify chat_id if provided
        if target_chat_id and sender_chat_id != target_chat_id:
            print(f"  -> Skipped: Chat ID mismatch! Configured: '{target_chat_id}', Actual: '{sender_chat_id}'")
            continue

        url_found = extract_url(text)
        if not url_found:
            print(f"  -> Skipped: No valid Instagram/YouTube link found in text: '{text[:80]}'")
            continue

        if url_found in state.get("processed_urls", []):
            print(f"  -> Skipped: Link already processed earlier: {url_found}")
            continue

        print(f"  -> SUCCESS! Found new link: {url_found}")
        new_links.append(url_found)
        state["processed_urls"].append(url_found)

    state["processed_urls"] = state.get("processed_urls", [])[-500:]
    _save_state(state)
    return new_links

def send_notification(token, chat_id, text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{token.strip()}/sendMessage",
            data={"chat_id": str(chat_id).strip(), "text": text, "parse_mode": "HTML"},
            timeout=15
        )
    except Exception as e:
        print(f"Failed to send Telegram notification: {e}")
