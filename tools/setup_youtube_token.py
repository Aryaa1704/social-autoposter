import sys
import os
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

print("Starting OAuth flow...", flush=True)
flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)

# Get auth url
auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')
with open("auth_url.txt", "w", encoding="utf-8") as f:
    f.write(auth_url)

print(f"AUTH_URL_READY: {auth_url}", flush=True)

# Launch in browser using Windows shell
os.system(f'start "" "{auth_url}"')

# Listen for redirect
creds = flow.run_local_server(port=8080, open_browser=False)

output = f"""YOUTUBE_REFRESH_TOKEN={creds.refresh_token}
YOUTUBE_CLIENT_ID={creds.client_id}
YOUTUBE_CLIENT_SECRET={creds.client_secret}"""

print("\n" + "=" * 50, flush=True)
print(output, flush=True)
print("=" * 50, flush=True)

with open("youtube_tokens.txt", "w", encoding="utf-8") as f:
    f.write(output)

print("ALL_DONE_SUCCESS", flush=True)
