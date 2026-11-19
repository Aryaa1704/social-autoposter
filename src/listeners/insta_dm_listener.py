"""Instagram DM listener for dummy account."""
import os
import json

STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'state', 'insta_dm_state.json')
SESSION_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'state', 'insta_session.json')

def get_new_links_from_dm():
    u = os.environ.get('INSTA_DM_USERNAME')
    p = os.environ.get('INSTA_DM_PASSWORD')
    main_u = os.environ.get('INSTA_MAIN_USERNAME')
    if not u or not p: return []

    try:
        from instagrapi import Client
        cl = Client()
        if os.path.exists(SESSION_FILE):
            try:
                cl.load_settings(SESSION_FILE)
                cl.login(u, p)
            except Exception:
                cl.login(u, p)
        else:
            cl.login(u, p)
        os.makedirs(os.path.dirname(SESSION_FILE), exist_ok=True)
        cl.dump_settings(SESSION_FILE)

        threads = cl.direct_threads(amount=10)
        links = []
        for t in threads:
            if main_u and main_u not in [usr.username for usr in t.users]:
                continue
            for msg in cl.direct_messages(t.id, amount=10):
                url = None
                if msg.item_type == 'clip' and msg.clip and getattr(msg.clip, 'code', None):
                    url = f"https://www.instagram.com/reel/{msg.clip.code}/"
                elif msg.item_type == 'text' and 'instagram.com/reel/' in (msg.text or ''):
                    import re
                    m = re.search(r'https?://(?:www\.)?instagram\.com/reel/[\w-]+/?', msg.text)
                    if m: url = m.group(0).rstrip('/')
                if url: links.append(url)
        return list(set(links))
    except Exception as e:
        print(f"DM listener error: {e}")
        return []
