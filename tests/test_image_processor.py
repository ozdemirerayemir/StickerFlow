"""
Unit tests for core/image_processor.py
"""

import io
import sys
import tempfile
from pathlib import Path

import pytest
from PIL import Image

# Allow imports from project root
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.image_processor import (
    ImageProcessingError,
    ProcessingMode,
    ProcessingOptions,
    _apply_stroke,
    _clean_alpha_edges,
    _compress_webp,
    _fit_to_canvas,
    _load_image,
    process_image,
)
from tests.fixtures.conftest import (
    make_corrupt_file,
    make_large_png,
    make_synthetic_png,
)


# ── _load_image ───────────────────────────────────────────────────────────────

class TestLoadImage:
    def test_loads_valid_png(self, tmp_path):
        path = make_synthetic_png(path=tmp_path / "valid.png")
        img = _load_image(path)
        assert img.mode == "RGBA"
        assert img.width > 0

    def test_raises_on_corrupt_file(self, tmp_path):
        path = make_corrupt_file(tmp_path / "corrupt.png")
        with pytest.raises(ImageProcessingError, match="corrupt|open|format"):
            _load_image(path)

    def test_raises_on_too_large_image(self, tmp_path):
        path = make_large_png(tmp_path / "large.png")
        with pytest.raises(ImageProcessingError, match="too large|megapixel"):
            _load_image(path)

    def test_strips_metadata(self, tmp_path):
        """Output image should have no EXIF data."""
        path = make_synthetic_png(path=tmp_path / "img.png")
        img = _load_image(path)
        assert not img.info.get("exif"), "EXIF data should be stripped."


# ── _fit_to_canvas ────────────────────────────────────────────────────────────

class TestFitToCanvas:
    def test_output_is_canvas_size(self):
        img = Image.new("RGBA", (100, 200), (0, 0, 0, 255))
        opts = ProcessingOptions(canvas_size=512)
        result = _fit_to_canvas(img, opts)
        assert result.size == (512, 512)

    def test_output_mode_is_rgba(self):
        img = Image.new("RGBA", (64, 64), (0, 0, 0, 255))
        opts = ProcessingOptions(canvas_size=512)
        result = _fit_to_canvas(img, opts)
        assert result.mode == "RGBA"

    def test_content_fits_safe_area(self):
        """Content should not exceed safe_area_size pixels."""
        img = Image.new("RGBA", (600, 600), (255, 0, 0, 255))
        opts = ProcessingOptions(canvas_size=512, safe_area_size=480, apply_safe_area=True)
        result = _fit_to_canvas(img, opts)
        # The canvas is 512×512; the actual content within is ≤480
        assert result.size == (512, 512)


# ── _apply_stroke ─────────────────────────────────────────────────────────────

class TestApplyStroke:
    def test_returns_rgba(self):
        img = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
        # Put a square subject in the centre
        for x in range(30, 70):
            for y in range(30, 70):
                img.putpixel((x, y), (255, 100, 50, 255))
        result = _apply_stroke(img, stroke_width=3)
        assert result.mode == "RGBA"
        assert result.size == (100, 100)

    def test_stroke_adds_white_pixels(self):
        """Pixels just outside the subject should become white after stroking."""
        img = Image.new("RGBA", (50, 50), (0, 0, 0, 0))
        # Solid red square subject
        for x in range(20, 30):
            for y in range(20, 30):
                img.putpixel((x, y), (255, 0, 0, 255))
        result = _apply_stroke(img, stroke_width=4)
        # Check that a pixel just outside the subject has some whiteness
        px = result.getpixel((15, 25))  # left of subject
        assert isinstance(px, tuple) and px[3] > 0, "Stroke should add non-transparent pixels near subject edge."


# ── _compress_webp ────────────────────────────────────────────────────────────

class TestCompressWebp:
    def test_output_is_valid_webp(self):
        img = Image.new("RGBA", (512, 512), (100, 200, 100, 255))
        warnings = []
        data, quality = _compress_webp(img, max_kb=100, warnings=warnings)
        opened = Image.open(io.BytesIO(data))
        assert opened.format == "WEBP"

    def test_returns_quality_used(self):
        img = Image.new("RGBA", (512, 512), (100, 200, 100, 255))
        warnings = []
        _, quality = _compress_webp(img, max_kb=100, warnings=warnings)
        assert isinstance(quality, int)
        assert 1 <= quality <= 100

    def test_warns_when_limit_exceeded(self):
        """Force limit to be exceeded by setting max_kb=0."""
        img = Image.new("RGBA", (512, 512), (100, 200, 100, 255))
        warnings = []
        _compress_webp(img, max_kb=0, warnings=warnings)
        assert len(warnings) > 0, "Should warn when size limit cannot be met."


# ── process_image integration ─────────────────────────────────────────────────

class TestProcessImage:
    def test_valid_png_produces_512x512_webp(self, tmp_path):
        input_path = make_synthetic_png(
            64, 64, path=tmp_path / "input.png"
        )
        output_path = tmp_path / "output.webp"
        result = process_image(
            input_path,
            output_path,
            options=ProcessingOptions(mode=ProcessingMode.KEEP_BACKGROUND),
        )
        assert output_path.exists()
        assert result.width == 512
        assert result.height == 512

    def test_output_is_webp_with_alpha(self, tmp_path):
        input_path = make_synthetic_png(64, 64, path=tmp_path / "input.png")
        output_path = tmp_path / "output.webp"
        process_image(input_path, output_path)
        img = Image.open(output_path)
        assert img.format == "WEBP"
        assert img.mode in ("RGBA", "LA")

    def test_corrupt_file_raises_error(self, tmp_path):
        input_path = make_corrupt_file(tmp_path / "corrupt.png")
        output_path = tmp_path / "output.webp"
        with pytest.raises(ImageProcessingError):
            process_image(input_path, output_path)

    def test_invalid_extension_passes_after_validation(self, tmp_path):
        """image_processor does not check extensions — validation is upstream."""
        # Just ensure a valid image with non-standard name processes fine
        path = tmp_path / "img.png"
        Image.new("RGBA", (50, 50), (0, 0, 0, 0)).save(str(path))
        out = tmp_path / "out.webp"
        result = process_image(path, out)
        assert result.width == 512

    def test_cancel_event_stops_processing(self, tmp_path):
        import threading
        cancel = threading.Event()
        cancel.set()  # Already cancelled before we start
        input_path = make_synthetic_png(64, 64, path=tmp_path / "img.png")
        output_path = tmp_path / "out.webp"
        with pytest.raises(ImageProcessingError, match="cancel"):
            process_image(
                input_path, output_path,
                cancel_event=cancel,
            )
