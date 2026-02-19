@echo off
setlocal

echo Creating virtual environment...
python -m venv .venv
call .venv\Scripts\activate

echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo Building Windows executable...
set "GTK_DIR=C:\Program Files\GTK3-Runtime Win64"

if exist "%GTK_DIR%\bin" (
  echo Including GTK runtime from %GTK_DIR%
  pyinstaller --noconfirm --clean --windowed --onefile ^
    --name "Pushp-Menu-Generator" ^
    --hidden-import menu_generator ^
    --hidden-import weasyprint ^
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
    --add-data "templates;templates" ^
    --add-data "assets;assets" ^
    --add-data "static;static" ^
    app.py
)

echo.
echo Build complete. Output: dist\Pushp-Menu-Generator.exe
pause
