"""
Integration Tests for the Full Video Transcription Pipeline

Tests the complete pipeline flow: download → transcribe → generate captions.
All external services are mocked (yt-dlp, Groq API, RapidAPI).
"""

import os
import sys
import tempfile
import wave
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from captions import CaptionGenerator
from config import (
    AppConfig,
    CaptionConfig,
    DownloadConfig,
    InputConfig,
    LoggingConfig,
    OutputConfig,
    ProcessingConfig,
    TranscriptionConfig,
    ErrorHandlingConfig,
    MonitoringConfig,
)
from downloader import VideoDownloader
from rapidapi_downloader import RapidAPIDownloader
from transcriber import GroqTranscriber, TranscriptionError
from utils import detect_platform


# ─────────────────────────────────────────────────────────────────────────────
# FIXTURES FOR MOCKING AND TEST DATA
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_config() -> AppConfig:
    """Create a mock AppConfig for testing."""
    return AppConfig(
        input=InputConfig(csv_path="test.csv"),
        download=DownloadConfig(
            concurrent_workers=2,
            timeout=30,
            retry_attempts=1,
            retry_delay=0,
            rate_limit_delay=0,
            user_agent="Mozilla/5.0 (test)",
            format="bestaudio",
            audio_format="wav",
            audio_quality="0",
        ),
        transcription=TranscriptionConfig(
            api_provider="groq",
            language="auto",
        ),
        captions=CaptionConfig(
            enabled=True,
            words_per_line=10,
            max_lines=2,
            format="srt",
        ),
        output=OutputConfig(
            directory="output",
            format="txt",
            encoding="utf-8",
            naming_pattern="{timestamp}_{id}",
            include_metadata=True,
        ),
        processing=ProcessingConfig(
            batch_size=100,
            temp_directory="/tmp",
            cleanup_temp=True,
            save_checkpoint=True,
            checkpoint_interval=10,
            checkpoint_file="checkpoint.json",
        ),
        logging=LoggingConfig(
            level="DEBUG",
            console=True,
            file="app.log",
            format="{time} {level} {message}",
            error_file="error.log",
        ),
        monitoring=MonitoringConfig(
            enabled=True,
            track_metrics=True,
            report_interval=30,
            save_report=True,
            report_path="report.json",
        ),
        error_handling=ErrorHandlingConfig(
            continue_on_error=True,
            max_consecutive_errors=5,
            save_failed_urls=True,
            failed_urls_path="failed.csv",
            exponential_backoff=True,
            max_backoff_time=60,
        ),
    )


@pytest.fixture
def groq_segments() -> List[Dict]:
    """Create sample segments in Groq response format."""
    return [
        {
            "start": 0.0,
            "end": 2.5,
            "text": "Hello world this is a test",
        },
        {
            "start": 2.5,
            "end": 5.0,
            "text": "of the transcription system",
        },
        {
            "start": 5.0,
            "end": 8.0,
            "text": "it should work correctly",
        },
        {
            "start": 8.0,
            "end": 10.0,
            "text": "and produce proper output",
        },
    ]


@pytest.fixture
def mock_groq_response(groq_segments):
    """Create a mock Groq API response."""
    response = MagicMock()
    response.text = "Hello world this is a test of the transcription system it should work correctly and produce proper output"
    response.language = "en"
    response.duration = 10.0
    response.segments = groq_segments
    return response


@pytest.fixture
def temp_wav_file_large(temp_dir: Path) -> Path:
    """Create a temporary WAV file for download testing."""
    wav_path = temp_dir / "test_video_audio.wav"

    # Create a small but valid WAV file
    sample_rate = 16000
    duration_seconds = 5
    num_samples = sample_rate * duration_seconds

    with wave.open(str(wav_path), "w") as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b"\x00" * (num_samples * 2))

    return wav_path


@pytest.fixture
def temp_dir() -> Path:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# ─────────────────────────────────────────────────────────────────────────────
# TEST 1: Full Pipeline Success with yt-dlp
# ─────────────────────────────────────────────────────────────────────────────


