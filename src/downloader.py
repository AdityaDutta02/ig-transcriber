"""
Downloader Module

Handles downloading videos from Instagram and YouTube using yt-dlp with parallel processing.
Extracts audio automatically and manages temporary files.
"""

import os
import time
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess

from loguru import logger
from tqdm import tqdm

from config import DownloadConfig
from utils import extract_video_id, detect_platform, ensure_directory


class DownloadError(Exception):
    """Custom exception for download errors."""
    pass


class VideoDownloader:
    """
    Downloads videos from Instagram and YouTube using yt-dlp.

    Features:
    - Supports Instagram Reels and YouTube videos
    - Parallel downloads with configurable workers
    - Automatic audio extraction
    - Rate limiting to avoid bans
    - Retry logic with exponential backoff
    - Progress tracking
    - No login required (public content only)
    """

    def __init__(self, config: DownloadConfig):
        """
        Initialize downloader.

        Args:
            config: Download configuration
        """
        self.config = config
        self.temp_dir = Path(tempfile.gettempdir()) / "video_downloads"
        ensure_directory(self.temp_dir)

        # Check if yt-dlp is available
        if not self._check_ytdlp():
            raise RuntimeError("yt-dlp is not installed. Install with: pip install yt-dlp")

        logger.info("Video downloader initialized")
        logger.info(f"Concurrent workers: {config.concurrent_workers}")
        logger.info(f"Temp directory: {self.temp_dir}")
        logger.info(f"Rate limit delay: {config.rate_limit_delay}s")
        logger.info("Supported platforms: Instagram, YouTube")

        # PO token diagnostics — plugin auto-discovers server at 127.0.0.1:4416
        try:
            import importlib
            pot_plugin = importlib.import_module("yt_dlp_plugins.extractor.getpot_bgutil_http")
            logger.info("bgutil PO token plugin loaded (getpot_bgutil_http)")
        except (ImportError, ModuleNotFoundError):
            logger.warning(
                "bgutil PO token plugin not loadable — "
                "YouTube downloads may fail with bot detection"
            )
    
    def _check_ytdlp(self) -> bool:
        """Check if yt-dlp is available."""
        try:
            import yt_dlp
            return True
        except ImportError:
            return False
    
    def download_video(
        self,
        url: str,
        output_path: Optional[Path] = None
    ) -> Tuple[bool, Optional[Path], Optional[str], Optional[str]]:
        """
        Download a single video (Instagram or YouTube).

        Args:
            url: Video URL (Instagram or YouTube)
            output_path: Optional custom output path

        Returns:
            Tuple of (success, audio_file_path, error_message, platform)
        """
        import yt_dlp

        # Detect platform
        platform = detect_platform(url)
        if not platform:
            return False, None, "Unsupported URL format. Supported platforms: Instagram, YouTube", None

        # Extract video ID
        video_id = extract_video_id(url)
        if not video_id:
            return False, None, f"Could not extract video ID from {platform} URL", platform

        logger.debug(f"Detected platform: {platform}, video ID: {video_id}")

        # Set output path
        if output_path is None:
            output_path = self.temp_dir / f"{platform}_{video_id}.%(ext)s"
        
        # yt-dlp options
        ydl_opts = {
            'format': self.config.format,
            'outtmpl': str(output_path),
            'quiet': False,
            'no_warnings': False,
            'verbose': True,
            'extract_audio': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': self.config.audio_format,
                'preferredquality': self.config.audio_quality,
            }],
            'user_agent': self.config.user_agent,
            'socket_timeout': self.config.timeout,
            'retries': 0,  # We handle retries ourselves
            'http_headers': {
                'User-Agent': self.config.user_agent,
            },
        }

        # Configure PO token provider for YouTube bot detection bypass.
        # bgutil-ytdlp-pot-provider auto-discovers the server at 127.0.0.1:4416
        # by default. Explicit extractor_args only needed for non-default URLs.
        if platform == "youtube":
            pot_base = os.environ.get("POT_SERVER_URL")
            if pot_base and pot_base != "http://127.0.0.1:4416":
                ydl_opts['extractor_args'] = {
                    'youtubepot-bgutilhttp': {
                        'base_url': [pot_base],
                    },
                }
                logger.debug(f"PO token extractor arg set: base_url={pot_base}")
            else:
                logger.debug("PO token: using default auto-discovery (127.0.0.1:4416)")

        # YouTube authentication to bypass bot detection
        cookies_path = os.environ.get("YT_COOKIES_PATH")
        if cookies_path and Path(cookies_path).exists():
            logger.info(f"Using YouTube cookies from {cookies_path}")
            ydl_opts['cookiefile'] = cookies_path
        else:
            if cookies_path:
                logger.warning(f"YT_COOKIES_PATH set to {cookies_path} but file not found")
            if os.environ.get("YT_COOKIES_B64"):
                logger.warning("YT_COOKIES_B64 is set but cookie file was not decoded")
        
        # Attempt download with retries
        for attempt in range(self.config.retry_attempts):
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    logger.debug(f"Downloading {platform} video {video_id} (attempt {attempt + 1})")
                    ydl.download([url])

                    # Find the downloaded audio file
                    audio_file = self.temp_dir / f"{platform}_{video_id}.{self.config.audio_format}"

                    if audio_file.exists():
                        logger.debug(f"Successfully downloaded: {platform}/{video_id}")
                        return True, audio_file, None, platform
                    else:
                        logger.warning(f"Download succeeded but file not found: {audio_file}")
                        return False, None, "Downloaded file not found", platform

            except Exception as e:
                error_msg = str(e)
                logger.debug(f"Download attempt {attempt + 1} failed for {platform}/{video_id}: {error_msg}")

                # Check if it's a truly private/deleted video (skip fallback)
                if any(x in error_msg.lower() for x in ['private', 'not available', 'deleted', 'removed']):
                    logger.info(f"Video {platform}/{video_id} is private or unavailable")
                    return False, None, f"Video is private or unavailable: {error_msg}", platform

                # "login required" from YouTube is usually bot detection, not
                # actually private content — let it fall through to RapidAPI.

                # If not last attempt, wait before retry
                if attempt < self.config.retry_attempts - 1:
                    delay = self.config.retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.debug(f"Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    logger.warning(f"All retry attempts failed for {platform}/{video_id}: {error_msg}")
                    ytdlp_error = f"Download failed after {self.config.retry_attempts} attempts: {error_msg}"

                    # Attempt RapidAPI fallback if key is available
                    if not os.environ.get("RAPIDAPI_KEY"):
                        logger.info(
                            "RAPIDAPI_KEY not set; skipping RapidAPI fallback"
                        )
                        return False, None, ytdlp_error, platform

                    from rapidapi_downloader import RapidAPIDownloader
                    rapidapi = RapidAPIDownloader()

                    if platform == "youtube":
                        logger.info(
                            f"yt-dlp exhausted; trying RapidAPI YouTube MP3 for {video_id}"
                        )
                        ra_success, ra_audio, ra_error, ra_source = (
                            rapidapi.download_youtube_mp3(video_id, self.temp_dir)
                        )
                    elif platform == "instagram":
                        logger.info(
                            f"yt-dlp exhausted; trying RapidAPI fallback for {video_id}"
                        )
                        ra_success, ra_audio, ra_error, ra_source = (
                            rapidapi.download_instagram(url, self.temp_dir)
                        )
                    else:
                        return False, None, ytdlp_error, platform

                    if ra_success:
                        logger.info(
                            f"RapidAPI fallback succeeded ({ra_source}) for {video_id}"
                        )
                        return True, ra_audio, None, ra_source

                    logger.warning(
                        f"RapidAPI fallback also failed for {video_id}: {ra_error}"
                    )
                    combined_error = (
                        f"{ytdlp_error}; RapidAPI fallback: {ra_error}"
                    )
                    return False, None, combined_error, ra_source

        return False, None, "Download failed", platform
    
    def download_batch(
        self,
        url_records: List[Dict],
        progress_callback: Optional[callable] = None
    ) -> Tuple[List[Dict], List[Dict]]:
        """
        Download multiple videos in parallel.

        Args:
            url_records: List of URL records from CSV parser
            progress_callback: Optional callback for progress updates

        Returns:
            Tuple of (successful_downloads, failed_downloads)
        """
        successful = []
        failed = []

        logger.info(f"Starting batch download of {len(url_records)} videos")
        logger.info(f"Using {self.config.concurrent_workers} concurrent workers")

        # Create progress bar
        with tqdm(total=len(url_records), desc="Downloading videos", unit="video") as pbar:
            # Use ThreadPoolExecutor for parallel downloads
            with ThreadPoolExecutor(max_workers=self.config.concurrent_workers) as executor:
                # Submit all download tasks
                future_to_record = {
                    executor.submit(self._download_with_rate_limit, record): record
                    for record in url_records
                }
                
                # Process completed downloads
                for future in as_completed(future_to_record):
                    record = future_to_record[future]

                    try:
                        success, audio_file, error, platform = future.result()

                        if success:
                            result = {
                                **record,
                                'audio_file': str(audio_file),
                                'download_success': True,
                                'platform': platform
                            }
                            successful.append(result)
                            video_id = record.get('video_id', extract_video_id(record.get('url', 'unknown')))
                            logger.debug(f"Download successful: {platform}/{video_id}")
                        else:
                            result = {
                                **record,
                                'download_success': False,
                                'error': error,
                                'platform': platform
                            }
                            failed.append(result)
                            video_id = record.get('video_id', extract_video_id(record.get('url', 'unknown')))
                            logger.warning(f"Download failed: {platform}/{video_id} - {error}")

                        # Update progress
                        pbar.update(1)

                        # Call progress callback if provided
                        if progress_callback:
                            progress_callback(len(successful) + len(failed), len(url_records))

                    except Exception as e:
                        video_id = record.get('video_id', extract_video_id(record.get('url', 'unknown')))
                        logger.error(f"Unexpected error downloading {video_id}: {e}")
                        failed.append({
                            **record,
                            'download_success': False,
                            'error': str(e)
                        })
                        pbar.update(1)
        
        logger.info(f"Batch download complete: {len(successful)} successful, {len(failed)} failed")
        
        return successful, failed
    
    def _download_with_rate_limit(self, record: Dict) -> Tuple[bool, Optional[Path], Optional[str], Optional[str]]:
        """
        Download with rate limiting.

        Args:
            record: URL record from CSV parser

        Returns:
            Tuple of (success, audio_file_path, error_message, platform)
        """
        # Apply rate limiting
        time.sleep(self.config.rate_limit_delay)

        # Download the video
        return self.download_video(record['url'])
    
    def cleanup_temp_files(self, audio_files: Optional[List[Path]] = None) -> None:
        """
        Clean up temporary downloaded files.
        
        Args:
            audio_files: Optional list of specific files to delete
        """
        if audio_files:
            for audio_file in audio_files:
                try:
                    if Path(audio_file).exists():
                        Path(audio_file).unlink()
                        logger.debug(f"Cleaned up: {audio_file}")
                except Exception as e:
                    logger.warning(f"Failed to cleanup {audio_file}: {e}")
        else:
            # Clean up all files in temp directory
            try:
                for file in self.temp_dir.glob("*"):
                    if file.is_file():
                        file.unlink()
                logger.info(f"Cleaned up temp directory: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory: {e}")
    
    def get_video_info(self, url: str) -> Optional[Dict]:
        """
        Get information about a video without downloading.

        Args:
            url: Video URL (Instagram or YouTube)

        Returns:
            Dictionary with video information or None if failed
        """
        import yt_dlp

        platform = detect_platform(url)

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'user_agent': self.config.user_agent,
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                return {
                    'platform': platform,
                    'title': info.get('title'),
                    'duration': info.get('duration'),
                    'uploader': info.get('uploader'),
                    'description': info.get('description'),
                    'view_count': info.get('view_count'),
                    'like_count': info.get('like_count'),
                }
        except Exception as e:
            logger.warning(f"Failed to get video info: {e}")
            return None


def download_videos(
    url_records: List[Dict],
    config: Optional[DownloadConfig] = None,
    progress_callback: Optional[callable] = None
) -> Tuple[List[Dict], List[Dict]]:
    """
    Convenience function to download videos (Instagram or YouTube).

    Args:
        url_records: List of URL records from CSV parser
        config: Optional download configuration
        progress_callback: Optional callback for progress updates

    Returns:
        Tuple of (successful_downloads, failed_downloads)

    Example:
        >>> from csv_parser import parse_csv
        >>> urls, _ = parse_csv("data/input/videos.csv")
        >>> successful, failed = download_videos(urls)
        >>> print(f"Downloaded: {len(successful)}, Failed: {len(failed)}")
    """
    if config is None:
        from config import load_config
        config = load_config().download

    downloader = VideoDownloader(config)
    return downloader.download_batch(url_records, progress_callback)


# Backwards compatibility alias
download_reels = download_videos
ReelDownloader = VideoDownloader


# Testing and example usage
if __name__ == "__main__":
    import sys
    from pathlib import Path
    
    # Add src to path
    sys.path.insert(0, str(Path(__file__).parent))
    
    from config import load_config
    from csv_parser import parse_csv
    
    print("=" * 70)
    print("Downloader Module - Test Mode")
    print("=" * 70)
    print()
    
    # Load configuration
    config = load_config()
    
    # Test 1: Check yt-dlp availability
    print("Test 1: Checking yt-dlp availability...")
    try:
        import yt_dlp
        print(f"✓ yt-dlp is installed (version {yt_dlp.version.__version__})")
    except ImportError:
        print("✗ yt-dlp is not installed")
        print("  Install with: pip install yt-dlp")
        sys.exit(1)
    
    print()
    
    # Test 2: Initialize downloader
    print("Test 2: Initializing downloader...")
    try:
        downloader = ReelDownloader(config.download)
        print("✓ Downloader initialized successfully")
        print(f"  Workers: {config.download.concurrent_workers}")
        print(f"  Temp dir: {downloader.temp_dir}")
    except Exception as e:
        print(f"✗ Failed to initialize: {e}")
        sys.exit(1)
    
    print()
    
    # Test 3: Test with sample CSV (if it has valid URLs)
    print("Test 3: Testing with sample CSV...")
    csv_file = "data/input/sample_reels.csv"
    
    try:
        # Parse CSV
        urls, stats = parse_csv(csv_file)
        
        if urls:
            print(f"✓ Found {len(urls)} URLs in CSV")
            print()
            print("Note: Sample CSV has placeholder URLs.")
            print("Replace with real Instagram reel URLs to test downloading.")
            print()
            print("Example real URL format:")
            print("  https://www.instagram.com/reel/CzAbC123XyZ")
        else:
            print("✗ No valid URLs found in sample CSV")
    
    except Exception as e:
        print(f"✗ Failed to parse CSV: {e}")
    
    print()
    print("=" * 70)
    print("Downloader module test complete!")
    print("=" * 70)
    print()
    print("To test with real URLs:")
    print("1. Add real Instagram reel URLs to your CSV")
    print("2. Run: python main.py")
    print()

