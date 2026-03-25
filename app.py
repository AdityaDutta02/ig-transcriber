"""
Video Transcriber - Web UI

Streamlit-based interface for downloading and transcribing Instagram Reels
and YouTube videos. Uses Groq Whisper Large v3 for cloud transcription.
"""

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import streamlit as st

# ── Path setup ────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).parent / "src"))

from captions import CaptionGenerator
from config import load_config
from downloader import VideoDownloader
from transcriber import GroqTranscriber, TranscriptionError
from ui_helpers import (
    render_api_status,
    render_csv_processing,
    render_downloader_badge,
    render_platform_badge,
)
from auth import check_auth, render_user_menu
from ui_styles import CUSTOM_CSS
from utils import detect_platform, extract_video_id, validate_video_url
from youtube_transcriber import fetch_via_worker, fetch_via_supadata

# ── Page config ───────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Video Transcriber",
    page_icon=None,
    layout="centered",
    initial_sidebar_state="expanded",
)

# ── Inject custom CSS ─────────────────────────────────────────────────────
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ── Cached resources ──────────────────────────────────────────────────────

@st.cache_resource
def get_config():
    """Load application configuration once."""
    return load_config()


@st.cache_resource
def get_downloader(_config):
    """Initialize and cache the VideoDownloader."""
    return VideoDownloader(_config.download)


@st.cache_resource
def get_transcriber(_config):
    """
    Initialize and cache the GroqTranscriber.
    Returns None if GROQ_API_KEY is missing.
    """
    try:
        return GroqTranscriber(_config.transcription)
    except TranscriptionError:
        return None


# ── YouTube transcript-first helper ───────────────────────────────────────

def _build_yt_result(data: dict, operations: dict) -> dict:
    """Attach SRT/VTT captions to a YouTube result dict if requested."""
    segments = data.get("segments") or []
    if operations.get("generate_captions") and segments:
        cg = CaptionGenerator(
            words_per_line=operations.get("words_per_line", 10),
            max_lines=operations.get("max_lines", 2),
        )
        data["srt_content"] = cg.generate_srt(segments)
        data["vtt_content"] = cg.generate_vtt(segments)
    return {"success": True, "data": data, "error": None}


def _youtube_transcript_first(url: str, operations: dict, transcriber) -> dict | None:
    """YouTube transcription: Worker → Supadata → fall through to yt-dlp."""
    from loguru import logger

    # ── Tier 1: Cloudflare Worker (captions via edge network) ─────────
    with st.spinner("Fetching YouTube captions..."):
        t1 = fetch_via_worker(url)
    if t1.success:
        return _build_yt_result({
            "url": url, "platform": "youtube", "source": t1.source,
            "transcription": t1.text, "language": t1.language,
            "duration": None, "segments": t1.segments or [],
        }, operations)

    logger.info(f"Tier 1 Worker failed ({t1.error}), trying Supadata")

    # ── Tier 2: Supadata managed API ─────────────────────────────────
    with st.spinner("Fetching transcript via Supadata..."):
        t2 = fetch_via_supadata(url)
    if t2.success:
        return _build_yt_result({
            "url": url, "platform": "youtube", "source": t2.source,
            "transcription": t2.text, "language": t2.language,
            "duration": None, "segments": t2.segments or [],
        }, operations)

    logger.warning(f"All YouTube tiers failed for {video_id}")
    return None  # fall through to yt-dlp as absolute last resort


# ── Processing helpers ────────────────────────────────────────────────────

