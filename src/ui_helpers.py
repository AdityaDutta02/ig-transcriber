"""
UI Helpers Module

Helper functions and CSV processing logic extracted from app.py
to keep the main module under 500 lines.
"""

import io
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st


# ---------------------------------------------------------------------------
# HTML badge / indicator helpers
# ---------------------------------------------------------------------------

def render_downloader_badge(source: Optional[str]) -> str:
    """
    Return HTML for a download-source pill badge.

    Args:
        source: The platform/source string returned as the 4th element of
                download_video(). Values: 'instagram', 'youtube',
                'rapidapi_backup1', 'rapidapi_backup2', or None.

    Returns:
        HTML string for the badge.
    """
    if source == "rapidapi_backup1":
        dot_class = "fallback-1"
        label = "RapidAPI Backup 1"
    elif source == "rapidapi_backup2":
        dot_class = "fallback-2"
        label = "RapidAPI Backup 2"
    else:
        dot_class = ""
        label = "yt-dlp"

    return (
        f'<span class="downloader-badge">'
        f'<span class="downloader-badge-dot {dot_class}"></span>'
        f"{label}"
        f"</span>"
    )


def render_api_status(api_key_present: bool) -> str:
    """
    Return HTML for the Groq API status indicator.

    Args:
        api_key_present: True if GROQ_API_KEY is set in the environment.

    Returns:
        HTML string for the status pill.
    """
    if api_key_present:
        css_class = "connected"
        label = "Groq connected"
    else:
        css_class = "disconnected"
        label = "API key missing"

    return (
        f'<div class="api-status {css_class}">'
        f'<span class="api-status-dot"></span>'
        f"{label}"
        f"</div>"
    )


def render_platform_badge(platform: str) -> str:
    """
    Return HTML for a platform pill badge.

    Args:
        platform: 'instagram' or 'youtube'.

    Returns:
        HTML string.
    """
    label = platform.title()
    return f'<span class="platform-badge">{label}</span>'


# ---------------------------------------------------------------------------
# CSV processing
# ---------------------------------------------------------------------------

def render_csv_processing(
    config: Any,
    transcriber: Any,
    downloader: Any,
    caption_generator_cls: Any,
) -> None:
    """
    Render the bulk CSV processing section including file upload, processing
    trigger, and results display.

    Args:
        config: AppConfig loaded from load_config().
        transcriber: GroqTranscriber instance (cached resource).
        downloader: VideoDownloader instance (cached resource).
        caption_generator_cls: The CaptionGenerator class (not an instance).
    """
    from utils import extract_video_id

    st.markdown(
        "Upload a CSV file with a column containing video URLs.",
        help=None,
    )

    with st.expander("CSV format reference", expanded=False):
        st.code(
            "url\nhttps://www.youtube.com/watch?v=...\nhttps://www.instagram.com/reel/...",
            language="text",
        )

    # ── Session state init ────────────────────────────────────────────────
    if "csv_results" not in st.session_state:
        st.session_state.csv_results = None
    if "last_uploaded_file" not in st.session_state:
        st.session_state.last_uploaded_file = None

    # ── Operations (read from sidebar state stored by app.py) ─────────────
    operations: Dict[str, Any] = st.session_state.get(
        "operations",
        {
            "download": True,
            "transcribe": True,
            "generate_captions": True,
            "words_per_line": 10,
            "max_lines": 2,
        },
    )

    # ── File uploader ──────────────────────────────────────────────────────
    uploaded_file = st.file_uploader(
        "Choose a CSV file",
        type=["csv"],
        help="Upload a CSV with a 'url' column",
        label_visibility="collapsed",
        key="csv_uploader",
    )

    if uploaded_file is not None:
        current_file_id = f"{uploaded_file.name}_{uploaded_file.size}"
        if st.session_state.last_uploaded_file != current_file_id:
            st.session_state.csv_results = None
            st.session_state.last_uploaded_file = current_file_id
        st.success(f"File uploaded: {uploaded_file.name}")

    if uploaded_file is not None:
        if st.button("Process CSV", type="primary", key="csv_process_btn"):
            if not operations["download"] and not operations["transcribe"]:
                st.error("Select at least one operation (Download or Transcribe) in the sidebar.")
            else:
                st.session_state.csv_results = _process_csv_file(
                    uploaded_file,
                    operations,
                    config,
                    caption_generator_cls,
                )

    # ── Results ───────────────────────────────────────────────────────────
    if st.session_state.csv_results is not None:
        _render_csv_results(st.session_state.csv_results, extract_video_id)


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _process_csv_file(
    csv_file: Any,
    operations: Dict[str, Any],
    config: Any,
    caption_generator_cls: Any,
) -> Dict[str, list]:
    """Parse, download, transcribe, and optionally caption a CSV of URLs."""
    from csv_parser import parse_csv
    from downloader import download_videos
    from transcriber import transcribe_audio_files

    results: Dict[str, list] = {"successful": [], "failed": []}

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
            tmp.write(csv_file.getvalue())
            csv_path = tmp.name

        url_records, _stats = parse_csv(csv_path)

        if not url_records:
            st.error("No valid URLs found in the CSV file.")
            return results

        st.info(f"Found {len(url_records)} valid URLs")

        # Download
        if operations["download"]:
            with st.spinner(f"Downloading {len(url_records)} videos..."):
                successful_dl, failed_dl = download_videos(url_records, config.download)
                url_records = successful_dl
                results["failed"].extend(failed_dl)
            st.success(f"Downloaded: {len(successful_dl)} / {len(successful_dl) + len(failed_dl)}")

        # Transcribe
        if operations["transcribe"] and url_records:
            with st.spinner(f"Transcribing {len(url_records)} audio files..."):
                successful_tr, failed_tr = transcribe_audio_files(url_records, config.transcription)
                results["successful"] = successful_tr
                results["failed"].extend(failed_tr)
            st.success(f"Transcribed: {len(successful_tr)} / {len(url_records)}")

            # Generate captions
            if operations.get("generate_captions") and results["successful"]:
                caption_gen = caption_generator_cls(
                    words_per_line=operations.get("words_per_line", 10),
                    max_lines=operations.get("max_lines", 2),
                )
                caption_count = 0
                with st.spinner("Generating captions..."):
                    for item in results["successful"]:
                        segments = item.get("transcription_metadata", {}).get("segments", [])
                        if segments:
                            item["srt_content"] = caption_gen.generate_srt(segments)
                            item["vtt_content"] = caption_gen.generate_vtt(segments)
                            caption_count += 1
                st.success(f"Generated captions for {caption_count} / {len(results['successful'])} videos")

        Path(csv_path).unlink(missing_ok=True)

    except Exception as exc:
        st.error(f"Error processing CSV: {exc}")

    return results


