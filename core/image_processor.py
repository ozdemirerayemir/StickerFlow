"""
StickerFlow — Static Image Processor
Converts static images (PNG, JPG, WEBP, BMP) into 512×512 WebP sticker assets.

Processing modes:
  Mode 1 — Keep original background (fit + transparent pad)
  Mode 2 — AI background removal via rembg
  Mode 3 — AI background removal + configurable white stroke
"""

import io
import logging
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Optional

from PIL import Image, ImageFilter, ImageOps

from config import (
    MAX_INPUT_PIXELS,
    STATIC_QUALITY_STEPS,
    WHATSAPP_TARGETS,
)
from utils.threading_worker import post_progress, post_status

logger = logging.getLogger("stickerflow.image")


class ProcessingMode(Enum):
    KEEP_BACKGROUND = auto()       # Mode 1
    REMOVE_BACKGROUND = auto()     # Mode 2
    REMOVE_BACKGROUND_STROKE = auto()  # Mode 3


@dataclass
class ProcessingOptions:
    mode: ProcessingMode = ProcessingMode.KEEP_BACKGROUND
    canvas_size: int = 512
    safe_area_size: int = 480
    padding_px: int = 16
    stroke_width: int = 3          # used in Mode 3 (2–4 px)
    max_file_kb: int = 100
    apply_safe_area: bool = True   # pad content to safe_area_size


@dataclass
class ProcessingResult:
    output_path: Path
    size_kb: float
    width: int
    height: int
    mode: str
    quality_used: int
    within_limit: bool
    warnings: list[str]


class ImageProcessingError(Exception):
    """Raised when image processing fails with a user-friendly message."""


def process_image(
    input_path: str | Path,
    output_path: str | Path,
    options: Optional[ProcessingOptions] = None,
    cancel_event=None,
    progress_queue=None,
) -> ProcessingResult:
    """
    Process a static image into a WhatsApp-compatible WebP sticker.

    Args:
        input_path:     Source image file.
        output_path:    Destination .webp file path.
        options:        Processing options (uses defaults if None).
        cancel_event:   threading.Event — checked at each major step.
        progress_queue: Queue for posting progress updates to UI.

    Returns:
        ProcessingResult with output metadata.

    Raises:
        ImageProcessingError: On any processing failure.
    """
    if options is None:
        options = ProcessingOptions()

    input_path = Path(input_path)
    output_path = Path(output_path)

    def _check_cancel():
        if cancel_event and cancel_event.is_set():
            raise ImageProcessingError("Processing was cancelled.")

    def _progress(value: float, text: str = ""):
        if progress_queue:
            post_progress(progress_queue, value, text)

    def _status(text: str):
        if progress_queue:
            post_status(progress_queue, text)

    try:
        # ── Step 1: Load & validate ──────────────────────────────────────────
        _status("Loading image…")
        _progress(0.05)
        img = _load_image(input_path)
        _check_cancel()

        # ── Step 2: Mode-specific processing ────────────────────────────────
        mode_label = options.mode.name.replace("_", " ").title()
        _status(f"Processing ({mode_label})…")
        _progress(0.15)

        if options.mode == ProcessingMode.KEEP_BACKGROUND:
            img = _fit_to_canvas(img, options)

        elif options.mode == ProcessingMode.REMOVE_BACKGROUND:
            _status("Removing background (AI)…")
            _progress(0.2)
            img = _remove_background(img)
            _check_cancel()
            img = _fit_to_canvas(img, options)

        elif options.mode == ProcessingMode.REMOVE_BACKGROUND_STROKE:
            _status("Removing background (AI)…")
            _progress(0.2)
            img = _remove_background(img)
            _check_cancel()
            _status("Adding white stroke…")
            _progress(0.5)
            img = _apply_stroke(img, options.stroke_width)
            img = _fit_to_canvas(img, options)

        _check_cancel()
        _progress(0.65, "Encoding WebP…")

        # ── Step 3: Iterative WebP compression ──────────────────────────────
        warnings: list[str] = []
        output_data, quality_used = _compress_webp(
            img, options.max_file_kb, warnings, progress_queue
        )
        _check_cancel()

        # ── Step 4: Write output ─────────────────────────────────────────────
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(output_data)
        _progress(1.0, "Done.")

        size_kb = len(output_data) / 1024
        w, h = img.size

        return ProcessingResult(
            output_path=output_path,
            size_kb=size_kb,
            width=w,
            height=h,
            mode=mode_label,
            quality_used=quality_used,
            within_limit=size_kb <= options.max_file_kb,
            warnings=warnings,
        )

    except ImageProcessingError:
        raise
    except Exception as exc:
        logger.error("Image processing failed: %s", exc, exc_info=True)
        raise ImageProcessingError(
            f"An unexpected error occurred during image processing: {exc}"
        ) from exc


# ── Internal helpers ──────────────────────────────────────────────────────────

def _load_image(path: Path) -> Image.Image:
    """Load, fix EXIF orientation, convert to RGBA, and guard memory."""
    try:
        img = Image.open(path)
    except Exception as exc:
        raise ImageProcessingError(
            f"Cannot open image file. It may be corrupt or in an unsupported format. "
            f"Detail: {exc}"
        ) from exc

    # Memory guard
    if img.width * img.height > MAX_INPUT_PIXELS:
        raise ImageProcessingError(
            f"Image is too large ({img.width}×{img.height} pixels). "
            "Please use an image with fewer than 25 megapixels."
        )

    # Fix EXIF orientation
    try:
        img = ImageOps.exif_transpose(img)
    except Exception as exc:
        logger.warning("EXIF transpose failed (non-critical): %s", exc)

    # Normalize to RGBA
    if img.mode != "RGBA":
        img = img.convert("RGBA")

    # Strip metadata (privacy: no GPS, user comments, etc.)
    # Re-create image from raw pixel data to discard all EXIF/metadata.
    clean_img = Image.frombytes("RGBA", img.size, img.tobytes())

    logger.debug("Loaded image: %dx%d RGBA", clean_img.width, clean_img.height)
    return clean_img


