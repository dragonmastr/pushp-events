@echo off
setlocal

echo Creating virtual environment...
python -m venv .venv
call .venv\Scripts\activate

echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller
pip install pillow

echo Building Windows executable...
set "GTK_DIR=C:\Program Files\GTK3-Runtime Win64"
set "ICON_PNG=assets\logo.png"
if not exist "%ICON_PNG%" set "ICON_PNG=assets\pushp-event-logo.png"
set "ICON_ICO=assets\app-icon.ico"
set "ICON_ARG="

if exist "%ICON_PNG%" (
  echo Creating Windows icon from %ICON_PNG%
  if exist "%ICON_ICO%" del /f /q "%ICON_ICO%"
  python -c "from PIL import Image; img=Image.open(r'%ICON_PNG%'); img.save(r'%ICON_ICO%', format='ICO', sizes=[(256,256),(128,128),(64,64),(32,32),(16,16)])"
)
if exist "%ICON_ICO%" set "ICON_ARG=--icon %ICON_ICO%"

if not exist "%ICON_PNG%" (
  echo Icon PNG not found. Continuing without custom icon.
)

if exist "%GTK_DIR%\bin" (
  echo Including GTK runtime from %GTK_DIR%
  pyinstaller --noconfirm --clean --windowed --onefile ^
    --name "Pushp-Menu-Generator" ^
    --hidden-import menu_generator ^
    --hidden-import weasyprint ^
    %ICON_ARG% ^
    --add-data "%GTK_DIR%;gtk" ^
    --add-data "templates;templates" ^
    --add-data "assets;assets" ^
    --add-data "static;static" ^
    app.py
) else (
  echo GTK runtime not found at %GTK_DIR%. Building without bundled GTK.
  pyinstaller --noconfirm --clean --windowed --onefile ^
    --name "Pushp-Menu-Generator" ^
    --hidden-import menu_generator ^
    --hidden-import weasyprint ^
    %ICON_ARG% ^
    --add-data "templates;templates" ^
    --add-data "assets;assets" ^
    --add-data "static;static" ^
    app.py
)

echo.
echo Build complete. Output: dist\Pushp-Menu-Generator.exe
pause
