"""
StickerFlow — Linux Clipboard Backend
Tries wl-copy (Wayland), xclip (X11), then xsel (X11 fallback).
"""

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path

from clipboard.base import ClipboardBackend

logger = logging.getLogger("stickerflow.clipboard.linux")

_TOOLS = [
    # (tool_name, check_cmd, copy_cmd_fn)
    # copy_cmd_fn receives the PNG temp file path
    ("wl-copy",  "wl-copy",  lambda p: ["wl-copy", "--type", "image/png"]),
    ("xclip",    "xclip",    lambda p: ["xclip", "-selection", "clipboard", "-t", "image/png", "-i"]),
    ("xsel",     "xsel",     lambda p: ["xsel", "--clipboard", "--input"]),
]


class LinuxClipboardBackend(ClipboardBackend):

    def __init__(self) -> None:
        self._tool: str | None = None
        self._cmd_fn = None
        self._reason: str = ""
        self._detect()

    def _detect(self) -> None:
        for name, check, cmd_fn in _TOOLS:
            if shutil.which(check):
                self._tool = name
                self._cmd_fn = cmd_fn
                logger.debug("Linux clipboard: using %s.", name)
                return
        self._reason = (
            "Image clipboard on Linux requires wl-copy (Wayland) or "
            "xclip / xsel (X11). None were found on this system. "
            "Install one with your package manager, e.g.:\n"
            "  sudo apt install wl-clipboard  # Wayland\n"
            "  sudo apt install xclip          # X11"
        )
        logger.debug("Linux clipboard: no supported tool found.")

    @property
    def unavailable_reason(self) -> str:
        return self._reason

    def is_supported(self) -> bool:
        return self._tool is not None

    def copy_image_png(self, pil_image) -> None:
        if not self.is_supported():
            raise RuntimeError(self._reason)

        img = pil_image.convert("RGBA")

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            img.save(str(tmp_path), format="PNG")
            assert self._cmd_fn is not None, "cmd_fn is None but is_supported() returned True"
            cmd = self._cmd_fn(tmp_path)


            with open(tmp_path, "rb") as png_data:
                result = subprocess.run(
                    cmd,
                    stdin=png_data,
                    capture_output=True,
                    timeout=10,
                    shell=False,
                )
            if result.returncode != 0:
                err = result.stderr.decode("utf-8", errors="replace")
                raise RuntimeError(
                    f"{self._tool} clipboard copy failed (exit {result.returncode}): {err}"
                )
            logger.debug("Image copied to clipboard via %s.", self._tool)
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Linux clipboard copy failed: {exc}") from exc
        finally:
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
