"""
RapidAPI Fallback Downloader Module

Provides fallback downloading via RapidAPI-hosted endpoints when yt-dlp fails.
- YouTube: Uses youtube-mp36 API to get direct MP3 links.
- Instagram: Tries configured endpoints from config/rapidapi_endpoints.json.
"""

import os
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
import json

from loguru import logger


# Candidate field names to probe when parsing a download URL from API JSON.
_DOWNLOAD_URL_FIELDS = ("url", "download_url", "link", "video_url")

_REQUEST_TIMEOUT = 30  # seconds

_ENDPOINTS_FILE = Path(__file__).parent.parent / "config" / "rapidapi_endpoints.json"


def load_endpoints(config_path: Path = _ENDPOINTS_FILE) -> List[Dict]:
    """Load RapidAPI endpoint definitions from YAML config.

    Returns an empty list (with a warning) if the file is missing or invalid.
    """
    if not config_path.exists():
        logger.warning(f"RapidAPI endpoints config not found: {config_path}")
        return []

    try:
        with open(config_path, "r") as fh:
            data = json.load(fh)
        endpoints = data.get("endpoints", [])
        if not isinstance(endpoints, list):
            logger.warning(f"Invalid endpoints format in {config_path}")
            return []
        logger.info(f"Loaded {len(endpoints)} RapidAPI fallback endpoint(s)")
        return endpoints
    except Exception as exc:
        logger.warning(f"Failed to load RapidAPI endpoints config: {exc}")
        return []


