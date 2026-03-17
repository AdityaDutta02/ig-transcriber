#!/usr/bin/env bash
# Render build script — runs once during each deploy
set -e

# ── Python dependencies ───────────────────────────────────────────────
pip install --upgrade pip
pip install -r requirements.txt

# ── Build the PO Token server ─────────────────────────────────────────
# Clones bgutil-ytdlp-pot-provider and compiles the TypeScript server.
# At runtime, start.sh launches it as a background process.
POT_SERVER_DIR="$HOME/bgutil-server"

echo "Setting up PO Token server..."
rm -rf "$POT_SERVER_DIR"
git clone --depth 1 --single-branch \
    https://github.com/Brainicism/bgutil-ytdlp-pot-provider.git \
    "$POT_SERVER_DIR"

cd "$POT_SERVER_DIR/server"
npm ci
npx tsc
echo "PO Token server built successfully at $POT_SERVER_DIR/server/build/"

# Move build up for cleaner paths
mv build "$POT_SERVER_DIR/build"
mv node_modules "$POT_SERVER_DIR/node_modules"

echo "Build complete."
