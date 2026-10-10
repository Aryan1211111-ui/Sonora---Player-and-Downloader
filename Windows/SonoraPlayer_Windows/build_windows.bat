@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo === Sonora Player - Windows PyInstaller build ===

where py >nul 2>&1
if errorlevel 1 (
  where python >nul 2>&1
  if errorlevel 1 (
    echo Python 3 is required. Install Python from python.org with PATH enabled.
    exit /b 1
  )
  set "PY=python"
) else (
  set "PY=py -3"
)

if not exist ".venv-build-windows\Scripts\python.exe" %PY% -m venv .venv-build-windows
call .venv-build-windows\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt

where ffmpeg >nul 2>&1
if errorlevel 1 (
  echo ffmpeg.exe was not found in PATH.
  echo Install FFmpeg and put its bin directory in PATH, then rerun this script.
  exit /b 1
)
where ffplay >nul 2>&1
if errorlevel 1 (
  echo ffplay.exe was not found in PATH.
  exit /b 1
)
where ffprobe >nul 2>&1
if errorlevel 1 (
  echo ffprobe.exe was not found in PATH.
  exit /b 1
)

for /f "delims=" %%I in ('where ffmpeg') do if not defined FFMPEG set "FFMPEG=%%I"
for %%I in ("%FFMPEG%") do set "FFBIN=%%~dpI"

rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
rmdir /s /q bundled-bin 2>nul
mkdir bundled-bin
xcopy "%FFBIN%*" "bundled-bin\" /E /I /Y >nul

python -m PyInstaller --noconfirm --clean --onedir --name SonoraPlayer ^
  --windowed --noconsole ^
  --collect-all yt_dlp ^
  --add-data "bundled-bin;bin" ^
  app.py

copy /Y run_windows.bat dist\SonoraPlayer\run_windows.bat >nul

echo.
echo === BUILD COMPLETE ===
echo EXE: dist\SonoraPlayer\SonoraPlayer.exe
pause
