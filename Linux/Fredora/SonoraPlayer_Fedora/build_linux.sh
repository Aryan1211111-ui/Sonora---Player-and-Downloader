#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3}"
VENV=".venv-build"

command -v "$PYTHON" >/dev/null 2>&1 || { echo "Python 3 is required."; exit 1; }
if ! "$PYTHON" -c 'import tkinter' >/dev/null 2>&1; then
  echo "Python Tkinter is required. Install your distro's python3-tkinter package."
  exit 1
fi

if [ ! -d "$VENV" ]; then "$PYTHON" -m venv "$VENV"; fi
source "$VENV/bin/activate"
python -m pip install --upgrade pip
python -m pip install -r requirements-build.txt

for tool in ffmpeg ffplay ffprobe; do
  command -v "$tool" >/dev/null 2>&1 || { echo "$tool is required in PATH."; exit 1; }
done

rm -rf build dist bundled-bin
mkdir -p bundled-bin
cp "$(command -v ffmpeg)" bundled-bin/ffmpeg
cp "$(command -v ffplay)" bundled-bin/ffplay
cp "$(command -v ffprobe)" bundled-bin/ffprobe

python -m PyInstaller --noconfirm --clean --onedir --name SonoraPlayer \
  --windowed --noconsole \
  --collect-all yt_dlp \
  --add-data "bundled-bin:bin" \
  app.py

chmod +x dist/SonoraPlayer/SonoraPlayer
cat > dist/SonoraPlayer/run-sonora.sh <<'EOF'
#!/usr/bin/env bash
cd "$(dirname "$0")"
exec ./SonoraPlayer
EOF
chmod +x dist/SonoraPlayer/run-sonora.sh

tar -C dist -czf dist/SonoraPlayer-linux-x86_64.tar.gz SonoraPlayer

echo "Built: dist/SonoraPlayer/"
echo "Archive: dist/SonoraPlayer-linux-x86_64.tar.gz"
