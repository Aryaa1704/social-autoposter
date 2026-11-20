"""
YouTube Shorts Uploader with Multi-Channel Category Routing
and Custom Thumbnail Support.
"""
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

def get_channel_token(category="general"):
    """
    Routes video to specific channel if configured:
    - gaming     -> YOUTUBE_REFRESH_TOKEN_GAMING
    - tech_facts -> YOUTUBE_REFRESH_TOKEN_FACTS
    - comedy     -> YOUTUBE_REFRESH_TOKEN_COMEDY
    Fallback     -> YOUTUBE_REFRESH_TOKEN (Main Channel)
    """
    cat_key = f"YOUTUBE_REFRESH_TOKEN_{category.upper().replace('-', '_')}"
    token = os.environ.get(cat_key, '').strip()
    if token:
        print(f"   🎯 Routing to specialized channel: {cat_key}")
        return token
    return os.environ.get('YOUTUBE_REFRESH_TOKEN', '').strip()

def upload_to_youtube(video_path, title, description, tags, category_id="22", category="general", thumbnail_path=None):
    refresh_token = get_channel_token(category)
    if not refresh_token:
        raise ValueError("No YouTube refresh token found for this channel!")

    client_id = os.environ.get('YOUTUBE_CLIENT_ID', '').strip()
    client_secret = os.environ.get('YOUTUBE_CLIENT_SECRET', '').strip()

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri='https://oauth2.googleapis.com/token',
    )
    youtube = build('youtube', 'v3', credentials=credentials)

    # Ensure #Shorts tag & viral hashtags in description
    if not any(t.lower() in ('shorts', '#shorts') for t in tags):
        tags.append('Shorts')

    tag_hash_str = ' '.join(f"#{t.strip('#')}" for t in tags[:10])
    if tag_hash_str not in description:
        description += f"\n\n{tag_hash_str}"

    body = {
        'snippet': {
            'title': title[:100],
            'description': description[:5000],
            'tags': tags[:15],
            'categoryId': str(category_id),
        },
        'status': {
            'privacyStatus': 'public',
            'selfDeclaredMadeForKids': False,
        }
    }

    media = MediaFileUpload(video_path, mimetype='video/mp4', resumable=True)
    request = youtube.videos().insert(part='snippet,status', body=body, media_body=media)

    response = None
    while response is None:
        status, response = request.next_chunk()

    video_id = response['id']
    video_url = f"https://youtube.com/shorts/{video_id}"

    # Try setting custom thumbnail if extracted
    if thumbnail_path and os.path.exists(thumbnail_path):
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype='image/jpeg')
            ).execute()
            print("   🖼️ Set high-action thumbnail frame!")
        except Exception as e:
            # Custom thumbnails require verified phone on YouTube channel
            pass

    return {
        'video_id': video_id,
        'url': video_url,
        'title': title,
        'category': category
    }
