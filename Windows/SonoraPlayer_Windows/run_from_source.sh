#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

VENV=".venv-source"
if [ ! -x "$VENV/bin/python" ]; then
	python3 -m venv "$VENV"
fi

PYTHON="$VENV/bin/python"
if ! "$PYTHON" -c 'import yt_dlp' >/dev/null 2>&1; then
	"$PYTHON" -m pip install yt-dlp
fi

exec "$PYTHON" app.py
