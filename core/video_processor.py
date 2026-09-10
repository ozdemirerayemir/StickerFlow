"""
StickerFlow — Video Processor
Converts short video clips into 512×512 animated WebP sticker assets.

Processing pipeline:
  1. Read metadata (FFprobe or ffmpeg -i fallback)
  2. Validate and enforce 3-second trim
  3. Run FFmpeg: trim → crop/pad → FPS → audio strip → animated WebP
  4. Iterative compression (quality steps, then FPS fallback)
  5. Validate output
"""

import logging
import re
import subprocess
import sys
import threading
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Optional

_NO_WINDOW_FLAG = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

from config import (
    ANIMATED_QUALITY_STEPS,
    WHATSAPP_TARGETS,
)
from core.ffmpeg_helper import (
    FFmpegError,
    FFmpegNotFoundError,
    find_ffmpeg,
    _terminate_process,
    _validate_args,
)
from core.ffprobe_helper import VideoMetadata, get_video_metadata
from utils.temp_manager import temp_workspace
from utils.threading_worker import post_progress, post_status

logger = logging.getLogger("stickerflow.video")


class CropMode(Enum):
    COVER_CROP = auto()   # Mode A: crop + scale — fills 512×512
    FIT_PAD = auto()      # Mode B: scale + transparent pad


@dataclass
class VideoProcessingOptions:
    start_sec: float = 0.0
    end_sec: Optional[float] = None         # None = auto-detect from metadata
    crop_mode: CropMode = CropMode.COVER_CROP
    canvas_size: int = 512
    fps: int = 16                           # will fallback to 12 if too large
    loop: int = 0                           # 0 = infinite
    max_duration_sec: float = 3.0
    max_file_kb: int = 500
    ffmpeg_path: str = ""
    ffprobe_path: str = ""
    alpha_webp_supported: bool = True       # from capability probe


@dataclass
class VideoProcessingResult:
    output_path: Path
    size_kb: float
    duration_sec: float
    fps_used: int
    quality_used: int
    within_limit: bool
    warnings: list[str]


class VideoProcessingError(Exception):
    """Raised with a user-friendly message when video processing fails."""


def process_video(
    input_path: str | Path,
    output_path: str | Path,
    options: Optional[VideoProcessingOptions] = None,
    cancel_event: Optional[threading.Event] = None,
    progress_queue=None,
) -> VideoProcessingResult:
    """
    Convert a video clip to an animated WebP sticker asset.

    Args:
        input_path:     Source video file.
        output_path:    Destination .webp file path.
        options:        Processing options (defaults if None).
        cancel_event:   Signal to abort processing.
        progress_queue: Queue for posting progress to UI.

    Returns:
        VideoProcessingResult with output metadata.

    Raises:
        VideoProcessingError: On any failure.
        FFmpegNotFoundError:  If FFmpeg is not installed.
    """
    if options is None:
        options = VideoProcessingOptions()

    input_path = Path(input_path)
    output_path = Path(output_path)
    warnings: list[str] = []

    def _check_cancel():
        if cancel_event and cancel_event.is_set():
            raise VideoProcessingError("Processing was cancelled.")

    def _progress(v: float, text: str = ""):
        if progress_queue:
            post_progress(progress_queue, v, text)

    def _status(text: str):
        if progress_queue:
            post_status(progress_queue, text)

    try:
        # ── Step 1: Read metadata ────────────────────────────────────────────
        _status("Reading video metadata…")
        _progress(0.05)
        meta = _read_metadata(input_path, options, warnings)
        _check_cancel()

        # ── Step 2: Validate and clamp trim range ────────────────────────────
        _status("Validating trim range…")
        start_sec, end_sec = _resolve_trim(meta, options, warnings)
        duration_sec = end_sec - start_sec
        logger.info(
            "Trim: %.2fs – %.2fs (%.2fs)", start_sec, end_sec, duration_sec
        )
        _check_cancel()

        # ── Step 3: FFmpeg encode (with iterative compression) ───────────────
        _status("Encoding animated WebP…")
        _progress(0.15)

        fps_used = options.fps
        quality_used = ANIMATED_QUALITY_STEPS[0]
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with temp_workspace() as workspace:
            quality_used, fps_used = _encode_with_retry(
                input_path=input_path,
                output_path=output_path,
                workspace=workspace,
                start_sec=start_sec,
                duration_sec=duration_sec,
                options=options,
                fps_initial=options.fps,
                warnings=warnings,
                cancel_event=cancel_event,
                progress_fn=_progress,
                status_fn=_status,
            )

        _check_cancel()
        _progress(0.95, "Finalising…")

        # ── Step 4: Gather result stats ──────────────────────────────────────
        if not output_path.exists():
            raise VideoProcessingError(
                "Output file was not created. FFmpeg may have failed silently."
            )

        size_kb = output_path.stat().st_size / 1024
        return VideoProcessingResult(
            output_path=output_path,
            size_kb=size_kb,
            duration_sec=duration_sec,
            fps_used=fps_used,
            quality_used=quality_used,
            within_limit=size_kb <= options.max_file_kb,
            warnings=warnings,
        )

    except (VideoProcessingError, FFmpegNotFoundError):
        raise
    except Exception as exc:
        logger.error("Video processing failed: %s", exc, exc_info=True)
        raise VideoProcessingError(
            f"An unexpected error occurred during video processing: {exc}"
        ) from exc


