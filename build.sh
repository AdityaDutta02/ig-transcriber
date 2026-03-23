#!/usr/bin/env bash
# Render build script — runs once during each deploy
set -e

# ── Python dependencies ───────────────────────────────────────────────
pip install --upgrade pip
pip install -r requirements.txt

# ── Build the PO Token server ─────────────────────────────────────────
# Must be inside the repo directory — Render only persists build
# artifacts within the project root.
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
POT_SERVER_DIR="$REPO_DIR/.pot-server"

echo "Setting up PO Token server..."
echo "Node.js version: $(node --version)"
echo "npm version: $(npm --version)"

rm -rf "$POT_SERVER_DIR"
git clone --depth 1 --single-branch \
    https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git \
    "$POT_SERVER_DIR"

cd "$POT_SERVER_DIR/server"
npm ci
npx tsc
echo "PO Token server built successfully"

# Move build up for cleaner paths
mv build "$POT_SERVER_DIR/build"
mv node_modules "$POT_SERVER_DIR/node_modules"

# Verify the build artifact exists
if [ -f "$POT_SERVER_DIR/build/main.js" ]; then
    echo "Verified: $POT_SERVER_DIR/build/main.js exists"
else
    echo "ERROR: $POT_SERVER_DIR/build/main.js not found after build!"
    ls -la "$POT_SERVER_DIR/build/" 2>/dev/null || echo "  build/ directory missing"
fi

# Show installed yt-dlp and plugin versions
echo "yt-dlp version: $(python -c 'import yt_dlp; print(yt_dlp.version.__version__)' 2>/dev/null || echo 'not found')"
echo "bgutil plugin: $(pip show bgutil-ytdlp-pot-provider 2>/dev/null | grep Version || echo 'not found')"

echo "Build complete."
