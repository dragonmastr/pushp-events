# Build Executables

You must build on each target OS.

## Windows (.exe)
1. Install Python 3.11+.
2. Build using the project script:
   ```bat
   build_windows.bat
   ```
3. Output:
   `dist\Pushp-Menu-Generator.exe`
4. Runtime prerequisite (target machine):
   Install GTK3 Runtime 64-bit before running the EXE.
5. Expected GTK path used by the app:
   `C:\Program Files\GTK3-Runtime Win64\bin`

## macOS (.app + .dmg)
1. Install Python 3.11+
2. Build `.app`:
   ```bash
   ./build_mac.sh
   ```
3. Manual build alternative:
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
- Windows build intentionally does not bundle GTK runtime to reduce EXE size.
- WeasyPrint depends on system libraries. If runtime fails, verify GTK installation and PATH.
- Always build on the same OS you are targeting.

## Runtime Output Folder
Generated PDFs are saved at:
```
<selected-output-folder>/Generated-menu/<excel_filename>/<event_name>_English.pdf
<selected-output-folder>/Generated-menu/<excel_filename>/<event_name>_Hindi.pdf
```
This folder is created after user selects output location in the app.