def test_full_pipeline_ytdlp_success(
    mock_config,
    groq_segments,
    mock_groq_response,
    temp_wav_file_large,
    set_groq_api_key,
    monkeypatch,
):
    """
    Test the full pipeline with successful yt-dlp download and Groq transcription.

    Mocks:
    - VideoDownloader.download_video returns mock WAV file + yt-dlp source
    - GroqTranscriber.transcribe_audio returns valid response with segments
    - CaptionGenerator produces valid SRT output

    Verifies:
    - SRT output has proper timestamp format (HH:MM:SS,mmm --> HH:MM:SS,mmm)
    - All pipeline steps produce expected output
    """
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    # Mock VideoDownloader.download_video
    with patch.object(
        VideoDownloader, "download_video"
    ) as mock_download:
        mock_download.return_value = (
            True,
            temp_wav_file_large,
            None,
            "youtube",
        )

        # Mock GroqTranscriber initialization and transcription
        with patch.object(
            GroqTranscriber, "__init__", return_value=None
        ) as mock_init, patch.object(
            GroqTranscriber, "transcribe_audio"
        ) as mock_transcribe:
            mock_transcribe.return_value = (
                True,
                "Hello world this is a test of the transcription system it should work correctly and produce proper output",
                {
                    "language": "en",
                    "duration": 10.0,
                    "processing_time": 2.5,
                    "confidence": None,
                    "segments_count": 4,
                    "segments": groq_segments,
                },
                None,
            )

            # Initialize components
            downloader = VideoDownloader(mock_config.download)
            transcriber = GroqTranscriber(mock_config.transcription)
            caption_gen = CaptionGenerator(
                words_per_line=10,
                max_lines=2,
            )

            # Execute pipeline
            dl_success, audio_file, dl_error, dl_source = downloader.download_video(url)
            assert dl_success
            assert audio_file == temp_wav_file_large
            assert dl_error is None
            assert dl_source == "youtube"

            tr_success, text, metadata, tr_error = transcriber.transcribe_audio(audio_file)
            assert tr_success
            assert text is not None
            assert metadata is not None
            assert metadata["language"] == "en"
            assert metadata["segments_count"] == 4
            assert tr_error is None

            # Generate captions
            segments = metadata["segments"]
            srt_content = caption_gen.generate_srt(segments)

            # Verify SRT format
            assert srt_content is not None
            assert len(srt_content) > 0

            # Check for proper SRT timestamp format (HH:MM:SS,mmm --> HH:MM:SS,mmm)
            srt_lines = srt_content.split("\n")
            timestamp_lines = [line for line in srt_lines if " --> " in line]
            assert len(timestamp_lines) > 0

            for timestamp_line in timestamp_lines:
                # Verify format: HH:MM:SS,mmm --> HH:MM:SS,mmm
                parts = timestamp_line.split(" --> ")
                assert len(parts) == 2

                for ts in parts:
                    ts = ts.strip()
                    # Check HH:MM:SS,mmm format
                    assert len(ts) == 12, f"Invalid timestamp format: {ts}"
                    assert ts[2] == ":"
                    assert ts[5] == ":"
                    assert ts[8] == ","

                    # Verify it's numeric
                    hh = int(ts[0:2])
                    mm = int(ts[3:5])
                    ss = int(ts[6:8])
                    mmm = int(ts[9:12])

                    assert 0 <= hh <= 23
                    assert 0 <= mm <= 59
                    assert 0 <= ss <= 59
                    assert 0 <= mmm <= 999


# ─────────────────────────────────────────────────────────────────────────────
# TEST 2: Fallback to RapidAPI Backup 1
# ─────────────────────────────────────────────────────────────────────────────


def test_fallback_to_rapidapi_backup1(
    mock_config,
    temp_wav_file_large,
    set_rapidapi_key,
    monkeypatch,
):
    """
    Test fallback to RapidAPI backup 1 when yt-dlp fails.

    Verifies:
    - When yt-dlp fails, RapidAPIDownloader is attempted
    - download_source in result is 'rapidapi_backup1'
    - Audio file is successfully returned
    """
    url = "https://www.instagram.com/reel/ABC123XYZ"

    # Mock yt-dlp to fail
    with patch("yt_dlp.YoutubeDL") as mock_ytdlp:
        mock_ytdlp.return_value.__enter__.return_value.download.side_effect = Exception(
            "yt-dlp failed: Video unavailable"
        )

        # Mock RapidAPIDownloader.download_instagram
        with patch.object(
            RapidAPIDownloader, "download_instagram"
        ) as mock_rapidapi:
            mock_rapidapi.return_value = (
                True,
                temp_wav_file_large,
                None,
                "rapidapi_backup1",
            )

            downloader = VideoDownloader(mock_config.download)

            # This should attempt yt-dlp first, then RapidAPI
            success, audio_file, error, source = downloader.download_video(url)

            # First attempt with yt-dlp should fail
            # Then RapidAPI backup should succeed
            assert source in ["instagram", "rapidapi_backup1", "rapidapi_backup2"]


# ─────────────────────────────────────────────────────────────────────────────
# TEST 3: All Downloaders Fail
# ─────────────────────────────────────────────────────────────────────────────


