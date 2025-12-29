"""
Utility Functions Module

Common utility functions used across the application.
"""

import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import validators


def validate_instagram_url(url: str) -> bool:
    """
    Validate if URL is a valid Instagram reel URL.

    Args:
        url: URL string to validate

    Returns:
        True if valid Instagram reel URL, False otherwise
    """
    if not validators.url(url):
        return False

    parsed = urlparse(url)

    # Check if it's an Instagram domain
    if "instagram.com" not in parsed.netloc:
        return False

    # Check if it's a reel URL
    if "/reel/" not in parsed.path and "/reels/" not in parsed.path:
        return False

    return True


def validate_youtube_url(url: str) -> bool:
    """
    Validate if URL is a valid YouTube URL.

    Args:
        url: URL string to validate

    Returns:
        True if valid YouTube URL, False otherwise
    """
    if not validators.url(url):
        return False

    parsed = urlparse(url)

    # Check if it's a YouTube domain
    youtube_domains = ["youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"]

    if not any(domain in parsed.netloc for domain in youtube_domains):
        return False

    return True


def validate_video_url(url: str) -> bool:
    """
    Validate if URL is a valid video URL (Instagram or YouTube).

    Args:
        url: URL string to validate

    Returns:
        True if valid video URL, False otherwise
    """
    return validate_instagram_url(url) or validate_youtube_url(url)


def detect_platform(url: str) -> Optional[str]:
    """
    Detect the platform from URL.

    Args:
        url: Video URL

    Returns:
        Platform name ('instagram', 'youtube') or None if unknown
    """
    if validate_instagram_url(url):
        return "instagram"
    elif validate_youtube_url(url):
        return "youtube"
    else:
        return None


def extract_reel_id(url: str) -> Optional[str]:
    """
    Extract reel ID from Instagram URL.

    Args:
        url: Instagram reel URL

    Returns:
        Reel ID if found, None otherwise
    """
    # Pattern: /reel/REEL_ID or /reels/REEL_ID
    pattern = r'/reels?/([A-Za-z0-9_-]+)'
    match = re.search(pattern, url)

    if match:
        return match.group(1)

    return None


def extract_youtube_id(url: str) -> Optional[str]:
    """
    Extract video ID from YouTube URL.

    Args:
        url: YouTube video URL

    Returns:
        Video ID if found, None otherwise
    """
    # Handle different YouTube URL formats
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/)([A-Za-z0-9_-]{11})',
        r'youtube\.com\/embed\/([A-Za-z0-9_-]{11})',
        r'youtube\.com\/v\/([A-Za-z0-9_-]{11})',
        r'youtube\.com\/shorts\/([A-Za-z0-9_-]{11})',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    return None


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract video ID from URL (works for both Instagram and YouTube).

    Args:
        url: Video URL

    Returns:
        Video ID if found, None otherwise
    """
    platform = detect_platform(url)

    if platform == "instagram":
        return extract_reel_id(url)
    elif platform == "youtube":
        return extract_youtube_id(url)
    else:
        return None


def generate_filename(pattern: str, reel_id: str, **kwargs) -> str:
    """
    Generate filename based on pattern and parameters.
    
    Args:
        pattern: Filename pattern (e.g., "{timestamp}_{id}")
        reel_id: Instagram reel ID
        **kwargs: Additional parameters for pattern
        
    Returns:
        Generated filename
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    replacements = {
        "timestamp": timestamp,
        "id": reel_id,
        **kwargs
    }
    
    filename = pattern
    for key, value in replacements.items():
        filename = filename.replace(f"{{{key}}}", str(value))
    
    return filename


def calculate_file_hash(file_path: Path) -> str:
    """
    Calculate SHA256 hash of a file.
    
    Args:
        file_path: Path to file
        
    Returns:
        Hex digest of file hash
    """
    sha256_hash = hashlib.sha256()
    
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    
    return sha256_hash.hexdigest()


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string (e.g., "2m 30s")
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    
    minutes = int(seconds // 60)
    remaining_seconds = seconds % 60
    
    if minutes < 60:
        return f"{minutes}m {remaining_seconds:.0f}s"
    
    hours = int(minutes // 60)
    remaining_minutes = minutes % 60
    
    return f"{hours}h {remaining_minutes}m"


def ensure_directory(directory: Path) -> Path:
    """
    Ensure directory exists, create if it doesn't.
    
    Args:
        directory: Directory path
        
    Returns:
        Directory path
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def clean_filename(filename: str) -> str:
    """
    Clean filename by removing invalid characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Cleaned filename
    """
    # Remove invalid characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    return filename


# Stub for future implementation
if __name__ == "__main__":
    # Test utility functions
    test_url = "https://www.instagram.com/reel/abc123xyz"
    
    print(f"Valid URL: {validate_instagram_url(test_url)}")
    print(f"Reel ID: {extract_reel_id(test_url)}")
    print(f"Filename: {generate_filename('{timestamp}_{id}', 'abc123')}")
    print(f"Duration: {format_duration(150.5)}")
