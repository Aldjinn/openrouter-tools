#!/usr/bin/env bash
#
# Build and run the OpenRouter prices Docker container, then copy output files.
#
# Usage:
#   chmod +x run.sh
#   ./run.sh
#

set -euo pipefail

IMAGE_NAME="openrouter-prices"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT_DIR="$(pwd)/output"

mkdir -p "$OUTPUT_DIR"

echo "Building Docker image '$IMAGE_NAME'..."
docker build -t "$IMAGE_NAME" "$SCRIPT_DIR"

echo "Running container (scraping rankings and generating reports)..."
docker run --rm -v "${OUTPUT_DIR}:/app/output" "$IMAGE_NAME"

# Only copy output files if they exist and are non-empty
updated=false

if [ -f "$OUTPUT_DIR/prices.html" ] && [ -s "$OUTPUT_DIR/prices.html" ]; then
    cp -f "$OUTPUT_DIR/prices.html" ./prices.html
    updated=true
fi

if [ -f "$OUTPUT_DIR/prices.md" ] && [ -s "$OUTPUT_DIR/prices.md" ]; then
    cp -f "$OUTPUT_DIR/prices.md" ./prices.md
    updated=true
fi

if [ -f "$OUTPUT_DIR/money.png" ]; then
    cp -f "$OUTPUT_DIR/money.png" ./money.png
fi

# Cleanup output dir
rm -rf "$OUTPUT_DIR"

if [ "$updated" = true ]; then
    echo "Done. Files written:"
    echo "  ./prices.html"
    echo "  ./prices.md"
else
    echo "No output files generated. Check logs above for errors."
    exit 1
fi