# ── Metadata ──────────────────────────────────────────────────────────────────

def _read_metadata(
    path: Path,
    options: VideoProcessingOptions,
    warnings: list[str],
) -> VideoMetadata:
    try:
        return get_video_metadata(
            path,
            ffprobe_path=options.ffprobe_path,
            ffmpeg_path=options.ffmpeg_path,
        )
    except Exception as exc:
        raise VideoProcessingError(
            f"Could not read video metadata: {exc}"
        ) from exc


# ── Trim logic ────────────────────────────────────────────────────────────────

def _resolve_trim(
    meta: VideoMetadata,
    options: VideoProcessingOptions,
    warnings: list[str],
) -> tuple[float, float]:
    """
    Resolve and clamp the trim range.

    Rules:
    - start_sec must be ≥ 0 and < video duration.
    - end_sec defaults to min(start + max_duration, video duration).
    - If the selected range > max_duration, it is clamped and the user is warned.
    - If start ≥ end, raises VideoProcessingError.
    """
    max_dur = options.max_duration_sec
    vid_dur = meta.duration if meta.duration > 0 else max_dur

    start = max(0.0, options.start_sec)
    end = options.end_sec if options.end_sec is not None else min(start + max_dur, vid_dur)
    end = min(end, vid_dur)

    if start >= end:
        raise VideoProcessingError(
            "Start time must be before end time. Please adjust the trim range."
        )

    selected = end - start
    if selected > max_dur:
        clamped_end = start + max_dur
        warnings.append(
            f"Selected duration ({selected:.2f}s) exceeds the {max_dur:.1f}s limit. "
            f"Clip trimmed to {max_dur:.1f}s."
        )
        end = clamped_end

    return start, end


# ── FFmpeg encode with retry ──────────────────────────────────────────────────

def _encode_with_retry(
    input_path: Path,
    output_path: Path,
    workspace: Path,
    start_sec: float,
    duration_sec: float,
    options: VideoProcessingOptions,
    fps_initial: int,
    warnings: list[str],
    cancel_event,
    progress_fn,
    status_fn,
) -> tuple[int, int]:
    """
    Encode animated WebP with iterative quality reduction.

    Compression order:
      1. quality 65 → 55 → 45 → 35 at fps_initial (16)
      2. If still over limit: repeat at fps_fallback (12)
      3. If still over limit: warn user and save anyway

    Returns:
        (quality_used, fps_used)
    """
    fallback_fps = WHATSAPP_TARGETS["animated_fallback_fps"]
    max_kb = options.max_file_kb

    total_steps = len(ANIMATED_QUALITY_STEPS) * 2 + 1  # two FPS passes
    step = 0

    for fps in (fps_initial, fallback_fps):
        for quality in ANIMATED_QUALITY_STEPS:
            step += 1
            progress_fn(
                0.15 + 0.75 * (step / total_steps),
                f"Encoding WebP (FPS {fps}, quality {quality})…",
            )

            if cancel_event and cancel_event.is_set():
                raise VideoProcessingError("Processing was cancelled.")

            try:
                _run_ffmpeg_encode(
                    input_path=input_path,
                    output_path=output_path,
                    start_sec=start_sec,
                    duration_sec=duration_sec,
                    fps=fps,
                    quality=quality,
                    options=options,
                    cancel_event=cancel_event,
                )
            except VideoProcessingError:
                raise
            except Exception as exc:
                raise VideoProcessingError(
                    f"FFmpeg encode failed: {exc}"
                ) from exc

            if output_path.exists():
                size_kb = output_path.stat().st_size / 1024
                logger.debug(
                    "Encode attempt FPS=%d Q=%d → %.1f KB", fps, quality, size_kb
                )
                if size_kb <= max_kb:
                    return quality, fps

        if fps == fps_initial and fps_initial != fallback_fps:
            status_fn(
                f"File too large at {fps} FPS; retrying at {fallback_fps} FPS…"
            )
            warnings.append(
                f"Could not reach {max_kb} KB at {fps_initial} FPS; "
                f"retrying at {fallback_fps} FPS."
            )

    # All attempts exhausted
    size_kb = output_path.stat().st_size / 1024 if output_path.exists() else -1
    warnings.append(
        f"Could not compress the video below {max_kb} KB "
        f"(final size: {size_kb:.1f} KB). "
        "The output was saved anyway but may not meet WhatsApp's size limit. "
        "Try using a shorter clip or a less complex scene."
    )
    return ANIMATED_QUALITY_STEPS[-1], fallback_fps