def process_single_url(
    url: str,
    operations: dict,
    config,
    downloader: VideoDownloader,
    transcriber,
) -> dict:
    """
    Download and transcribe a single video URL.

    Returns a dict with keys: success (bool), data (dict | None), error (str | None).
    """
    result: dict = {"success": False, "data": None, "error": None}

    try:
        if not operations["download"]:
            result["error"] = "Download operation is required."
            return result

        platform = detect_platform(url)

        # ── YouTube transcript-first path ─────────────────────────────
        # Fetch captions directly — no audio download, no Groq needed.
        # Falls back to Cobalt audio download + Groq, then yt-dlp.
        if platform == "youtube" and operations.get("transcribe"):
            yt_result = _youtube_transcript_first(
                url, operations, transcriber
            )
            if yt_result is not None:
                return yt_result

        # ── Standard download path (Instagram, or YouTube last-resort) ─
        with st.spinner(f"Downloading from {platform}..."):
            dl_success, audio_file, dl_error, source = downloader.download_video(url)

        if not dl_success:
            result["error"] = f"Download failed: {dl_error}"
            return result

        result["data"] = {
            "url": url,
            "platform": platform or "unknown",
            "audio_file": str(audio_file),
            "source": source,
        }

        if not operations["transcribe"]:
            result["success"] = True
            return result

        if transcriber is None:
            result["error"] = "Transcription unavailable: GROQ_API_KEY is not set."
            return result

        with st.spinner("Transcribing audio via Groq..."):
            tr_success, transcription, metadata, tr_error = transcriber.transcribe_audio(
                Path(str(audio_file))
            )

        if not tr_success:
            result["error"] = f"Transcription failed: {tr_error}"
            return result

        result["data"].update(
            {
                "transcription": transcription,
                "language": metadata["language"],
                "duration": metadata["duration"],
                "segments": metadata.get("segments", []),
            }
        )

        segments = metadata.get("segments", [])
        if operations.get("generate_captions") and segments:
            caption_gen = CaptionGenerator(
                words_per_line=operations.get("words_per_line", 10),
                max_lines=operations.get("max_lines", 2),
            )
            result["data"]["srt_content"] = caption_gen.generate_srt(segments)
            result["data"]["vtt_content"] = caption_gen.generate_vtt(segments)
        elif operations.get("generate_captions") and not segments:
            result["data"]["caption_error"] = "No segments returned — captions unavailable."

        result["success"] = True

    except Exception as exc:
        result["error"] = str(exc)

    return result


# ── Sidebar ───────────────────────────────────────────────────────────────

def render_sidebar(config) -> dict:
    """
    Render the sidebar and return an operations dict.

    Returns:
        dict with keys: download, transcribe, generate_captions,
        words_per_line, max_lines.
    """
    with st.sidebar:
        # API status
        api_key_present = bool(os.environ.get("GROQ_API_KEY"))
        st.markdown(render_api_status(api_key_present), unsafe_allow_html=True)

        st.markdown("### Operations")
        do_download = st.checkbox("Download", value=True, key="op_download")
        do_transcribe = st.checkbox("Transcribe", value=True, key="op_transcribe")
        do_captions = st.checkbox("Generate Captions", value=True, key="op_captions")

        words_per_line = 10
        max_lines = 2

        if do_captions and do_transcribe:
            st.markdown("### Caption Settings")
            words_per_line = st.slider(
                "Words per line",
                min_value=5,
                max_value=20,
                value=10,
                key="cap_wpl",
            )
            max_lines = st.slider(
                "Lines per caption",
                min_value=1,
                max_value=3,
                value=2,
                key="cap_ml",
            )

        st.markdown("### Supported Platforms")
        st.caption("Instagram Reels")
        st.caption("YouTube Videos")
        st.caption("YouTube Shorts")

    operations = {
        "download": do_download,
        "transcribe": do_transcribe,
        "generate_captions": do_captions,
        "words_per_line": words_per_line,
        "max_lines": max_lines,
    }
    # Store for csv helper access
    st.session_state["operations"] = operations
    return operations


# ── Results card ──────────────────────────────────────────────────────────

