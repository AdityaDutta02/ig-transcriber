#!/usr/bin/env bash

# ── Decode YouTube cookies if provided ────────────────────────────────
if [ -n "$YT_COOKIES_B64" ]; then
    if echo "$YT_COOKIES_B64" | base64 --decode > /tmp/yt_cookies.txt 2>/dev/null; then
        export YT_COOKIES_PATH=/tmp/yt_cookies.txt
        echo "Decoded YouTube cookies to /tmp/yt_cookies.txt"
    else
        echo "WARNING: Failed to decode YT_COOKIES_B64 — skipping cookies"
        rm -f /tmp/yt_cookies.txt
    fi
fi

# ── Start the PO Token server in the background ──────────────────────
POT_SERVER_DIR="/opt/bgutil-server"
if [ -f "$POT_SERVER_DIR/build/main.js" ]; then
    echo "Starting PO Token server on port 4416..."
    node "$POT_SERVER_DIR/build/main.js" --port 4416 &
    POT_PID=$!
    sleep 3
    if kill -0 "$POT_PID" 2>/dev/null; then
        echo "PO Token server running (PID $POT_PID)"
    else
        echo "WARNING: PO Token server failed to start — falling back to RapidAPI"
    fi
else
    echo "WARNING: PO Token server not found at $POT_SERVER_DIR — falling back to RapidAPI"
fi

# ── Start Streamlit ───────────────────────────────────────────────────
exec streamlit run app.py \
    --server.port="${PORT:-8501}" \
    --server.address=0.0.0.0 \
    --server.headless=true
