"""
StickerFlow — AI Background Remover
Wraps rembg with lazy import, model consent/download flow,
and graceful degradation when rembg is not installed.
"""

import io
import logging
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("stickerflow.ai")

# Cached availability state — checked once per session
_rembg_available: Optional[bool] = None
_rembg_error: str = ""


def is_rembg_available() -> Tuple[bool, str]:
    """
    Check if rembg is installed without loading heavy ML dependencies.

    Returns:
        (available: bool, reason: str)
        If not available, reason contains a user-friendly explanation.
    """
    global _rembg_available, _rembg_error

    if _rembg_available is not None:
        return _rembg_available, _rembg_error

    import importlib.util
    try:
        spec = importlib.util.find_spec("rembg")
        if spec is not None:
            _rembg_available = True
            _rembg_error = ""
            logger.info("rembg is available.")
        else:
            _rembg_available = False
            _rembg_error = (
                "rembg is not installed. "
                "Install it with: pip install rembg[cpu]\n"
                "AI background removal will be disabled."
            )
            logger.warning("rembg not available: %s", _rembg_error)
    except Exception as exc:
        _rembg_available = False
        _rembg_error = f"rembg failed to load: {exc}"
        logger.error("rembg load error: %s", exc)

    return _rembg_available, _rembg_error


def remove_background(
    image_bytes: bytes,
    cancel_event=None,
) -> bytes:
    """
    Remove the background from image data using rembg.

    Args:
        image_bytes:  Raw image bytes (any PIL-supported format).
        cancel_event: threading.Event — checked before and after rembg call.

    Returns:
        PNG bytes with background removed (RGBA).

    Raises:
        RuntimeError: If rembg is not available.
        RuntimeError: If processing fails.
        RuntimeError: If cancelled.
    """
    available, reason = is_rembg_available()
    if not available:
        raise RuntimeError(reason)

    if cancel_event and cancel_event.is_set():
        raise RuntimeError("Processing was cancelled.")

    try:
        import rembg  # type: ignore[import]
        logger.debug("Running rembg background removal…")
        result = rembg.remove(image_bytes)
        logger.debug("rembg completed.")
    except RuntimeError:
        raise
    except Exception as exc:
        logger.error("rembg processing failed: %s", exc, exc_info=True)
        raise RuntimeError(
            f"AI background removal failed: {exc}. "
            "This may be a model download issue. Check your internet connection "
            "for the first run."
        ) from exc

    if cancel_event and cancel_event.is_set():
        raise RuntimeError("Processing was cancelled.")

    from typing import cast
    return cast(bytes, result)


def remove_background_pil(
    pil_image,
    cancel_event=None,
):
    """
    Convenience wrapper: accepts a PIL Image, returns a PIL Image.

    Args:
        pil_image:    PIL.Image.Image (any mode).
        cancel_event: Optional cancellation event.

    Returns:
        PIL.Image.Image in RGBA mode with background removed.

    Raises:
        RuntimeError: See remove_background().
    """
    from PIL import Image

    buf = io.BytesIO()
    pil_image.save(buf, format="PNG")
    result_bytes = remove_background(buf.getvalue(), cancel_event=cancel_event)
    return Image.open(io.BytesIO(result_bytes)).convert("RGBA")


def get_model_info() -> dict:
    """
    Return information about the rembg model state.
    Used by the UI to display status and consent dialog text.
    """
    available, reason = is_rembg_available()
    info = {
        "available": available,
        "reason": reason,
        "model_name": "u2net (default rembg model)",
        "first_run_note": (
            "On first use, rembg will download the AI model (~170 MB). "
            "An internet connection is required for the initial download. "
            "Subsequent uses will work offline."
        ),
    }
    return info
