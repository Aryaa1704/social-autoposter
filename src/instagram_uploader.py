"""
Instagram Reels Uploader with Direct Meta Resumable Upload & Category Routing.
Features:
- Direct binary upload to Meta's rupload.facebook.com (no 3rd-party hosting dependency)
- Automatic fallback to hosted URL if direct upload is unsupported
- Detailed container status inspection (fields=status_code,status,error_message)
- Multi-Account Category Routing (Gaming, Tech/Facts, Comedy, Main)
"""
import os
import time
import requests

def _upload_to_temp_hosting(video_path):
    """Fallback public hosting if direct upload is not supported."""
    try:
        with open(video_path, 'rb') as f:
            res = requests.post('https://tmpfiles.org/api/v1/upload', files={'file': ('video.mp4', f, 'video/mp4')}, timeout=120)
        if res.status_code == 200:
            url = res.json()['data']['url']
            return url.replace('tmpfiles.org/', 'tmpfiles.org/dl/')
    except Exception as e:
        print(f"   ⚠️ Temp hosting failed: {e}")
    return None

def get_instagram_credentials(category="general"):
    """
    Routes video to specific Instagram account based on niche:
    - gaming     -> INSTAGRAM_ACCESS_TOKEN_GAMING, INSTAGRAM_USER_ID_GAMING
    - tech_facts -> INSTAGRAM_ACCESS_TOKEN_TECH_FACTS, INSTAGRAM_USER_ID_TECH_FACTS
    - comedy     -> INSTAGRAM_ACCESS_TOKEN_COMEDY, INSTAGRAM_USER_ID_COMEDY
    Fallback     -> INSTAGRAM_ACCESS_TOKEN, INSTAGRAM_USER_ID (Main Account)
    """
    cat_key = category.upper().replace('-', '_')
    token = os.environ.get(f"INSTAGRAM_ACCESS_TOKEN_{cat_key}", '').strip()
    uid = os.environ.get(f"INSTAGRAM_USER_ID_{cat_key}", '').strip()
    if token and uid:
        print(f"   🎯 Routing to specialized Instagram account: {cat_key} (ID: {uid})")
        return token, uid

    return os.environ.get('INSTAGRAM_ACCESS_TOKEN', '').strip(), os.environ.get('INSTAGRAM_USER_ID', '').strip()

def upload_to_instagram(video_path, caption, hashtags, category="general"):
    access_token, user_id = get_instagram_credentials(category)
    if not access_token or not user_id:
        raise ValueError("Instagram credentials (token or user_id) missing for this category!")

    tags_str = ' '.join(f'#{h.strip("#")}' for h in hashtags[:25])
    full_caption = f"{caption}\n\n{tags_str}".strip()[:2200]
    file_size = os.path.getsize(video_path)

    container_id = None

    # Method 1: Meta Resumable Upload (Direct Binary to Meta, 0 3rd party host issues)
    print("   📤 [Method 1] Initializing direct resumable upload with Meta Graph API...")
    try:
        init_res = requests.post(
            f"https://graph.facebook.com/v21.0/{user_id}/media",
            data={
                'upload_type': 'resumable',
                'media_type': 'REELS',
                'caption': full_caption,
                'share_to_feed': 'true',
                'access_token': access_token
            },
            timeout=60
        )
        if init_res.status_code == 200:
            init_data = init_res.json()
            container_id = init_data.get('id')
            upload_uri = init_data.get('uri') or f"https://rupload.facebook.com/ig-api-upload/v21.0/{container_id}"

            print(f"   📦 Streaming {file_size / (1024*1024):.2f} MB directly to Meta rupload servers...")
            headers = {
                "Authorization": f"OAuth {access_token}",
                "offset": "0",
                "file_size": str(file_size),
                "Content-Type": "application/octet-stream"
            }
            with open(video_path, 'rb') as f:
                up_res = requests.post(upload_uri, headers=headers, data=f, timeout=180)

            if up_res.status_code in (200, 201):
                print("   ✅ Direct binary upload to Meta succeeded!")
            else:
                print(f"   ⚠️ Direct binary upload status {up_res.status_code}: {up_res.text[:150]}")
                container_id = None
        else:
            print(f"   ⚠️ Resumable init response {init_res.status_code}: {init_res.text[:150]}")
    except Exception as e:
        print(f"   ⚠️ Resumable upload failed ({e}), falling back to hosted URL method...")
        container_id = None

    # Method 2: Hosted URL Fallback
    if not container_id:
        print("   🌐 [Method 2] Trying hosted video URL upload...")
        video_url = _upload_to_temp_hosting(video_path)
        if not video_url:
            raise Exception("Failed to upload video to temporary public hosting for Instagram.")

        res = requests.post(
            f"https://graph.facebook.com/v21.0/{user_id}/media",
            data={
                'media_type': 'REELS',
                'video_url': video_url,
                'caption': full_caption,
                'share_to_feed': 'true',
                'access_token': access_token
            },
            timeout=60
        )
        if res.status_code != 200:
            raise Exception(f"Container creation failed: {res.text}")
        container_id = res.json().get('id')

    # Step 3: Poll Meta Container Status until FINISHED
    print(f"   ⏳ Waiting for Meta to process Reel container ({container_id})...")
    for attempt in range(40):
        time.sleep(6)
        s_res = requests.get(
            f"https://graph.facebook.com/v21.0/{container_id}",
            params={'fields': 'status_code,status,error_message', 'access_token': access_token},
            timeout=30
        )
        if s_res.status_code != 200:
            print(f"      Polling note: status {s_res.status_code}")
            continue

        s_data = s_res.json()
        code = s_data.get('status_code', '')
        if code == 'FINISHED':
            print("   ✅ Reel processed and ready to publish!")
            break
        elif code == 'ERROR':
            err_msg = s_data.get('error_message') or s_data.get('status') or 'Meta encoding rejected'
            raise Exception(f"Instagram processing failed by Meta: {err_msg}")
        elif code in ('IN_PROGRESS', ''):
            pass

    # Step 4: Publish Reel
    print("   🚀 Publishing Reel to feed...")
    pub = requests.post(
        f"https://graph.facebook.com/v21.0/{user_id}/media_publish",
        data={'creation_id': container_id, 'access_token': access_token},
        timeout=60
    )
    if pub.status_code != 200:
        raise Exception(f"Publish failed: {pub.text}")

    media_id = pub.json().get('id')
    return {
        'media_id': media_id,
        'url': f"https://www.instagram.com/reel/",
        'category': category
    }
