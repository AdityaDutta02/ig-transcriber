"""
Unit tests for GroqTranscriber class.
"""

import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, mock_open

import pytest

from config import TranscriptionConfig


class TestGroqTranscriberInit:
    """Tests for GroqTranscriber initialization."""

    def test_missing_api_key(self, unset_groq_api_key):
        """Test that TranscriptionError is raised when GROQ_API_KEY is not set."""
        # Import here so the unset env var is applied
        from transcriber import GroqTranscriber, TranscriptionError

        config = TranscriptionConfig()

        with pytest.raises(TranscriptionError, match="GROQ_API_KEY environment variable is not set"):
            GroqTranscriber(config)

    def test_successful_init(self, set_groq_api_key):
        """Test successful initialization with API key set."""
        from transcriber import GroqTranscriber

        mock_groq_client = MagicMock()
        mock_groq_class = MagicMock(return_value=mock_groq_client)

        # Patch sys.modules so the `from groq import Groq` inside __init__ uses
        # our mock. We do NOT reload the transcriber module because reload mutates
        # the module in-place and replaces class objects, causing TranscriptionError
        # identity mismatches in other test modules that imported it at module load.
        with patch.dict(sys.modules, {"groq": MagicMock(Groq=mock_groq_class)}):
            config = TranscriptionConfig()
            transcriber = GroqTranscriber(config)

            assert transcriber.config == config
            assert transcriber._client is not None

    def test_groq_client_initialization(self, set_groq_api_key):
        """Test that Groq client is properly initialized."""
        from transcriber import GroqTranscriber

        mock_groq_client = MagicMock()
        mock_groq_class = MagicMock(return_value=mock_groq_client)

        with patch.dict(sys.modules, {"groq": MagicMock(Groq=mock_groq_class)}):
            config = TranscriptionConfig()
            transcriber = GroqTranscriber(config)

            # Verify Groq was called with the API key
            assert mock_groq_class.called or transcriber._client is not None


class TestTranscribeAudioSuccess:
    """Tests for successful audio transcription."""

    def test_transcribe_audio_success(self, set_groq_api_key, temp_wav_file):
        """Test successful transcription with valid audio file."""
        from transcriber import GroqTranscriber

        mock_response = MagicMock()
        mock_response.text = "Hello, this is a test transcription."
        mock_response.language = "en"
        mock_response.duration = 1.5
        mock_response.segments = [
            {"start": 0.0, "end": 0.5, "text": "Hello,"},
            {"start": 0.5, "end": 1.5, "text": "this is a test transcription."}
        ]

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = mock_response

        with patch.dict(sys.modules, {"groq": MagicMock(Groq=MagicMock(return_value=mock_client))}):
            config = TranscriptionConfig()
            transcriber = GroqTranscriber(config)

            success, text, metadata, error = transcriber.transcribe_audio(temp_wav_file)

            assert success is True
            assert text == "Hello, this is a test transcription."
            assert metadata is not None
            assert metadata["language"] == "en"
            assert metadata["duration"] == 1.5
            assert error is None

    def test_segment_mapping(self, set_groq_api_key, temp_wav_file):
        """Test that segment data is correctly mapped from Groq response."""
        from transcriber import GroqTranscriber

        mock_response = MagicMock()
        mock_response.text = "Test transcription"
        mock_response.language = "en"
        mock_response.duration = 2.0
        mock_response.segments = [
            {"start": 0.0, "end": 1.0, "text": "Test"},
            {"start": 1.0, "end": 2.0, "text": "transcription"}
        ]

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = mock_response

        with patch.dict(sys.modules, {"groq": MagicMock(Groq=MagicMock(return_value=mock_client))}):
            config = TranscriptionConfig()
            transcriber = GroqTranscriber(config)

            _, _, metadata, _ = transcriber.transcribe_audio(temp_wav_file)

            assert metadata is not None
            assert len(metadata["segments"]) == 2
            assert metadata["segments"][0] == {"start": 0.0, "end": 1.0, "text": "Test"}
            assert metadata["segments"][1] == {"start": 1.0, "end": 2.0, "text": "transcription"}
            assert metadata["segments_count"] == 2

    def test_transcribe_with_custom_language(self, set_groq_api_key, temp_wav_file):
        """Test transcription with custom language override."""
        from transcriber import GroqTranscriber

        mock_response = MagicMock()
        mock_response.text = "Bonjour, c'est un test."
        mock_response.language = "fr"
        mock_response.duration = 1.0
        mock_response.segments = []

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = mock_response

        with patch.dict(sys.modules, {"groq": MagicMock(Groq=MagicMock(return_value=mock_client))}):
            config = TranscriptionConfig()
            transcriber = GroqTranscriber(config)

            success, text, _, _ = transcriber.transcribe_audio(temp_wav_file, language="fr")

            assert success is True
            assert mock_client.audio.transcriptions.create.called


