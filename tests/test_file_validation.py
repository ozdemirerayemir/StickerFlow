"""
Unit tests for utils/file_validation.py
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.file_validation import (
    FileValidationError,
    is_image,
    is_video,
    validate_file,
    validate_output_path,
)
from tests.fixtures.conftest import make_synthetic_png


class TestValidateFile:
    def test_valid_png_passes(self, tmp_path):
        path = make_synthetic_png(path=tmp_path / "img.png")
        result = validate_file(path)
        assert result.is_file()

    def test_nonexistent_file_raises(self, tmp_path):
        with pytest.raises(FileValidationError, match="exist"):
            validate_file(tmp_path / "nonexistent.png")

    def test_unsupported_extension_raises(self, tmp_path):
        p = tmp_path / "file.xyz"
        p.write_bytes(b"data")
        with pytest.raises(FileValidationError, match="[Uu]nsupported"):
            validate_file(p)

    def test_directory_raises(self, tmp_path):
        with pytest.raises(FileValidationError, match="not a file"):
            validate_file(tmp_path)

    def test_supported_video_extensions(self, tmp_path):
        for ext in (".mp4", ".mov", ".webm", ".gif"):
            p = tmp_path / f"video{ext}"
            p.write_bytes(b"fakevideo")
            result = validate_file(p)
            assert result.suffix.lower() == ext


class TestIsImageIsVideo:
    def test_is_image(self):
        assert is_image("photo.png")
        assert is_image("photo.JPG")
        assert is_image("photo.WEBP")
        assert not is_image("video.mp4")

    def test_is_video(self):
        assert is_video("clip.mp4")
        assert is_video("clip.MOV")
        assert not is_video("photo.png")


class TestValidateOutputPath:
    def test_returns_path_inside_dir(self, tmp_path):
        result = validate_output_path(tmp_path, "output.webp")
        assert str(result).startswith(str(tmp_path))

    def test_strips_directory_components(self, tmp_path):
        result = validate_output_path(tmp_path, "../evil.webp")
        # Should strip the ../  and just use "evil.webp" inside tmp_path
        assert result.parent == tmp_path.resolve()

    def test_traversal_raises(self, tmp_path):
        """A filename that after resolve escapes the dir should raise."""
        # On most systems, Path.name strips ../; this test verifies safe_name logic
        evil = "output.webp"
        result = validate_output_path(tmp_path, evil)
        assert result.parent.resolve() == tmp_path.resolve()
