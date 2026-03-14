"""
Common fixtures and test utilities for the test suite.
"""

import os
import sys
import tempfile
import wave
from pathlib import Path
from typing import Generator

import pytest


# Add src directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def temp_wav_file(temp_dir: Path) -> Path:
    """Create a small temporary WAV file for testing."""
    wav_path = temp_dir / "test_audio.wav"

    # Create a minimal valid WAV file (mono, 16-bit PCM, 16 kHz, 1 second)
    sample_rate = 16000
    duration_seconds = 1
    num_samples = sample_rate * duration_seconds

    with wave.open(str(wav_path), "w") as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)

        # Write silence (zeros)
        wav_file.writeframes(b"\x00" * (num_samples * 2))

    return wav_path


@pytest.fixture
def large_wav_file(temp_dir: Path) -> Path:
    """Create a large temporary WAV file (>24MB) for testing compression."""
    wav_path = temp_dir / "large_audio.wav"

    # Create a large WAV file that exceeds 24MB limit
    sample_rate = 16000
    duration_seconds = 3000  # ~50 minutes at 16 kHz
    num_samples = sample_rate * duration_seconds

    with wave.open(str(wav_path), "w") as wav_file:
        wav_file.setnchannels(1)  # mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)

        # Write in chunks to avoid memory issues
        chunk_size = 100000
        for _ in range(0, num_samples, chunk_size):
            chunk_samples = min(chunk_size, num_samples)
            wav_file.writeframes(b"\x00" * (chunk_samples * 2))

    return wav_path


@pytest.fixture
def mock_env_cleanup():
    """Fixture to clean up environment variable changes after test."""
    original_env = os.environ.copy()
    yield
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def unset_groq_api_key(monkeypatch):
    """Unset GROQ_API_KEY for testing missing API key scenarios."""
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    return monkeypatch


@pytest.fixture
def unset_rapidapi_key(monkeypatch):
    """Unset RAPIDAPI_KEY for testing missing API key scenarios."""
    monkeypatch.delenv("RAPIDAPI_KEY", raising=False)
    return monkeypatch


@pytest.fixture
def set_groq_api_key(monkeypatch):
    """Set a mock GROQ_API_KEY for testing."""
    monkeypatch.setenv("GROQ_API_KEY", "test_groq_key_12345")
    return monkeypatch


@pytest.fixture
def set_rapidapi_key(monkeypatch):
    """Set a mock RAPIDAPI_KEY for testing."""
    monkeypatch.setenv("RAPIDAPI_KEY", "test_rapidapi_key_12345")
    return monkeypatch
