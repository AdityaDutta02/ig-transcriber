#!/usr/bin/env bash

# ── Start the PO Token server in the background ──────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
POT_SERVER_DIR="$SCRIPT_DIR/.pot-server"

echo "=== PO Token Server Setup ==="
echo "Node.js: $(node --version 2>/dev/null || echo 'NOT FOUND')"
echo "Looking for: $POT_SERVER_DIR/build/main.js"

if [ -f "$POT_SERVER_DIR/build/main.js" ]; then
    echo "Starting PO Token server on port 4416..."
    node "$POT_SERVER_DIR/build/main.js" --port 4416 &
    POT_PID=$!
    sleep 5  # Give the server more time to start

    if kill -0 "$POT_PID" 2>/dev/null; then
        echo "PO Token server process alive (PID $POT_PID)"
        # Test HTTP connectivity — /ping is what the yt-dlp plugin checks
        for endpoint in "/ping" "/" "/health"; do
            RESPONSE=$(curl -s -w "\nHTTP_CODE:%{http_code}" "http://127.0.0.1:4416${endpoint}" 2>/dev/null)
            HTTP_CODE=$(echo "$RESPONSE" | grep "HTTP_CODE:" | cut -d: -f2)
            BODY=$(echo "$RESPONSE" | grep -v "HTTP_CODE:")
            echo "  GET :4416${endpoint} -> $HTTP_CODE ${BODY:0:100}"
        done
        echo "PO Token server ready — bgutil plugin will auto-discover on 127.0.0.1:4416"
    else
        echo "ERROR: PO Token server process died after start"
        echo "  Trying to capture error output..."
        node "$POT_SERVER_DIR/build/main.js" --port 4416 2>&1 | head -20 || true
    fi
else
    echo "WARNING: PO Token server not found"
    echo "  Expected: $POT_SERVER_DIR/build/main.js"
    if [ -d "$POT_SERVER_DIR" ]; then
        echo "  Directory exists. Contents:"
        ls -la "$POT_SERVER_DIR/"
        ls -la "$POT_SERVER_DIR/build/" 2>/dev/null || echo "  build/ subdirectory missing"
    else
        echo "  Directory does not exist at all"
    fi
fi

echo "=== yt-dlp Plugin Check ==="
python -c "
try:
    import yt_dlp
    print(f'yt-dlp version: {yt_dlp.version.__version__}')
except Exception as e:
    print(f'yt-dlp: {e}')
try:
    from yt_dlp_plugins.extractor.getpot_bgutil_http import *
    print('bgutil PO token HTTP plugin: LOADED')
except ImportError as e:
    print(f'bgutil PO token HTTP plugin: FAILED ({e})')
try:
    from yt_dlp_plugins.extractor.getpot_bgutil_script import *
    print('bgutil PO token script plugin: LOADED')
except ImportError as e:
    print(f'bgutil PO token script plugin: FAILED ({e})')
" 2>&1
echo "==========================="

# ── Start Streamlit ───────────────────────────────────────────────────
exec streamlit run app.py \
    --server.port="${PORT:-8501}" \
    --server.address=0.0.0.0 \
    --server.headless=true