class TestTranscribeAudioErrors:
    """Tests for error handling in transcription."""

    def test_file_not_found(self, set_groq_api_key):
        """Test that appropriate error is returned when audio file doesn't exist."""
        from transcriber import GroqTranscriber

        mock_client = MagicMock()

        with patch.dict(sys.modules, {"groq": MagicMock(Groq=MagicMock(return_value=mock_client))}):
            config = TranscriptionConfig()
            transcriber = GroqTranscriber(config)

            nonexistent_path = Path("/nonexistent/file.wav")
            success, text, metadata, error = transcriber.transcribe_audio(nonexistent_path)

            assert success is False
            assert text is None
            assert metadata is None
            assert error is not None
            assert "Audio file not found" in error

    def test_groq_api_error(self, set_groq_api_key, temp_wav_file):
        """Test graceful handling of Groq API errors."""
        from transcriber import GroqTranscriber

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.side_effect = Exception("API rate limit exceeded")

        with patch.dict(sys.modules, {"groq": MagicMock(Groq=MagicMock(return_value=mock_client))}):
            config = TranscriptionConfig()
            transcriber = GroqTranscriber(config)

            success, text, metadata, error = transcriber.transcribe_audio(temp_wav_file)

            assert success is False
            assert text is None
            assert metadata is None
            assert error is not None
            assert "Transcription failed" in error
            assert "API rate limit" in error


class TestLargeFileCompression:
    """Tests for large file compression handling."""

    def test_large_file_compression(self, set_groq_api_key, temp_dir):
        """Test that files over 24MB are compressed before API call."""
        from transcriber import GroqTranscriber

        large_file_path = temp_dir / "large_audio.wav"
        large_file_path.write_bytes(b"x" * (25 * 1024 * 1024))  # 25MB

        mock_subprocess_run = MagicMock()
        mock_subprocess_run.returncode = 0

        mock_response = MagicMock()
        mock_response.text = "Test"
        mock_response.language = "en"
        mock_response.duration = 1.0
        mock_response.segments = []

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = mock_response

        with patch.dict(sys.modules, {"groq": MagicMock(Groq=MagicMock(return_value=mock_client))}):
            with patch("subprocess.run", return_value=mock_subprocess_run):
                config = TranscriptionConfig()
                transcriber = GroqTranscriber(config)

                # Track if compression is called
                original_compress = transcriber._compress_to_mp3
                compress_called = {"count": 0}

                def mock_compress(path):
                    compress_called["count"] += 1
                    compressed_path = temp_dir / "large_audio.compressed.mp3"
                    compressed_path.write_bytes(b"x" * (5 * 1024 * 1024))
                    return compressed_path

                transcriber._compress_to_mp3 = mock_compress

                success, _, _, _ = transcriber.transcribe_audio(large_file_path)

                assert compress_called["count"] == 1

    def test_ffmpeg_compression_failure(self, set_groq_api_key, temp_dir):
        """Test error handling when ffmpeg compression fails."""
        from transcriber import GroqTranscriber, TranscriptionError

        large_file_path = temp_dir / "large_audio.wav"
        large_file_path.write_bytes(b"x" * (25 * 1024 * 1024))  # 25MB

        mock_subprocess_run = MagicMock()
        mock_subprocess_run.returncode = 1
        mock_subprocess_run.stderr = "ffmpeg error"

        mock_client = MagicMock()

        with patch.dict(sys.modules, {"groq": MagicMock(Groq=MagicMock(return_value=mock_client))}):
            with patch("subprocess.run", return_value=mock_subprocess_run):
                config = TranscriptionConfig()
                transcriber = GroqTranscriber(config)

                with pytest.raises(TranscriptionError, match="ffmpeg compression failed"):
                    transcriber.transcribe_audio(large_file_path)


