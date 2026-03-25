# ig-transcriber — Project Status & Tech Debt

> Last updated: 2026-03-25
> Deployed at: https://transcribe.studioionique.com
> Hosting: Render (free tier, Python web service)

---

## What This App Does

Streamlit web app that transcribes YouTube and Instagram videos. User pastes a URL, gets back a text transcript + optional SRT/VTT captions. Supports single URLs and batch CSV processing.

**Tech stack:** Python 3.11, Streamlit, Groq Whisper Large v3, yt-dlp, Render.com

---

## Current Architecture (as of 2026-03-25)

### YouTube Transcription Flow

```
YouTube URL
  → Tier 1: Cloudflare Worker (fetches captions via edge network)
      ✅ Works sometimes, free (100K req/day)
      ❌ YouTube returns 429 for many requests — Cloudflare edge IPs
         are also flagged by YouTube's datacenter detection
  → Tier 2: Supadata API (managed transcript service)
      ✅ WORKS RELIABLY — confirmed in production
      ✅ Supports lang=en parameter for English transcripts
      ✅ Has AI fallback for videos without captions
      ⚠️  100 free credits/month, then $9/mo for 1,000
  → Tier 3: yt-dlp + RapidAPI (legacy, last resort)
      ❌ yt-dlp blocked by YouTube datacenter IP detection
      ❌ youtube-mp36 RapidAPI CDN returns 404 from server IPs
      ❌ Effectively non-functional for YouTube on Render
```

### Instagram Transcription Flow

```
Instagram URL
  → yt-dlp downloads audio (works for public reels)
  → Groq Whisper Large v3 transcribes audio
  → If yt-dlp fails: RapidAPI fallback (4 configurable endpoints)
```

### Key Components

| File | Lines | Purpose |
|------|-------|---------|
| `app.py` | 431 | Streamlit UI, orchestrates download → transcribe flow |
| `src/downloader.py` | 476 | yt-dlp download with retry, RapidAPI fallback (Instagram + YouTube legacy) |
| `src/youtube_transcriber.py` | 154 | Cloudflare Worker (Tier 1) + Supadata (Tier 2) for YouTube |
| `src/transcriber.py` | 404 | Groq Whisper API integration, audio compression |
| `src/rapidapi_downloader.py` | 453 | RapidAPI fallback for Instagram + YouTube (legacy) |
| `src/browser_download.py` | 124 | Browser-side Cobalt download (UNUSED — Cobalt requires JWT now) |
| `src/captions.py` | 326 | SRT/VTT caption generation from segments |
| `src/auth.py` | 328 | Google OAuth + email/password authentication |
| `src/csv_parser.py` | 384 | Batch CSV upload and processing |
| `src/config.py` | 170 | Pydantic settings, YAML config loading |
| `src/utils.py` | 276 | URL validation, platform detection, video ID extraction |
| `youtube-transcript-worker/` | — | Cloudflare Worker (JS) for YouTube captions |

### Environment Variables (Render)

| Var | Required | Purpose |
|-----|----------|---------|
| `GROQ_API_KEY` | Yes | Groq Whisper transcription API |
| `SUPADATA_API_KEY` | Yes (for YouTube) | Supadata transcript API (Tier 2) |
| `TRANSCRIPT_WORKER_URL` | Yes (for YouTube) | Cloudflare Worker URL (Tier 1) |
| `RAPIDAPI_KEY` | No | RapidAPI fallback (Instagram) |
| `RAPIDAPI_USER` | No | RapidAPI CDN auth (unused for YouTube now) |
| `AUTH_CREDENTIALS` | No | Email/password auth pairs |
| `GOOGLE_CLIENT_ID` | No | Google OAuth |
| `GOOGLE_CLIENT_SECRET` | No | Google OAuth |
| `APP_URL` | No | OAuth redirect URL |

---

## What Works

- **YouTube transcription via Supadata** — confirmed working, returns English text with segments
- **Instagram download + transcription** — yt-dlp works for public reels, Groq transcribes
- **Batch CSV processing** — upload CSV with URLs, get transcripts for all
- **SRT/VTT caption generation** — from transcript segments
- **Authentication** — Google OAuth + email/password gate
- **Streamlit UI** — clean single-page interface with sidebar controls
- **Render deployment** — auto-deploys from GitHub main branch
- **Cloudflare Worker** — deployed and functional, but YouTube rate-limits it

---

## Tech Debt & Known Issues

### Critical

1. **Cloudflare Worker gets 429 from YouTube** — YouTube flags Cloudflare edge IPs the same as datacenter IPs. Worker works for some videos/edge nodes but fails for many. Supadata is the actual reliable path.

2. **Supadata free tier is only 100/month** — production usage will need the $9/mo plan. No way around this — YouTube blocks all cloud IPs, only managed services with residential proxies work.

3. **`src/browser_download.py` is dead code** — Cobalt public instances now require JWT authentication. This file was created for a browser-side download approach but was abandoned. Should be deleted.

### Important

4. **`src/downloader.py` still has YouTube RapidAPI fallback code** — The YouTube path in `download_video()` (yt-dlp + youtube-mp36 RapidAPI) is dead code for YouTube on Render. It only works for Instagram. The YouTube-specific RapidAPI code in `rapidapi_downloader.py` (`download_youtube_mp3()`) should be removed.

5. **`.env.example` is outdated** — Missing `TRANSCRIPT_WORKER_URL`, `SUPADATA_API_KEY`. Still references removed features.

6. **No codebase index** — Per project conventions, `codebase_index.md` should exist in memory for fast navigation.

7. **Multiple files over 400 lines** — `downloader.py` (476), `rapidapi_downloader.py` (453), `app.py` (431), `transcriber.py` (404). Per code standards, files >500 lines must be split.

