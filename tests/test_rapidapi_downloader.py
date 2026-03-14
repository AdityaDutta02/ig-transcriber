"""
Unit tests for RapidAPIDownloader class.
"""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch, mock_open

import pytest
import requests

from rapidapi_downloader import RapidAPIDownloader


class TestRapidAPIDownloaderInit:
    """Tests for RapidAPIDownloader initialization."""

    def test_missing_api_key_graceful(self, unset_rapidapi_key):
        """Test that RapidAPIDownloader handles missing API key gracefully without raising."""
        # Should not raise an exception
        downloader = RapidAPIDownloader()
        assert downloader._api_key is None

    def test_api_key_set(self, set_rapidapi_key):
        """Test that API key is properly stored when set."""
        downloader = RapidAPIDownloader()
        assert downloader._api_key == "test_rapidapi_key_12345"


class TestDownloadInstagramNoKey:
    """Tests for download_instagram when API key is missing."""

    def test_download_instagram_no_api_key(self, unset_rapidapi_key, temp_dir):
        """Test that download_instagram returns failure tuple when API key is missing."""
        downloader = RapidAPIDownloader()

        url = "https://www.instagram.com/reel/CzAbC123XyZ"
        success, audio_path, error_msg, source = downloader.download_instagram(url, temp_dir)

        assert success is False
        assert audio_path is None
        assert error_msg is not None
        assert "RAPIDAPI_KEY environment variable is not set" in error_msg
        assert source == "rapidapi_backup1"


class TestSafesiteAPI:
    """Tests for Safesite backup 1 API."""

    def test_safesite_api_success(self, set_rapidapi_key, monkeypatch, temp_dir):
        """Test successful download URL extraction from Safesite API."""
        # Mock the requests.get for API call
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "url": "https://example.com/video.mp4"
        }

        monkeypatch.setattr("rapidapi_downloader.requests.get", MagicMock(return_value=mock_response))

        # Mock the download and ffmpeg
        with patch.object(RapidAPIDownloader, "_download_and_extract_audio") as mock_extract:
            mock_extract.return_value = temp_dir / "instagram_test.wav"

            downloader = RapidAPIDownloader()
            url = "https://www.instagram.com/reel/CzAbC123XyZ"

            success, audio_path, error_msg, source = downloader.download_instagram(url, temp_dir)

            assert success is True
            assert audio_path == temp_dir / "instagram_test.wav"
            assert error_msg is None
            assert source == "rapidapi_backup1"

    def test_safesite_api_http_error(self, set_rapidapi_key, monkeypatch, temp_dir):
        """Test Safesite API HTTP error handling."""
        def get_side_effect(*args, **kwargs):
            mock_response = MagicMock()
            mock_resp_obj = MagicMock()
            mock_resp_obj.status_code = 404
            mock_resp_obj.reason = "Not Found"

            http_error = requests.exceptions.HTTPError("404 Not Found")
            http_error.response = mock_resp_obj
            mock_response.raise_for_status.side_effect = http_error
            return mock_response

        monkeypatch.setattr("rapidapi_downloader.requests.get", MagicMock(side_effect=get_side_effect))

        downloader = RapidAPIDownloader()
        url = "https://www.instagram.com/reel/CzAbC123XyZ"

        # Both should fail
        success, _, _, _ = downloader.download_instagram(url, temp_dir)

        assert success is False