def _fit_to_canvas(img: Image.Image, opts: ProcessingOptions) -> Image.Image:
    """
    Fit *img* into a canvas_size × canvas_size canvas with transparent padding.
    Content is scaled to fit within safe_area_size (or canvas_size if safe area disabled).
    """
    canvas_size = opts.canvas_size
    content_size = opts.safe_area_size if opts.apply_safe_area else canvas_size

    # Scale down (or up) to fit content_size, preserving aspect ratio
    img.thumbnail((content_size, content_size), Image.Resampling.LANCZOS)

    # Center on transparent canvas
    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    offset_x = (canvas_size - img.width) // 2
    offset_y = (canvas_size - img.height) // 2
    canvas.paste(img, (offset_x, offset_y), mask=img if img.mode == "RGBA" else None)

    return canvas


def _remove_background(img: Image.Image) -> Image.Image:
    """Remove background using rembg (lazy import)."""
    try:
        import rembg  # type: ignore[import]
    except ImportError:
        raise ImageProcessingError(
            "rembg is not installed. Install it with: pip install rembg[cpu]\n"
            "Or choose 'Keep Background' mode instead."
        )

    try:
        # rembg works with bytes or PIL Image
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)
        result_bytes = rembg.remove(img_bytes.read())
        result = Image.open(io.BytesIO(result_bytes)).convert("RGBA")
    except ImageProcessingError:
        raise
    except Exception as exc:
        raise ImageProcessingError(
            f"Background removal failed: {exc}. "
            "Check your internet connection if this is the first run (model download required)."
        ) from exc

    # Light post-processing: clean up noisy alpha edges
    result = _clean_alpha_edges(result)
    return result


def _clean_alpha_edges(img: Image.Image, threshold: int = 10) -> Image.Image:
    """
    Remove semi-transparent noise pixels around edges.
    Pixels with alpha < threshold are set fully transparent.
    Avoids over-aggressive clipping that would lose fine detail.
    """
    r, g, b, a = img.split()
    # Slight Gaussian blur on alpha to smooth jagged edges
    a_smooth = a.filter(ImageFilter.GaussianBlur(radius=0.5))
    # Zero out near-transparent pixels
    import struct
    a_bytes = bytearray(a_smooth.tobytes())
    for i in range(len(a_bytes)):
        if a_bytes[i] < threshold:
            a_bytes[i] = 0
    a_clean = Image.frombytes("L", img.size, bytes(a_bytes))
    result = Image.merge("RGBA", (r, g, b, a_clean))
    return result


def _apply_stroke(
    img: Image.Image,
    stroke_width: int = 3,
) -> Image.Image:
    """
    Add a white stroke around the subject's alpha mask.

    Strategy:
    1. Extract alpha channel.
    2. Dilate alpha by stroke_width using MaxFilter.
    3. Blur slightly for anti-aliasing.
    4. Build white stroke layer from dilated alpha.
    5. Composite: white_stroke behind original image.
    """
    from PIL import ImageFilter

    if img.mode != "RGBA":
        img = img.convert("RGBA")

    r, g, b, a = img.split()

    # Dilate alpha: apply MaxFilter iteratively for stroke_width pixels
    dilated_a = a.copy()
    for _ in range(stroke_width):
        dilated_a = dilated_a.filter(ImageFilter.MaxFilter(3))

    # Light Gaussian blur for anti-aliasing
    dilated_a = dilated_a.filter(ImageFilter.GaussianBlur(radius=0.8))

    # Build a white stroke layer
    stroke_layer = Image.new("RGBA", img.size, (255, 255, 255, 0))
    white_solid = Image.new("RGBA", img.size, (255, 255, 255, 255))
    stroke_layer.paste(white_solid, mask=dilated_a)

    # Composite: stroke behind original
    result = Image.alpha_composite(stroke_layer, img)
    return result


def _compress_webp(
    img: Image.Image,
    max_kb: int,
    warnings: list[str],
    progress_queue=None,
) -> tuple[bytes, int]:
    """
    Iteratively compress *img* as lossy WebP until under max_kb.

    Returns:
        (webp_bytes, quality_used)
    """
    data: bytes = b""
    size_kb: float = 0.0

    for i, quality in enumerate(STATIC_QUALITY_STEPS):
        if progress_queue:
            post_progress(
                progress_queue,
                0.65 + 0.25 * (i / len(STATIC_QUALITY_STEPS)),
                f"Encoding WebP (quality {quality})…",
            )

        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=quality, method=6, lossless=False)
        data = buf.getvalue()
        size_kb = len(data) / 1024

        logger.debug("WebP quality %d → %.1f KB", quality, size_kb)

        if size_kb <= max_kb:
            return data, quality

    # Failed all quality steps — return lowest quality with a warning
    warnings.append(
        f"Could not compress below {max_kb} KB limit "
        f"(smallest attempt: {size_kb:.1f} KB). "
        "The file was saved anyway, but it may not meet WhatsApp's size requirements."
    )
    return data, STATIC_QUALITY_STEPS[-1]

