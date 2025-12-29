"""
Video Transcriber - Web UI

Streamlit-based web interface for downloading and transcribing Instagram Reels and YouTube videos.
"""

import streamlit as st
import sys
from pathlib import Path
import tempfile
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from downloader import VideoDownloader
from transcriber import ReelTranscriber
from captions import CaptionGenerator
from config import load_config
from utils import validate_video_url, detect_platform, extract_video_id


# Page configuration
st.set_page_config(
    page_title="Video Transcriber",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Load configuration once
@st.cache_resource
def get_config():
    """Load configuration."""
    return load_config()


@st.cache_resource
def get_downloader(_config):
    """Initialize downloader."""
    return VideoDownloader(_config.download)


@st.cache_resource
def get_transcriber(_config):
    """Initialize transcriber."""
    return ReelTranscriber(_config.transcription)


def process_single_url(url, operations, config):
    """Process a single URL."""
    results = {"success": False, "data": None, "error": None}

    try:
        # Download
        if operations["download"]:
            with st.spinner(f"Downloading from {detect_platform(url)}..."):
                downloader = get_downloader(config)
                success, audio_file, error, platform = downloader.download_video(url)

                if not success:
                    results["error"] = f"Download failed: {error}"
                    return results

                results["data"] = {
                    "url": url,
                    "platform": platform,
                    "audio_file": str(audio_file)
                }

        # Transcribe
        if operations["transcribe"]:
            if not results.get("data") or "audio_file" not in results["data"]:
                results["error"] = "No audio file available for transcription"
                return results

            with st.spinner("Transcribing audio..."):
                transcriber = get_transcriber(config)
                audio_path = Path(results["data"]["audio_file"])
                success, transcription, metadata, error = transcriber.transcribe_audio(audio_path)

                if not success:
                    results["error"] = f"Transcription failed: {error}"
                    return results

                results["data"].update({
                    "transcription": transcription,
                    "language": metadata["language"],
                    "duration": metadata["duration"],
                    "confidence": metadata.get("confidence"),
                    "segments": metadata.get("segments", [])
                })

                # Generate captions if enabled
                segments = metadata.get("segments", [])
                if operations.get("generate_captions"):
                    if segments:
                        caption_gen = CaptionGenerator(
                            words_per_line=operations.get("words_per_line", 10),
                            max_lines=operations.get("max_lines", 2)
                        )
                        srt_content = caption_gen.generate_srt(segments)
                        vtt_content = caption_gen.generate_vtt(segments)

                        results["data"].update({
                            "srt_content": srt_content,
                            "vtt_content": vtt_content
                        })
                    else:
                        # Debug: segments not available
                        results["data"]["caption_error"] = "No segments available for caption generation"

        results["success"] = True
        return results

    except Exception as e:
        results["error"] = str(e)
        return results


def process_csv_file(csv_file, operations, config):
    """Process CSV file."""
    from csv_parser import parse_csv
    from downloader import download_videos
    from transcriber import transcribe_audio_files

    results = {"successful": [], "failed": []}

    try:
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_file:
            tmp_file.write(csv_file.getvalue())
            csv_path = tmp_file.name

        # Parse CSV
        url_records, stats = parse_csv(csv_path)

        if not url_records:
            st.error("No valid URLs found in CSV")
            return results

        st.info(f"Found {len(url_records)} valid URLs")

        # Download
        if operations["download"]:
            with st.spinner(f"Downloading {len(url_records)} videos..."):
                successful_downloads, failed_downloads = download_videos(url_records, config.download)
                url_records = successful_downloads
                results["failed"].extend(failed_downloads)

            st.success(f"Downloaded: {len(successful_downloads)}/{len(url_records)}")

        # Transcribe
        if operations["transcribe"] and url_records:
            with st.spinner(f"Transcribing {len(url_records)} videos..."):
                successful_transcriptions, failed_transcriptions = transcribe_audio_files(
                    url_records, config.transcription
                )
                results["successful"] = successful_transcriptions
                results["failed"].extend(failed_transcriptions)

            st.success(f"Transcribed: {len(successful_transcriptions)}/{len(url_records)}")

            # Generate captions if enabled
            if operations.get("generate_captions") and successful_transcriptions:
                with st.spinner("Generating captions..."):
                    caption_gen = CaptionGenerator(
                        words_per_line=operations.get("words_per_line", 10),
                        max_lines=operations.get("max_lines", 2)
                    )

                    caption_count = 0
                    for item in successful_transcriptions:
                        metadata = item.get("transcription_metadata", {})
                        segments = metadata.get("segments", [])
                        if segments:
                            # Generate SRT and VTT content
                            srt_content = caption_gen.generate_srt(segments)
                            vtt_content = caption_gen.generate_vtt(segments)

                            # Add to item data
                            item["srt_content"] = srt_content
                            item["vtt_content"] = vtt_content
                            caption_count += 1

                st.success(f"Generated captions for {caption_count}/{len(successful_transcriptions)} videos")

        # Clean up temp file
        Path(csv_path).unlink()

        return results

    except Exception as e:
        st.error(f"Error processing CSV: {e}")
        return results


def main():
    """Main Streamlit app."""

    # Initialize session state
    if "csv_results" not in st.session_state:
        st.session_state.csv_results = None
    if "last_input_method" not in st.session_state:
        st.session_state.last_input_method = None
    if "last_uploaded_file" not in st.session_state:
        st.session_state.last_uploaded_file = None

    # Header
    st.title("🎬 Video Transcriber")
    st.markdown("### Download and transcribe Instagram Reels & YouTube videos")

    # Load configuration
    config = get_config()

    # Sidebar
    with st.sidebar:
        st.header("⚙️ Settings")

        # Input method
        input_method = st.radio(
            "Input Method",
            ["Single URL", "CSV File"],
            help="Choose how to provide video URLs"
        )

        # Clear results if input method changed
        if st.session_state.last_input_method != input_method:
            st.session_state.csv_results = None
            st.session_state.last_input_method = input_method

        # Operations
        st.subheader("Operations")
        download_videos_option = st.checkbox("Download Videos", value=True)
        transcribe_videos_option = st.checkbox("Transcribe Audio", value=True)
        generate_captions_option = st.checkbox("Generate Captions (SRT/VTT)", value=True)

        # Caption settings
        if generate_captions_option and transcribe_videos_option:
            st.subheader("Caption Settings")
            words_per_line = st.slider("Words per Line", 5, 20, 10, help="Number of words per caption line")
            max_lines = st.slider("Lines per Caption", 1, 3, 2, help="Maximum lines per caption")
        else:
            words_per_line = 10
            max_lines = 2

        operations = {
            "download": download_videos_option,
            "transcribe": transcribe_videos_option,
            "generate_captions": generate_captions_option,
            "words_per_line": words_per_line,
            "max_lines": max_lines
        }

        # Model info
        st.subheader("Model Info")
        st.text(f"Model: {config.transcription.model}")
        st.text(f"Device: {config.transcription.device}")
        st.text(f"Compute: {config.transcription.compute_type}")

        # Supported platforms
        st.subheader("Supported Platforms")
        st.markdown("✅ Instagram Reels")
        st.markdown("✅ YouTube Videos")
        st.markdown("✅ YouTube Shorts")

    # Main content
    if input_method == "Single URL":
        st.header("🔗 Single URL Processing")

        # URL input
        url = st.text_input(
            "Enter video URL",
            placeholder="https://www.youtube.com/watch?v=... or https://www.instagram.com/reel/...",
            help="Paste an Instagram Reel or YouTube video URL"
        )

        # Validate URL
        if url:
            if validate_video_url(url):
                platform = detect_platform(url)
                st.success(f"✓ Valid {platform.title()} URL")

                # Process button
                if st.button("🚀 Process Video", type="primary"):
                    if not operations["download"] and not operations["transcribe"]:
                        st.error("Please select at least one operation (Download or Transcribe)")
                    else:
                        results = process_single_url(url, operations, config)

                        if results["success"]:
                            st.success("✅ Processing complete!")

                            data = results["data"]

                            # Display results
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Platform", data["platform"].title())
                            with col2:
                                if "language" in data:
                                    st.metric("Language", data["language"].upper())
                            with col3:
                                if "duration" in data:
                                    st.metric("Duration", f"{data['duration']:.1f}s")

                            # Transcription
                            if "transcription" in data:
                                st.subheader("📝 Transcription")
                                st.text_area(
                                    "Transcription Text",
                                    data["transcription"],
                                    height=300,
                                    help="Copy the transcription from here"
                                )

                                # Show caption generation debug info if present
                                if "caption_error" in data:
                                    st.warning(f"⚠️ Caption Generation: {data['caption_error']}")

                                # Download buttons
                                video_id = extract_video_id(url) or "unknown"
                                col_dl1, col_dl2, col_dl3 = st.columns(3)

                                with col_dl1:
                                    filename = f"{data['platform']}_{video_id}.txt"
                                    st.download_button(
                                        "💾 Download TXT",
                                        data=data["transcription"],
                                        file_name=filename,
                                        mime="text/plain"
                                    )

                                # SRT download
                                if "srt_content" in data:
                                    with col_dl2:
                                        srt_filename = f"{data['platform']}_{video_id}.srt"
                                        st.download_button(
                                            "📥 Download SRT",
                                            data=data["srt_content"],
                                            file_name=srt_filename,
                                            mime="text/plain"
                                        )

                                # VTT download
                                if "vtt_content" in data:
                                    with col_dl3:
                                        vtt_filename = f"{data['platform']}_{video_id}.vtt"
                                        st.download_button(
                                            "📥 Download VTT",
                                            data=data["vtt_content"],
                                            file_name=vtt_filename,
                                            mime="text/plain"
                                        )

                                # Show caption preview
                                if "srt_content" in data:
                                    st.subheader("🎬 Caption Preview (SRT)")
                                    with st.expander("View SRT Content"):
                                        st.code(data["srt_content"][:1000] + "\n..." if len(data["srt_content"]) > 1000 else data["srt_content"], language="text")
                        else:
                            st.error(f"❌ Error: {results['error']}")
            else:
                st.error("❌ Invalid URL. Please enter a valid Instagram or YouTube URL.")

    else:  # CSV File
        st.header("📂 CSV File Processing")

        st.markdown("""
        Upload a CSV file with a column containing video URLs.

        **CSV Format:**
        ```csv
        url
        https://www.youtube.com/watch?v=...
        https://www.instagram.com/reel/...
        ```
        """)

        # File upload
        uploaded_file = st.file_uploader(
            "Choose a CSV file",
            type=["csv"],
            help="Upload a CSV file with video URLs"
        )

        # Clear results if new file uploaded
        if uploaded_file is not None:
            current_file_id = f"{uploaded_file.name}_{uploaded_file.size}"
            if st.session_state.last_uploaded_file != current_file_id:
                st.session_state.csv_results = None
                st.session_state.last_uploaded_file = current_file_id

        if uploaded_file is not None:
            st.success(f"✓ File uploaded: {uploaded_file.name}")

            # Process button
            if st.button("🚀 Process CSV", type="primary"):
                if not operations["download"] and not operations["transcribe"]:
                    st.error("Please select at least one operation (Download or Transcribe)")
                else:
                    # Process and store in session state
                    st.session_state.csv_results = process_csv_file(uploaded_file, operations, config)

        # Display results from session state
        if st.session_state.csv_results is not None:
            results = st.session_state.csv_results

            # Display summary
            st.subheader("📊 Results Summary")

            col1, col2 = st.columns(2)
            with col1:
                st.metric("✅ Successful", len(results["successful"]))
            with col2:
                st.metric("❌ Failed", len(results["failed"]))

            # Platform breakdown
            if results["successful"]:
                st.subheader("🌐 Platform Breakdown")
                platforms = {}
                for item in results["successful"]:
                    platform = item.get("platform", "unknown")
                    platforms[platform] = platforms.get(platform, 0) + 1

                for platform, count in platforms.items():
                    st.text(f"{platform.title()}: {count} videos")

            # Transcriptions
            if results["successful"]:
                st.subheader("📝 Transcriptions")

                for idx, item in enumerate(results["successful"], 1):
                    with st.expander(f"Video {idx} - {item.get('platform', 'unknown').title()}"):
                        st.text(f"URL: {item['url']}")

                        metadata = item.get("transcription_metadata", {})
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.text(f"Language: {metadata.get('language', 'unknown')}")
                        with col2:
                            st.text(f"Duration: {metadata.get('duration', 0):.1f}s")
                        with col3:
                            conf = metadata.get("confidence")
                            if conf:
                                st.text(f"Confidence: {conf:.1%}")

                        st.text_area(
                            "Transcription",
                            item.get("transcription", ""),
                            height=200,
                            key=f"trans_{idx}"
                        )

                        # Individual download buttons
                        if "transcription" in item:
                            video_id = extract_video_id(item["url"]) or "unknown"
                            platform = item.get("platform", "unknown")

                            dl_cols = st.columns(3)

                            with dl_cols[0]:
                                txt_content = f"URL: {item['url']}\n"
                                txt_content += f"Platform: {platform}\n"
                                txt_content += f"Language: {metadata.get('language', 'unknown')}\n"
                                txt_content += f"Duration: {metadata.get('duration', 0):.1f}s\n"
                                txt_content += "-" * 70 + "\n\n"
                                txt_content += item.get("transcription", "")

                                st.download_button(
                                    "💾 TXT",
                                    data=txt_content,
                                    file_name=f"{platform}_{video_id}.txt",
                                    mime="text/plain",
                                    key=f"txt_{idx}"
                                )

                            if "srt_content" in item:
                                with dl_cols[1]:
                                    st.download_button(
                                        "📥 SRT",
                                        data=item["srt_content"],
                                        file_name=f"{platform}_{video_id}.srt",
                                        mime="text/plain",
                                        key=f"srt_{idx}"
                                    )

                            if "vtt_content" in item:
                                with dl_cols[2]:
                                    st.download_button(
                                        "📥 VTT",
                                        data=item["vtt_content"],
                                        file_name=f"{platform}_{video_id}.vtt",
                                        mime="text/plain",
                                        key=f"vtt_{idx}"
                                    )

                # Download all button (outside the loop)
                st.subheader("📦 Bulk Download")

                # Count files
                txt_count = len(results["successful"])
                srt_count = sum(1 for item in results["successful"] if "srt_content" in item)
                vtt_count = sum(1 for item in results["successful"] if "vtt_content" in item)
                total_files = txt_count + srt_count + vtt_count

                st.info(f"📊 Ready to download: {txt_count} TXT + {srt_count} SRT + {vtt_count} VTT = {total_files} files total")

                # Create zip file
                import zipfile
                import io

                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zip_file:
                    for item in results["successful"]:
                        platform = item.get("platform", "unknown")
                        video_id = extract_video_id(item["url"]) or "unknown"

                        # Add transcription TXT file
                        filename = f"{platform}_{video_id}.txt"
                        content = f"URL: {item['url']}\n"
                        content += f"Platform: {platform}\n"
                        metadata = item.get("transcription_metadata", {})
                        content += f"Language: {metadata.get('language', 'unknown')}\n"
                        content += f"Duration: {metadata.get('duration', 0):.1f}s\n"
                        content += "-" * 70 + "\n\n"
                        content += item.get("transcription", "")
                        zip_file.writestr(filename, content)

                        # Add SRT file if available
                        if "srt_content" in item:
                            srt_filename = f"{platform}_{video_id}.srt"
                            zip_file.writestr(srt_filename, item["srt_content"])

                        # Add VTT file if available
                        if "vtt_content" in item:
                            vtt_filename = f"{platform}_{video_id}.vtt"
                            zip_file.writestr(vtt_filename, item["vtt_content"])

                zip_buffer.seek(0)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

                # Single download button - no intermediate button needed
                st.download_button(
                    "📥 Download All Files (ZIP)",
                    data=zip_buffer.getvalue(),
                    file_name=f"transcriptions_{timestamp}.zip",
                    mime="application/zip",
                    help=f"Download all {total_files} files in one ZIP archive",
                    type="primary"
                )

            # Failed items
            if results["failed"]:
                st.subheader("❌ Failed Items")
                for item in results["failed"]:
                    st.error(f"{item.get('url', 'unknown')}: {item.get('error', 'Unknown error')}")

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center'>
            <p>Built for Creators with :heart: by Ionique Labs</p>
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
