#!/usr/bin/env bash
set -euo pipefail

echo "Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

ICON_PNG="assets/logo.png"
if [ ! -f "$ICON_PNG" ]; then
  ICON_PNG="assets/pushp-event-logo.png"
fi
ICONSET="assets/app-icon.iconset"
ICON_ICNS="assets/app-icon.icns"
ICON_ARG=""

if [ -f "$ICON_PNG" ]; then
  echo "Creating macOS icon from $ICON_PNG"
  rm -rf "$ICONSET"
  mkdir -p "$ICONSET"
  sips -z 16 16 "$ICON_PNG" --out "$ICONSET/icon_16x16.png" >/dev/null
  sips -z 32 32 "$ICON_PNG" --out "$ICONSET/icon_16x16@2x.png" >/dev/null
  sips -z 32 32 "$ICON_PNG" --out "$ICONSET/icon_32x32.png" >/dev/null
  sips -z 64 64 "$ICON_PNG" --out "$ICONSET/icon_32x32@2x.png" >/dev/null
  sips -z 128 128 "$ICON_PNG" --out "$ICONSET/icon_128x128.png" >/dev/null
  sips -z 256 256 "$ICON_PNG" --out "$ICONSET/icon_128x128@2x.png" >/dev/null
  sips -z 256 256 "$ICON_PNG" --out "$ICONSET/icon_256x256.png" >/dev/null
  sips -z 512 512 "$ICON_PNG" --out "$ICONSET/icon_256x256@2x.png" >/dev/null
  sips -z 512 512 "$ICON_PNG" --out "$ICONSET/icon_512x512.png" >/dev/null
  sips -z 1024 1024 "$ICON_PNG" --out "$ICONSET/icon_512x512@2x.png" >/dev/null
  iconutil -c icns "$ICONSET" -o "$ICON_ICNS"
  rm -rf "$ICONSET"
  if [ -f "$ICON_ICNS" ]; then
    ICON_ARG="--icon $ICON_ICNS"
  fi
else
  echo "Icon PNG not found. Continuing without custom icon."
fi

echo "Building macOS app..."
pyinstaller --noconfirm --clean --windowed --onefile \
  --name "Pushp-Menu-Generator" \
  --hidden-import menu_generator \
  --hidden-import weasyprint \
  $ICON_ARG \
  --add-data "templates:templates" \
  --add-data "assets:assets" \
  --add-data "static:static" \
  app.py

echo ""
echo "Build complete. Output: dist/Pushp-Menu-Generator"