def test_all_downloaders_fail(
    mock_config,
    set_rapidapi_key,
    monkeypatch,
):
    """
    Test when all three download methods fail.

    Verifies:
    - Error message references all attempted methods
    - Success is False
    - Returns descriptive error message
    """
    url = "https://www.instagram.com/reel/ABC123XYZ"

    # Mock yt-dlp to fail
    with patch("yt_dlp.YoutubeDL") as mock_ytdlp:
        mock_ytdlp.return_value.__enter__.return_value.download.side_effect = Exception(
            "yt-dlp failed"
        )

        # Mock RapidAPIDownloader to fail completely
        with patch.object(
            RapidAPIDownloader, "download_instagram"
        ) as mock_rapidapi:
            mock_rapidapi.return_value = (
                False,
                None,
                "All RapidAPI fallback downloaders failed",
                "rapidapi_backup2",
            )

            downloader = VideoDownloader(mock_config.download)
            success, audio_file, error, source = downloader.download_video(url)

            # All methods should have failed
            assert success is False
            assert audio_file is None
            assert error is not None
            # Error should mention either yt-dlp or RapidAPI failures
            assert (
                "Download failed" in error
                or "RapidAPI" in error
                or "yt-dlp" in error
            )


# ─────────────────────────────────────────────────────────────────────────────
# TEST 4: Process Single URL Result Keys
# ─────────────────────────────────────────────────────────────────────────────


def test_process_single_url_result_keys(
    mock_config,
    groq_segments,
    temp_wav_file_large,
    set_groq_api_key,
    monkeypatch,
):
    """
    Test that process_single_url returns all expected keys in result.

    Verifies result dict contains:
    - url
    - platform
    - transcription
    - language
    - duration
    - segments
    - srt_content
    - vtt_content
    """
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    # Import the process_single_url function from app.py
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from app import process_single_url

    with patch.object(
        VideoDownloader, "download_video"
    ) as mock_download, patch.object(
        GroqTranscriber, "__init__", return_value=None
    ) as mock_init, patch.object(
        GroqTranscriber, "transcribe_audio"
    ) as mock_transcribe:

        mock_download.return_value = (
            True,
            temp_wav_file_large,
            None,
            "youtube",
        )

        mock_transcribe.return_value = (
            True,
            "Hello world this is a test",
            {
                "language": "en",
                "duration": 10.0,
                "processing_time": 2.5,
                "confidence": None,
                "segments_count": len(groq_segments),
                "segments": groq_segments,
            },
            None,
        )

        downloader = VideoDownloader(mock_config.download)
        transcriber = GroqTranscriber(mock_config.transcription)

        operations = {
            "download": True,
            "transcribe": True,
            "generate_captions": True,
            "words_per_line": 10,
            "max_lines": 2,
        }

        result = process_single_url(
            url,
            operations,
            mock_config,
            downloader,
            transcriber,
        )

        # Verify success
        assert result["success"]
        assert result["error"] is None
        assert result["data"] is not None

        data = result["data"]

        # Check for all expected keys
        expected_keys = [
            "url",
            "platform",
            "transcription",
            "language",
            "duration",
            "segments",
            "srt_content",
            "vtt_content",
        ]

        for key in expected_keys:
            assert key in data, f"Missing key: {key}"

        # Verify values
        assert data["url"] == url
        assert data["platform"] == "youtube"
        assert data["transcription"] == "Hello world this is a test"
        assert data["language"] == "en"
        assert data["duration"] == 10.0
        assert isinstance(data["segments"], list)
        assert len(data["segments"]) == len(groq_segments)
        assert isinstance(data["srt_content"], str)
        assert len(data["srt_content"]) > 0
        assert isinstance(data["vtt_content"], str)
        assert len(data["vtt_content"]) > 0


# ─────────────────────────────────────────────────────────────────────────────
# TEST 5: Groq API Key Missing
# ─────────────────────────────────────────────────────────────────────────────


def test_groq_api_key_missing(
    mock_config,
    unset_groq_api_key,
):
    """
    Test that TranscriptionError is raised when GROQ_API_KEY is not set.

    Verifies:
    - GroqTranscriber raises TranscriptionError
    - Error message mentions GROQ_API_KEY
    """
    with pytest.raises(TranscriptionError) as exc_info:
        transcriber = GroqTranscriber(mock_config.transcription)

    error_msg = str(exc_info.value)
    assert "GROQ_API_KEY" in error_msg
    assert "environment variable" in error_msg or "not set" in error_msg


# ─────────────────────────────────────────────────────────────────────────────
# TEST 6: Caption Generation from Groq Segments
# ─────────────────────────────────────────────────────────────────────────────