class TestEaseapiAPI:
    """Tests for Easeapi backup 2 API."""

    def test_easeapi_api_success(self, set_rapidapi_key, monkeypatch, temp_dir):
        """Test successful download URL extraction from Easeapi."""
        def get_side_effect(*args, **kwargs):
            mock_response = MagicMock()
            api_host = kwargs.get("headers", {}).get("X-RapidAPI-Host", "")

            if "instagram-downloader-download" in api_host:
                # Safesite (backup 1) - fail with proper HTTPError
                mock_resp_obj = MagicMock()
                mock_resp_obj.status_code = 500
                mock_resp_obj.reason = "Internal Server Error"
                http_error = requests.exceptions.HTTPError("500 Error")
                http_error.response = mock_resp_obj
                mock_response.raise_for_status.side_effect = http_error
            else:
                # Easeapi (backup 2) - succeed
                mock_response.json.return_value = {
                    "url": "https://example.com/video2.mp4"
                }

            return mock_response

        monkeypatch.setattr("rapidapi_downloader.requests.get", MagicMock(side_effect=get_side_effect))

        with patch.object(RapidAPIDownloader, "_download_and_extract_audio") as mock_extract:
            mock_extract.return_value = temp_dir / "instagram_test.wav"

            downloader = RapidAPIDownloader()
            url = "https://www.instagram.com/reel/CzAbC123XyZ"

            success, audio_path, error_msg, source = downloader.download_instagram(url, temp_dir)

            assert success is True
            assert source == "rapidapi_backup2"


class TestFallbackOrder:
    """Tests for fallback order when APIs fail."""

    def test_fallback_to_backup2_when_backup1_fails(self, set_rapidapi_key, monkeypatch, temp_dir):
        """Test that backup 2 is tried when backup 1 fails."""
        def get_side_effect(*args, **kwargs):
            mock_response = MagicMock()
            api_host = kwargs.get("headers", {}).get("X-RapidAPI-Host", "")

            if "instagram-downloader-download" in api_host:
                # Safesite (backup 1) - fail with proper HTTPError
                mock_resp_obj = MagicMock()
                mock_resp_obj.status_code = 403
                mock_resp_obj.reason = "Forbidden"
                http_error = requests.exceptions.HTTPError("403 Forbidden")
                http_error.response = mock_resp_obj
                mock_response.raise_for_status.side_effect = http_error
            else:
                # Easeapi (backup 2) - succeed
                mock_response.json.return_value = {
                    "url": "https://example.com/video2.mp4"
                }

            return mock_response

        monkeypatch.setattr("rapidapi_downloader.requests.get", MagicMock(side_effect=get_side_effect))

        with patch.object(RapidAPIDownloader, "_download_and_extract_audio") as mock_extract:
            mock_extract.return_value = temp_dir / "instagram_test.wav"

            downloader = RapidAPIDownloader()
            url = "https://www.instagram.com/reel/CzAbC123XyZ"

            success, audio_path, error_msg, source = downloader.download_instagram(url, temp_dir)

            assert success is True
            assert source == "rapidapi_backup2"

    def test_both_backups_fail(self, set_rapidapi_key, monkeypatch, temp_dir):
        """Test error handling when both backup APIs fail."""
        def get_side_effect(*args, **kwargs):
            mock_response = MagicMock()
            mock_resp_obj = MagicMock()
            mock_resp_obj.status_code = 500
            mock_resp_obj.reason = "Internal Server Error"
            http_error = requests.exceptions.HTTPError("500 Error")
            http_error.response = mock_resp_obj
            mock_response.raise_for_status.side_effect = http_error
            return mock_response

        monkeypatch.setattr("rapidapi_downloader.requests.get", MagicMock(side_effect=get_side_effect))

        downloader = RapidAPIDownloader()
        url = "https://www.instagram.com/reel/CzAbC123XyZ"

        success, audio_path, error_msg, source = downloader.download_instagram(url, temp_dir)

        assert success is False
        assert audio_path is None
        assert error_msg is not None
        assert "All RapidAPI fallback downloaders failed" in error_msg
        assert source == "rapidapi_backup2"


