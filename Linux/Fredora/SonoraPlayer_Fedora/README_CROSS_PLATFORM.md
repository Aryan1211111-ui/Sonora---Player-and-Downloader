# Sonora Player — Windows + Ubuntu + Fedora

This is the Python/Tkinter + PyInstaller version of Sonora Player. It does not use Electron, Node.js, npm or `.deb`.

## Windows `.exe`

Build on Windows:

1. Install Python 3.11+.
2. Install FFmpeg and put the FFmpeg `bin` directory in PATH. It must contain `ffmpeg.exe`, `ffplay.exe`, and `ffprobe.exe`.
3. Double-click `build_windows.bat`.

Output:

```text
dist\\SonoraPlayer\\SonoraPlayer.exe
```

Double-click `SonoraPlayer.exe` to open the GUI. No terminal window is opened.

## Ubuntu

Install Python/Tkinter and FFmpeg using your Ubuntu package manager, then:

```bash
chmod +x build_ubuntu.sh
./build_ubuntu.sh
```

Output:

```text
dist/SonoraPlayer/SonoraPlayer
dist/SonoraPlayer-linux-x86_64.tar.gz
```

Double-click `SonoraPlayer` in the file manager after enabling executable permission.

## Fedora

Install Python/Tkinter and FFmpeg using your configured Fedora repositories, then:

```bash
chmod +x build_fedora.sh
./build_fedora.sh
```

The output is the same PyInstaller one-folder Linux bundle and tar.gz archive.

## Important PyInstaller rule

PyInstaller is not a true cross-compiler. Build the Windows `.exe` on Windows, and build Linux binaries on Linux. The included GitHub Actions workflow can build Windows, Ubuntu and Fedora artifacts automatically.

## Offline

The player and already-downloaded/local music can work without internet. The URL downloader needs an internet connection while downloading. The build bundles the Python `yt_dlp` package and FFmpeg tools available during the build.

Use the downloader only for audio/content you own or are legally authorized to download.
