# FFmpeg Setup Guide

StickerFlow uses FFmpeg for all video processing. FFmpeg is not bundled with the application and must be installed separately.

---

## Windows

### Option 1: Winget (recommended)
```powershell
winget install --id=Gyan.FFmpeg -e
```

### Option 2: Manual download
1. Visit https://ffmpeg.org/download.html → Windows → "Windows builds from gyan.dev" or "BtbN builds"
2. Download the **full** or **essentials** build (zip)
3. Extract to a location like `C:\ffmpeg\`
4. Add `C:\ffmpeg\bin` to your system `PATH`:
   - Open **Start → Edit system environment variables**
   - Under **System variables**, select `Path` → **Edit**
   - Click **New** → paste `C:\ffmpeg\bin`
   - Click **OK** → restart any open terminals
5. Verify: open a new Command Prompt and run `ffmpeg -version`

### Option 3: Set path inside StickerFlow
If you cannot modify PATH, launch StickerFlow and go to **Settings → Set FFmpeg Path**, then browse to `ffmpeg.exe`.

---

## macOS

### Option 1: Homebrew (recommended)
```bash
brew install ffmpeg
```

### Option 2: MacPorts
```bash
sudo port install ffmpeg
```

### Option 3: Manual
1. Download a macOS build from https://evermeet.cx/ffmpeg/
2. Place the `ffmpeg` binary in `/usr/local/bin/` (or anywhere in your PATH)
3. Make it executable: `chmod +x /usr/local/bin/ffmpeg`
4. Verify: `ffmpeg -version`

---

## Linux

### Debian / Ubuntu
```bash
sudo apt update
sudo apt install ffmpeg
```

### Fedora / RHEL
```bash
sudo dnf install ffmpeg
```

### Arch Linux
```bash
sudo pacman -S ffmpeg
```

### Snap
```bash
sudo snap install ffmpeg
```

---

## Adding FFmpeg to PATH

After installation, verify FFmpeg is in your PATH:
```bash
ffmpeg -version
```

If this command is not found, you need to add the directory containing `ffmpeg` to your `PATH` environment variable (see Windows instructions above for the general approach).

---

## Setting the Path Inside StickerFlow

If FFmpeg is installed but not in PATH:

1. Launch StickerFlow — you will see a "FFmpeg Not Found" warning
2. Click **Browse for FFmpeg** in the warning dialog
3. Navigate to the `ffmpeg` / `ffmpeg.exe` binary
4. StickerFlow will save this path and use it in all future sessions

---

## Verifying WebP & Animation Support

StickerFlow automatically probes FFmpeg capabilities on startup:
- **libwebp** — required for any WebP output
- **Animated WebP** — required for video stickers
- **Alpha WebP** — required for transparent animated stickers (Fit+Pad mode)

If any capability is missing, the relevant features are disabled with an explanation.

---

## Common Errors

| Error | Solution |
|-------|----------|
| `ffmpeg: command not found` | FFmpeg not in PATH — see above |
| `Unknown encoder 'libwebp'` | Your FFmpeg build lacks libwebp — install a full build |
| `Output file is empty` | FFmpeg ran but produced no frames — check trim range |
| `FFmpeg timed out` | Video is too large or complex — try a shorter clip |

---

## Supported FFmpeg Versions

StickerFlow works with FFmpeg 4.x and newer. FFmpeg 6.x or newer is recommended for the best WebP alpha support.
