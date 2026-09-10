"""
StickerFlow — Windows Clipboard Backend
Copies a PIL Image to the clipboard as PNG.
Primary:  pywin32 (win32clipboard)
Fallback: PowerShell + .NET System.Windows.Forms
"""

import io
import logging
import subprocess
import tempfile
from pathlib import Path

from clipboard.base import ClipboardBackend

logger = logging.getLogger("stickerflow.clipboard.windows")


class WindowsClipboardBackend(ClipboardBackend):

    def __init__(self) -> None:
        self._pywin32_available: bool | None = None
        self._powershell_available: bool | None = None
        self._reason: str = ""
        self._detect()

    def _detect(self) -> None:
        try:
            import win32clipboard  # noqa: F401
            self._pywin32_available = True
            logger.debug("Clipboard: pywin32 available.")
            return
        except ImportError:
            self._pywin32_available = False

        # Check PowerShell fallback
        try:
            result = subprocess.run(
                ["powershell", "-Command", "echo ok"],
                capture_output=True, timeout=5, shell=False,
            )
            self._powershell_available = result.returncode == 0
        except Exception:
            self._powershell_available = False

        if not self._powershell_available:
            self._reason = (
                "Image clipboard requires pywin32 (pip install pywin32) "
                "or PowerShell. Neither is available."
            )

    @property
    def unavailable_reason(self) -> str:
        return self._reason

    def is_supported(self) -> bool:
        return bool(self._pywin32_available or self._powershell_available)

    def copy_image_png(self, pil_image) -> None:
        if not self.is_supported():
            raise RuntimeError(self._reason or "Clipboard not supported on this system.")

        img = pil_image.convert("RGBA")

        if self._pywin32_available:
            self._copy_via_pywin32(img)
        else:
            self._copy_via_powershell(img)

    # ── pywin32 path ──────────────────────────────────────────────────────────

    def _copy_via_pywin32(self, img) -> None:
        try:
            import win32clipboard
            from PIL import Image

            # Convert to BMP for CF_DIB (most compatible with Windows clipboard)
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="BMP")
            bmp_data = buf.getvalue()

            # Strip the 14-byte BMP file header; clipboard expects DIB
            dib_data = bmp_data[14:]

            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, dib_data)
            finally:
                win32clipboard.CloseClipboard()
            logger.debug("Image copied to clipboard via pywin32.")
        except Exception as exc:
            logger.error("pywin32 clipboard copy failed: %s", exc)
            raise RuntimeError(f"Clipboard copy failed: {exc}") from exc

    # ── PowerShell fallback ───────────────────────────────────────────────────

    def _copy_via_powershell(self, img) -> None:
        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp_path = Path(tmp.name)
            img.save(str(tmp_path), format="PNG")


            ps_script = (
                "Add-Type -AssemblyName System.Windows.Forms; "
                f"[System.Windows.Forms.Clipboard]::SetImage("
                f"[System.Drawing.Image]::FromFile('{tmp_path}'));"
            )
            result = subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True, timeout=15, shell=False,
            )
            if result.returncode != 0:
                err = result.stderr.decode("utf-8", errors="replace")
                raise RuntimeError(f"PowerShell clipboard failed: {err}")
            logger.debug("Image copied to clipboard via PowerShell.")
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Clipboard copy failed: {exc}") from exc
        finally:
            try:
                if tmp_path is not None:
                    tmp_path.unlink(missing_ok=True)
            except Exception:
                pass