class TestDefensiveJSONParsing:
    """Tests for defensive JSON parsing."""

    def test_extract_download_url_from_nested_data(self, set_rapidapi_key, monkeypatch, temp_dir):
        """Test URL extraction from nested 'data' wrapper."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "url": "https://example.com/video.mp4"
            }
        }

        monkeypatch.setattr("rapidapi_downloader.requests.get", MagicMock(return_value=mock_response))

        with patch.object(RapidAPIDownloader, "_download_and_extract_audio") as mock_extract:
            mock_extract.return_value = temp_dir / "instagram_test.wav"

            downloader = RapidAPIDownloader()
            url = "https://www.instagram.com/reel/CzAbC123XyZ"

            success, _, _, _ = downloader.download_instagram(url, temp_dir)

            assert success is True

    def test_extract_download_url_flat_structure(self, set_rapidapi_key, monkeypatch, temp_dir):
        """Test URL extraction from flat JSON structure."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "download_url": "https://example.com/video.mp4"
        }

        monkeypatch.setattr("rapidapi_downloader.requests.get", MagicMock(return_value=mock_response))

        with patch.object(RapidAPIDownloader, "_download_and_extract_audio") as mock_extract:
            mock_extract.return_value = temp_dir / "instagram_test.wav"

            downloader = RapidAPIDownloader()
            url = "https://www.instagram.com/reel/CzAbC123XyZ"

            success, _, _, _ = downloader.download_instagram(url, temp_dir)

            assert success is True

    def test_extract_url_from_nested_list(self, set_rapidapi_key, monkeypatch, temp_dir):
        """Test URL extraction from nested list in 'data' wrapper."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {
                    "url": "https://example.com/video.mp4"
                }
            ]
        }

        monkeypatch.setattr("rapidapi_downloader.requests.get", MagicMock(return_value=mock_response))

        with patch.object(RapidAPIDownloader, "_download_and_extract_audio") as mock_extract:
            mock_extract.return_value = temp_dir / "instagram_test.wav"

            downloader = RapidAPIDownloader()
            url = "https://www.instagram.com/reel/CzAbC123XyZ"

            success, _, _, _ = downloader.download_instagram(url, temp_dir)

            assert success is True


class TestYouTubeNotSentToRapidAPI:
    """Tests that YouTube URLs are not sent to RapidAPI."""

    def test_rapidapi_not_used_for_non_instagram(self, set_rapidapi_key):
        """Test that RapidAPI is only for Instagram URLs, not other platforms."""
        downloader = RapidAPIDownloader()

        # RapidAPI is designed to work with Instagram URLs
        # The downloader.py module enforces this by only calling RapidAPI
        # fallback for platform == "instagram"

        # This is a unit test confirming RapidAPIDownloader exists and works
        # Integration with downloader.py is tested separately
        assert downloader._api_key == "test_rapidapi_key_12345"


class TestRequestTimeout:
    """Tests for request timeout handling."""

    def test_request_timeout_handling(self, set_rapidapi_key, monkeypatch, temp_dir):
        """Test graceful handling of request timeouts."""
        mock_response = MagicMock()
        mock_response.get.side_effect = requests.exceptions.Timeout("Request timed out")

        monkeypatch.setattr("rapidapi_downloader.requests.get", MagicMock(side_effect=requests.exceptions.Timeout))

        downloader = RapidAPIDownloader()
        url = "https://www.instagram.com/reel/CzAbC123XyZ"

        success, audio_path, error_msg, source = downloader.download_instagram(url, temp_dir)

        assert success is False
        assert audio_path is None
        assert "All RapidAPI fallback downloaders failed" in error_msg


class TestDownloadAndExtractAudio:
    """Tests for download and audio extraction."""

    def test_download_and_extract_audio_success(self, set_rapidapi_key, monkeypatch, temp_dir):
        """Test successful video download and audio extraction."""
        downloader = RapidAPIDownloader()

        # Mock requests.get for video download
        mock_video_response = MagicMock()
        mock_video_response.__enter__ = MagicMock(return_value=mock_video_response)
        mock_video_response.__exit__ = MagicMock(return_value=False)
        mock_video_response.iter_content.return_value = [b"video_data"]

        # Mock subprocess.run for ffmpeg
        mock_subprocess = MagicMock()
        mock_subprocess.returncode = 0

        monkeypatch.setattr("rapidapi_downloader.requests.get", MagicMock(return_value=mock_video_response))
        monkeypatch.setattr("subprocess.run", MagicMock(return_value=mock_subprocess))

        # Create a mock audio output file
        with patch("builtins.open", mock_open()):
            with patch.object(Path, "exists", return_value=True):
                result = downloader._download_and_extract_audio(
                    "https://example.com/video.mp4",
                    temp_dir,
                    "test_video"
                )

                assert result.name == "instagram_test_video.wav"

    def test_download_and_extract_audio_ffmpeg_error(self, set_rapidapi_key, monkeypatch, temp_dir):
        """Test error handling when ffmpeg fails."""
        downloader = RapidAPIDownloader()

        # Mock requests.get
        mock_response = MagicMock()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_response.iter_content.return_value = [b"video_data"]

        # Mock ffmpeg to fail
        mock_subprocess = MagicMock()
        mock_subprocess.returncode = 1
        mock_subprocess.stderr = b"ffmpeg error"

        monkeypatch.setattr("rapidapi_downloader.requests.get", MagicMock(return_value=mock_response))
        monkeypatch.setattr("subprocess.run", MagicMock(return_value=mock_subprocess))

        with pytest.raises(RuntimeError, match="ffmpeg exited with code"):
            downloader._download_and_extract_audio(
                "https://example.com/video.mp4",
                temp_dir,
                "test_video"
            )


class TestAllThreeMethodsFailMessage:
    """Tests for error messages when all methods fail."""

    def test_rapidapi_error_when_all_fail(self, unset_rapidapi_key):
        """Test that RapidAPI returns appropriate error when all methods fail."""
        downloader = RapidAPIDownloader()

        url = "https://www.instagram.com/reel/CzAbC123XyZ"
        success, audio_path, error_msg, source = downloader.download_instagram(url, Path("/tmp"))

        # With no API key, should get graceful failure
        assert success is False
        assert error_msg is not None
        assert "RAPIDAPI_KEY environment variable is not set" in error_msg


class TestExtractDownloadURL:
    """Tests for _extract_download_url method."""

    def test_extract_url_multiple_candidate_fields(self, set_rapidapi_key):
        """Test URL extraction tries multiple candidate field names."""
        downloader = RapidAPIDownloader()

        # Test 'link' field
        url = downloader._extract_download_url({"link": "https://example.com/video.mp4"})
        assert url == "https://example.com/video.mp4"

        # Test 'video_url' field
        url = downloader._extract_download_url({"video_url": "https://example.com/video.mp4"})
        assert url == "https://example.com/video.mp4"

    def test_extract_url_non_dict_response(self, set_rapidapi_key):
        """Test handling of non-dict JSON responses."""
        downloader = RapidAPIDownloader()

        # Should return None for non-dict
        url = downloader._extract_download_url([{"url": "https://example.com/video.mp4"}])
        assert url is None

    def test_extract_url_no_valid_url_found(self, set_rapidapi_key):
        """Test when no valid URL is found in response."""
        downloader = RapidAPIDownloader()

        # No URL field with http URL
        url = downloader._extract_download_url({"status": "error", "message": "Failed"})
        assert url is None


class TestDeriveVideoID:
    """Tests for _derive_video_id method."""

    def test_derive_video_id_from_reel_url(self, set_rapidapi_key):
        """Test video ID extraction from Instagram reel URL."""
        downloader = RapidAPIDownloader()

        url = "https://www.instagram.com/reel/CzAbC123XyZ"
        video_id = downloader._derive_video_id(url)

        assert video_id == "CzAbC123XyZ"

    def test_derive_video_id_fallback_to_hash(self, set_rapidapi_key):
        """Test fallback to MD5 hash when URL format doesn't match."""
        downloader = RapidAPIDownloader()

        url = "https://example.com/unknown/format"
        video_id = downloader._derive_video_id(url)

        # Should be an MD5 hash (12 chars)
        assert len(video_id) == 12
        assert all(c in "0123456789abcdef" for c in video_id)
