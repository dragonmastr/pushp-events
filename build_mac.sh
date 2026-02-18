#!/usr/bin/env bash
set -euo pipefail

echo "Creating virtual environment..."
python3 -m venv .venv
source .venv/bin/activate

echo "Installing dependencies..."
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo "Building macOS app..."
pyinstaller --noconfirm --clean --windowed --onefile \
  --name "Pushp-Menu-Generator" \
  --add-data "templates:templates" \
  --add-data "assets:assets" \
  --add-data "static:static" \
  app.py

echo ""
echo "Build complete. Output: dist/Pushp-Menu-Generator"