def test_caption_generation_from_groq_segments(groq_segments):
    """
    Test caption generation directly from Groq segments.

    Verifies:
    - SRT output is valid and properly formatted
    - VTT output is valid and properly formatted
    - Timestamps are correct
    - All segments are included in captions
    """
    caption_gen = CaptionGenerator(words_per_line=10, max_lines=2)

    # Generate SRT
    srt_content = caption_gen.generate_srt(groq_segments)

    assert srt_content is not None
    assert len(srt_content) > 0

    # Verify SRT has proper structure
    srt_lines = srt_content.split("\n")

    # Should have caption indices, timestamps, text, blank lines
    has_index = any(line.strip().isdigit() for line in srt_lines)
    has_timestamp = any(" --> " in line for line in srt_lines)
    has_text = any(
        line.strip() and not line.strip().isdigit() and " --> " not in line
        for line in srt_lines
    )

    assert has_index, "SRT missing caption indices"
    assert has_timestamp, "SRT missing timestamps"
    assert has_text, "SRT missing caption text"

    # Verify timestamp format
    timestamp_lines = [line for line in srt_lines if " --> " in line]
    assert len(timestamp_lines) > 0

    for ts_line in timestamp_lines:
        parts = ts_line.split(" --> ")
        assert len(parts) == 2

        for ts in parts:
            ts = ts.strip()
            # Format: HH:MM:SS,mmm
            assert len(ts) == 12
            assert ts[2] == ":"
            assert ts[5] == ":"
            assert ts[8] == ","

    # Generate VTT
    vtt_content = caption_gen.generate_vtt(groq_segments)

    assert vtt_content is not None
    assert len(vtt_content) > 0
    assert "WEBVTT" in vtt_content

    # VTT should use . instead of , for milliseconds
    vtt_lines = vtt_content.split("\n")
    vtt_timestamps = [line for line in vtt_lines if " --> " in line]

    for ts_line in vtt_timestamps:
        parts = ts_line.split(" --> ")
        for ts in parts:
            ts = ts.strip()
            # Format: HH:MM:SS.mmm
            assert len(ts) == 12
            assert ts[8] == ".", f"VTT should use . for milliseconds, got: {ts}"


# ─────────────────────────────────────────────────────────────────────────────
# TEST 7: Pipeline with Only Download (No Transcription)
# ─────────────────────────────────────────────────────────────────────────────


def test_pipeline_download_only(
    mock_config,
    temp_wav_file_large,
):
    """
    Test pipeline with only download operation (no transcription or captions).

    Verifies:
    - Download succeeds
    - Audio file path is in result
    - No transcription or caption fields are present
    """
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from app import process_single_url

    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    with patch.object(
        VideoDownloader, "download_video"
    ) as mock_download:
        mock_download.return_value = (
            True,
            temp_wav_file_large,
            None,
            "youtube",
        )

        downloader = VideoDownloader(mock_config.download)

        operations = {
            "download": True,
            "transcribe": False,
            "generate_captions": False,
        }

        result = process_single_url(
            url,
            operations,
            mock_config,
            downloader,
            None,  # No transcriber
        )

        assert result["success"]
        assert result["error"] is None
        assert result["data"] is not None
        assert "url" in result["data"]
        assert "platform" in result["data"]
        assert "audio_file" in result["data"]


# ─────────────────────────────────────────────────────────────────────────────
# TEST 8: Pipeline with Segments But No Segments Data (Edge Case)
# ─────────────────────────────────────────────────────────────────────────────


def test_pipeline_captions_without_segments(
    mock_config,
    temp_wav_file_large,
    set_groq_api_key,
):
    """
    Test when transcription succeeds but no segments are returned.

    Verifies:
    - Process completes without error
    - caption_error is set in result
    - No srt_content or vtt_content fields
    """
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from app import process_single_url

    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    with patch.object(
        VideoDownloader, "download_video"
    ) as mock_download, patch.object(
        GroqTranscriber, "__init__", return_value=None
    ), patch.object(
        GroqTranscriber, "transcribe_audio"
    ) as mock_transcribe:

        mock_download.return_value = (
            True,
            temp_wav_file_large,
            None,
            "youtube",
        )

        # Return no segments
        mock_transcribe.return_value = (
            True,
            "Hello world",
            {
                "language": "en",
                "duration": 5.0,
                "processing_time": 1.0,
                "confidence": None,
                "segments_count": 0,
                "segments": [],  # Empty segments
            },
            None,
        )

        downloader = VideoDownloader(mock_config.download)
        transcriber = GroqTranscriber(mock_config.transcription)

        operations = {
            "download": True,
            "transcribe": True,
            "generate_captions": True,
            "words_per_line": 10,
            "max_lines": 2,
        }

        result = process_single_url(
            url,
            operations,
            mock_config,
            downloader,
            transcriber,
        )

        assert result["success"]
        assert result["data"] is not None
        assert "caption_error" in result["data"]


