#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
echo "Fedora build: install Python 3, Tkinter and FFmpeg with your configured Fedora repositories, then run build_linux.sh."
exec ./build_linux.sh