def _run_ffmpeg_encode(
    input_path: Path,
    output_path: Path,
    start_sec: float,
    duration_sec: float,
    fps: int,
    quality: int,
    options: VideoProcessingOptions,
    cancel_event,
) -> None:
    """
    Build and execute a single FFmpeg encode command.
    All arguments are passed as a list (shell=False).
    """
    ffmpeg_bin = find_ffmpeg(options.ffmpeg_path)
    canvas = options.canvas_size

    # Build video filter
    vf = _build_vf(canvas, fps, options.crop_mode, options.alpha_webp_supported)

    cmd = [
        ffmpeg_bin,
        "-y",                          # overwrite output
        "-ss", str(start_sec),        # seek before input (fast seek)
        "-i", str(input_path),
        "-t", str(duration_sec),       # duration
        "-an",                         # remove audio
        "-vf", vf,
        "-vcodec", "libwebp",
        "-loop", str(options.loop),
        "-q:v", str(quality),
        str(output_path),
    ]

    _validate_args(cmd[1:])  # validate everything except binary name
    logger.debug("FFmpeg cmd: %s", " ".join(str(a) for a in cmd))

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
        creationflags=_NO_WINDOW_FLAG,
    )

    try:
        if cancel_event:
            while proc.poll() is None:
                if cancel_event.is_set():
                    _terminate_process(proc)
                    raise VideoProcessingError("Processing was cancelled.")
                cancel_event.wait(timeout=0.2)
            stdout, stderr = proc.communicate()
        else:
            stdout, stderr = proc.communicate(timeout=120)
    except subprocess.TimeoutExpired:
        _terminate_process(proc)
        raise VideoProcessingError("FFmpeg timed out. The video may be too complex.")

    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace").strip()[-500:]
        logger.error("FFmpeg failed (code %d): %s", proc.returncode, err)
        raise VideoProcessingError(
            f"FFmpeg failed with exit code {proc.returncode}. "
            "Check the log for details."
        )


def _build_vf(
    canvas: int,
    fps: int,
    crop_mode: CropMode,
    alpha_supported: bool,
) -> str:
    """
    Build the FFmpeg -vf filter string.

    Mode A (COVER_CROP):
        crop to 1:1 square at centre, then scale to canvas×canvas.

    Mode B (FIT_PAD):
        scale preserving aspect ratio, then pad to canvas×canvas.
        Only used when alpha_supported is confirmed.
    """
    if crop_mode == CropMode.COVER_CROP or not alpha_supported:
        # Crop to square then scale
        vf = (
            f"crop='min(iw,ih)':'min(iw,ih)',"
            f"scale={canvas}:{canvas}:flags=lanczos,"
            f"fps={fps}"
        )
    else:
        # Fit + transparent pad
        # Note: transparent pad color syntax varies by FFmpeg version; 0x00000000 is standard
        vf = (
            f"scale='if(gt(iw,ih),{canvas},-2)':'if(gt(ih,iw),{canvas},-2)',"
            f"pad={canvas}:{canvas}:(ow-iw)/2:(oh-ih)/2:color=0x00000000,"
            f"fps={fps},"
            f"format=rgba"
        )
    return vf


# ── Public utilities ──────────────────────────────────────────────────────────

def build_ffmpeg_command(
    input_path: str | Path,
    output_path: str | Path,
    start_sec: float,
    duration_sec: float,
    fps: int,
    quality: int,
    canvas: int,
    crop_mode: CropMode,
    loop: int,
    alpha_supported: bool,
    ffmpeg_bin: str = "ffmpeg",
) -> list[str]:
    """
    Return the FFmpeg command as a list (for testing / inspection).
    Does NOT execute the command.
    """
    vf = _build_vf(canvas, fps, crop_mode, alpha_supported)
    return [
        ffmpeg_bin,
        "-y",
        "-ss", str(start_sec),
        "-i", str(input_path),
        "-t", str(duration_sec),
        "-an",
        "-vf", vf,
        "-vcodec", "libwebp",
        "-loop", str(loop),
        "-q:v", str(quality),
        str(output_path),
    ]