def render_results_card(data: dict, url: str) -> None:
    """Render the transcription results inside a styled card."""
    source = data.get("source")
    badge_html = render_downloader_badge(source)

    st.markdown(
        f"""
        <div class="result-card">
            <div class="result-card-header">
                <span class="result-card-title">Transcription</span>
                {badge_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Metrics row
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Platform", data.get("platform", "unknown").title())
    with m2:
        lang = data.get("language", "unknown")
        st.metric("Language", lang.upper() if lang else "N/A")
    with m3:
        duration = data.get("duration")
        st.metric("Duration", f"{duration:.1f}s" if duration else "N/A")

    # Transcription text area
    st.text_area(
        "Transcription text",
        data.get("transcription", ""),
        height=280,
        key="main_transcription",
        label_visibility="collapsed",
    )

    if "caption_error" in data:
        st.warning(f"Caption generation: {data['caption_error']}")

    # Download buttons
    video_id = extract_video_id(url) or "unknown"
    platform = data.get("platform", "unknown")

    db1, db2, db3 = st.columns(3)
    with db1:
        st.download_button(
            "Download TXT",
            data=data.get("transcription", ""),
            file_name=f"{platform}_{video_id}.txt",
            mime="text/plain",
            key="dl_txt",
        )
    if "srt_content" in data:
        with db2:
            st.download_button(
                "Download SRT",
                data=data["srt_content"],
                file_name=f"{platform}_{video_id}.srt",
                mime="text/plain",
                key="dl_srt",
            )
    if "vtt_content" in data:
        with db3:
            st.download_button(
                "Download VTT",
                data=data["vtt_content"],
                file_name=f"{platform}_{video_id}.vtt",
                mime="text/plain",
                key="dl_vtt",
            )

    # Caption preview
    if "srt_content" in data:
        with st.expander("Caption Preview (SRT)"):
            preview = data["srt_content"]
            if len(preview) > 1000:
                preview = preview[:1000] + "\n..."
            st.code(preview, language="text")


# ── Main ──────────────────────────────────────────────────────────────────

def main() -> None:
    """Entry point for the Streamlit app."""
    # ── Auth gate ──────────────────────────────────────────────────────────
    if not check_auth():
        st.stop()

    config = get_config()
    downloader = get_downloader(config)
    transcriber = get_transcriber(config)

    operations = render_sidebar(config)
    render_user_menu()

    # ── Header ────────────────────────────────────────────────────────────
    st.title("Video Transcriber")
    st.markdown(
        '<p class="muted">Transcribe Instagram Reels and YouTube videos</p>',
        unsafe_allow_html=True,
    )

    # ── API key warning banner ────────────────────────────────────────────
    if not os.environ.get("GROQ_API_KEY"):
        st.error(
            "GROQ_API_KEY is not set. Add it to your .env file and restart the app. "
            "Transcription will not work until the key is provided.",
        )

    # ── URL input ─────────────────────────────────────────────────────────
    url = st.text_input(
        "Video URL",
        placeholder="https://www.youtube.com/watch?v=... or https://www.instagram.com/reel/...",
        label_visibility="collapsed",
        key="url_input",
    )

    # Platform badge when URL is valid
    if url:
        if validate_video_url(url):
            platform = detect_platform(url)
            if platform:
                st.markdown(
                    render_platform_badge(platform),
                    unsafe_allow_html=True,
                )

            if st.button("Transcribe Video", type="primary", key="transcribe_btn"):
                if not operations["download"] and not operations["transcribe"]:
                    st.error("Enable at least one operation in the sidebar.")
                else:
                    result = process_single_url(
                        url, operations, config, downloader, transcriber
                    )
                    if result["success"] and result["data"]:
                        if "transcription" in result["data"]:
                            render_results_card(result["data"], url)
                        else:
                            st.success("Download complete. Transcription was not selected.")
                    else:
                        st.error(f"Error: {result['error']}")
        else:
            st.error("Invalid URL. Enter a valid Instagram Reel or YouTube URL.")

    # ── Bulk CSV processing ───────────────────────────────────────────────
    st.markdown("---")
    with st.expander("Bulk CSV Processing", expanded=False):
        render_csv_processing(config, transcriber, downloader, CaptionGenerator)

    # ── Footer ────────────────────────────────────────────────────────────
    st.markdown(
        '<div class="footer">Built for Creators by Ionique Labs</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
