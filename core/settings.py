"""
StickerFlow — User Settings
Persists user preferences as a JSON file in the app data directory.
All WhatsApp target values can be overridden by the user here.
"""

import json
import logging
from pathlib import Path
from typing import Any

from config import WHATSAPP_TARGETS
from utils.paths import get_settings_path, get_default_output_dir

logger = logging.getLogger("stickerflow.settings")

# Default settings structure
_DEFAULTS: dict[str, Any] = {
    "ffmpeg_path": "",           # empty string = search PATH
    "ffprobe_path": "",          # empty string = search PATH
    "output_dir": "",            # empty string = default output dir
    "whatsapp_targets": dict(WHATSAPP_TARGETS),
    "default_stroke_width": 3,
    "safe_area_enabled": True,
    "theme": "dark",
    "last_open_dir": "",
}


class UserSettings:
    """
    Load, access, and save user preferences.

    Settings are persisted as a JSON file. Missing keys fall back to
    _DEFAULTS, so old settings files remain compatible with new defaults.
    """

    def __init__(self, settings_path: Path | None = None) -> None:
        self._path = settings_path or get_settings_path()
        self._data: dict[str, Any] = dict(_DEFAULTS)
        self._load()

    # ── Public accessors ───────────────────────────────────────────────────

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
        self.save()

    def get_ffmpeg_path(self) -> str:
        return self._data.get("ffmpeg_path", "")

    def get_ffprobe_path(self) -> str:
        return self._data.get("ffprobe_path", "")

    def get_output_dir(self) -> Path:
        path_str = self._data.get("output_dir", "")
        if path_str:
            p = Path(path_str)
            if p.is_dir():
                return p
        return get_default_output_dir()

    def get_whatsapp_targets(self) -> dict:
        return dict(self._data.get("whatsapp_targets", WHATSAPP_TARGETS))

    def set_ffmpeg_path(self, path: str) -> None:
        self.set("ffmpeg_path", path)

    def set_ffprobe_path(self, path: str) -> None:
        self.set("ffprobe_path", path)

    def set_output_dir(self, path: str | Path) -> None:
        self.set("output_dir", str(path))

    def set_whatsapp_target(self, key: str, value: Any) -> None:
        targets = self.get_whatsapp_targets()
        targets[key] = value
        self.set("whatsapp_targets", targets)

    # ── Persistence ─────────────────────────────────────────────────────────

    def save(self) -> None:
        """Write current settings to disk."""
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("w", encoding="utf-8") as fh:
                json.dump(self._data, fh, indent=2, ensure_ascii=False)
            logger.debug("Settings saved.")
        except Exception as exc:
            logger.error("Failed to save settings: %s", exc)

    def _load(self) -> None:
        """Load settings from disk, filling missing keys with defaults."""
        if not self._path.exists():
            logger.debug("No settings file found; using defaults.")
            return
        try:
            with self._path.open("r", encoding="utf-8") as fh:
                loaded: dict = json.load(fh)
            # Merge: loaded values override defaults; missing keys use defaults
            for key, default_val in _DEFAULTS.items():
                if key in loaded:
                    if isinstance(default_val, dict) and isinstance(loaded[key], dict):
                        merged = dict(default_val)
                        merged.update(loaded[key])
                        self._data[key] = merged
                    else:
                        self._data[key] = loaded[key]
            logger.debug("Settings loaded from %s.", self._path.name)
        except json.JSONDecodeError as exc:
            logger.warning("Settings file is corrupted; using defaults. Error: %s", exc)
        except Exception as exc:
            logger.error("Failed to load settings: %s", exc)
