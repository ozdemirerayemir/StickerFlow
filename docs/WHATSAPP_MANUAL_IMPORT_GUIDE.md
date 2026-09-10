# WhatsApp Manual Import Guide

> **Disclaimer:** WhatsApp's sticker acceptance behaviour varies by version across
> Desktop, Web, and Mobile. The information in this guide represents possible workflows
> observed by users — it is **not** guaranteed to work in all environments.
>
> StickerFlow is a sticker asset producer. It does not control how WhatsApp
> handles the files it produces.

---

## Static Sticker — Possible Workflow

1. Produce a static sticker in StickerFlow (PNG/JPG/WEBP input → 512×512 WebP output).
2. Save the output `.webp` file to a known location.
3. **WhatsApp Web / Desktop (paste attempt):**
   - Copy the WebP file to clipboard using StickerFlow's "Copy to Clipboard" button.
   - Open WhatsApp Web or Desktop, click on a chat.
   - Paste (`Ctrl+V` / `Cmd+V`).
   - WhatsApp *may* accept the pasted image as a sticker — behaviour depends on the WhatsApp version.
4. **If paste does not work as a sticker:**
   - Transfer the `.webp` file to your phone (USB, cloud drive, email, etc.).
   - Use a third-party sticker creator app (e.g., Sticker Maker, WAStickerapps) to package it.
   - Or use WhatsApp's built-in sticker creator if available in your WhatsApp version.
5. Send the sticker from your phone as normal.

---

## Animated Sticker — Possible Workflow

1. Produce an animated sticker in StickerFlow (MP4/MOV/GIF input → animated WebP output).
2. Verify the output meets the targets:
   - File size: ≤ 500 KB
   - Dimensions: 512×512 pixels
   - Duration: ≤ 3 seconds
3. Transfer the `.webp` file to your phone.
4. Use a sticker pack creation app that supports animated WebP import.
5. Add it to a WhatsApp sticker pack and send it.
6. If WhatsApp does not accept it directly as a sticker, note that StickerFlow's scope is limited to asset production — it cannot guarantee WhatsApp-side acceptance.

---

## Platform Notes

### WhatsApp Web
- Clipboard paste behaviour for stickers is version-dependent.
- Some versions treat pasted WebP as a regular image, not a sticker.
- Manual file upload through the attachment dialog will send it as a document, not a sticker.

### WhatsApp Desktop (Windows / macOS)
- Similar limitations to WhatsApp Web.
- Sticker sending from Desktop typically requires the sticker to be in your sticker collection first.

### WhatsApp Mobile (iOS / Android)
- Stickers can be added via third-party sticker creator apps.
- The official WhatsApp sticker maker (within the app) may accept WebP files in some versions.
- Check the sticker maker app store description for WebP animated support.

---

> **Important reminder:**
>
> WhatsApp's Desktop, Web, and Mobile sticker acceptance behaviour may change between
> versions without notice. For this reason, outputs produced by StickerFlow must be
> manually tested in your target WhatsApp environment.
>
> This application is not officially affiliated with WhatsApp.
> It only produces sticker-compatible media assets.
