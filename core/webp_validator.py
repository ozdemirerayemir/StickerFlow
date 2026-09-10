"""
StickerFlow — WebP Output Validator
Validates generated static and animated WebP files against WhatsApp targets.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("stickerflow.validator")


@dataclass
class ValidationResult:
    """Outcome of a WebP validation pass."""

    ok: bool = True
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def __post_init__(self):
        pass  # fields are always initialized via field(default_factory=list)

    @property
    def status_label(self) -> str:
        if self.errors:
            return "LIMIT EXCEEDED"
        if self.warnings:
            return "WARNING"
        return "OK"

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.ok = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


def validate_static_webp(
    path: str | Path,
    canvas_size: int = 512,
    max_kb: int = 100,
) -> ValidationResult:
    """
    Validate a static WebP sticker asset.

    Checks:
    - File exists and is readable.
    - File opens as a valid WebP image.
    - Dimensions are canvas_size × canvas_size.
    - Alpha channel is present.
    - File size is within max_kb.

    Args:
        path:        Path to the WebP file.
        canvas_size: Expected width and height in pixels (default 512).
        max_kb:      Maximum allowed file size in KB (default 100).

    Returns:
        ValidationResult with ok flag, warnings, and errors.
    """
    from PIL import Image, UnidentifiedImageError

    result = ValidationResult()
    p = Path(path)

    # ── Existence & readability ──────────────────────────────────────────────
    if not p.exists():
        result.add_error("Output file was not created.")
        return result

    if not p.is_file():
        result.add_error("Output path is not a file.")
        return result

    # ── File size ────────────────────────────────────────────────────────────
    size_kb = p.stat().st_size / 1024
    if size_kb > max_kb:
        result.add_error(
            f"File size {size_kb:.1f} KB exceeds the {max_kb} KB limit."
        )
    else:
        logger.debug("File size OK: %.1f KB / %d KB", size_kb, max_kb)

    # ── Open and inspect ─────────────────────────────────────────────────────
    try:
        with Image.open(p) as img:
            # Format
            if img.format != "WEBP":
                result.add_error(
                    f"File is not a valid WebP image (detected format: {img.format})."
                )

            # Dimensions
            w, h = img.size
            if w != canvas_size or h != canvas_size:
                result.add_error(
                    f"Dimensions {w}×{h} do not match required {canvas_size}×{canvas_size}."
                )
            else:
                logger.debug("Dimensions OK: %dx%d", w, h)

            # Alpha channel
            if img.mode not in ("RGBA", "LA"):
                result.add_warning(
                    "Output image does not have an alpha channel. "
                    "WhatsApp stickers typically require transparency."
                )
            else:
                logger.debug("Alpha channel present (mode: %s).", img.mode)

    except UnidentifiedImageError:
        result.add_error("Output file cannot be opened as an image. It may be corrupt.")
    except Exception as exc:
        result.add_error(f"Failed to inspect output file: {exc}")

    return result


def validate_animated_webp(
    path: str | Path,
    canvas_size: int = 512,
    max_kb: int = 500,
    max_duration_sec: float = 3.0,
) -> ValidationResult:
    """
    Validate an animated WebP sticker asset.

    Checks:
    - File exists and is readable.
    - Opens as a valid animated WebP.
    - Dimensions are canvas_size × canvas_size.
    - Duration does not exceed max_duration_sec.
    - File size is within max_kb.
    - Loop count is 0 (infinite).
    - First and last frames are not fully black (basic corruption check).

    Args:
        path:            Path to the animated WebP file.
        canvas_size:     Expected canvas size (default 512).
        max_kb:          Maximum allowed file size in KB (default 500).
        max_duration_sec: Maximum allowed duration (default 3.0 s).

    Returns:
        ValidationResult.
    """
    from PIL import Image, ImageStat, UnidentifiedImageError

    result = ValidationResult()
    p = Path(path)

    if not p.exists():
        result.add_error("Output file was not created.")
        return result

    size_kb = p.stat().st_size / 1024
    if size_kb > max_kb:
        result.add_error(
            f"File size {size_kb:.1f} KB exceeds the {max_kb} KB limit."
        )

    try:
        with Image.open(p) as img:
            if img.format != "WEBP":
                result.add_error(
                    f"File is not a valid WebP image (detected format: {img.format})."
                )
                return result

            if not getattr(img, "is_animated", False):
                result.add_error(
                    "Output file is a static WebP, not animated. "
                    "Video processing may have failed."
                )
                return result

            # Dimensions
            w, h = img.size
            if w != canvas_size or h != canvas_size:
                result.add_error(
                    f"Dimensions {w}×{h} do not match required {canvas_size}×{canvas_size}."
                )

            # Frame count and duration
            n_frames: int = getattr(img, "n_frames", 1)
            logger.debug("Animated WebP: %d frames.", n_frames)

            # Calculate total duration from frame durations
            total_ms = 0
            try:
                for frame_idx in range(n_frames):
                    img.seek(frame_idx)
                    frame_info = img.info
                    total_ms += frame_info.get("duration", 0)
            except EOFError:
                pass

            if total_ms > 0:
                total_sec = total_ms / 1000.0
                if total_sec > max_duration_sec:
                    result.add_error(
                        f"Animation duration {total_sec:.2f}s exceeds "
                        f"the {max_duration_sec:.1f}s limit."
                    )
                else:
                    logger.debug("Duration OK: %.2fs.", total_sec)

            # Loop count (0 = infinite)
            loop = img.info.get("loop", -1)
            if loop != 0:
                result.add_warning(
                    f"Loop count is {loop}; expected 0 (infinite loop) "
                    "for WhatsApp stickers."
                )

            # Basic corruption check on first frame
            img.seek(0)
            first_frame = img.convert("RGB")
            stat = ImageStat.Stat(first_frame)
            if all(m < 2 for m in stat.mean):
                result.add_warning(
                    "First frame appears to be fully black. "
                    "The output may be corrupt."
                )

    except UnidentifiedImageError:
        result.add_error("Output file cannot be opened as an image. It may be corrupt.")
    except Exception as exc:
        result.add_error(f"Failed to inspect animated output: {exc}")

    return result
