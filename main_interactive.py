"""
Video Transcriber - Interactive CLI

Interactive command-line interface for downloading and transcribing Instagram Reels and YouTube videos.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from loguru import logger
from downloader import download_videos, VideoDownloader
from transcriber import transcribe_audio_files, ReelTranscriber
from captions import CaptionGenerator
from config import load_config
from utils import validate_video_url, detect_platform, extract_video_id


def print_banner():
    """Print welcome banner."""
    print()
    print("=" * 70)
    print("  VIDEO TRANSCRIBER - Instagram Reels & YouTube Videos")
    print("=" * 70)
    print()


def get_input_choice():
    """Get user's input choice: single URL or CSV file."""
    print("How would you like to provide input?")
    print("  1. Single URL (Instagram Reel or YouTube video)")
    print("  2. CSV file with multiple URLs")
    print()

    while True:
        choice = input("Enter your choice (1 or 2): ").strip()
        if choice in ["1", "2"]:
            return choice
        print("Invalid choice. Please enter 1 or 2.")


def get_single_url():
    """Get and validate a single URL from user."""
    print()
    print("Enter video URL:")
    print("  - Instagram: https://www.instagram.com/reel/...")
    print("  - YouTube: https://www.youtube.com/watch?v=...")
    print()

    while True:
        url = input("URL: ").strip()

        if not url:
            print("URL cannot be empty. Please try again.")
            continue

        if not validate_video_url(url):
            print("Invalid URL. Please enter a valid Instagram or YouTube URL.")
            continue

        platform = detect_platform(url)
        print(f"Detected platform: {platform}")
        return url


def get_csv_path():
    """Get CSV file path from user."""
    print()
    print("Enter the path to your CSV file:")
    print("  Example: data/input/videos.csv")
    print()

    while True:
        csv_path = input("CSV path: ").strip()

        if not csv_path:
            print("Path cannot be empty. Please try again.")
            continue

        csv_file = Path(csv_path)

        if not csv_file.exists():
            print(f"File not found: {csv_path}")
            print("Please check the path and try again.")
            continue

        if not csv_file.suffix.lower() == ".csv":
            print("File must be a CSV file (.csv)")
            continue

        return csv_file


def get_operations():
    """Get operations to perform from user."""
    print()
    print("What operations would you like to perform?")
    print("  1. Download only")
    print("  2. Transcribe only (requires pre-downloaded audio)")
    print("  3. Download and Transcribe (recommended)")
    print()

    while True:
        choice = input("Enter your choice (1, 2, or 3): ").strip()
        if choice in ["1", "2", "3"]:
            operations = {
                "download": choice in ["1", "3"],
                "transcribe": choice in ["2", "3"]
            }

            # Ask about captions if transcribing
            if operations["transcribe"]:
                print()
                caption_choice = input("Generate captions (SRT/VTT)? (y/n, default: y): ").strip().lower()
                operations["generate_captions"] = caption_choice != "n"

                if operations["generate_captions"]:
                    operations.update(get_caption_options())
            else:
                operations["generate_captions"] = False

            return operations
        print("Invalid choice. Please enter 1, 2, or 3.")


