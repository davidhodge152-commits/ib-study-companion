#!/usr/bin/env bash
#
# Bundle and minify JavaScript with esbuild.
#
# Produces: static/dist/app.<hash>.min.js
# Requires: npx esbuild (npm install esbuild)
#
# Usage:
#   ./scripts/build_js.sh          # build
#   ./scripts/build_js.sh --watch  # dev mode with rebuild on change

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="$ROOT/static/js/app.js"
DIST="$ROOT/static/dist"

if ! command -v npx &> /dev/null; then
    echo "Error: npx not found. Install Node.js first."
    exit 1
fi

# Clean previous builds
rm -rf "$DIST"
mkdir -p "$DIST"

if [[ "${1:-}" == "--watch" ]]; then
    echo "[build_js] Watching for changes..."
    npx esbuild "$SRC" \
        --bundle \
        --minify \
        --sourcemap \
        --format=esm \
        --outdir="$DIST" \
        --entry-names='[name].[hash]' \
        --watch
else
    echo "[build_js] Building production bundle..."
    npx esbuild "$SRC" \
        --bundle \
        --minify \
        --sourcemap \
        --format=esm \
        --outdir="$DIST" \
        --entry-names='[name].[hash]' \
        --metafile="$DIST/meta.json"

    # Generate manifest
    python3 "$ROOT/scripts/build_manifest.py" "$DIST"

    echo "[build_js] Done. Output:"
    ls -lh "$DIST"/*.js 2>/dev/null || echo "  (no .js files produced)"
fi
