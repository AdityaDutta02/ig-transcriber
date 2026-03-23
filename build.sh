#!/usr/bin/env bash
# Render build script
set -e

pip install --upgrade pip
pip install -r requirements.txt

echo "yt-dlp version: $(python -c 'import yt_dlp; print(yt_dlp.version.__version__)' 2>/dev/null || echo 'not found')"
echo "Build complete."
