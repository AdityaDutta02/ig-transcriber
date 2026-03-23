#!/usr/bin/env bash

# ── Start the PO Token server in the background ──────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
POT_SERVER_DIR="$SCRIPT_DIR/.pot-server"

if [ -f "$POT_SERVER_DIR/build/main.js" ]; then
    echo "Starting PO Token server on port 4416..."
    node "$POT_SERVER_DIR/build/main.js" --port 4416 &
    POT_PID=$!
    sleep 3
    if kill -0 "$POT_PID" 2>/dev/null; then
        echo "PO Token server process alive (PID $POT_PID)"
        # Verify the server actually responds
        if curl -sf http://127.0.0.1:4416/ >/dev/null 2>&1 || curl -sf http://127.0.0.1:4416/health >/dev/null 2>&1; then
            echo "PO Token server responding on port 4416"
        else
            echo "PO Token server process running but HTTP check inconclusive (may still work)"
        fi
        # Tell bgutil-ytdlp-pot-provider plugin where the server is
        export BGUTIL_POT_PROVIDER_HTTP_BASE="http://127.0.0.1:4416"
        echo "BGUTIL_POT_PROVIDER_HTTP_BASE set to http://127.0.0.1:4416"
    else
        echo "WARNING: PO Token server failed to start — falling back to RapidAPI"
    fi
else
    echo "WARNING: PO Token server not found at $POT_SERVER_DIR"
    echo "  Looked for: $POT_SERVER_DIR/build/main.js"
    ls -la "$POT_SERVER_DIR/" 2>/dev/null || echo "  Directory does not exist"
    echo "Falling back to RapidAPI"
fi

# ── Start Streamlit ───────────────────────────────────────────────────
exec streamlit run app.py \
    --server.port="${PORT:-8501}" \
    --server.address=0.0.0.0 \
    --server.headless=true
