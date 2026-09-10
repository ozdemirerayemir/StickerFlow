"""
StickerFlow — macOS Clipboard Backend
Copies a PIL Image to the clipboard using AppleScript / osascript.
Falls back to pbcopy if osascript is unavailable.
"""

import logging
import subprocess
import tempfile
from pathlib import Path

from clipboard.base import ClipboardBackend

logger = logging.getLogger("stickerflow.clipboard.macos")


class MacOSClipboardBackend(ClipboardBackend):

    def __init__(self) -> None:
        self._supported: bool | None = None
        self._reason: str = ""
        self._detect()

    def _detect(self) -> None:
        try:
            result = subprocess.run(
                ["osascript", "-e", "return 1"],
                capture_output=True, timeout=5, shell=False,
            )
            self._supported = result.returncode == 0
        except Exception:
            self._supported = False

        if not self._supported:
            self._reason = (
                "Image clipboard on macOS requires osascript. "
                "It was not found on this system."
            )
        logger.debug("macOS clipboard supported: %s", self._supported)

    @property
    def unavailable_reason(self) -> str:
        return self._reason

    def is_supported(self) -> bool:
        return bool(self._supported)

    def copy_image_png(self, pil_image) -> None:
        if not self.is_supported():
            raise RuntimeError(self._reason)

        img = pil_image.convert("RGBA")

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            img.save(str(tmp_path), format="PNG")
            script = (
                f'set theFile to POSIX file "{tmp_path}"\n'
                f'set theImage to read theFile as JPEG picture\n'
                f'set the clipboard to (read theFile as JPEG picture)'
            )
            # Simpler approach: use set the clipboard to
            script = (
                f'tell application "Finder"\n'
                f'  set theFile to POSIX file "{tmp_path}" as alias\n'
                f'end tell\n'
                f'set the clipboard to (read POSIX file "{tmp_path}" as «class PNGf»)'
            )
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True, timeout=15, shell=False,
            )
            if result.returncode != 0:
                err = result.stderr.decode("utf-8", errors="replace")
                raise RuntimeError(f"osascript clipboard copy failed: {err}")
            logger.debug("Image copied to clipboard via osascript.")
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"macOS clipboard copy failed: {exc}") from exc
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
