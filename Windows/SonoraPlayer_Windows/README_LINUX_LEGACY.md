# Sonora Player — PyInstaller Edition

This edition is a **Python desktop application packaged with PyInstaller**. It does not use Electron, npm, Node.js or `.deb`.

## Features

- Spotify-style dark desktop UI
- Local music library
- Import individual files
- Import full folders recursively
- Search
- Play / pause / resume / stop
- Previous / next
- Seek bar
- Volume control
- Queue
- Shuffle
- Repeat
- Create playlists
- Add songs to playlists
- Downloads page using `yt-dlp`
- Downloaded audio is automatically added to the library
- Settings
- Persistent library and playlists

## Build on Zorin OS

Because Zorin/Ubuntu uses PEP 668, **do not install PyInstaller into system Python**. The supplied build script creates its own virtual environment automatically.

Install the system build prerequisites:

```bash
sudo apt update
sudo apt install python3 python3-venv ffmpeg
```

Then:

```bash
chmod +x build_pyinstaller.sh
./build_pyinstaller.sh
```

The script creates:

```text
.venv-build/
dist/SonoraPlayer/
dist/SonoraPlayer-linux-x86_64.tar.gz
```

Run the finished app:

```bash
./dist/SonoraPlayer/run-sonora.sh
```

You can copy the entire `dist/SonoraPlayer/` directory to another compatible Linux x86_64 machine. Node.js and npm are not required.

## Offline behavior

The built player can play already-imported/local audio without internet. The downloader obviously needs internet when fetching a URL.

The build attempts to bundle `ffplay`, `ffprobe`, `ffmpeg`, and the Python `yt-dlp` package, making the **player itself** portable. The bundle is Linux x86_64 and should be built on a compatible Linux machine.

## Downloader / authorization

Use the downloader only for audio or other content you own or are legally authorized to download. Sonora does not bypass DRM, private access, paywalls, or other access controls.

## If PyInstaller installation fails

Use the virtual environment created by the script:

```bash
source .venv-build/bin/activate
python -m pip install pyinstaller yt-dlp
```

Then rerun:

```bash
./build_pyinstaller.sh
```


## Double-click launch

The PyInstaller build uses `--windowed --noconsole`, so the built `SonoraPlayer` executable is a GUI application and does not require a terminal. After building, open:

```text
dist/SonoraPlayer/
```

Then double-click the **SonoraPlayer** file. Make sure the file is executable:

```bash
chmod +x dist/SonoraPlayer/SonoraPlayer
```

For an application-menu entry, run:

```bash
./dist/SonoraPlayer/install-desktop-launcher.sh
```

The `SonoraPlayer.desktop` file has `Terminal=false`, so it also launches without opening a terminal.

## Scrolling music list

The music library and queue pages now have a dedicated vertical scrollbar and mouse-wheel scrolling. The top header, sidebar and bottom player controls stay fixed while the song list scrolls.
