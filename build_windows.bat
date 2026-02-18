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
pyinstaller --noconfirm --clean --windowed --onefile ^
  --name "Pushp-Menu-Generator" ^
  --add-data "templates;templates" ^
  --add-data "assets;assets" ^
  --add-data "static;static" ^
  app.py

echo.
echo Build complete. Output: dist\Pushp-Menu-Generator.exe
pause
