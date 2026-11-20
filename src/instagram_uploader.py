"""Instagram Reels Uploader with Multi-Account Category Routing."""
import os
import time
import requests

def _upload_to_temp_hosting(video_path):
    with open(video_path, 'rb') as f:
        res = requests.post('https://tmpfiles.org/api/v1/upload', files={'file': ('video.mp4', f, 'video/mp4')}, timeout=120)
    if res.status_code == 200:
        url = res.json()['data']['url']
        return url.replace('tmpfiles.org/', 'tmpfiles.org/dl/')
    raise Exception(f"Temp hosting upload failed: {res.text}")

def get_instagram_credentials(category="general"):
    """
    Routes video to specific Instagram account based on niche:
    - gaming     -> INSTAGRAM_ACCESS_TOKEN_GAMING, INSTAGRAM_USER_ID_GAMING
    - tech_facts -> INSTAGRAM_ACCESS_TOKEN_FACTS, INSTAGRAM_USER_ID_FACTS
    - comedy     -> INSTAGRAM_ACCESS_TOKEN_COMEDY, INSTAGRAM_USER_ID_COMEDY
    Fallback     -> INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID (Main Account)
    """
    cat_key = category.upper().replace('-', '_')
    token = os.environ.get(f"INSTAGRAM_ACCESS_TOKEN_{cat_key}", '').strip()
    uid = os.environ.get(f"INSTAGRAM_USER_ID_{cat_key}", '').strip()
    if token and uid:
        print(f"   🎯 Routing to specialized Instagram account: {cat_key}")
        return token, uid

    return os.environ.get('INSTAGRAM_ACCESS_TOKEN', '').strip(), os.environ.get('INSTAGRAM_USER_ID', '').strip()

def upload_to_instagram(video_path, caption, hashtags, category="general"):
    access_token, user_id = get_instagram_credentials(category)
    if not access_token or not user_id:
        raise ValueError("Instagram credentials (token or user_id) missing for this category!")

    video_url = _upload_to_temp_hosting(video_path)
    tags_str = ' '.join(f'#{h.strip("#")}' for h in hashtags[:25])
    full_caption = f"{caption}\n\n{tags_str}"

    res = requests.post(
        f"https://graph.facebook.com/v21.0/{user_id}/media",
        data={'media_type': 'REELS', 'video_url': video_url, 'caption': full_caption[:2200], 'share_to_feed': 'true', 'access_token': access_token},
        timeout=60
    )
    if res.status_code != 200:
        raise Exception(f"Container failed: {res.text}")

    container_id = res.json()['id']
    for _ in range(30):
        s_res = requests.get(f"https://graph.facebook.com/v21.0/{container_id}", params={'fields': 'status_code', 'access_token': access_token}, timeout=30)
        code = s_res.json().get('status_code', '')
        if code == 'FINISHED':
            break
        elif code == 'ERROR':
            raise Exception("Instagram processing failed")
        time.sleep(10)

    pub = requests.post(f"https://graph.facebook.com/v21.0/{user_id}/media_publish", data={'creation_id': container_id, 'access_token': access_token}, timeout=60)
    if pub.status_code != 200:
        raise Exception(f"Publish failed: {pub.text}")

    media_id = pub.json()['id']
    return {'media_id': media_id, 'url': f"https://www.instagram.com", 'category': category}