def _render_csv_results(results: Dict[str, list], extract_video_id: Any) -> None:
    """Render the CSV results section."""
    st.markdown("### Results Summary")

    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Successful", len(results["successful"]), label_visibility="visible")
    with col_b:
        st.metric("Failed", len(results["failed"]), label_visibility="visible")

    if results["successful"]:
        # Platform breakdown
        platforms: Dict[str, int] = {}
        for item in results["successful"]:
            plat = item.get("platform", "unknown")
            platforms[plat] = platforms.get(plat, 0) + 1

        st.markdown("**Platform breakdown:** " + ", ".join(
            f"{p.title()}: {c}" for p, c in platforms.items()
        ))

        # Individual transcriptions
        st.markdown("### Transcriptions")
        for idx, item in enumerate(results["successful"], 1):
            platform = item.get("platform", "unknown")
            meta = item.get("transcription_metadata", {})
            with st.expander(
                f"Video {idx} — {platform.title()}",
                expanded=False,
            ):
                st.caption(f"URL: {item['url']}")

                mc1, mc2, mc3 = st.columns(3)
                with mc1:
                    st.metric("Language", meta.get("language", "unknown").upper())
                with mc2:
                    st.metric("Duration", f"{meta.get('duration', 0):.1f}s")
                with mc3:
                    conf = meta.get("confidence")
                    st.metric("Confidence", f"{conf:.1%}" if conf else "N/A")

                st.text_area(
                    "Transcription",
                    item.get("transcription", ""),
                    height=180,
                    key=f"csv_trans_{idx}",
                    label_visibility="collapsed",
                )

                video_id = extract_video_id(item["url"]) or "unknown"
                dl1, dl2, dl3 = st.columns(3)

                txt_content = (
                    f"URL: {item['url']}\n"
                    f"Platform: {platform}\n"
                    f"Language: {meta.get('language', 'unknown')}\n"
                    f"Duration: {meta.get('duration', 0):.1f}s\n"
                    + "-" * 70 + "\n\n"
                    + item.get("transcription", "")
                )
                with dl1:
                    st.download_button(
                        "Download TXT",
                        data=txt_content,
                        file_name=f"{platform}_{video_id}.txt",
                        mime="text/plain",
                        key=f"csv_txt_{idx}",
                    )
                if "srt_content" in item:
                    with dl2:
                        st.download_button(
                            "Download SRT",
                            data=item["srt_content"],
                            file_name=f"{platform}_{video_id}.srt",
                            mime="text/plain",
                            key=f"csv_srt_{idx}",
                        )
                if "vtt_content" in item:
                    with dl3:
                        st.download_button(
                            "Download VTT",
                            data=item["vtt_content"],
                            file_name=f"{platform}_{video_id}.vtt",
                            mime="text/plain",
                            key=f"csv_vtt_{idx}",
                        )

        # Bulk download ZIP
        st.markdown("### Bulk Download")
        txt_count = len(results["successful"])
        srt_count = sum(1 for i in results["successful"] if "srt_content" in i)
        vtt_count = sum(1 for i in results["successful"] if "vtt_content" in i)
        total_files = txt_count + srt_count + vtt_count
        st.caption(
            f"Ready to download: {txt_count} TXT + {srt_count} SRT + {vtt_count} VTT = {total_files} files"
        )

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zf:
            for item in results["successful"]:
                plat = item.get("platform", "unknown")
                vid_id = extract_video_id(item["url"]) or "unknown"
                meta = item.get("transcription_metadata", {})

                content = (
                    f"URL: {item['url']}\n"
                    f"Platform: {plat}\n"
                    f"Language: {meta.get('language', 'unknown')}\n"
                    f"Duration: {meta.get('duration', 0):.1f}s\n"
                    + "-" * 70 + "\n\n"
                    + item.get("transcription", "")
                )
                zf.writestr(f"{plat}_{vid_id}.txt", content)
                if "srt_content" in item:
                    zf.writestr(f"{plat}_{vid_id}.srt", item["srt_content"])
                if "vtt_content" in item:
                    zf.writestr(f"{plat}_{vid_id}.vtt", item["vtt_content"])

        zip_buffer.seek(0)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        st.download_button(
            f"Download All Files as ZIP ({total_files} files)",
            data=zip_buffer.getvalue(),
            file_name=f"transcriptions_{timestamp}.zip",
            mime="application/zip",
            type="primary",
        )

    if results["failed"]:
        st.markdown("### Failed Items")
        for item in results["failed"]:
            st.error(f"{item.get('url', 'unknown')}: {item.get('error', 'Unknown error')}")
