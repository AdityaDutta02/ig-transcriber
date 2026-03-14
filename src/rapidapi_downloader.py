"""
RapidAPI Fallback Downloader Module

Provides fallback Instagram video downloading via two RapidAPI-hosted endpoints
when yt-dlp fails. Used exclusively as a secondary option inside VideoDownloader.
"""

import os
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Optional, Tuple

import requests
from loguru import logger


# Candidate field names to probe when parsing a download URL from API JSON.
_DOWNLOAD_URL_FIELDS = ("url", "download_url", "link", "video_url")

_REQUEST_TIMEOUT = 30  # seconds


class RapidAPIDownloader:
    """Fallback Instagram downloader using RapidAPI-hosted endpoints.

    Both backup services are tried in order:
      1. instagram-downloader-download-instagram-stories-videos4.p.rapidapi.com
      2. instagram-reels-downloader-api.p.rapidapi.com

    The class never raises exceptions to the caller; all failures are captured
    and returned as part of the result tuple.
    """

    _SAFESITE_HOST = (
        "instagram-downloader-download-instagram-stories-videos4.p.rapidapi.com"
    )
    _EASEAPI_HOST = "instagram-reels-downloader-api.p.rapidapi.com"

    def __init__(self) -> None:
        self._api_key: Optional[str] = os.environ.get("RAPIDAPI_KEY")
        if not self._api_key:
            logger.warning(
                "RAPIDAPI_KEY is not set — RapidAPI fallback will be unavailable"
            )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def download_instagram(
        self,
        url: str,
        output_dir: Path,
    ) -> Tuple[bool, Optional[Path], Optional[str], str]:
        """Try backup downloaders in order.

        Args:
            url:        Instagram reel/video URL.
            output_dir: Directory where the extracted audio file will be saved.

        Returns:
            (success, audio_path, error_message, source_name)
            source_name is one of: 'rapidapi_backup1', 'rapidapi_backup2'
        """
        if not self._api_key:
            return (
                False,
                None,
                "RAPIDAPI_KEY environment variable is not set",
                "rapidapi_backup1",
            )

        video_id = self._derive_video_id(url)

        # --- Backup 1 ---
        logger.info(f"RapidAPI backup 1 (safesite): attempting download for {video_id}")
        download_url = self._try_safesite_api(url)
        if download_url:
            try:
                audio_path = self._download_and_extract_audio(
                    download_url, output_dir, video_id
                )
                logger.info(f"RapidAPI backup 1 succeeded for {video_id}")
                return True, audio_path, None, "rapidapi_backup1"
            except Exception as exc:
                logger.warning(
                    f"RapidAPI backup 1 audio extraction failed for {video_id}: {exc}"
                )
        else:
            logger.warning(f"RapidAPI backup 1 returned no download URL for {video_id}")

        # --- Backup 2 ---
        logger.info(f"RapidAPI backup 2 (easeapi): attempting download for {video_id}")
        download_url = self._try_easeapi_api(url)
        if download_url:
            try:
                audio_path = self._download_and_extract_audio(
                    download_url, output_dir, video_id
                )
                logger.info(f"RapidAPI backup 2 succeeded for {video_id}")
                return True, audio_path, None, "rapidapi_backup2"
            except Exception as exc:
                logger.warning(
                    f"RapidAPI backup 2 audio extraction failed for {video_id}: {exc}"
                )
        else:
            logger.warning(f"RapidAPI backup 2 returned no download URL for {video_id}")

        error_msg = "All RapidAPI fallback downloaders failed"
        logger.error(f"{error_msg} for {video_id}")
        return False, None, error_msg, "rapidapi_backup2"

    # ------------------------------------------------------------------
    # Private API callers
    # ------------------------------------------------------------------

    def _try_safesite_api(self, url: str) -> Optional[str]:
        """Backup 1: instagram-downloader-download-instagram-stories-videos4.

        GET /index?url=<instagram_url>
        Headers: X-RapidAPI-Key, X-RapidAPI-Host
        """
        endpoint = f"https://{self._SAFESITE_HOST}/index"
        headers = {
            "X-RapidAPI-Key": self._api_key,
            "X-RapidAPI-Host": self._SAFESITE_HOST,
        }
        params = {"url": url}

        try:
            response = requests.get(
                endpoint,
                headers=headers,
                params=params,
                timeout=_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            logger.debug(f"Safesite API raw response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
            return self._extract_download_url(data)
        except requests.exceptions.Timeout:
            logger.warning(f"Safesite API request timed out after {_REQUEST_TIMEOUT}s")
        except requests.exceptions.HTTPError as exc:
            logger.warning(f"Safesite API HTTP error: {exc.response.status_code} {exc.response.reason}")
        except requests.exceptions.RequestException as exc:
            logger.warning(f"Safesite API request failed: {exc}")
        except ValueError as exc:
            logger.warning(f"Safesite API returned non-JSON response: {exc}")

        return None

    def _try_easeapi_api(self, url: str) -> Optional[str]:
        """Backup 2: instagram-reels-downloader-api.

        GET /download?url=<instagram_url>
        Headers: X-RapidAPI-Key, X-RapidAPI-Host
        """
        endpoint = f"https://{self._EASEAPI_HOST}/download"
        headers = {
            "X-RapidAPI-Key": self._api_key,
            "X-RapidAPI-Host": self._EASEAPI_HOST,
        }
        params = {"url": url}

        try:
            response = requests.get(
                endpoint,
                headers=headers,
                params=params,
                timeout=_REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            logger.debug(f"Easeapi raw response keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
            return self._extract_download_url(data)
        except requests.exceptions.Timeout:
            logger.warning(f"Easeapi API request timed out after {_REQUEST_TIMEOUT}s")
        except requests.exceptions.HTTPError as exc:
            logger.warning(f"Easeapi API HTTP error: {exc.response.status_code} {exc.response.reason}")
        except requests.exceptions.RequestException as exc:
            logger.warning(f"Easeapi API request failed: {exc}")
        except ValueError as exc:
            logger.warning(f"Easeapi API returned non-JSON response: {exc}")

        return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _extract_download_url(self, data: object) -> Optional[str]:
        """Defensively probe a parsed JSON payload for a video download URL.

        Handles both flat dicts and dicts containing a nested list/dict under
        common wrapper keys ('data', 'result', 'media').
        """
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
        """Download video from URL and extract audio as WAV using ffmpeg.

        Args:
            download_url: Direct URL to the video file.
            output_dir:   Directory to write the final WAV file.
            video_id:     Identifier used for naming the output file.

        Returns:
            Path to the extracted WAV audio file.

        Raises:
            RuntimeError: If the download or ffmpeg conversion fails.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Use a unique suffix on the temp video file to avoid collisions during
        # parallel downloads of different videos.
        unique_suffix = uuid.uuid4().hex[:8]
        temp_video_path = Path(tempfile.gettempdir()) / f"rapidapi_{video_id}_{unique_suffix}.mp4"
        audio_output_path = output_dir / f"instagram_{video_id}.wav"

        try:
            logger.debug(f"Downloading video from RapidAPI URL to {temp_video_path}")
            self._stream_download(download_url, temp_video_path)

            logger.debug(f"Extracting audio from {temp_video_path} -> {audio_output_path}")
            self._run_ffmpeg_extract_audio(temp_video_path, audio_output_path)

            if not audio_output_path.exists():
                raise RuntimeError(
                    f"ffmpeg did not produce output file: {audio_output_path}"
                )

            return audio_output_path

        finally:
            # Always remove the intermediate video file.
            if temp_video_path.exists():
                try:
                    temp_video_path.unlink()
                    logger.debug(f"Removed temporary video file: {temp_video_path}")
                except OSError as exc:
                    logger.warning(f"Could not remove temp video file {temp_video_path}: {exc}")

    def _stream_download(self, url: str, destination: Path) -> None:
        """Stream-download a URL to a local file.

        Args:
            url:         HTTP URL of the resource.
            destination: Local path to write bytes to.

        Raises:
            RuntimeError: On any network or HTTP error.
        """
        try:
            with requests.get(url, stream=True, timeout=_REQUEST_TIMEOUT) as resp:
                resp.raise_for_status()
                with open(destination, "wb") as fh:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            fh.write(chunk)
        except requests.exceptions.Timeout as exc:
            raise RuntimeError(f"Video download timed out after {_REQUEST_TIMEOUT}s") from exc
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"Video download request failed: {exc}") from exc

    def _run_ffmpeg_extract_audio(
        self,
        video_path: Path,
        audio_path: Path,
    ) -> None:
        """Run ffmpeg to extract audio from a video file as WAV.

        Args:
            video_path: Path to input video file (mp4).
            audio_path: Path for the output WAV file.

        Raises:
            RuntimeError: If ffmpeg exits with a non-zero return code.
        """
        cmd = [
            "ffmpeg",
            "-y",                    # Overwrite output without prompting
            "-i", str(video_path),
            "-vn",                   # Disable video stream
            "-acodec", "pcm_s16le",  # WAV codec
            "-ar", "16000",          # 16 kHz sample rate (optimal for Whisper)
            "-ac", "1",              # Mono channel
            str(audio_path),
        ]
        logger.debug(f"Running ffmpeg: {' '.join(cmd)}")

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
        """Extract an identifier from the URL for use in file names and log messages."""
        import re
        match = re.search(r"/reels?/([A-Za-z0-9_-]+)", url)
        if match:
            return match.group(1)
        # Fall back to a hash of the URL so we always have a usable string.
        import hashlib
        return hashlib.md5(url.encode()).hexdigest()[:12]