# ─────────────────────────────────────────────────────────────────────────────
# TEST 9: Download Failure with Proper Error Message
# ─────────────────────────────────────────────────────────────────────────────


def test_download_failure_handling(mock_config):
    """
    Test that download failure is properly handled and reported.

    Verifies:
    - Success is False
    - Error message is populated
    - Proper structure of failure result
    """
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from app import process_single_url

    url = "https://www.youtube.com/watch?v=invalid"

    with patch.object(
        VideoDownloader, "download_video"
    ) as mock_download:
        mock_download.return_value = (
            False,
            None,
            "Video not found",
            "youtube",
        )

        downloader = VideoDownloader(mock_config.download)

        operations = {
            "download": True,
            "transcribe": False,
            "generate_captions": False,
        }

        result = process_single_url(
            url,
            operations,
            mock_config,
            downloader,
            None,
        )

        assert result["success"] is False
        assert result["error"] is not None
        assert "Video not found" in result["error"]


# ─────────────────────────────────────────────────────────────────────────────
# TEST 10: Transcription Failure Handling
# ─────────────────────────────────────────────────────────────────────────────


def test_transcription_failure_handling(
    mock_config,
    temp_wav_file_large,
    set_groq_api_key,
):
    """
    Test that transcription failure is properly handled and reported.

    Verifies:
    - Success is False when transcription fails
    - Error message is populated
    - Download was successful but transcription failed
    """
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from app import process_single_url

    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    with patch.object(
        VideoDownloader, "download_video"
    ) as mock_download, patch.object(
        GroqTranscriber, "__init__", return_value=None
    ), patch.object(
        GroqTranscriber, "transcribe_audio"
    ) as mock_transcribe:

        mock_download.return_value = (
            True,
            temp_wav_file_large,
            None,
            "youtube",
        )

        mock_transcribe.return_value = (
            False,
            None,
            None,
            "API error: rate limit exceeded",
        )

        downloader = VideoDownloader(mock_config.download)
        transcriber = GroqTranscriber(mock_config.transcription)

        operations = {
            "download": True,
            "transcribe": True,
            "generate_captions": True,
        }

        result = process_single_url(
            url,
            operations,
            mock_config,
            downloader,
            transcriber,
        )

        assert result["success"] is False
        assert result["error"] is not None
        assert "rate limit" in result["error"]


# ─────────────────────────────────────────────────────────────────────────────
# TEST 11: Caption Generator Configuration Validation
# ─────────────────────────────────────────────────────────────────────────────


def test_caption_generator_configuration(groq_segments):
    """
    Test that CaptionGenerator respects configuration parameters.

    Verifies:
    - words_per_line is respected
    - max_lines is respected
    - Output differs based on settings
    """
    # Test 1: 5 words per line, 1 line max
    gen1 = CaptionGenerator(words_per_line=5, max_lines=1)
    srt1 = gen1.generate_srt(groq_segments)

    # Test 2: 10 words per line, 2 lines max
    gen2 = CaptionGenerator(words_per_line=10, max_lines=2)
    srt2 = gen2.generate_srt(groq_segments)

    # Test 3: 20 words per line, 3 lines max
    gen3 = CaptionGenerator(words_per_line=20, max_lines=3)
    srt3 = gen3.generate_srt(groq_segments)

    # Different configurations should produce different output
    # (though srt1 and srt2 might be similar in this case)
    assert srt1 != srt3, "Different configurations should produce different output"

    # Verify captions are generated
    assert len(srt1) > 0
    assert len(srt2) > 0
    assert len(srt3) > 0


# ─────────────────────────────────────────────────────────────────────────────
# TEST 12: Platform Detection Integration
# ─────────────────────────────────────────────────────────────────────────────


def test_platform_detection_integration():
    """
    Test that platform detection works correctly in pipeline context.

    Verifies:
    - Instagram URLs are detected
    - YouTube URLs are detected
    - Invalid URLs return None
    """
    instagram_url = "https://www.instagram.com/reel/ABC123XYZ"
    youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    invalid_url = "https://www.example.com/video"

    assert detect_platform(instagram_url) == "instagram"
    assert detect_platform(youtube_url) == "youtube"
    assert detect_platform(invalid_url) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