class RapidAPIDownloader:
    """Fallback Instagram downloader using RapidAPI-hosted endpoints.

    Endpoints are loaded from config/rapidapi_endpoints.json and tried
    in order. Edit that file to add, remove, or reorder backups —
    no code changes required.
    """

    def __init__(self) -> None:
        self._api_key: Optional[str] = os.environ.get("RAPIDAPI_KEY")
        self._rapidapi_user: Optional[str] = os.environ.get("RAPIDAPI_USER")
        if not self._api_key:
            logger.warning(
                "RAPIDAPI_KEY is not set — RapidAPI fallback will be unavailable"
            )
        self._endpoints = load_endpoints()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def download_instagram(
        self,
        url: str,
        output_dir: Path,
    ) -> Tuple[bool, Optional[Path], Optional[str], str]:
        """Try all configured backup downloaders in order.

        Args:
            url:        Instagram reel/video URL.
            output_dir: Directory where the extracted audio file will be saved.

        Returns:
            (success, audio_path, error_message, source_name)
        """
        if not self._api_key:
            return (
                False,
                None,
                "RAPIDAPI_KEY environment variable is not set",
                "rapidapi_none",
            )

        if not self._endpoints:
            return (
                False,
                None,
                "No RapidAPI endpoints configured in config/rapidapi_endpoints.json",
                "rapidapi_none",
            )

        video_id = self._derive_video_id(url)
        last_source = "rapidapi_none"

        for idx, endpoint in enumerate(self._endpoints, start=1):
            name = endpoint.get("name", f"RapidAPI Backup {idx}")
            source_key = f"rapidapi_backup{idx}"
            last_source = source_key

            logger.info(f"{name}: attempting download for {video_id}")
            download_url = self._try_endpoint(endpoint, url)

            if download_url:
                try:
                    audio_path = self._download_and_extract_audio(
                        download_url, output_dir, video_id
                    )
                    logger.info(f"{name} succeeded for {video_id}")
                    return True, audio_path, None, source_key
                except Exception as exc:
                    logger.warning(
                        f"{name} audio extraction failed for {video_id}: {exc}"
                    )
            else:
                logger.warning(f"{name} returned no download URL for {video_id}")

        error_msg = (
            f"All {len(self._endpoints)} RapidAPI fallback downloaders failed"
        )
        logger.error(f"{error_msg} for {video_id}")
        return False, None, error_msg, last_source

    def download_youtube_mp3(
        self,
        video_id: str,
        output_dir: Optional[Path] = None,
    ) -> Tuple[bool, Optional[Path], Optional[str], str]:
        """Download YouTube video as MP3 via youtube-mp36 RapidAPI.

        Uses polling to handle the 'processing' status that the API may
        return while converting the video. Downloads the MP3 immediately
        to avoid link expiration.

        Args:
            video_id:   11-character YouTube video ID.
            output_dir: Directory for the MP3 file (defaults to system temp).

        Returns:
            (success, audio_path, error_message, source_name)
        """
        source = "rapidapi_youtube_mp3"

        if not self._api_key:
            return False, None, "RAPIDAPI_KEY environment variable is not set", source

        api_url = "https://youtube-mp36.p.rapidapi.com/dl"
        headers = {
            "X-RapidAPI-Key": self._api_key,
            "X-RapidAPI-Host": "youtube-mp36.p.rapidapi.com",
            "Content-Type": "application/json",
        }

        max_polls = 10
        poll_delay = 5  # seconds between polls
        max_download_retries = 3
        last_error = None

        save_dir = Path(output_dir) if output_dir else Path(tempfile.gettempdir())
        save_dir.mkdir(parents=True, exist_ok=True)
        audio_path = save_dir / f"youtube_{video_id}.mp3"

        for dl_attempt in range(max_download_retries):
            try:
                mp3_link = None

                for attempt in range(max_polls):
                    resp = requests.get(
                        api_url,
                        headers=headers,
                        params={"id": video_id},
                        timeout=_REQUEST_TIMEOUT,
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    logger.debug(f"youtube-mp36 response: {data}")
                    status = data.get("status", "").lower()

                    if status == "ok":
                        mp3_link = data.get("link")
                        break

                    if status == "processing":
                        logger.debug(
                            f"YouTube MP3 still processing, poll {attempt + 1}/{max_polls} "
                            f"(waiting {poll_delay}s)"
                        )
                        time.sleep(poll_delay)
                        continue

                    if status == "fail":
                        msg = data.get("msg", "Unknown error from youtube-mp36 API")
                        return False, None, f"API error: {msg}", source

                    return False, None, f"Unexpected API status: {status}", source

                if not mp3_link:
                    return False, None, "Timed out waiting for MP3 processing", source

                title = data.get("title", video_id)
                logger.info(
                    f"YouTube MP3 ready (attempt {dl_attempt + 1}): {title} → {mp3_link}"
                )

                # Download immediately — links expire quickly
                self._stream_download(mp3_link, audio_path)

                if audio_path.exists() and audio_path.stat().st_size > 0:
                    logger.info(f"YouTube MP3 saved: {audio_path}")
                    return True, audio_path, None, source

                last_error = "MP3 download produced empty or no file"

            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    f"YouTube MP3 download attempt {dl_attempt + 1} failed: {last_error}"
                )
                # Clean up partial file
                if audio_path.exists():
                    audio_path.unlink(missing_ok=True)

            # Wait before retrying with a fresh link
            if dl_attempt < max_download_retries - 1:
                time.sleep(3)

        return False, None, f"YouTube MP3 download failed after {max_download_retries} attempts: {last_error}", source

    # ------------------------------------------------------------------
    # Private API caller (generic, driven by JSON config)
    # ------------------------------------------------------------------

    def _try_endpoint(self, endpoint: Dict, instagram_url: str) -> Optional[str]:
        """Call a single RapidAPI endpoint and extract the download URL."""
        host = endpoint.get("host", "")
        path = endpoint.get("path", "")
        method = endpoint.get("method", "GET").upper()
        param_name = endpoint.get("param", "url")
        name = endpoint.get("name", host)

        full_url = f"https://{host}{path}"
        headers = {
            "X-RapidAPI-Key": self._api_key,
            "X-RapidAPI-Host": host,
        }

        try:
            if method == "POST":
                response = requests.post(
                    full_url,
                    headers=headers,
                    json={param_name: instagram_url},
                    timeout=_REQUEST_TIMEOUT,
                )
            else:
                response = requests.get(
                    full_url,
                    headers=headers,
                    params={param_name: instagram_url},
                    timeout=_REQUEST_TIMEOUT,
                )

            response.raise_for_status()
            data = response.json()
            logger.debug(
                f"{name} raw response keys: "
                f"{list(data.keys()) if isinstance(data, dict) else type(data)}"
            )
            return self._extract_download_url(data)

        except requests.exceptions.Timeout:
            logger.warning(f"{name} request timed out after {_REQUEST_TIMEOUT}s")
        except requests.exceptions.HTTPError as exc:
            logger.warning(
                f"{name} HTTP error: {exc.response.status_code} {exc.response.reason}"
            )
        except requests.exceptions.RequestException as exc:
            logger.warning(f"{name} request failed: {exc}")
        except ValueError as exc:
            logger.warning(f"{name} returned non-JSON response: {exc}")

        return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_download_url(self, data: object) -> Optional[str]:
        """Defensively probe a parsed JSON payload for a video download URL."""
        if not isinstance(data, dict):
            logger.debug(f"Unexpected API response type: {type(data)}")
            return None

        # Direct field probe on top-level dict
        for field in _DOWNLOAD_URL_FIELDS:
            value = data.get(field)
            if isinstance(value, str) and value.startswith("http"):
                return value

        # Probe one level deeper under common wrapper keys
        for wrapper_key in ("data", "result", "media"):
            nested = data.get(wrapper_key)
            if isinstance(nested, dict):
                for field in _DOWNLOAD_URL_FIELDS:
                    value = nested.get(field)
                    if isinstance(value, str) and value.startswith("http"):
                        return value
            elif isinstance(nested, list) and nested:
                first = nested[0]
                if isinstance(first, dict):
                    for field in _DOWNLOAD_URL_FIELDS:
                        value = first.get(field)
                        if isinstance(value, str) and value.startswith("http"):
                            return value

        logger.debug(f"Could not locate a download URL in API response: {data}")
        return None

    def _download_and_extract_audio(
        self,
        download_url: str,
        output_dir: Path,
        video_id: str,
    ) -> Path:
        """Download video from URL and extract audio as WAV using ffmpeg."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        unique_suffix = uuid.uuid4().hex[:8]
        temp_video_path = (
            Path(tempfile.gettempdir()) / f"rapidapi_{video_id}_{unique_suffix}.mp4"
        )
        audio_output_path = output_dir / f"instagram_{video_id}.wav"

        try:
            logger.debug(f"Downloading video from RapidAPI URL to {temp_video_path}")
            self._stream_download(download_url, temp_video_path)

            logger.debug(
                f"Extracting audio from {temp_video_path} -> {audio_output_path}"
            )
            self._run_ffmpeg_extract_audio(temp_video_path, audio_output_path)

            if not audio_output_path.exists():
                raise RuntimeError(
                    f"ffmpeg did not produce output file: {audio_output_path}"
                )

            return audio_output_path

        finally:
            if temp_video_path.exists():
                try:
                    temp_video_path.unlink()
                except OSError as exc:
                    logger.warning(
                        f"Could not remove temp video file {temp_video_path}: {exc}"
                    )

    def _stream_download(self, url: str, destination: Path) -> None:
        """Stream-download a URL to a local file.

        For youtube-mp36 CDN links, the server requires the RapidAPI
        username in the User-Agent header to pass its secure-link check.
        """
        import hashlib

        # youtube-mp36 CDN requires RapidAPI username for secure links
        rapidapi_user = self._rapidapi_user or ""
        ua_suffix = f" {rapidapi_user}" if rapidapi_user else ""
        download_headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/131.0.0.0 Safari/537.36{ua_suffix}"
            ),
        }
        # Also add X-RUN header (MD5 of username) as alternative auth
        if rapidapi_user:
            download_headers["X-RUN"] = hashlib.md5(
                rapidapi_user.encode()
            ).hexdigest()

        logger.debug(f"Downloading with headers: {list(download_headers.keys())}")
        try:
            with requests.get(
                url, stream=True, timeout=120, headers=download_headers
            ) as resp:
                resp.raise_for_status()
                with open(destination, "wb") as fh:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            fh.write(chunk)
        except requests.exceptions.Timeout as exc:
            raise RuntimeError(
                f"Video download timed out after 120s"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Video download request failed: {exc}") from exc

    def _run_ffmpeg_extract_audio(
        self,
        video_path: Path,
        audio_path: Path,
    ) -> None:
        """Run ffmpeg to extract audio from a video file as WAV."""
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(video_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            str(audio_path),
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )

        if result.returncode != 0:
            stderr_output = result.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(
                f"ffmpeg exited with code {result.returncode}: {stderr_output}"
            )

    @staticmethod
    def _derive_video_id(url: str) -> str:
        """Extract an identifier from the URL for file naming."""
        import re

        match = re.search(r"/reels?/([A-Za-z0-9_-]+)", url)
        if match:
            return match.group(1)
        import hashlib

        return hashlib.md5(url.encode()).hexdigest()[:12]
