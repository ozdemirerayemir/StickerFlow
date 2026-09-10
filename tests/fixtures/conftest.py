"""
StickerFlow — Test Fixtures
Generates small synthetic images and other test data at test time.
No large real media files required.
"""

import io
from pathlib import Path

from PIL import Image


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def make_synthetic_png(
    width: int = 64,
    height: int = 64,
    mode: str = "RGBA",
    color: tuple = (100, 150, 200, 255),
    path: Path | None = None,
) -> Path:
    """
    Create a small synthetic PNG image.

    Args:
        width, height: Image dimensions.
        mode:          Pillow mode (RGBA, RGB, L, …).
        color:         Fill colour matching the mode.
        path:          Save path. Defaults to fixtures/synthetic_<w>x<h>.png.

    Returns:
        Path to the created PNG file.
    """
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    if path is None:
        path = FIXTURE_DIR / f"synthetic_{width}x{height}.png"
    img = Image.new(mode, (width, height), color)
    img.save(str(path))
    return path


def make_corrupt_file(path: Path | None = None) -> Path:
    """Create a file with garbage bytes that cannot be opened as an image."""
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    if path is None:
        path = FIXTURE_DIR / "corrupt.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 10)  # valid header, corrupt body
    return path


def make_large_png(path: Path | None = None) -> Path:
    """Create a PNG that exceeds the memory guard threshold."""
    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)
    if path is None:
        path = FIXTURE_DIR / "large.png"
    img = Image.new("RGB", (5001, 5001), (255, 0, 0))
    img.save(str(path))
    return path
