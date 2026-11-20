/**
 * Cloudflare Worker: Telegram Webhook -> Instant GitHub Actions Trigger
 * 
 * Whenever you send any Instagram Reel or YouTube Short link to your Telegram bot,
 * this worker catches the webhook and fires GitHub repository_dispatch,
 * starting your workflow within 1-2 seconds!
 * 
 * How to setup:
 * 1. Create a free worker on dash.cloudflare.com -> Workers & Pages -> Create Worker
 * 2. Paste this code and save & deploy.
 * 3. In Settings -> Variables, add:
 *    - GITHUB_PAT = your github personal access token (repo permissions)
 *    - GITHUB_REPO = Aryaa1704/social-autoposter
 * 4. Set Telegram Webhook in browser:
 *    https://api.telegram.org/bot<YOUR_TELEGRAM_BOT_TOKEN>/setWebhook?url=<YOUR_WORKER_URL>
 */

export default {
  async fetch(request, env) {
    if (request.method !== 'POST') {
      return new Response('Telegram Webhook Trigger is Live!', { status: 200 });
    }

    try {
      const update = await request.json();
      const message = update.message || update.channel_post;
      const text = message ? (message.text || message.caption || '') : '';

      // Check if message contains a reel or short link
      if (text.includes('instagram.com') || text.includes('youtube.com') || text.includes('youtu.be')) {
        const repo = env.GITHUB_REPO || 'Aryaa1704/social-autoposter';
        const pat = env.GITHUB_PAT;

        if (!pat) {
          return new Response('Missing GITHUB_PAT env variable', { status: 500 });
        }

        // Trigger GitHub Actions workflow instantly via repository_dispatch
        const ghResponse = await fetch(`https://api.github.com/repos/${repo}/dispatches`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${pat}`,
            'User-Agent': 'Cloudflare-Worker-Telegram-Trigger',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            event_type: 'telegram_link',
            client_payload: {
              url: text,
              sender: message.from ? message.from.username : 'user'
            }
          })
        });

        const success = (ghResponse.status === 204);
        return new Response(JSON.stringify({ success, status: ghResponse.status }), {
          headers: { 'Content-Type': 'application/json' }
        });
      }

      return new Response(JSON.stringify({ ok: true, note: 'No video link detected' }), {
        headers: { 'Content-Type': 'application/json' }
      });
    } catch (err) {
      return new Response(JSON.stringify({ error: err.message }), {
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  }
};
