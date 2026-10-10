#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="python3"
VENV=".venv-build"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
  echo "Python 3 is required."
  exit 1
fi

if [ ! -x "$VENV/bin/python3" ]; then
  echo "Creating Python virtual environment..."
  "$PYTHON" -m venv "$VENV"
fi

VENV_PYTHON="$VENV/bin/python3"
"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install pyinstaller yt-dlp

if ! command -v ffplay >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  echo "ffplay/ffprobe are required to bundle local audio playback."
  echo "Install them with: sudo apt install ffmpeg"
  exit 1
fi

rm -rf build dist
mkdir -p bundled-bin
cp "$(command -v ffplay)" bundled-bin/ffplay
cp "$(command -v ffprobe)" bundled-bin/ffprobe
if command -v ffmpeg >/dev/null 2>&1; then cp "$(command -v ffmpeg)" bundled-bin/ffmpeg; fi

# Build a portable one-folder PyInstaller app.
"$VENV_PYTHON" -m PyInstaller --noconfirm --clean --onedir --name SonoraPlayer \
  --windowed --noconsole \
  --collect-all yt_dlp \
  --add-binary "bundled-bin/ffplay:bin" \
  --add-binary "bundled-bin/ffprobe:bin" \
  ${PWD}/app.py

# If ffmpeg exists, copy it into the same portable bin directory.
if [ -f bundled-bin/ffmpeg ]; then
  cp bundled-bin/ffmpeg dist/SonoraPlayer/_internal/bin/ffmpeg
fi

cat > dist/SonoraPlayer/run-sonora.sh <<'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")"
exec ./SonoraPlayer
EOF
chmod +x dist/SonoraPlayer/run-sonora.sh
chmod +x dist/SonoraPlayer/SonoraPlayer

# Desktop launcher helper. The binary itself is the app: double-click it to open
# without a terminal. The desktop file is optional and can be installed locally.
cat > dist/SonoraPlayer/SonoraPlayer.desktop <<EOF
[Desktop Entry]
Type=Application
Name=Sonora Player
Comment=Local music player
Exec=$(pwd)/dist/SonoraPlayer/SonoraPlayer
Path=$(pwd)/dist/SonoraPlayer
Terminal=false
Categories=AudioVideo;Audio;Player;
StartupNotify=true
EOF
chmod +x dist/SonoraPlayer/SonoraPlayer.desktop

cat > dist/SonoraPlayer/install-desktop-launcher.sh <<EOF
#!/usr/bin/env bash
set -e
APP_DIR="$(pwd)/dist/SonoraPlayer"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
mkdir -p "$DESKTOP_DIR"
sed "s#^Exec=.*#Exec=$APP_DIR/SonoraPlayer#; s#^Path=.*#Path=$APP_DIR#" "$APP_DIR/SonoraPlayer.desktop" > "$DESKTOP_DIR/SonoraPlayer.desktop"
chmod +x "$APP_DIR/SonoraPlayer"
echo "Sonora Player launcher installed to $DESKTOP_DIR/SonoraPlayer.desktop"
EOF
chmod +x dist/SonoraPlayer/install-desktop-launcher.sh

# Convenience archive.
tar -C dist -czf SonoraPlayer-linux-x86_64.tar.gz SonoraPlayer

echo
echo "==============================================="
echo "Sonora Player PyInstaller build complete."
echo "==============================================="
echo "Run:    ./dist/SonoraPlayer/run-sonora.sh"
echo "Copy:   dist/SonoraPlayer/"
echo "Archive: dist/SonoraPlayer-linux-x86_64.tar.gz"
echo
echo "Node.js/npm are NOT required for the built app."
echo "The bundled app includes Python code, yt-dlp, ffplay and ffprobe."
