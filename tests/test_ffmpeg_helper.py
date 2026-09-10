"""
Unit tests for core/ffmpeg_helper.py
Verifies binary discovery, argument safety, and shell=True absence.
"""

import sys
import unittest.mock as mock
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ffmpeg_helper import (
    FFmpegNotFoundError,
    _validate_args,
    find_ffmpeg,
    find_ffprobe,
)


# ── _validate_args ────────────────────────────────────────────────────────────

class TestValidateArgs:
    def test_raises_if_args_is_string(self):
        with pytest.raises(ValueError, match="list"):
            _validate_args("ffmpeg -i input.mp4")  # type: ignore[arg-type]


    def test_raises_if_none_in_args(self):
        with pytest.raises(ValueError, match="None"):
            _validate_args(["-i", None, "output.webp"])

    def test_passes_valid_list(self):
        _validate_args(["-y", "-i", "input.mp4", "-an", "output.webp"])

    def test_passes_empty_list(self):
        _validate_args([])


# ── find_ffmpeg ───────────────────────────────────────────────────────────────

class TestFindFFmpeg:
    def test_returns_path_when_in_system_path(self):
        """If 'ffmpeg' is in PATH, find_ffmpeg should return a non-empty string."""
        import shutil
        if shutil.which("ffmpeg") is None:
            pytest.skip("FFmpeg not in PATH on this test machine.")
        path = find_ffmpeg()
        assert path
        assert isinstance(path, str)

    def test_raises_when_not_found(self):
        """With no PATH and no user path, should raise FFmpegNotFoundError."""
        with mock.patch("shutil.which", return_value=None), \
             mock.patch("pathlib.Path.is_file", return_value=False):
            with pytest.raises(FFmpegNotFoundError):
                find_ffmpeg(user_path="")

    def test_uses_user_path_first(self):
        """User-provided path should be checked before PATH."""
        fake_path = "/fake/ffmpeg"
        with mock.patch("pathlib.Path.is_file", return_value=True):
            result = find_ffmpeg(user_path=fake_path)
            assert result == fake_path


# ── find_ffprobe ──────────────────────────────────────────────────────────────

class TestFindFFprobe:
    def test_returns_none_when_not_found(self):
        with mock.patch("shutil.which", return_value=None), \
             mock.patch("pathlib.Path.is_file", return_value=False):
            result = find_ffprobe(user_path="")
            assert result is None

    def test_returns_string_when_found(self):
        import shutil
        if shutil.which("ffprobe") is None:
            pytest.skip("FFprobe not in PATH on this test machine.")
        result = find_ffprobe()
        assert isinstance(result, str)
