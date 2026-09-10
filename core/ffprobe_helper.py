"""
StickerFlow — FFprobe Helper
Reads video metadata via FFprobe (preferred) or falls back to
parsing `ffmpeg -i` stderr output.
"""

import json
import logging
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from core.ffmpeg_helper import find_ffmpeg, find_ffprobe

logger = logging.getLogger("stickerflow.ffprobe")


@dataclass
class VideoMetadata:
    """Structured video metadata extracted from FFprobe or ffmpeg -i."""

    duration: float = 0.0          # seconds
    width: int = 0
    height: int = 0
    fps: float = 0.0
    codec: str = ""
    rotation: int = 0              # degrees (0, 90, 180, 270)
    pixel_format: str = ""
    color_space: str = ""
    has_audio: bool = False
    raw: dict = field(default_factory=dict)  # full FFprobe JSON (if available)

    @property
    def display_width(self) -> int:
        """Width after applying rotation."""
        return self.height if self.rotation in (90, 270) else self.width

    @property
    def display_height(self) -> int:
        """Height after applying rotation."""
        return self.width if self.rotation in (90, 270) else self.height


class FFprobeError(Exception):
    """Raised when metadata cannot be read."""


def get_video_metadata(
    file_path: str | Path,
    ffprobe_path: str = "",
    ffmpeg_path: str = "",
) -> VideoMetadata:
    """
    Return VideoMetadata for *file_path*.

    Tries FFprobe first; falls back to `ffmpeg -i` stderr parsing.

    Args:
        file_path:    Path to the video file.
        ffprobe_path: User-specified FFprobe binary path (optional).
        ffmpeg_path:  User-specified FFmpeg binary path (optional, for fallback).

    Returns:
        Populated VideoMetadata instance.

    Raises:
        FFprobeError: If metadata cannot be obtained by either method.
    """
    path = Path(file_path)
    if not path.is_file():
        raise FFprobeError(f"File not found: {path.name}")

    # Try FFprobe first
    ffprobe_bin = find_ffprobe(ffprobe_path)
    if ffprobe_bin:
        try:
            return _read_via_ffprobe(path, ffprobe_bin)
        except Exception as exc:
            logger.warning("FFprobe failed, trying ffmpeg fallback: %s", exc)

    # Fallback: ffmpeg -i stderr parsing
    try:
        ffmpeg_bin = find_ffmpeg(ffmpeg_path)
        return _read_via_ffmpeg_fallback(path, ffmpeg_bin)
    except Exception as exc:
        raise FFprobeError(
            f"Could not read video metadata. Check that FFmpeg is installed. "
            f"Detail: {exc}"
        ) from exc


# ── FFprobe JSON path ─────────────────────────────────────────────────────────

def _read_via_ffprobe(path: Path, ffprobe_bin: str) -> VideoMetadata:
    cmd = [
        ffprobe_bin,
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        "-show_format",
        str(path),
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        timeout=30,
        shell=False,
    )
    if result.returncode != 0:
        raise FFprobeError(
            "FFprobe returned non-zero exit code: "
            + result.stderr.decode("utf-8", errors="replace")[-300:]
        )

    data = json.loads(result.stdout.decode("utf-8", errors="replace"))
    return _parse_ffprobe_json(data)


def _parse_ffprobe_json(data: dict) -> VideoMetadata:
    meta = VideoMetadata(raw=data)
    streams = data.get("streams", [])
    fmt = data.get("format", {})

    # Duration from format (more reliable than stream)
    try:
        meta.duration = float(fmt.get("duration", 0))
    except (ValueError, TypeError):
        pass

    video_stream = next(
        (s for s in streams if s.get("codec_type") == "video"), None
    )
    audio_stream = next(
        (s for s in streams if s.get("codec_type") == "audio"), None
    )
    meta.has_audio = audio_stream is not None

    if video_stream:
        meta.width = int(video_stream.get("width", 0))
        meta.height = int(video_stream.get("height", 0))
        meta.codec = video_stream.get("codec_name", "")
        meta.pixel_format = video_stream.get("pix_fmt", "")
        meta.color_space = video_stream.get("color_space", "")

        # FPS from avg_frame_rate or r_frame_rate
        for key in ("avg_frame_rate", "r_frame_rate"):
            fps_str = video_stream.get(key, "0/1")
            try:
                num, den = fps_str.split("/")
                fps = float(num) / float(den)
                if fps > 0:
                    meta.fps = fps
                    break
            except Exception:
                pass

        # Duration from stream if format didn't have it
        if meta.duration == 0:
            try:
                meta.duration = float(video_stream.get("duration", 0))
            except (ValueError, TypeError):
                pass

        # Rotation from side_data or tags
        rotation = 0
        for side_data in video_stream.get("side_data_list", []):
            if side_data.get("side_data_type") == "Display Matrix":
                try:
                    rotation = abs(int(side_data.get("rotation", 0)))
                except (ValueError, TypeError):
                    pass
        if rotation == 0:
            tags = video_stream.get("tags", {})
            try:
                rotation = abs(int(tags.get("rotate", 0)))
            except (ValueError, TypeError):
                pass
        meta.rotation = rotation

    logger.debug(
        "FFprobe metadata: %dx%d @ %.2ffps, %.2fs, audio=%s",
        meta.width, meta.height, meta.fps, meta.duration, meta.has_audio,
    )
    return meta


# ── ffmpeg -i fallback ────────────────────────────────────────────────────────

_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):([\d.]+)")
_VIDEO_STREAM_RE = re.compile(
    r"Stream.*Video.*?,\s*([\d.]+)\s*(?:fps|tbr|tbn|tbc)"
)
_RESOLUTION_RE = re.compile(r"(\d{2,5})x(\d{2,5})")
_AUDIO_STREAM_RE = re.compile(r"Stream.*Audio")


def _read_via_ffmpeg_fallback(path: Path, ffmpeg_bin: str) -> VideoMetadata:
    """Parse `ffmpeg -i <file>` stderr for basic metadata."""
    cmd = [ffmpeg_bin, "-i", str(path)]
    # ffmpeg -i always "fails" (no output file), so we capture stderr
    result = subprocess.run(
        cmd,
        capture_output=True,
        timeout=30,
        shell=False,
    )
    stderr = result.stderr.decode("utf-8", errors="replace")

    meta = VideoMetadata()

    # Duration
    m = _DURATION_RE.search(stderr)
    if m:
        h, mins, secs = int(m.group(1)), int(m.group(2)), float(m.group(3))
        meta.duration = h * 3600 + mins * 60 + secs

    # Resolution
    m = _RESOLUTION_RE.search(stderr)
    if m:
        meta.width = int(m.group(1))
        meta.height = int(m.group(2))

    # FPS
    m = _VIDEO_STREAM_RE.search(stderr)
    if m:
        try:
            meta.fps = float(m.group(1))
        except ValueError:
            pass

    meta.has_audio = bool(_AUDIO_STREAM_RE.search(stderr))

    if meta.width == 0 or meta.duration == 0:
        raise FFprobeError(
            "Could not parse video metadata from ffmpeg output. "
            "The file may be corrupt or in an unsupported format."
        )

    logger.debug(
        "ffmpeg fallback metadata: %dx%d @ %.2ffps, %.2fs",
        meta.width, meta.height, meta.fps, meta.duration,
    )
    return meta
