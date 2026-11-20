/**
 * Cloudflare Worker: Telegram Webhook -> Instant GitHub Actions Trigger
 * Hardcoded to Aryaa1704/social-autoposter to prevent any typo or space issues!
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
        // EXACT repository name with no spaces and proper hyphen
        const repo = 'Aryaa1704/social-autoposter';

        // Auto-sanitize PAT token
        let pat = (env.GITHUB_PAT || env.GITHUB_TOKEN || '').trim().replace(/^["']|["']$/g, '');

        if (!pat) {
          return new Response(JSON.stringify({ error: 'Missing GITHUB_PAT env variable in Cloudflare' }), { status: 500 });
        }

        // Trigger GitHub Actions workflow instantly via repository_dispatch
        const ghResponse = await fetch(`https://api.github.com/repos/${repo}/dispatches`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${pat}`,
            'User-Agent': 'Cloudflare-Worker-Telegram-Trigger',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
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

        const ghText = await ghResponse.text();
        const success = (ghResponse.status === 204);

        return new Response(JSON.stringify({
          success,
          status: ghResponse.status,
          repo_called: repo,
          github_response: ghText || 'OK'
        }), {
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
