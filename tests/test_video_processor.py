"""
Unit tests for core/video_processor.py
Tests focus on command construction and trim logic — no real video files required.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.video_processor import (
    CropMode,
    VideoProcessingError,
    VideoProcessingOptions,
    _build_vf,
    _resolve_trim,
    build_ffmpeg_command,
)
from core.ffprobe_helper import VideoMetadata


# ── _resolve_trim ─────────────────────────────────────────────────────────────

class TestResolveTrim:
    def _meta(self, duration: float = 10.0) -> VideoMetadata:
        m = VideoMetadata()
        m.duration = duration
        return m

    def _opts(self, start=0.0, end=None, max_dur=3.0):
        return VideoProcessingOptions(start_sec=start, end_sec=end, max_duration_sec=max_dur)

    def test_default_end_clamps_to_max_duration(self):
        meta = self._meta(10.0)
        opts = self._opts(start=0.0, end=None, max_dur=3.0)
        start, end = _resolve_trim(meta, opts, [])
        assert end - start <= 3.0

    def test_selection_exceeds_max_gets_clamped(self):
        meta = self._meta(10.0)
        opts = self._opts(start=0.0, end=8.0, max_dur=3.0)
        warnings = []
        start, end = _resolve_trim(meta, opts, warnings)
        assert end - start <= 3.0
        assert len(warnings) > 0

    def test_start_greater_than_end_raises(self):
        meta = self._meta(10.0)
        opts = self._opts(start=5.0, end=2.0, max_dur=3.0)
        with pytest.raises(VideoProcessingError, match="[Ss]tart"):
            _resolve_trim(meta, opts, [])

    def test_video_shorter_than_max_uses_full_duration(self):
        meta = self._meta(1.5)
        opts = self._opts(start=0.0, end=None, max_dur=3.0)
        start, end = _resolve_trim(meta, opts, [])
        assert abs((end - start) - 1.5) < 0.01

    def test_negative_start_clamped_to_zero(self):
        meta = self._meta(5.0)
        opts = self._opts(start=-1.0, end=2.0, max_dur=3.0)
        start, end = _resolve_trim(meta, opts, [])
        assert start >= 0.0


# ── _build_vf ─────────────────────────────────────────────────────────────────

class TestBuildVf:
    def test_cover_crop_contains_crop_and_scale(self):
        vf = _build_vf(512, 16, CropMode.COVER_CROP, True)
        assert "crop" in vf
        assert "scale=512:512" in vf
        assert "fps=16" in vf

    def test_fit_pad_contains_pad(self):
        vf = _build_vf(512, 16, CropMode.FIT_PAD, True)
        assert "pad" in vf
        assert "fps=16" in vf

    def test_fit_pad_falls_back_to_cover_when_alpha_unsupported(self):
        vf = _build_vf(512, 16, CropMode.FIT_PAD, alpha_supported=False)
        # Should use cover crop logic
        assert "crop" in vf
        assert "scale=512:512" in vf

    def test_no_shell_injection_in_vf(self):
        """Filter string must not contain shell metacharacters."""
        vf = _build_vf(512, 16, CropMode.COVER_CROP, True)
        dangerous = [";", "&&", "||", "`", "$"]
        for char in dangerous:
            assert char not in vf, f"Potentially dangerous char '{char}' in filter string."


# ── build_ffmpeg_command ──────────────────────────────────────────────────────

class TestBuildFFmpegCommand:
    def _base_cmd(self, **kwargs) -> list:
        input_path: Path = kwargs.get("input_path", Path("/tmp/input.mp4"))  # type: ignore[assignment]
        output_path: Path = kwargs.get("output_path", Path("/tmp/output.webp"))  # type: ignore[assignment]
        start_sec: float = kwargs.get("start_sec", 0.0)  # type: ignore[assignment]
        duration_sec: float = kwargs.get("duration_sec", 3.0)  # type: ignore[assignment]
        fps: int = kwargs.get("fps", 16)  # type: ignore[assignment]
        quality: int = kwargs.get("quality", 65)  # type: ignore[assignment]
        canvas: int = kwargs.get("canvas", 512)  # type: ignore[assignment]
        crop_mode: CropMode = kwargs.get("crop_mode", CropMode.COVER_CROP)  # type: ignore[assignment]
        loop: int = kwargs.get("loop", 0)  # type: ignore[assignment]
        alpha_supported: bool = kwargs.get("alpha_supported", True)  # type: ignore[assignment]
        ffmpeg_bin: str = kwargs.get("ffmpeg_bin", "ffmpeg")  # type: ignore[assignment]
        return build_ffmpeg_command(
            input_path=input_path,
            output_path=output_path,
            start_sec=start_sec,
            duration_sec=duration_sec,
            fps=fps,
            quality=quality,
            canvas=canvas,
            crop_mode=crop_mode,
            loop=loop,
            alpha_supported=alpha_supported,
            ffmpeg_bin=ffmpeg_bin,
        )


    def test_returns_list(self):
        cmd = self._base_cmd()
        assert isinstance(cmd, list)

    def test_starts_with_ffmpeg(self):
        cmd = self._base_cmd(ffmpeg_bin="ffmpeg")
        assert cmd[0] == "ffmpeg"

    def test_no_shell_true(self):
        """shell=True must NEVER appear in the command — we just verify the list is safe."""
        cmd = self._base_cmd()
        # shell=True is a Popen argument, not in cmd; but verify no string form
        assert "shell=True" not in " ".join(str(a) for a in cmd)

    def test_contains_an_flag(self):
        cmd = self._base_cmd()
        assert "-an" in cmd

    def test_contains_no_audio(self):
        cmd = self._base_cmd()
        joined = " ".join(str(a) for a in cmd)
        assert "-an" in joined

    def test_loop_is_zero(self):
        cmd = self._base_cmd(loop=0)
        loop_idx = cmd.index("-loop")
        assert cmd[loop_idx + 1] == "0"

    def test_contains_libwebp_codec(self):
        cmd = self._base_cmd()
        assert "libwebp" in cmd

    def test_contains_quality(self):
        cmd = self._base_cmd(quality=45)
        q_idx = cmd.index("-q:v")
        assert cmd[q_idx + 1] == "45"

    def test_no_none_in_args(self):
        cmd = self._base_cmd()
        for arg in cmd:
            assert arg is not None, "None found in FFmpeg command arguments."
