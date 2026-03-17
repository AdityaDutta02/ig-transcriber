"""
Transcriber Module

Handles audio transcription using the Groq Whisper Large API.
Processes audio files from the downloader and generates text transcriptions.
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from loguru import logger
from tqdm import tqdm

from config import TranscriptionConfig
from utils import ensure_directory, format_duration


# Groq API file size limit in bytes (25 MB hard limit; use 24 MB as a safe threshold)
_GROQ_SIZE_LIMIT_BYTES = 24 * 1024 * 1024


class TranscriptionError(Exception):
    """Custom exception for transcription errors."""
    pass


class GroqTranscriber:
    """
    Transcribes audio using the Groq Whisper Large v3 API.

    Features:
    - Cloud-based inference via Groq (no local GPU required)
    - Automatic language detection
    - Multi-language support (99+ languages)
    - Large file handling via ffmpeg MP3 compression
    - Batch processing with progress tracking
    - Structured error handling
    """

    def __init__(self, config: TranscriptionConfig) -> None:
        """
        Initialize the Groq transcriber.

        Args:
            config: Transcription configuration

        Raises:
            TranscriptionError: If GROQ_API_KEY is not set in the environment.
        """
        self.config = config

        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise TranscriptionError(
                "GROQ_API_KEY environment variable is not set. "
                "Add it to your .env file or export it before running."
            )

        try:
            from groq import Groq
            self._client = Groq(api_key=api_key)
        except ImportError as exc:
            raise TranscriptionError(
                "groq package is not installed. Install with: pip install groq>=0.9.0"
            ) from exc

        logger.info("GroqTranscriber initialized")
        logger.info(f"API provider: {config.api_provider}")
        logger.info(f"Language: {config.language}")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _compress_to_mp3(self, audio_path: Path) -> Path:
        """
        Compress an audio file to MP3 using ffmpeg so it fits under Groq's
        25 MB file-size limit.

        Args:
            audio_path: Path to the original audio file.

        Returns:
            Path to the compressed MP3 file (written alongside the original).

        Raises:
            TranscriptionError: If ffmpeg is unavailable or conversion fails.
        """
        mp3_path = audio_path.with_suffix(".compressed.mp3")
        logger.info(
            f"Audio file exceeds 24 MB — compressing to MP3: {audio_path.name}"
        )

        cmd = [
            "ffmpeg",
            "-y",              # overwrite output if it exists
            "-i", str(audio_path),
            "-vn",             # no video
            "-ar", "16000",    # 16 kHz sample rate (adequate for speech)
            "-ac", "1",        # mono
            "-b:a", "32k",     # low bitrate keeps file small
            str(mp3_path),
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except FileNotFoundError as exc:
            raise TranscriptionError(
                "ffmpeg is not installed or not on PATH. "
                "Install ffmpeg to handle audio files larger than 24 MB."
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise TranscriptionError(
                f"ffmpeg timed out while compressing {audio_path.name}"
            ) from exc

        if result.returncode != 0:
            raise TranscriptionError(
                f"ffmpeg compression failed for {audio_path.name}: {result.stderr}"
            )

        logger.info(
            f"Compressed {audio_path.name} "
            f"({audio_path.stat().st_size / (1024**2):.1f} MB) → "
            f"{mp3_path.name} "
            f"({mp3_path.stat().st_size / (1024**2):.1f} MB)"
        )
        return mp3_path

    def _resolve_audio_path(self, audio_path: Path) -> Path:
        """
        Return a Groq-uploadable audio path, compressing first if needed.

        Args:
            audio_path: Original audio file path.

        Returns:
            Path that is safe to send to the Groq API.
        """
        file_size = audio_path.stat().st_size
        if file_size > _GROQ_SIZE_LIMIT_BYTES:
            return self._compress_to_mp3(audio_path)
        return audio_path

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def transcribe_audio(
        self,
        audio_path: Path,
        language: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], Optional[Dict], Optional[str]]:
        """
        Transcribe a single audio file via the Groq Whisper Large v3 API.

        Args:
            audio_path: Path to the audio file.
            language: Optional ISO-639-1 language code override (e.g. "en", "hi").
                      Pass None or "auto" for automatic language detection.

        Returns:
            A 4-tuple of:
              - success (bool)
              - transcription text (str | None)
              - metadata dict (Dict | None) containing:
                  language, duration, processing_time, confidence,
                  segments_count, segments
              - error message (str | None)
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            return False, None, None, f"Audio file not found: {audio_path}"

        # Determine effective language (None == auto-detect in Whisper)
        effective_language: Optional[str] = language or self.config.language
        if effective_language == "auto":
            effective_language = None

        upload_path = audio_path
        try:
            upload_path = self._resolve_audio_path(audio_path)
            start_time = time.time()

            logger.debug(f"Sending to Groq API: {upload_path.name}")

            with open(upload_path, "rb") as audio_file:
                response = self._client.audio.transcriptions.create(
                    model="whisper-large-v3",
                    file=audio_file,
                    response_format="verbose_json",
                    language=effective_language,
                )

            processing_time = time.time() - start_time

            # Map Groq response segments to the format captions.py expects
            raw_segments = getattr(response, "segments", None) or []
            segments_data: List[Dict] = [
                {
                    "start": float(seg.get("start", 0.0) if isinstance(seg, dict) else seg.start),
                    "end": float(seg.get("end", 0.0) if isinstance(seg, dict) else seg.end),
                    "text": (seg.get("text", "") if isinstance(seg, dict) else seg.text).strip(),
                }
                for seg in raw_segments
            ]

            # Full transcription text
            transcription = getattr(response, "text", "") or ""
            transcription = transcription.strip()

            # Detected language
            detected_language = getattr(response, "language", "unknown") or "unknown"

            # Duration from response; fall back to last segment end time
            duration: float = getattr(response, "duration", 0.0) or 0.0
            if duration == 0.0 and segments_data:
                duration = segments_data[-1]["end"]

            metadata: Dict = {
                "language": detected_language,
                "duration": duration,
                "processing_time": processing_time,
                "confidence": None,  # Groq verbose_json does not expose logprobs
                "segments_count": len(segments_data),
                "segments": segments_data,
            }

            logger.debug(
                f"Transcribed {audio_path.name} in {processing_time:.2f}s — "
                f"language: {detected_language}, "
                f"chars: {len(transcription)}, "
                f"segments: {len(segments_data)}"
            )

            return True, transcription, metadata, None

        except TranscriptionError:
            raise  # Let compression errors propagate unmodified
        except Exception as exc:
            error_msg = f"Transcription failed: {exc}"
            logger.error(f"{audio_path.name}: {error_msg}")
            return False, None, None, error_msg
        finally:
            # Remove temporary compressed file if one was created
            if upload_path != audio_path and upload_path.exists():
                try:
                    upload_path.unlink()
                    logger.debug(f"Removed temporary file: {upload_path.name}")
                except OSError as exc:
                    logger.warning(f"Could not remove temporary file {upload_path.name}: {exc}")

    def transcribe_batch(
        self,
        audio_records: List[Dict],
        progress_callback: Optional[callable] = None,
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Transcribe multiple audio files.

        Args:
            audio_records: List of record dicts, each must contain an 'audio_file' key.
            progress_callback: Optional callable(completed: int, total: int) for progress.

        Returns:
            Tuple of (successful_transcriptions, failed_transcriptions).
            Each item in the lists is the original record dict augmented with
            transcription results.
        """
        successful: List[Dict] = []
        failed: List[Dict] = []
        total = len(audio_records)

        logger.info(f"Starting batch transcription of {total} audio files")
        logger.info(f"API provider: {self.config.api_provider}")

        with tqdm(total=total, desc="Transcribing audio", unit="file") as pbar:
            for record in audio_records:
                reel_id = record.get("reel_id", "unknown")
                try:
                    audio_file = Path(record["audio_file"])
                    success, transcription, metadata, error = self.transcribe_audio(audio_file)

                    if success:
                        successful.append({
                            **record,
                            "transcription": transcription,
                            "transcription_metadata": metadata,
                            "transcription_success": True,
                        })
                        logger.debug(f"Success: {reel_id}")
                    else:
                        failed.append({
                            **record,
                            "transcription_success": False,
                            "error": error,
                        })
                        logger.warning(f"Failed: {reel_id} — {error}")

                except Exception as exc:
                    logger.error(f"Unexpected error transcribing {reel_id}: {exc}")
                    failed.append({
                        **record,
                        "transcription_success": False,
                        "error": str(exc),
                    })

                pbar.update(1)
                if progress_callback:
                    progress_callback(len(successful) + len(failed), total)

        logger.info(
            f"Batch transcription complete: {len(successful)} successful, {len(failed)} failed"
        )
        return successful, failed


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------

def transcribe_audio_files(
    audio_records: List[Dict],
    config: Optional[TranscriptionConfig] = None,
    progress_callback: Optional[callable] = None,
) -> Tuple[List[Dict], List[Dict]]:
    """
    Convenience function to transcribe a list of audio records.

    Args:
        audio_records: List of records with an 'audio_file' key.
        config: Optional TranscriptionConfig; loads from config.yaml if omitted.
        progress_callback: Optional callable(completed: int, total: int).

    Returns:
        Tuple of (successful_transcriptions, failed_transcriptions).

    Example:
        >>> from downloader import download_reels
        >>> successful_downloads, _ = download_reels(urls)
        >>> successful_transcriptions, _ = transcribe_audio_files(successful_downloads)
        >>> print(f"Transcribed: {len(successful_transcriptions)}")
    """
    if config is None:
        from config import load_config
        config = load_config().transcription

    transcriber = GroqTranscriber(config)
    return transcriber.transcribe_batch(audio_records, progress_callback)


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).parent))

    from config import load_config

    print("=" * 70)
    print("Transcriber Module — Smoke Test")
    print("=" * 70)
    print()

    # Test 1: API key presence
    print("Test 1: Checking GROQ_API_KEY environment variable...")
    api_key = os.environ.get("GROQ_API_KEY")
    if api_key:
        masked = api_key[:6] + "..." + api_key[-4:]
        print(f"[OK] GROQ_API_KEY is set ({masked})")
    else:
        print("[ERROR] GROQ_API_KEY is not set")
        print("  Set it in your .env file: GROQ_API_KEY=your_key_here")
        sys.exit(1)

    print()

    # Test 2: Initialize transcriber
    print("Test 2: Initializing GroqTranscriber...")
    try:
        cfg = load_config()
        transcriber = GroqTranscriber(cfg.transcription)
        print("[OK] GroqTranscriber initialized successfully")
        print(f"  API provider: {cfg.transcription.api_provider}")
        print(f"  Language: {cfg.transcription.language}")
    except TranscriptionError as err:
        print(f"[ERROR] {err}")
        sys.exit(1)

    print()
    print("=" * 70)
    print("Smoke test complete — ready to transcribe audio files.")
    print("=" * 70)
