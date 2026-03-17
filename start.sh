#!/usr/bin/env bash
set -e

# ── Decode YouTube cookies if provided ────────────────────────────────
if [ -n "$YT_COOKIES_B64" ]; then
    echo "$YT_COOKIES_B64" | base64 -d > /tmp/yt_cookies.txt
    export YT_COOKIES_PATH=/tmp/yt_cookies.txt
    echo "Decoded YouTube cookies to /tmp/yt_cookies.txt"
fi

# ── Start the PO Token server in the background ──────────────────────
# The server was built during render build step (see build.sh).
# It listens on 127.0.0.1:4416 — the bgutil plugin auto-discovers it.
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