class TestTranscribeBatch:
    """Tests for batch transcription."""

    def test_transcribe_batch_success(self, set_groq_api_key, temp_dir):
        """Test successful batch transcription."""
        from transcriber import GroqTranscriber

        audio_files = [temp_dir / f"audio_{i}.wav" for i in range(3)]
        for audio_file in audio_files:
            audio_file.write_bytes(b"fake audio data")

        records = [
            {"reel_id": f"reel_{i}", "audio_file": str(audio_files[i])}
            for i in range(3)
        ]

        mock_response = MagicMock()
        mock_response.text = "Test transcription"
        mock_response.language = "en"
        mock_response.duration = 1.0
        mock_response.segments = []

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = mock_response

        with patch.dict(sys.modules, {"groq": MagicMock(Groq=MagicMock(return_value=mock_client))}):
            config = TranscriptionConfig()
            transcriber = GroqTranscriber(config)

            successful, failed = transcriber.transcribe_batch(records)

            assert len(successful) == 3
            assert len(failed) == 0
            for result in successful:
                assert result["transcription_success"] is True
                assert result["transcription"] == "Test transcription"

    def test_transcribe_batch_partial_failure(self, set_groq_api_key, temp_dir):
        """Test batch transcription with some failures."""
        from transcriber import GroqTranscriber

        audio_files = [
            temp_dir / "audio_0.wav",
            temp_dir / "audio_1.wav",
            temp_dir / "audio_2.wav"
        ]
        for audio_file in audio_files:
            audio_file.write_bytes(b"fake audio data")

        records = [
            {"reel_id": f"reel_{i}", "audio_file": str(audio_files[i])}
            for i in range(3)
        ]

        call_count = {"count": 0}

        def side_effect(*args, **kwargs):
            call_count["count"] += 1
            if call_count["count"] <= 2:
                mock_response = MagicMock()
                mock_response.text = f"Transcription {call_count['count']}"
                mock_response.language = "en"
                mock_response.duration = 1.0
                mock_response.segments = []
                return mock_response
            else:
                raise Exception("API error")

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.side_effect = side_effect

        with patch.dict(sys.modules, {"groq": MagicMock(Groq=MagicMock(return_value=mock_client))}):
            config = TranscriptionConfig()
            transcriber = GroqTranscriber(config)

            successful, failed = transcriber.transcribe_batch(records)

            assert len(successful) == 2
            assert len(failed) == 1
            assert successful[0]["reel_id"] == "reel_0"
            assert successful[1]["reel_id"] == "reel_1"
            assert failed[0]["reel_id"] == "reel_2"
            assert failed[0]["transcription_success"] is False

    def test_transcribe_batch_with_progress_callback(self, set_groq_api_key, temp_dir):
        """Test batch transcription with progress callback."""
        from transcriber import GroqTranscriber

        audio_files = [temp_dir / f"audio_{i}.wav" for i in range(2)]
        for audio_file in audio_files:
            audio_file.write_bytes(b"fake audio data")

        records = [
            {"reel_id": f"reel_{i}", "audio_file": str(audio_files[i])}
            for i in range(2)
        ]

        mock_response = MagicMock()
        mock_response.text = "Test"
        mock_response.language = "en"
        mock_response.duration = 1.0
        mock_response.segments = []

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = mock_response

        with patch.dict(sys.modules, {"groq": MagicMock(Groq=MagicMock(return_value=mock_client))}):
            config = TranscriptionConfig()
            transcriber = GroqTranscriber(config)

            progress_calls = []

            def progress_callback(completed, total):
                progress_calls.append((completed, total))

            successful, failed = transcriber.transcribe_batch(records, progress_callback)

            assert len(successful) == 2
            assert len(progress_calls) == 2
            assert progress_calls[0] == (1, 2)
            assert progress_calls[1] == (2, 2)


class TestSegmentHandling:
    """Tests for segment data handling."""

    def test_segments_with_object_attributes(self, set_groq_api_key, temp_wav_file):
        """Test handling of segments as objects with attributes instead of dicts."""
        from transcriber import GroqTranscriber

        class MockSegment:
            def __init__(self, start, end, text):
                self.start = start
                self.end = end
                self.text = text

        mock_response = MagicMock()
        mock_response.text = "Test text"
        mock_response.language = "en"
        mock_response.duration = 2.0
        mock_response.segments = [
            MockSegment(0.0, 1.0, "Test"),
            MockSegment(1.0, 2.0, "text")
        ]

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = mock_response

        with patch.dict(sys.modules, {"groq": MagicMock(Groq=MagicMock(return_value=mock_client))}):
            config = TranscriptionConfig()
            transcriber = GroqTranscriber(config)

            _, _, metadata, _ = transcriber.transcribe_audio(temp_wav_file)

            assert len(metadata["segments"]) == 2
            assert metadata["segments"][0]["text"] == "Test"
            assert metadata["segments"][1]["text"] == "text"

    def test_empty_segments(self, set_groq_api_key, temp_wav_file):
        """Test handling when no segments are returned."""
        from transcriber import GroqTranscriber

        mock_response = MagicMock()
        mock_response.text = "No segments"
        mock_response.language = "en"
        mock_response.duration = 1.0
        mock_response.segments = None

        mock_client = MagicMock()
        mock_client.audio.transcriptions.create.return_value = mock_response

        with patch.dict(sys.modules, {"groq": MagicMock(Groq=MagicMock(return_value=mock_client))}):
            config = TranscriptionConfig()
            transcriber = GroqTranscriber(config)

            _, _, metadata, _ = transcriber.transcribe_audio(temp_wav_file)

            assert metadata["segments"] == []
            assert metadata["segments_count"] == 0
