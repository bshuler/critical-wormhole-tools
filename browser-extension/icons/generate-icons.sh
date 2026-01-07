#!/bin/bash
# Generate PNG icons from SVG
# Requires: rsvg-convert (librsvg) or ImageMagick

SVG_FILE="wormhole.svg"

# Check for rsvg-convert
if command -v rsvg-convert &> /dev/null; then
    echo "Using rsvg-convert..."
    for size in 16 32 48 128; do
        rsvg-convert -w $size -h $size "$SVG_FILE" -o "wormhole-${size}.png"
        echo "Generated wormhole-${size}.png"
    done
# Fallback to ImageMagick
elif command -v convert &> /dev/null; then
    echo "Using ImageMagick..."
    for size in 16 32 48 128; do
        convert -background none -resize ${size}x${size} "$SVG_FILE" "wormhole-${size}.png"
        echo "Generated wormhole-${size}.png"
    done
else
    echo "Error: Neither rsvg-convert nor ImageMagick found."
    echo "Install with: brew install librsvg  OR  brew install imagemagick"
    exit 1
fi

echo "Done! Icons generated."
