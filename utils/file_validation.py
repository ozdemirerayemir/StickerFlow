"""
StickerFlow — File Validation Utilities
Validates user-provided files before processing.
"""

import logging
from pathlib import Path

from config import SUPPORTED_IMAGE_EXTENSIONS, SUPPORTED_VIDEO_EXTENSIONS

logger = logging.getLogger("stickerflow.validation")


class FileValidationError(Exception):
    """Raised when a file fails validation."""


def validate_file(path: str | Path) -> Path:
    """
    Validate that *path* points to a readable, supported media file.

    Args:
        path: File path (str or Path).

    Returns:
        Resolved, absolute Path if validation passes.

    Raises:
        FileValidationError: With a user-friendly message describing the issue.
    """
    try:
        resolved = Path(path).resolve()
    except Exception as exc:
        raise FileValidationError(f"Invalid file path: {exc}") from exc

    if not resolved.exists():
        raise FileValidationError("The selected file does not exist.")

    if not resolved.is_file():
        raise FileValidationError("The selected path is not a file.")

    try:
        # Check readability by opening in binary mode
        with resolved.open("rb") as fh:
            fh.read(1)
    except PermissionError:
        raise FileValidationError(
            "Cannot read the selected file. Check file permissions."
        )
    except Exception as exc:
        raise FileValidationError(f"Cannot read the selected file: {exc}") from exc

    ext = resolved.suffix.lower()
    all_supported = SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_VIDEO_EXTENSIONS
    if ext not in all_supported:
        raise FileValidationError(
            f"Unsupported file format: '{ext}'. "
            f"Supported image formats: {', '.join(sorted(SUPPORTED_IMAGE_EXTENSIONS))}. "
            f"Supported video formats: {', '.join(sorted(SUPPORTED_VIDEO_EXTENSIONS))}."
        )

    logger.debug("File validated: %s (extension: %s)", resolved.name, ext)
    return resolved


def is_image(path: str | Path) -> bool:
    """Return True if *path* has a supported image extension."""
    return Path(path).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS


def is_video(path: str | Path) -> bool:
    """Return True if *path* has a supported video extension."""
    return Path(path).suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS


def validate_output_path(output_dir: str | Path, filename: str) -> Path:
    """
    Validate and return a safe output file path inside *output_dir*.

    Guards against path-traversal by ensuring the resolved output path
    is still inside the intended directory.

    Args:
        output_dir: The intended parent directory.
        filename:   The desired output filename (basename only; directory
                    components are stripped for safety).

    Returns:
        Resolved output path.

    Raises:
        FileValidationError: If the path escapes *output_dir*.
    """
    safe_name = Path(filename).name  # strip any directory components
    resolved_dir = Path(output_dir).resolve()
    output_path = (resolved_dir / safe_name).resolve()

    if not str(output_path).startswith(str(resolved_dir)):
        raise FileValidationError(
            "Output path escapes the intended directory. Operation aborted."
        )

    return output_path
