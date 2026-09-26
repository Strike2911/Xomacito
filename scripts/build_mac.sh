#!/bin/bash
set -euo pipefail
[[ "$(uname -s)" == Darwin ]] || { echo "Compila este proyecto desde macOS." >&2; exit 1; }
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
command -v brew >/dev/null || { echo "Falta Homebrew." >&2; exit 1; }
export PATH="$(brew --prefix)/bin:$PATH"
for formula in python@3.11 ffmpeg deno poppler ghostscript cairo harfbuzz create-dmg; do
    brew list --versions "$formula" >/dev/null || { echo "Falta: brew install $formula" >&2; exit 1; }
done
PYTHON="${XOMACITO_PYTHON:-$(brew --prefix python@3.11)/bin/python3.11}"
"$PYTHON" -c 'import sys; assert sys.version_info[:2] == (3, 11), "Se requiere Python 3.11"'
VENV="$ROOT/.tools/mac-venv"
[[ -x "$VENV/bin/python" ]] || "$PYTHON" -m venv "$VENV"
PYTHON="$VENV/bin/python"
"$PYTHON" -c 'import sys; assert sys.version_info[:2] == (3, 11), "Recrea .tools/mac-venv con Python 3.11"'
"$PYTHON" -m pip install -r requirements.txt
"$PYTHON" -m pip check
[[ -f Xomacito-icon.icns ]] || bash scripts/make_mac_icon.sh
"$PYTHON" -m PyInstaller --noconfirm --clean \
    --workpath .build/work/mac --distpath dist/mac .build/XomacitoMac.spec
APP="$ROOT/dist/mac/Xomacito.app"
"$APP/Contents/MacOS/Xomacito" --self-test
codesign --verify --deep --strict "$APP"
ARCH="$("$PYTHON" -c 'import platform; print(platform.machine())')"
VERSION="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$APP/Contents/Info.plist")"
mkdir -p "$ROOT/release/mac"
DMG="$ROOT/release/mac/Xomacito-$VERSION-$ARCH.dmg"
[[ ! -e "$DMG" ]] || { echo "Ya existe $DMG; conservalo o retiralo antes de recompilar." >&2; exit 1; }
STAGE="$(mktemp -d "${TMPDIR:-/tmp}/xomacito-dmg.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT
ditto "$APP" "$STAGE/Xomacito.app"
create-dmg --volname Xomacito --window-size 540 360 \
    --icon-size 100 --icon Xomacito.app 140 160 \
    --app-drop-link 400 160 "$DMG" "$STAGE"
hdiutil verify "$DMG"
echo "APP: $APP"
echo "DMG: $DMG"
