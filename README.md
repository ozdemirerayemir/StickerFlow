# StickerFlow

**WhatsApp-Compatible Sticker Asset Studio**

> This application is not officially affiliated with WhatsApp.
> It only produces sticker-compatible media assets.

---

## 1. What is StickerFlow?

StickerFlow is a cross-platform desktop application (Windows, macOS, Linux) that converts your images and short video clips into WhatsApp-compatible sticker assets.

It is a **local-only sticker asset producer**. It does not automate WhatsApp, send any data to the cloud, or access your WhatsApp account.

---

## 2. What does it do?

- Converts static images (PNG, JPG, WEBP, BMP) into 512×512 WebP sticker files
- Converts short videos (MP4, MOV, WEBM, GIF) into 512×512 animated WebP sticker files
- Optional AI background removal (powered by rembg)
- Configurable stroke outline with slider (1–12px) and color palette (White, Black, Yellow, Red, Green, Cyan)
- Optional text overlay (meme / sticker text) with high-contrast outline
- Iterative compression to meet WhatsApp size targets (<100 KB static, <500 KB video)
- Output validation with clear status badges and quick "Show in Folder" action

---

## 3. What does it NOT do?

- Does **not** send stickers to WhatsApp automatically
- Does **not** access your WhatsApp account or messages
- Does **not** upload your media to any server
- Does **not** guarantee WhatsApp acceptance (see Section 11)
- Does **not** include Android/iOS ContentProvider integration
- Does **not** require an internet connection (except for the first rembg model download)

---

## 4. Quick Start

### Prerequisites
- Python 3.10 or newer

### Setup & Launch
```bash
# 1. Clone repository
git clone https://github.com/ozdemirerayemir/StickerFlow.git
cd StickerFlow

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run application
python main.py
```

---

## 5. FFmpeg Setup

Video sticker processing requires FFmpeg. See [`docs/FFMPEG_SETUP.md`](docs/FFMPEG_SETUP.md) for platform-specific installation instructions.

Quick summary:
- **Windows:** Download from https://ffmpeg.org/download.html, extract, add `bin\` to your PATH (or configure in Settings)
- **macOS:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg` or equivalent

If FFmpeg is not in your PATH, launch StickerFlow and use **Settings → Set FFmpeg Path** to point to the binary manually.

---

## 6. rembg Model Setup

AI background removal uses the `u2net` model (~170 MB). On first use, StickerFlow will:
1. Ask for your consent before downloading
2. Download the model automatically (requires internet on first run only)
3. Cache it locally for all future offline uses

If you do not want to use AI background removal, choose **Keep Background** mode — rembg is never downloaded in that case.

---

## 7. Static Sticker Production

1. Drop or select an image (PNG, JPG, WEBP, BMP)
2. Choose a processing mode:
   - **Keep Background** — fit image in a 512×512 transparent canvas
   - **AI Background Removal** — remove background, fit in canvas
   - **AI Removal + Stroke** — remove background, add outline
3. Optionally adjust:
   - **Stroke width** (1–12 px slider)
   - **Stroke color** (White, Black, Yellow, Red, Green, Cyan)
   - **Text overlay** (meme / sticker text, top or bottom)
   - **Safe area padding** (recommended for WhatsApp round bubbles)
4. Click **Create Sticker**
5. Output is saved to `~/StickerFlow Output/` by default
6. Click **Show in Folder** to reveal the file in Windows Explorer, or **Copy to Clipboard**

---

## 8. Video Sticker Production

1. Drop or select a video (MP4, MOV, WEBM, GIF)
2. Set start and end times (maximum 3 seconds)
3. Choose crop mode:
   - **Cover crop** — fills 512×512 (recommended)
   - **Fit + pad** — preserves aspect ratio with transparent padding
4. Click **Create Sticker**
5. Output is saved as an animated WebP

---

## 9. Clipboard Feature & Limitations

Static stickers can be copied to the clipboard as PNG.

> ⚠ **Warning:** WhatsApp Web/Desktop may receive a pasted image as a regular image rather than a sticker. Clipboard sticker support depends on the WhatsApp version and cannot be guaranteed.

Clipboard availability by platform:
- **Windows:** Requires `pywin32` (optional) or PowerShell
- **macOS:** Uses `osascript`
- **Linux:** Requires `wl-copy` (Wayland) or `xclip`/`xsel` (X11)

If clipboard is unavailable, the button is disabled with an explanation.

---

## 10. WhatsApp Manual Import

See [`docs/WHATSAPP_MANUAL_IMPORT_GUIDE.md`](docs/WHATSAPP_MANUAL_IMPORT_GUIDE.md) for step-by-step guidance on transferring sticker assets to WhatsApp.

> WhatsApp's sticker acceptance behaviour varies by version. All outputs must be manually tested in your target WhatsApp environment.

---

## 11. Running Tests

```bash
python -m pytest tests/ -v
```

No real media files required — tests generate synthetic images at runtime.

---

## 12. Building a Distributable

See [`build_scripts/`](build_scripts/) for Windows PyInstaller build configuration.

---

## 13. Known Limitations

- AI background removal is not available for video clips
- rembg model download requires internet on first use (~170 MB)
- Large or complex videos may not compress below the 500 KB limit
- WhatsApp sticker support varies by platform and version
- Clipboard image paste may not be recognised as a sticker by WhatsApp

---

## 14. FAQ

**Q: Does StickerFlow upload my images anywhere?**
A: No. All processing is local. No data is sent to any server.

**Q: Why does WhatsApp show my sticker as a regular image?**
A: WhatsApp's sticker-vs-image detection is version-dependent and cannot be controlled by this application.

**Q: The AI background removal is very slow — is that normal?**
A: Yes, on CPU-only setups rembg can take 5–30 seconds depending on your machine. This is expected.

**Q: Can I use StickerFlow to send stickers automatically?**
A: No. This is intentionally out of scope. StickerFlow only produces the asset files.

---

## 15. Legal Notice

Only use content you have the right to use. This application is not officially affiliated with WhatsApp. It only produces sticker-compatible media assets.

"WhatsApp" is a registered trademark of WhatsApp LLC. StickerFlow is an independent open-source project with no affiliation to WhatsApp LLC or Meta Platforms, Inc.