### Minor / Cleanup

8. **`youtube-transcript-api` was removed from requirements but old `youtube_transcriber.py` used it** — The file was fully rewritten, but the old code referencing `youtube-transcript-api` still exists in git history if needed.

9. **PO token server code fully removed** — `build.sh` and `start.sh` are now minimal. Node.js/npm removed from `packages.txt`. The `.pot-server/` directory may still exist on Render's filesystem from old builds.

10. **`src/pipeline.py`, `src/progress.py`, `src/storage.py` are stubs** — 10 lines each, placeholder files for future features.

11. **Config duplication** — Both `config.json` and `config.yaml` exist in `config/`, plus `rapidapi_endpoints.json` and `rapidapi_endpoints.yaml`. Should consolidate to one format.

---

## Approaches Tried & Failed (YouTube)

Documenting for context — do not re-attempt these.

| Approach | Why It Failed |
|----------|---------------|
| yt-dlp direct | YouTube blocks Render's datacenter IP at network level |
| yt-dlp + cookies | Cookies expire, don't help with IP-level blocks |
| yt-dlp + PO token server (bgutil) | PO tokens don't overcome IP-level blocks from datacenter |
| yt-dlp + JS runtime (node) | Same — IP blocked before JS challenges matter |
| youtube-mp36 RapidAPI | CDN (`123tokyo.xyz`) blocks datacenter IPs with 404 |
| youtube-transcript-api (Python) | YouTube blocks Render's IP from transcript API too |
| Cobalt API (server-side) | Public instances require JWT auth now |
| Cobalt API (browser-side) | Same JWT requirement, plus Streamlit component complexity |
| Cloudflare Worker | YouTube returns 429 to Cloudflare edge IPs too |

**What works:** Managed services with residential proxy infrastructure (Supadata, Scrapingdog, etc.) are the only reliable approach from cloud-hosted apps.

---

## Deployment

### Render
- **Service:** `ig-transcriber` (web service, free tier)
- **Build:** `bash build.sh` (just `pip install`)
- **Start:** `bash start.sh` (just `streamlit run app.py`)
- **Auto-deploy:** On push to `main` branch
- **URL:** https://transcribe.studioionique.com

### Cloudflare Worker
- **Directory:** `youtube-transcript-worker/`
- **Deploy:** `cd youtube-transcript-worker && npx wrangler deploy`
- **URL:** https://youtube-transcript-worker.studioionique.workers.dev
- **Purpose:** YouTube caption fetching (Tier 1, works intermittently)

---

## Future: Unlimited Free YouTube Transcripts via WARP

Research into how working Cobalt instances (like `cobalt-api.meowing.de`, 96% uptime) bypass YouTube revealed the technique: **Cloudflare WARP (free) via Gluetun Docker container**.

### How It Works

1. A **Gluetun** Docker container connects to Cloudflare WARP via WireGuard (free)
2. The app container routes all outbound traffic through Gluetun (`network_mode: service:gluetun`)
3. YouTube sees Cloudflare WARP IPs — treated as legitimate, not datacenter
4. Optional: IPv6 freebind rotation (`FREEBIND_CIDR`) to evade per-IP rate limits

### What You'd Need

- **$5/mo VPS** (Hetzner, DigitalOcean) with Docker
- **Gluetun** container with WARP config (generate with `wgcf register && wgcf generate`)
- **A tiny transcript proxy** — either `youtube-transcript-api` (Python) or yt-dlp behind the WARP tunnel
- Render app calls the VPS proxy instead of Supadata

### Cost Comparison

| Approach | Monthly Cost | Request Limit | Maintenance |
|----------|-------------|---------------|-------------|
| Supadata (current) | $0–$9 | 100–1,000 | Zero |
| VPS + WARP proxy | $5 | Unlimited | Docker, occasional player ID updates |

### References

- [Cloudflare WARP YouTube bypass guide](https://blog.arfevrier.fr/leveraging-cloudflare-warp-to-bypass-youtubes-api-restrictions/)
- [Gluetun VPN container](https://github.com/qdm12/gluetun)
- [wgcf — WARP credential generator](https://github.com/ViRb3/wgcf)
- [Cobalt YouTube config docs](https://github.com/imputnet/cobalt/blob/main/docs/configure-for-youtube.md)
- [imputnet/freebind.js — IPv6 rotation](https://github.com/imputnet/freebind.js/)

### Implementation Plan (when ready)

1. Provision a cheap VPS (Hetzner CX22, $5/mo)
2. Install Docker, run Gluetun with WARP WireGuard config
3. Run `youtube-transcript-api` or yt-dlp inside the WARP network
4. Expose a simple HTTP API: `GET /transcript?v=VIDEO_ID&lang=en`
5. Set `TRANSCRIPT_WORKER_URL` on Render to point to the VPS
6. Supadata becomes Tier 3 backup instead of Tier 2

---

## Next Steps (Suggested)

### Immediate Cleanup
1. **Delete dead code** — `browser_download.py`, YouTube RapidAPI code in `rapidapi_downloader.py`
2. **Update `.env.example`** — Add `TRANSCRIPT_WORKER_URL`, `SUPADATA_API_KEY`
3. **Create codebase index** — For faster future development sessions
4. **Consolidate config files** — Pick YAML or JSON, not both

### Monitoring
5. **Track Supadata usage** — Monitor how many of 100 free credits/month are used
6. **Add retry on Cloudflare Worker** — Sometimes 429 is transient; retry after 2s might succeed

### When Usage Exceeds Free Tier
7. **Option A:** Upgrade Supadata to $9/mo (1,000 credits) — simplest
8. **Option B:** Deploy VPS + WARP proxy ($5/mo, unlimited) — see section above