def get_caption_options():
    """Get caption generation options from user."""
    print()
    print("Caption Settings:")
    print()

    # Words per line
    while True:
        words_input = input("Words per line (5-20, default: 10): ").strip()
        if not words_input:
            words_per_line = 10
            break
        try:
            words_per_line = int(words_input)
            if 5 <= words_per_line <= 20:
                break
            print("Please enter a number between 5 and 20.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    # Lines per caption
    while True:
        lines_input = input("Lines per caption (1-3, default: 2): ").strip()
        if not lines_input:
            max_lines = 2
            break
        try:
            max_lines = int(lines_input)
            if 1 <= max_lines <= 3:
                break
            print("Please enter a number between 1 and 3.")
        except ValueError:
            print("Invalid input. Please enter a number.")

    return {
        "words_per_line": words_per_line,
        "max_lines": max_lines
    }


def get_cleanup_options():
    """Get file cleanup preferences from user."""
    print()
    print("What files would you like to keep after processing?")
    print("  (Enter comma-separated numbers, e.g., '1,3' or 'all')")
    print()
    print("  1. Audio files (.wav)")
    print("  2. Video files (if downloaded)")
    print("  3. Transcription files (.txt)")
    print("  all. Keep all files")
    print("  none. Delete all temporary files (keep only transcriptions)")
    print()

    while True:
        choice = input("Choice: ").strip().lower()

        if choice == "all":
            return {"audio": True, "video": True, "transcription": True}

        if choice == "none":
            return {"audio": False, "video": False, "transcription": True}

        if not choice:
            print("Please enter a choice.")
            continue

        try:
            numbers = [int(n.strip()) for n in choice.split(",")]
            if all(n in [1, 2, 3] for n in numbers):
                return {
                    "audio": 1 in numbers,
                    "video": 2 in numbers,
                    "transcription": 3 in numbers
                }
            else:
                print("Invalid numbers. Please enter 1, 2, 3, 'all', or 'none'.")
        except ValueError:
            print("Invalid input. Please enter numbers separated by commas.")


def get_output_directory():
    """Get output directory from user."""
    print()
    default_output = "data/output"
    print(f"Enter output directory (default: {default_output}):")
    print("  Press Enter to use default, or type a custom path")
    print()

    output_dir = input("Output directory: ").strip()

    if not output_dir:
        output_dir = default_output

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Output directory: {output_path.absolute()}")
    return output_path


def process_single_url(url, operations, cleanup_options, output_dir, config):
    """Process a single URL."""
    print()
    print("=" * 70)
    print("Processing...")
    print("=" * 70)
    print()

    results = {"successful": [], "failed": []}

    # Prepare URL record
    url_record = {"url": url}

    # Download
    if operations["download"]:
        print("Downloading video...")
        downloader = VideoDownloader(config.download)
        success, audio_file, error, platform = downloader.download_video(url)

        if success:
            print(f"[OK] Downloaded successfully")
            print(f"  Platform: {platform}")
            print(f"  Audio file: {audio_file}")
            url_record.update({
                "audio_file": str(audio_file),
                "download_success": True,
                "platform": platform
            })
        else:
            print(f"[ERROR] Download failed: {error}")
            results["failed"].append({"url": url, "error": error})
            return results

    # Transcribe
    if operations["transcribe"]:
        print()
        print("Transcribing audio...")

        if "audio_file" not in url_record:
            print("[ERROR] No audio file available. Please download first.")
            return results

        transcriber = ReelTranscriber(config.transcription)
        audio_path = Path(url_record["audio_file"])
        success, transcription, metadata, error = transcriber.transcribe_audio(audio_path)

        if success:
            print(f"[OK] Transcription successful")
            print(f"  Language: {metadata['language']}")
            print(f"  Duration: {metadata['duration']:.2f}s")
            print()
            print("Transcription:")
            print("-" * 70)
            print(transcription)
            print("-" * 70)

            url_record.update({
                "transcription": transcription,
                "transcription_metadata": metadata,
                "transcription_success": True
            })
            results["successful"].append(url_record)

            # Save transcription
            if cleanup_options["transcription"]:
                platform = url_record.get("platform", "unknown")
                from utils import extract_video_id
                video_id = extract_video_id(url) or "unknown"
                output_file = output_dir / "transcriptions" / f"{platform}_{video_id}.txt"
                output_file.parent.mkdir(parents=True, exist_ok=True)

                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(f"URL: {url}\n")
                    f.write(f"Platform: {platform}\n")
                    f.write(f"Language: {metadata['language']}\n")
                    f.write(f"Duration: {metadata['duration']:.2f}s\n")
                    f.write("-" * 70 + "\n\n")
                    f.write(transcription)

                print()
                print(f"Saved transcription: {output_file}")

            # Generate and save captions if enabled
            if operations.get("generate_captions") and metadata.get("segments"):
                from captions import CaptionGenerator

                caption_gen = CaptionGenerator(
                    words_per_line=operations.get("words_per_line", 10),
                    max_lines=operations.get("max_lines", 2)
                )

                platform = url_record.get("platform", "unknown")
                video_id = extract_video_id(url) or "unknown"

                # Save SRT file
                srt_file = output_dir / "transcriptions" / f"{platform}_{video_id}.srt"
                caption_gen.save_srt(metadata["segments"], srt_file)
                print(f"Saved SRT captions: {srt_file}")

                # Save VTT file
                vtt_file = output_dir / "transcriptions" / f"{platform}_{video_id}.vtt"
                caption_gen.save_vtt(metadata["segments"], vtt_file)
                print(f"Saved VTT captions: {vtt_file}")
        else:
            print(f"[ERROR] Transcription failed: {error}")
            results["failed"].append({**url_record, "error": error})

    # Cleanup
    if operations["download"] and "audio_file" in url_record:
        audio_path = Path(url_record["audio_file"])
        if not cleanup_options["audio"] and audio_path.exists():
            audio_path.unlink()
            print(f"Cleaned up audio file: {audio_path.name}")

    return results


def process_csv(csv_path, operations, cleanup_options, output_dir, config):
    """Process CSV file with multiple URLs."""
    from csv_parser import parse_csv

    print()
    print("=" * 70)
    print("Processing CSV...")
    print("=" * 70)
    print()

    # Parse CSV
    print(f"Reading CSV: {csv_path}")
    url_records, stats = parse_csv(str(csv_path))

    if not url_records:
        print("[ERROR] No valid URLs found in CSV")
        return {"successful": [], "failed": []}

    print(f"Found {len(url_records)} valid URLs")
    print()

    results = {"successful": [], "failed": []}

    # Download
    if operations["download"]:
        print("Downloading videos...")
        successful_downloads, failed_downloads = download_videos(url_records, config.download)

        print(f"Downloaded: {len(successful_downloads)}/{len(url_records)}")
        print()

        url_records = successful_downloads
        results["failed"].extend(failed_downloads)

        if not url_records:
            print("[ERROR] No successful downloads to transcribe")
            return results

    # Transcribe
    if operations["transcribe"]:
        print("Transcribing audio files...")
        successful_transcriptions, failed_transcriptions = transcribe_audio_files(
            url_records, config.transcription
        )

        print(f"Transcribed: {len(successful_transcriptions)}/{len(url_records)}")
        print()

        results["successful"] = successful_transcriptions
        results["failed"].extend(failed_transcriptions)

        # Save transcriptions
        if cleanup_options["transcription"] and successful_transcriptions:
            print("Saving transcriptions...")
            transcription_dir = output_dir / "transcriptions"
            transcription_dir.mkdir(parents=True, exist_ok=True)

            from utils import extract_video_id
            for item in successful_transcriptions:
                platform = item.get("platform", "unknown")
                video_id = extract_video_id(item["url"]) or "unknown"
                output_file = transcription_dir / f"{platform}_{video_id}.txt"

                metadata = item.get("transcription_metadata", {})
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(f"URL: {item['url']}\n")
                    f.write(f"Platform: {platform}\n")
                    f.write(f"Language: {metadata.get('language', 'unknown')}\n")
                    f.write(f"Duration: {metadata.get('duration', 0):.2f}s\n")
                    f.write("-" * 70 + "\n\n")
                    f.write(item["transcription"])

            print(f"Saved {len(successful_transcriptions)} transcriptions to: {transcription_dir}")

        # Generate and save captions if enabled
        if operations.get("generate_captions") and successful_transcriptions:
            print()
            print("Generating captions...")
            from captions import CaptionGenerator

            caption_gen = CaptionGenerator(
                words_per_line=operations.get("words_per_line", 10),
                max_lines=operations.get("max_lines", 2)
            )

            caption_count = 0
            for item in successful_transcriptions:
                metadata = item.get("transcription_metadata", {})
                if metadata.get("segments"):
                    platform = item.get("platform", "unknown")
                    video_id = extract_video_id(item["url"]) or "unknown"

                    # Save SRT file
                    srt_file = transcription_dir / f"{platform}_{video_id}.srt"
                    caption_gen.save_srt(metadata["segments"], srt_file)

                    # Save VTT file
                    vtt_file = transcription_dir / f"{platform}_{video_id}.vtt"
                    caption_gen.save_vtt(metadata["segments"], vtt_file)

                    caption_count += 1

            print(f"Saved {caption_count} SRT and VTT caption files to: {transcription_dir}")

    # Cleanup audio files
    if operations["download"] and not cleanup_options["audio"]:
        print()
        print("Cleaning up audio files...")
        downloader = VideoDownloader(config.download)
        audio_files = [Path(item["audio_file"]) for item in url_records if "audio_file" in item]
        downloader.cleanup_temp_files(audio_files)
        print(f"Cleaned up {len(audio_files)} audio files")

    return results


def print_summary(results):
    """Print processing summary."""
    print()
    print("=" * 70)
    print("Processing Complete!")
    print("=" * 70)
    print()
    print(f"Successful: {len(results['successful'])}")
    print(f"Failed: {len(results['failed'])}")

    if results["failed"]:
        print()
        print("Failed items:")
        for item in results["failed"]:
            print(f"  - {item.get('url', 'unknown')}: {item.get('error', 'Unknown error')}")

    if results["successful"]:
        print()
        print("Platform breakdown:")
        platforms = {}
        for item in results["successful"]:
            platform = item.get("platform", "unknown")
            platforms[platform] = platforms.get(platform, 0) + 1

        for platform, count in platforms.items():
            print(f"  {platform}: {count}")

    print()


def main():
    """Main entry point."""
    try:
        # Print banner
        print_banner()

        # Load configuration
        config = load_config()

        # Get user inputs
        input_choice = get_input_choice()

        if input_choice == "1":
            # Single URL
            url = get_single_url()
            input_data = ("url", url)
        else:
            # CSV file
            csv_path = get_csv_path()
            input_data = ("csv", csv_path)

        # Get operations
        operations = get_operations()

        # Get cleanup options
        cleanup_options = get_cleanup_options()

        # Get output directory
        output_dir = get_output_directory()

        # Process
        if input_data[0] == "url":
            results = process_single_url(
                input_data[1], operations, cleanup_options, output_dir, config
            )
        else:
            results = process_csv(
                input_data[1], operations, cleanup_options, output_dir, config
            )

        # Print summary
        print_summary(results)

    except KeyboardInterrupt:
        print()
        print()
        print("Operation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        logger.exception("Unexpected error")
        print()
        print(f"[ERROR] Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
