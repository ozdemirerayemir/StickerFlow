"""
StickerFlow — Clipboard Abstract Base Class
Defines the interface all platform backends must implement.
"""

import abc
from typing import Optional


class ClipboardBackend(abc.ABC):
    """Abstract clipboard backend for image copy operations."""

    @property
    def unavailable_reason(self) -> str:
        """Human-readable reason why clipboard is unavailable (empty if available)."""
        return ""

    @abc.abstractmethod
    def is_supported(self) -> bool:
        """Return True if image clipboard copy is available on this system."""

    @abc.abstractmethod
    def copy_image_png(self, pil_image) -> None:
        """
        Copy *pil_image* (PIL.Image.Image) to the clipboard as PNG.

        Args:
            pil_image: A PIL Image in any mode. Implementations should
                       convert to RGBA/RGB as needed.

        Raises:
            RuntimeError: If copy fails. The UI catches this and displays
                          an error message; it must never propagate to crash the app.
        """
