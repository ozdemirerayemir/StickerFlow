"""
StickerFlow — Clipboard Package
Provides get_clipboard_backend() factory for platform-specific image clipboard.
"""

import sys
from clipboard.base import ClipboardBackend


def get_clipboard_backend() -> ClipboardBackend:
    """
    Return the appropriate clipboard backend for the current platform.
    Always returns a ClipboardBackend instance — even if clipboard
    is not supported, so callers can check is_supported() safely.
    """
    if sys.platform == "win32":
        from clipboard.windows_clipboard import WindowsClipboardBackend
        return WindowsClipboardBackend()
    elif sys.platform == "darwin":
        from clipboard.macos_clipboard import MacOSClipboardBackend
        return MacOSClipboardBackend()
    else:
        from clipboard.linux_clipboard import LinuxClipboardBackend
        return LinuxClipboardBackend()
