"""
StickerFlow — Configuration & WhatsApp Target Constants
These values represent best-effort WhatsApp sticker asset targets.
They are NOT official WhatsApp specifications and must be manually verified.
All values are configurable via UserSettings (core/settings.py).
"""

from typing import Final

APP_NAME: Final[str] = "StickerFlow"
APP_VERSION: Final[str] = "0.1.0"

# ─── WhatsApp sticker asset targets (community-observed, unverified) ──────────
WHATSAPP_TARGETS: Final[dict] = {
    "canvas_size": 512,           # px — output canvas width and height
    "safe_area_size": 480,        # px — recommended content area (leaves padding)
    "padding_px": 16,             # px — padding around content within canvas
    "static_max_kb": 100,         # KB — max file size for static WebP
    "animated_max_kb": 500,       # KB — max file size for animated WebP
    "animated_max_duration_sec": 3.0,   # seconds
    "animated_default_fps": 16,
    "animated_fallback_fps": 12,
    "loop": 0,                    # 0 = infinite loop
}

# ─── Static image compression quality steps ───────────────────────────────────
STATIC_QUALITY_STEPS: Final[list] = [90, 85, 80, 75, 70, 65, 60]

# ─── Animated WebP compression quality steps ──────────────────────────────────
ANIMATED_QUALITY_STEPS: Final[list] = [65, 55, 45, 35]

# ─── Memory guard — reject images larger than this pixel count ────────────────
MAX_INPUT_PIXELS: Final[int] = 25_000_000  # ~25 megapixels

# ─── Supported input formats ──────────────────────────────────────────────────
SUPPORTED_IMAGE_EXTENSIONS: Final[frozenset] = frozenset(
    {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
)
SUPPORTED_VIDEO_EXTENSIONS: Final[frozenset] = frozenset(
    {".mp4", ".mov", ".webm", ".gif"}
)

# ─── Stroke options ───────────────────────────────────────────────────────────
STROKE_WIDTH_OPTIONS: Final[list] = [2, 3, 4]  # pixels
DEFAULT_STROKE_WIDTH: Final[int] = 3

# ─── Temp directory name (inside system temp) ─────────────────────────────────
TEMP_DIR_NAME: Final[str] = "stickerflow_tmp"

# ─── Settings file name (stored in user data dir) ─────────────────────────────
SETTINGS_FILE_NAME: Final[str] = "settings.json"

# ─── Legal disclaimer (shown in UI footer) ────────────────────────────────────
LEGAL_DISCLAIMER: Final[str] = (
    "This application is not officially affiliated with WhatsApp. "
    "It only produces sticker-compatible media assets."
)

# ─── Copyright notice ─────────────────────────────────────────────────────────
RIGHTS_NOTICE: Final[str] = (
    "Only use content you have the right to use. "
    "This application is not officially affiliated with WhatsApp."
)
