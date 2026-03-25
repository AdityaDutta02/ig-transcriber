/**
 * Cloudflare Worker — YouTube Transcript Fetcher
 *
 * Fetches captions directly from YouTube's page HTML.
 * Runs on Cloudflare's edge network (not blocked by YouTube).
 *
 * Usage: GET /?v=VIDEO_ID&lang=en
 * Returns: { videoId, language, segments: [{start, dur, text}], fullText }
 */

const YOUTUBE_URL = 'https://www.youtube.com/watch';
const USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36';

export default {
  async fetch(request) {
    const url = new URL(request.url);

    // CORS preflight
    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: corsHeaders() });
    }

    const videoId = url.searchParams.get('v');
    if (!videoId) {
      return json({ error: 'Missing ?v=VIDEO_ID parameter' }, 400);
    }

    const lang = url.searchParams.get('lang') || 'en';

    try {
      // Step 1: Fetch YouTube page to get player response
      const pageResp = await fetch(`${YOUTUBE_URL}?v=${videoId}`, {
        headers: { 'User-Agent': USER_AGENT },
      });
      if (!pageResp.ok) {
        return json({ error: `YouTube returned HTTP ${pageResp.status}` }, 502);
      }
      const html = await pageResp.text();

      // Step 2: Extract ytInitialPlayerResponse JSON
      const playerMatch = html.match(/ytInitialPlayerResponse\s*=\s*(\{.+?\})\s*;/s);
      if (!playerMatch) {
        return json({ error: 'Could not extract player response from YouTube page' }, 502);
      }

      let playerResponse;
      try {
        playerResponse = JSON.parse(playerMatch[1]);
      } catch {
        return json({ error: 'Failed to parse player response JSON' }, 502);
      }

      // Step 3: Find caption tracks
      const tracks = playerResponse?.captions?.playerCaptionsTracklistRenderer?.captionTracks;
      if (!tracks || tracks.length === 0) {
        return json({
          error: 'no_captions',
          message: 'No caption tracks available for this video',
          videoId,
        }, 404);
      }

      // Pick requested language or fall back to first available
      const track = tracks.find(t => t.languageCode.startsWith(lang)) || tracks[0];

      // Step 4: Fetch caption XML
      const captionResp = await fetch(track.baseUrl);
      if (!captionResp.ok) {
        return json({ error: `Caption fetch returned HTTP ${captionResp.status}` }, 502);
      }
      const xml = await captionResp.text();

      // Step 5: Parse XML into segments
      const segments = [];
      const regex = /<text start="([\d.]+)" dur="([\d.]+)"[^>]*>([\s\S]*?)<\/text>/g;
      let m;
      while ((m = regex.exec(xml)) !== null) {
        segments.push({
          start: parseFloat(m[1]),
          dur: parseFloat(m[2]),
          text: decodeEntities(m[3]),
        });
      }

      const fullText = segments.map(s => s.text).join(' ');

      return json({
        videoId,
        language: track.languageCode,
        languageName: track.name?.simpleText || track.languageCode,
        segmentCount: segments.length,
        segments,
        fullText,
      });
    } catch (err) {
      return json({ error: `Internal error: ${err.message}` }, 500);
    }
  },
};

function decodeEntities(str) {
  return str
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/\n/g, ' ')
    .trim();
}

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json', ...corsHeaders() },
  });
}
