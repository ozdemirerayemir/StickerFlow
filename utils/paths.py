"""
StickerFlow — Platform-Aware Path Utilities
Provides consistent directories for logs, user data, and default output.
"""

import sys
from pathlib import Path


def get_app_data_dir() -> Path:
    """
    Return the platform-appropriate application data directory.

    - Windows: %APPDATA%/StickerFlow
    - macOS:   ~/Library/Application Support/StickerFlow
    - Linux:   ~/.local/share/StickerFlow
    """
    if sys.platform == "win32":
        import os
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(
            __import__("os").environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")
        )
    app_dir = base / "StickerFlow"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_log_dir() -> Path:
    """Return the directory where log files are stored."""
    log_dir = get_app_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_default_output_dir() -> Path:
    """Return the default sticker output directory (~/StickerFlow Output)."""
    output_dir = Path.home() / "StickerFlow Output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_settings_path() -> Path:
    """Return the path to the user settings JSON file."""
    return get_app_data_dir() / "settings.json"


def sanitize_path(path: str | Path) -> Path:
    """
    Resolve a path and guard against path-traversal attacks.

    Raises ValueError if the resolved path is not absolute (safety check).
    """
    resolved = Path(path).resolve()
    if not resolved.is_absolute():
        raise ValueError(f"Path resolved to a non-absolute location: {resolved}")
    return resolved
