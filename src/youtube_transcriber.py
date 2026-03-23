"""
YouTube Transcript Fetcher

Fetches YouTube captions/transcripts directly via the youtube-transcript-api
package, bypassing audio download entirely. This is the preferred method for
YouTube URL transcription.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from loguru import logger
_ARTIFACT_PATTERN = re.compile(r"\[(?:Music|Applause|Laughter|Noise|Sound)\]", re.IGNORECASE)
_VIDEO_ID_PATTERNS = [
    re.compile(r"(?:v=|/v/)([A-Za-z0-9_-]{11})"),
    re.compile(r"youtu\.be/([A-Za-z0-9_-]{11})"),
    re.compile(r"/shorts/([A-Za-z0-9_-]{11})"),
    re.compile(r"/embed/([A-Za-z0-9_-]{11})"),
]


@dataclass
class TranscriptResult:
    """Result of a YouTube transcript fetch operation."""
    success: bool
    text: Optional[str] = None
    segments: Optional[list[dict]] = None
    language: Optional[str] = None
    error: Optional[str] = None
    source: str = field(default="youtube_captions")


def _fail(msg: str, level: str = "error") -> TranscriptResult:
    """Log msg at level and return a failed TranscriptResult."""
    getattr(logger, level)(msg)
    return TranscriptResult(success=False, error=msg)


def extract_video_id(url: str) -> Optional[str]:
    """Extract the 11-char YouTube video ID from watch, youtu.be, shorts, or embed URLs."""
    if not url:
        return None
    for pattern in _VIDEO_ID_PATTERNS:
        match = pattern.search(url)
        if match:
            video_id = match.group(1)
            logger.debug(f"Extracted video ID '{video_id}' from URL: {url}")
            return video_id
    logger.warning(f"Could not extract video ID from URL: {url}")
    return None


def _resolve_transcript(transcript_list: object, preferred_languages: list[str], video_id: str) -> tuple:
    """Try each preferred language in order, then fall back to any available transcript."""
    from youtube_transcript_api import NoTranscriptFound  # type: ignore[import-untyped]
    for lang in preferred_languages:
        try:
            transcript = transcript_list.find_transcript([lang])
            logger.debug(f"Found transcript in preferred language: {lang}")
            return transcript, lang
        except NoTranscriptFound:
            logger.debug(f"No transcript for '{lang}' on video {video_id}")
    available = list(transcript_list)
    if not available:
        raise ValueError(f"No transcripts available for video {video_id}")
    transcript = available[0]
    lang_code: str = transcript.language_code
    logger.info(f"Falling back to available language: {lang_code}")
    return transcript, lang_code


def _build_segments(raw_snippets: list) -> tuple[list[dict], str]:
    """Convert raw FetchedTranscriptSnippet objects into timed segments and plain text."""
    segments: list[dict] = []
    text_parts: list[str] = []
    for snippet in raw_snippets:
        start: float = float(getattr(snippet, "start", 0.0))
        duration: float = float(getattr(snippet, "duration", 0.0))
        raw_text: str = getattr(snippet, "text", "") or ""
        cleaned = _ARTIFACT_PATTERN.sub("", raw_text).strip()
        if not cleaned:
            continue
        segments.append({"start": start, "end": round(start + duration, 3), "text": cleaned})
        text_parts.append(cleaned)
    return segments, " ".join(text_parts).strip()


def _classify_error(video_id: str, exc: Exception) -> TranscriptResult:
    """Map a generic exception to a rate-limit or unexpected-error TranscriptResult."""
    exc_str = str(exc).lower()
    if "too many requests" in exc_str or "blocked" in exc_str or "429" in exc_str:
        msg = f"YouTube is rate-limiting transcript requests for {video_id}: {exc}"
    else:
        msg = f"Unexpected error fetching transcript for {video_id}: {exc}"
    return _fail(msg)


def fetch_transcript(url: str, preferred_languages: Optional[list[str]] = None) -> TranscriptResult:
    """
    Fetch captions for a YouTube video without downloading audio.

    Tries preferred_languages in order (default: ["en"]), then any available language.
    Strips [Music] and similar auto-caption artifacts from the output text.
    """
    try:
        from youtube_transcript_api import (  # type: ignore[import-untyped]
            YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled, VideoUnavailable,
        )
    except ImportError:
        return _fail("youtube-transcript-api not installed. Run: pip install youtube-transcript-api")

    if preferred_languages is None:
        preferred_languages = ["en"]

    video_id = extract_video_id(url)
    if not video_id:
        return _fail(f"Could not extract video ID from URL: {url}")

    logger.info(f"Fetching transcript for video ID: {video_id}")
    try:
        transcript_list = YouTubeTranscriptApi().list(video_id)
        transcript, language = _resolve_transcript(transcript_list, preferred_languages, video_id)
        segments, plain_text = _build_segments(transcript.fetch())
        logger.info(
            f"Transcript fetched: video={video_id}, language={language}, "
            f"segments={len(segments)}, chars={len(plain_text)}"
        )
        return TranscriptResult(success=True, text=plain_text, segments=segments, language=language)
    except TranscriptsDisabled:
        return _fail(f"Transcripts are disabled for video {video_id}", level="warning")
    except VideoUnavailable:
        return _fail(f"Video is unavailable: {video_id}", level="warning")
    except (NoTranscriptFound, ValueError) as exc:
        return _fail(str(exc), level="warning")
    except Exception as exc:
        return _classify_error(video_id, exc)
