"""
Cobalt Downloader Module

Downloads YouTube audio via Cobalt public API instances. Used as a fallback
when YouTube captions are unavailable and yt-dlp/RapidAPI have already failed.
"""
import hashlib
import re
import tempfile
from pathlib import Path
from typing import Optional, Tuple
import requests
from loguru import logger

COBALT_INSTANCES: list[str] = ["https://cobalt-api.meowing.de"]
_API_TIMEOUT = 30     # seconds — waiting for Cobalt to respond
_DL_TIMEOUT = 120     # seconds — streaming the audio file to disk
_MIN_FILE_SIZE = 1000 # bytes — sanity check after download

def _extract_video_id(url: str) -> str:
    """Return the YouTube video ID from a URL, or a short MD5 hash as fallback."""
    match = re.search(r"(?:v=|youtu\.be/|/embed/|/shorts/)([A-Za-z0-9_-]{11})", url)
    if match:
        return match.group(1)
    return hashlib.md5(url.encode()).hexdigest()[:12]

def _call_cobalt_api(
    instance_url: str, video_url: str
) -> Tuple[Optional[str], Optional[str]]:
    """POST to a Cobalt instance and return (download_url, error_message)."""
    endpoint = f"{instance_url.rstrip('/')}/api/json"
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    payload = {"url": video_url, "downloadMode": "audio", "audioFormat": "mp3"}
    try:
        resp = requests.post(endpoint, json=payload, headers=headers, timeout=_API_TIMEOUT)
        resp.raise_for_status()
        data: dict = resp.json()
    except requests.exceptions.Timeout:
        return None, f"Cobalt API timed out after {_API_TIMEOUT}s"
    except requests.exceptions.RequestException as exc:
        return None, f"Cobalt API request failed: {exc}"
    except ValueError as exc:
        return None, f"Cobalt returned non-JSON response: {exc}"
    status = data.get("status", "")
    if status in ("error", "rate-limit", "redirect", "picker"):
        msg = data.get("text") or data.get("error", {}).get("code") or status
        logger.warning(f"Cobalt {instance_url} status '{status}': {msg}")
        return None, f"Cobalt error status '{status}': {msg}"
    download_url: Optional[str] = data.get("url")
    if not download_url:
        return None, "Cobalt response contained no download URL"
    return download_url, None

def _stream_to_disk(download_url: str, audio_path: Path) -> Optional[str]:
    """Stream audio bytes from download_url to audio_path. Returns error or None."""
    try:
        with requests.get(download_url, stream=True, timeout=_DL_TIMEOUT) as dl_resp:
            dl_resp.raise_for_status()
            with open(audio_path, "wb") as fh:
                for chunk in dl_resp.iter_content(chunk_size=8192):
                    if chunk:
                        fh.write(chunk)
    except requests.exceptions.Timeout:
        audio_path.unlink(missing_ok=True)
        return f"Cobalt audio download timed out after {_DL_TIMEOUT}s"
    except requests.exceptions.RequestException as exc:
        audio_path.unlink(missing_ok=True)
        return f"Cobalt audio download failed: {exc}"
    if not audio_path.exists() or audio_path.stat().st_size < _MIN_FILE_SIZE:
        audio_path.unlink(missing_ok=True)
        return "Downloaded file is too small or missing — likely corrupt"
    return None

def _try_instance(
    instance_url: str, video_url: str, output_dir: Path
) -> Tuple[bool, Optional[Path], Optional[str]]:
    """Attempt to download audio from one Cobalt instance.

    Returns (success, audio_path, error_message).
    """
    logger.info(f"Cobalt: trying {instance_url} for {video_url}")
    download_url, api_error = _call_cobalt_api(instance_url, video_url)
    if api_error:
        return False, None, api_error
    audio_path = output_dir / f"cobalt_{_extract_video_id(video_url)}.mp3"
    logger.info(f"Cobalt: streaming audio to {audio_path}")
    dl_error = _stream_to_disk(download_url, audio_path)  # type: ignore[arg-type]
    if dl_error:
        return False, None, dl_error
    logger.info(f"Cobalt: download complete ({audio_path.stat().st_size} bytes)")
    return True, audio_path, None

def download_audio(
    url: str, output_dir: Optional[Path] = None
) -> Tuple[bool, Optional[Path], Optional[str]]:
    """Download YouTube audio via Cobalt, trying each configured instance in order.

    Args:
        url:        YouTube video URL.
        output_dir: Directory for the output MP3. Defaults to a system temp sub-dir.

    Returns:
        (success, audio_path, error_message)
    """
    save_dir = (
        Path(output_dir) if output_dir
        else Path(tempfile.gettempdir()) / "video_downloads"
    )
    save_dir.mkdir(parents=True, exist_ok=True)
    last_error: Optional[str] = "No Cobalt instances configured"
    for instance in COBALT_INSTANCES:
        success, audio_path, error = _try_instance(instance, url, save_dir)
        if success:
            return True, audio_path, None
        last_error = error
        logger.warning(f"Cobalt instance {instance} failed: {error}")
    logger.error(f"All Cobalt instances failed for {url}: {last_error}")
    return False, None, last_error
