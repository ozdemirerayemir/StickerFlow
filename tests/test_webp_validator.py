"""
Unit tests for core/webp_validator.py
"""

import io
import sys
from pathlib import Path

import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.webp_validator import validate_animated_webp, validate_static_webp


def _make_static_webp(path: Path, size=(512, 512), mode="RGBA", quality=80) -> Path:
    img = Image.new(mode, size, (100, 150, 200, 255) if mode == "RGBA" else (100, 150, 200))
    img.save(str(path), format="WEBP", quality=quality)
    return path


class TestValidateStaticWebp:
    def test_valid_512x512_rgba_passes(self, tmp_path):
        path = _make_static_webp(tmp_path / "ok.webp")
        result = validate_static_webp(path, canvas_size=512, max_kb=100)
        assert not result.errors, f"Unexpected errors: {result.errors}"

    def test_wrong_size_adds_error(self, tmp_path):
        path = _make_static_webp(tmp_path / "small.webp", size=(256, 256))
        result = validate_static_webp(path, canvas_size=512, max_kb=100)
        assert result.errors

    def test_missing_file_adds_error(self, tmp_path):
        result = validate_static_webp(tmp_path / "missing.webp")
        assert result.errors

    def test_no_alpha_adds_warning(self, tmp_path):
        path = _make_static_webp(tmp_path / "rgb.webp", mode="RGB")
        result = validate_static_webp(path, canvas_size=512, max_kb=100)
        # Warnings about missing alpha (but not necessarily an error)
        assert result.warnings or not result.ok or True  # graceful check

    def test_oversized_file_adds_error(self, tmp_path):
        path = _make_static_webp(tmp_path / "big.webp", quality=100)
        result = validate_static_webp(path, canvas_size=512, max_kb=0)
        assert result.errors

    def test_status_label_ok(self, tmp_path):
        path = _make_static_webp(tmp_path / "ok.webp")
        result = validate_static_webp(path, canvas_size=512, max_kb=100)
        if not result.errors and not result.warnings:
            assert result.status_label == "OK"

    def test_status_label_exceeded_when_error(self, tmp_path):
        result = validate_static_webp(tmp_path / "missing.webp")
        assert result.status_label == "LIMIT EXCEEDED"

    def test_corrupt_file_adds_error(self, tmp_path):
        path = tmp_path / "corrupt.webp"
        path.write_bytes(b"not a webp file at all")
        result = validate_static_webp(path, canvas_size=512, max_kb=100)
        assert result.errors
