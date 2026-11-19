"""One-time YouTube Token Setup."""
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
creds = flow.run_local_server(port=8080)
print("\nSave these to GitHub Secrets:")
print("YOUTUBE_REFRESH_TOKEN =", creds.refresh_token)
print("YOUTUBE_CLIENT_ID     =", creds.client_id)
print("YOUTUBE_CLIENT_SECRET =", creds.client_secret)
