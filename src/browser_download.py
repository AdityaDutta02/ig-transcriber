"""
Browser-Side Audio Download (Tier 2)

Embeds JavaScript in Streamlit that calls Cobalt API from the user's
browser (residential IP — not blocked by YouTube). Downloads MP3 as
base64 and passes it back to Python for Groq transcription.
"""

from __future__ import annotations

import base64
import tempfile
from pathlib import Path
from typing import Optional, Tuple

import streamlit as st
import streamlit.components.v1 as components
from loguru import logger

COBALT_INSTANCE = "https://cobalt-api.meowing.de"

_COMPONENT_HTML = """
<div id="status" style="font-family:sans-serif;font-size:14px;color:#888;">
  Downloading audio via your browser...
</div>
<script>
(async function() {
  const status = document.getElementById("status");
  const videoUrl = "VIDEO_URL_PLACEHOLDER";
  const cobaltUrl = "COBALT_URL_PLACEHOLDER";

  try {
    status.textContent = "Requesting audio from Cobalt...";

    const apiResp = await fetch(cobaltUrl, {
      method: "POST",
      headers: {"Content-Type": "application/json", "Accept": "application/json"},
      body: JSON.stringify({url: videoUrl, downloadMode: "audio", audioFormat: "mp3"}),
    });

    if (!apiResp.ok) {
      const errText = await apiResp.text();
      throw new Error("Cobalt API error: " + apiResp.status + " " + errText.slice(0, 200));
    }

    const data = await apiResp.json();
    if (data.status === "error") {
      throw new Error("Cobalt error: " + (data.error?.code || JSON.stringify(data)));
    }

    const downloadUrl = data.url;
    if (!downloadUrl) {
      throw new Error("Cobalt returned no download URL");
    }

    status.textContent = "Downloading audio file...";
    const audioResp = await fetch(downloadUrl);
    if (!audioResp.ok) {
      throw new Error("Audio download failed: HTTP " + audioResp.status);
    }

    const blob = await audioResp.blob();
    if (blob.size < 1000) {
      throw new Error("Downloaded file too small (" + blob.size + " bytes)");
    }

    status.textContent = "Encoding audio (" + (blob.size / 1024 / 1024).toFixed(1) + " MB)...";

    const reader = new FileReader();
    reader.onload = function() {
      const base64data = reader.result.split(",")[1];
      status.textContent = "Sending to server for transcription...";
      window.parent.postMessage({type: "streamlit:setComponentValue", value: base64data}, "*");
    };
    reader.readAsDataURL(blob);

  } catch (err) {
    status.textContent = "Failed: " + err.message;
    status.style.color = "#e74c3c";
    window.parent.postMessage({type: "streamlit:setComponentValue", value: "ERROR:" + err.message}, "*");
  }
})();
</script>
"""


def render_browser_download(video_url: str, cobalt_url: str = COBALT_INSTANCE) -> Optional[str]:
    """Render a Streamlit component that downloads audio via the user's browser.

    Returns base64-encoded MP3 audio string, or None if failed.
    Uses st.components.v1.html with bidirectional communication.
    """
    html = _COMPONENT_HTML.replace("VIDEO_URL_PLACEHOLDER", video_url)
    html = html.replace("COBALT_URL_PLACEHOLDER", cobalt_url)

    result = components.html(html, height=40)
    return result if result and not str(result).startswith("ERROR:") else None


def save_browser_audio(base64_audio: str, video_id: str) -> Tuple[bool, Optional[Path], Optional[str]]:
    """Decode base64 audio from browser and save to temp file.

    Returns (success, audio_path, error_message).
    """
    if not base64_audio or base64_audio.startswith("ERROR:"):
        error_msg = base64_audio.replace("ERROR:", "") if base64_audio else "No audio data"
        return False, None, error_msg

    try:
        audio_bytes = base64.b64decode(base64_audio)
        if len(audio_bytes) < 1000:
            return False, None, f"Audio too small ({len(audio_bytes)} bytes)"

        save_dir = Path(tempfile.gettempdir()) / "video_downloads"
        save_dir.mkdir(parents=True, exist_ok=True)
        audio_path = save_dir / f"browser_{video_id}.mp3"

        audio_path.write_bytes(audio_bytes)
        logger.info(f"Browser audio saved: {audio_path} ({len(audio_bytes):,} bytes)")
        return True, audio_path, None

    except Exception as exc:
        logger.warning(f"Failed to decode browser audio: {exc}")
        return False, None, str(exc)
