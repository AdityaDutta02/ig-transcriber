"""
YouTube Transcript Fetcher

Tier 1: Cloudflare Worker — fetches captions from YouTube via edge network.
Tier 3: Supadata API — managed transcript service with AI fallback.

Tier 2 (browser-side Cobalt) is handled in browser_download.py + app.py.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Optional

import requests
from loguru import logger


@dataclass
class TranscriptResult:
    """Result of a YouTube transcript fetch."""
    success: bool
    text: Optional[str] = None
    segments: Optional[list[dict]] = None
    language: Optional[str] = None
    error: Optional[str] = None
    source: str = field(default="youtube_captions")


def extract_video_id(url: str) -> Optional[str]:
    """Extract 11-char YouTube video ID from various URL formats."""
    patterns = [
        r"(?:v=|/v/)([A-Za-z0-9_-]{11})",
        r"youtu\.be/([A-Za-z0-9_-]{11})",
        r"/shorts/([A-Za-z0-9_-]{11})",
        r"/embed/([A-Za-z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def fetch_via_worker(url: str, lang: str = "en") -> TranscriptResult:
    """Tier 1: Fetch transcript via Cloudflare Worker."""
    worker_url = os.environ.get("TRANSCRIPT_WORKER_URL")
    if not worker_url:
        return TranscriptResult(success=False, error="TRANSCRIPT_WORKER_URL not set")

    video_id = extract_video_id(url)
    if not video_id:
        return TranscriptResult(success=False, error=f"Could not extract video ID from: {url}")

    endpoint = f"{worker_url.rstrip('/')}/?v={video_id}&lang={lang}"
    logger.info(f"Tier 1: fetching transcript from Worker for {video_id}")

    try:
        resp = requests.get(endpoint, timeout=15)
        data = resp.json()

        if resp.status_code == 404 and data.get("error") == "no_captions":
            logger.info(f"Worker: no captions for {video_id}")
            return TranscriptResult(success=False, error="no_captions")

        if resp.status_code != 200:
            error_msg = data.get("error", f"HTTP {resp.status_code}")
            logger.warning(f"Worker error for {video_id}: {error_msg}")
            return TranscriptResult(success=False, error=error_msg)

        full_text = data.get("fullText", "")
        segments = data.get("segments", [])
        language = data.get("language", lang)

        std_segments = []
        for seg in segments:
            start = seg.get("start", 0)
            dur = seg.get("dur", 0)
            std_segments.append({
                "start": start,
                "end": round(start + dur, 3),
                "text": seg.get("text", ""),
            })

        logger.info(
            f"Worker: transcript for {video_id}, "
            f"{len(std_segments)} segments, {len(full_text)} chars"
        )
        return TranscriptResult(
            success=True, text=full_text, segments=std_segments,
            language=language, source="cloudflare_worker",
        )
    except requests.exceptions.Timeout:
        return TranscriptResult(success=False, error="Worker request timed out")
    except Exception as exc:
        logger.warning(f"Worker failed for {video_id}: {exc}")
        return TranscriptResult(success=False, error=str(exc))


def fetch_via_supadata(url: str) -> TranscriptResult:
    """Tier 3: Fetch transcript via Supadata managed API."""
    api_key = os.environ.get("SUPADATA_API_KEY")
    if not api_key:
        return TranscriptResult(success=False, error="SUPADATA_API_KEY not set")

    video_id = extract_video_id(url) or "unknown"
    logger.info(f"Tier 3: fetching transcript from Supadata for {video_id}")

    try:
        resp = requests.get(
            "https://api.supadata.ai/v1/transcript",
            params={"url": url},
            headers={"x-api-key": api_key},
            timeout=30,
        )
        if resp.status_code != 200:
            return TranscriptResult(
                success=False,
                error=f"Supadata HTTP {resp.status_code}: {resp.text[:200]}",
            )

        data = resp.json()
        content = data.get("content") or data.get("transcript") or ""
        if not content:
            return TranscriptResult(success=False, error="Supadata returned empty transcript")

        segments = []
        if isinstance(content, list):
            for item in content:
                start = item.get("offset", item.get("start", 0))
                dur = item.get("duration", item.get("dur", 0))
                segments.append({
                    "start": start,
                    "end": round(start + dur, 3),
                    "text": item.get("text", ""),
                })
            full_text = " ".join(s["text"] for s in segments)
        else:
            full_text = str(content)

        lang = data.get("lang", data.get("language", "en"))
        logger.info(f"Supadata: transcript for {video_id}, {len(full_text)} chars")
        return TranscriptResult(
            success=True, text=full_text,
            segments=segments if segments else None,
            language=lang, source="supadata",
        )
    except requests.exceptions.Timeout:
        return TranscriptResult(success=False, error="Supadata request timed out")
    except Exception as exc:
        logger.warning(f"Supadata failed for {video_id}: {exc}")
        return TranscriptResult(success=False, error=str(exc))
