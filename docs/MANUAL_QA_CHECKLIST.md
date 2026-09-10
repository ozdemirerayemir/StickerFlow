# StickerFlow — Manual QA Checklist

Use this checklist to manually verify the application before each release.

---

## Static Image Processing

- [ ] PNG file processed successfully → 512×512 WebP output
- [ ] JPG file processed successfully → 512×512 WebP output
- [ ] WEBP file processed successfully → 512×512 WebP output
- [ ] BMP file processed successfully → 512×512 WebP output
- [ ] Corrupt/invalid file shows a clear error message (no crash)
- [ ] Unsupported file extension shows a clear error message
- [ ] Very large image (>25 MP) shows memory guard error message
- [ ] AI background removal works (requires rembg)
- [ ] AI removal + white stroke produces visible outline
- [ ] Stroke width options (2px / 3px / 4px) produce visibly different results
- [ ] Safe area padding toggle works correctly
- [ ] Output alpha channel is preserved
- [ ] Output file size is displayed correctly
- [ ] Output is within 100 KB limit (or clear warning is shown)
- [ ] Preview updates after processing
- [ ] Preview checkerboard background shows transparency correctly

---

## Video Processing

- [ ] MP4 metadata read correctly (duration, resolution, FPS)
- [ ] MOV file processed successfully
- [ ] WEBM file processed successfully
- [ ] GIF file processed successfully
- [ ] 3-second limit is enforced (longer clip is clamped with warning)
- [ ] Start > End shows a clear error message
- [ ] Audio is removed from output (silent animated WebP)
- [ ] 512×512 animated WebP created successfully
- [ ] Animation loops correctly when opened in a viewer
- [ ] Output file size shown correctly
- [ ] Output within 500 KB limit (or clear warning shown)
- [ ] Cover crop mode fills 512×512 without letterboxing
- [ ] Fit+pad mode (if available) preserves aspect ratio with transparency
- [ ] FFmpeg not installed → app opens, video button disabled, install guide shown
- [ ] Cancel button stops FFmpeg process (no hanging process after cancel)
- [ ] Temp files cleaned up after cancel or error

---

## AI Background Removal

- [ ] rembg not installed → AI mode buttons disabled with explanation
- [ ] First use of AI mode → consent dialog shown before download starts
- [ ] Cancel in consent dialog → no download starts, processing aborted
- [ ] AI model download completes successfully (online test)
- [ ] AI processing runs in background (UI does not freeze)
- [ ] Progress indicator visible during AI processing
- [ ] AI removal result has clean, non-noisy edges

---

## Clipboard

- [ ] **Windows:** Copy to Clipboard button works (static sticker copied as PNG)
- [ ] **macOS:** Copy to Clipboard button works
- [ ] **Linux:** Copy to Clipboard button works (with wl-copy or xclip)
- [ ] Clipboard unavailable → button disabled with clear explanation
- [ ] Clipboard failure does not crash the application
- [ ] Animated sticker → Copy to Clipboard button is not shown/enabled

---

## WhatsApp Manual Verification

> These cannot be automated. Must be tested manually.

- [ ] Static WebP file opens correctly on phone
- [ ] Static WebP accepted as sticker in WhatsApp (behaviour may vary)
- [ ] Animated WebP file opens correctly on phone
- [ ] Animated WebP accepted as animated sticker in WhatsApp (behaviour may vary)
- [ ] WhatsApp Web clipboard paste behaviour verified
- [ ] WhatsApp Desktop clipboard paste behaviour verified
- [ ] Application correctly communicates that acceptance is not guaranteed

---

## UI & Error Handling

- [ ] Drag-and-drop works (if tkinterdnd2 installed)
- [ ] File dialog works (always available)
- [ ] FFmpeg status indicator shows correctly (green ✓ or red ✗)
- [ ] rembg status indicator shows correctly
- [ ] Processing state: Create button disabled during processing
- [ ] Cancel button enabled during processing, disabled after
- [ ] Progress bar visible during processing
- [ ] Status messages update during processing
- [ ] Result card shows output filename and size
- [ ] Status badge shows OK / WARNING / LIMIT EXCEEDED correctly
- [ ] Show in Folder button opens the output directory
- [ ] WhatsApp Manual Guide dialog opens and is readable
- [ ] Legal notice visible in UI footer
- [ ] Application window resizes correctly (minimum size maintained)

---

## Security & Privacy

- [ ] No network traffic during image processing (verify with network monitor)
- [ ] No network traffic during video processing
- [ ] Temp files removed after processing completes
- [ ] Temp files removed after cancellation
- [ ] Temp files removed after error
- [ ] Log file contains no full user file paths
- [ ] No `shell=True` in any subprocess call (code review)
- [ ] No placeholder/TODO functions remaining (code review)
