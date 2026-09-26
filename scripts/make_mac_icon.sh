#!/bin/bash
set -euo pipefail
[[ "$(uname -s)" == Darwin ]] || { echo "Este script requiere macOS." >&2; exit 1; }
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/xomacito-icon.XXXXXX")"
trap 'rm -rf "$WORK"' EXIT
ICONSET="$WORK/Xomacito.iconset"
mkdir -p "$ICONSET"
sips -s format png "$ROOT/Xomacito-icon.ico" --out "$WORK/source.png" >/dev/null
for size in 16 32 128 256 512; do
    sips -z "$size" "$size" "$WORK/source.png" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
    double=$((size * 2))
    sips -z "$double" "$double" "$WORK/source.png" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$ROOT/Xomacito-icon.icns"
echo "$ROOT/Xomacito-icon.icns"
