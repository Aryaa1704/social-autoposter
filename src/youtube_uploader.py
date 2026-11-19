"""YouTube Shorts Uploader."""
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials

def upload_to_youtube(video_path, title, description, tags, category_id="22"):
    credentials = Credentials(
        token=None,
        refresh_token=os.environ['YOUTUBE_REFRESH_TOKEN'],
        client_id=os.environ['YOUTUBE_CLIENT_ID'],
        client_secret=os.environ['YOUTUBE_CLIENT_SECRET'],
        token_uri='https://oauth2.googleapis.com/token',
    )
    youtube = build('youtube', 'v3', credentials=credentials)

    if not any(t.lower() in ('shorts', '#shorts') for t in tags):
        tags.append('Shorts')

    if '#Shorts' not in description and '#shorts' not in description:
        description += "\n\n#Shorts"

    body = {
        'snippet': {
            'title': title[:100],
            'description': description[:5000],
            'tags': tags[:15],
            'categoryId': category_id,
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
    return {'video_id': video_id, 'url': f"https://youtube.com/shorts/{video_id}", 'title': title}
