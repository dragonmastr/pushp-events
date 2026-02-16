# Build Executables

You must build on each target OS.

## Windows (.exe)
1. Install Python 3.11+
2. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   python -m pip install pyinstaller
   ```
3. Build:
   ```bash
   pyinstaller --noconsole --onefile \
     --add-data "templates;templates" \
     --add-data "assets;assets" \
     --add-data "data;data" \
     app.py
   ```
4. Output:
   `dist/app.exe`

## macOS (.app + .dmg)
1. Install Python 3.11+
2. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   python -m pip install pyinstaller
   ```
3. Build `.app`:
   ```bash
   pyinstaller --noconsole --windowed \
     --add-data "templates:templates" \
     --add-data "assets:assets" \
     --add-data "data:data" \
     app.py
   ```
4. Create `.dmg` (requires `create-dmg`):
   ```bash
   brew install create-dmg
   create-dmg "dist/app.app"
   ```

## Notes
- WeasyPrint depends on system libraries. If the build fails, install the platform libraries needed by WeasyPrint.
- Always build on the same OS you are targeting.
