"""
StickerFlow — FFmpeg Helper
Locates the FFmpeg binary and runs commands safely (list args, no shell=True).
Supports timeout and process cancellation.
"""

import logging
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

logger = logging.getLogger("stickerflow.ffmpeg")

_NO_WINDOW_FLAG = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0

# FFmpeg capability probe: a tiny 1-frame WebP encode to verify libwebp support.
_PROBE_FILTER = (
    "lavfi",
    "color=c=black:size=16x16:rate=1:duration=0.1",
)


class FFmpegError(Exception):
    """Raised when FFmpeg is not found or returns a non-zero exit code."""


class FFmpegNotFoundError(FFmpegError):
    """Raised when FFmpeg binary cannot be located."""


def find_ffmpeg(user_path: str = "") -> str:
    """
    Locate the FFmpeg binary.

    Search order:
      1. User-specified path from settings (if non-empty and executable).
      2. System PATH.
      3. Bundled binary next to this file (./bin/ffmpeg or ./bin/ffmpeg.exe).

    Returns:
        Absolute path string to the ffmpeg executable.

    Raises:
        FFmpegNotFoundError: If no executable is found.
    """
    candidates: list[str] = []

    if user_path:
        candidates.append(user_path)

    # System PATH
    found_in_path = shutil.which("ffmpeg")
    if found_in_path:
        candidates.append(found_in_path)

    # Bundled binary (distributed alongside the app)
    bundled = Path(__file__).parent.parent / "bin" / _ffmpeg_exe_name()
    candidates.append(str(bundled))

    for candidate in candidates:
        if _is_executable(candidate):
            logger.info("FFmpeg found: %s", Path(candidate).name)
            return candidate

    raise FFmpegNotFoundError(
        "FFmpeg not found. Please install FFmpeg and add it to your PATH, "
        "or specify the path in Settings."
    )


def find_ffprobe(user_path: str = "") -> Optional[str]:
    """
    Locate FFprobe binary (optional — caller must handle None).

    Returns None if not found (caller should fall back to ffmpeg -i parsing).
    """
    candidates: list[str] = []

    if user_path:
        candidates.append(user_path)

    found_in_path = shutil.which("ffprobe")
    if found_in_path:
        candidates.append(found_in_path)

    bundled = Path(__file__).parent.parent / "bin" / _ffprobe_exe_name()
    candidates.append(str(bundled))

    for candidate in candidates:
        if _is_executable(candidate):
            logger.info("FFprobe found: %s", Path(candidate).name)
            return candidate

    logger.warning("FFprobe not found; will use ffmpeg -i fallback.")
    return None


def run_ffmpeg(
    args: list[str],
    timeout: Optional[float] = None,
    cancel_event: Optional[threading.Event] = None,
    capture_stderr: bool = True,
) -> subprocess.CompletedProcess:
    """
    Run FFmpeg with *args* (must NOT include the binary name as args[0]).

    Args:
        args:           Command arguments (list, never shell-joined).
        timeout:        Optional per-process wall-clock timeout in seconds.
        cancel_event:   If set, the process is terminated when the event fires.
        capture_stderr: Whether to capture stderr (needed for progress parsing).

    Returns:
        CompletedProcess with returncode, stdout, stderr.

    Raises:
        FFmpegNotFoundError: If ffmpeg binary is missing.
        FFmpegError:         If the process exits with a non-zero code.
        ValueError:          If *args* contains None or is a string (safety check).
    """
    _validate_args(args)

    try:
        ffmpeg_bin = find_ffmpeg()
    except FFmpegNotFoundError:
        raise

    cmd = [ffmpeg_bin] + args
    logger.debug("Running FFmpeg: %s", " ".join(str(a) for a in cmd))

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE if capture_stderr else subprocess.DEVNULL,
            shell=False,  # NEVER True — security requirement
            creationflags=_NO_WINDOW_FLAG,
        )
    except FileNotFoundError as exc:
        raise FFmpegNotFoundError(f"FFmpeg binary not found: {exc}") from exc
    except Exception as exc:
        raise FFmpegError(f"Failed to start FFmpeg: {exc}") from exc

    stdout_data = b""
    stderr_data = b""

    try:
        if cancel_event:
            # Poll for cancellation while waiting for the process
            while proc.poll() is None:
                if cancel_event.is_set():
                    logger.info("FFmpeg process cancelled by user.")
                    _terminate_process(proc)
                    raise FFmpegError("Processing was cancelled.")
                cancel_event.wait(timeout=0.2)
            stdout_data, stderr_data = proc.communicate()
        else:
            stdout_data, stderr_data = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _terminate_process(proc)
        raise FFmpegError(
            f"FFmpeg process timed out after {timeout:.0f} seconds."
        )

    if proc.returncode != 0:
        stderr_text = stderr_data.decode("utf-8", errors="replace").strip()
        logger.error("FFmpeg exited with code %d: %s", proc.returncode, stderr_text[-500:])
        raise FFmpegError(
            f"FFmpeg failed (exit code {proc.returncode}). "
            "Check the log for details."
        )

    return subprocess.CompletedProcess(
        args=cmd,
        returncode=proc.returncode,
        stdout=stdout_data,
        stderr=stderr_data,
    )


def check_webp_support(ffmpeg_path: str = "") -> dict[str, bool]:
    """
    Probe FFmpeg capabilities relevant to sticker production.

    Returns a dict with boolean flags:
        - "ffmpeg_ok":        FFmpeg is available and runs.
        - "libwebp":          libwebp encoder is compiled in.
        - "animated_webp":    Can encode animated WebP (basic probe).
        - "alpha_webp":       Can encode alpha-channel animated WebP.
    """
    caps = {
        "ffmpeg_ok": False,
        "libwebp": False,
        "animated_webp": False,
        "alpha_webp": False,
    }

    try:
        binary = find_ffmpeg(ffmpeg_path)
    except FFmpegNotFoundError:
        return caps

    # Check ffmpeg -version output
    try:
        result = subprocess.run(
            [binary, "-version"],
            capture_output=True,
            text=True,
            timeout=10,
            shell=False,
            creationflags=_NO_WINDOW_FLAG,
        )
        caps["ffmpeg_ok"] = result.returncode == 0
        caps["libwebp"] = "libwebp" in result.stdout
    except Exception as exc:
        logger.warning("FFmpeg version check failed: %s", exc)
        return caps

    if not caps["libwebp"]:
        return caps

    # Probe animated WebP encode
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmp:
        probe_out = Path(tmp) / "probe.webp"
        probe_cmd = [
            binary,
            "-y",
            "-f", "lavfi",
            "-i", "color=c=black:size=16x16:rate=1:duration=0.1",
            "-vframes", "2",
            "-loop", "0",
            str(probe_out),
        ]
        try:
            proc = subprocess.run(
                probe_cmd,
                capture_output=True,
                timeout=15,
                shell=False,
                creationflags=_NO_WINDOW_FLAG,
            )
            caps["animated_webp"] = proc.returncode == 0 and probe_out.exists()
        except Exception as exc:
            logger.warning("Animated WebP probe failed: %s", exc)

    # Probe alpha animated WebP
    if caps["animated_webp"]:
        with tempfile.TemporaryDirectory() as tmp:
            probe_out = Path(tmp) / "probe_alpha.webp"
            probe_cmd = [
                binary,
                "-y",
                "-f", "lavfi",
                "-i", "color=c=0x00000000:size=16x16:rate=1:duration=0.1",
                "-vf", "format=rgba",
                "-vframes", "2",
                "-loop", "0",
                str(probe_out),
            ]
            try:
                proc = subprocess.run(
                    probe_cmd,
                    capture_output=True,
                    timeout=15,
                    shell=False,
                    creationflags=_NO_WINDOW_FLAG,
                )
                caps["alpha_webp"] = proc.returncode == 0 and probe_out.exists()
            except Exception as exc:
                logger.warning("Alpha WebP probe failed: %s", exc)

    logger.info("FFmpeg capabilities: %s", caps)
    return caps


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ffmpeg_exe_name() -> str:
    import sys
    return "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"


def _ffprobe_exe_name() -> str:
    import sys
    return "ffprobe.exe" if sys.platform == "win32" else "ffprobe"


def _is_executable(path: str) -> bool:
    p = Path(path)
    return p.is_file() and shutil.which(str(p)) is not None or p.is_file()


def _validate_args(args: list) -> None:
    if isinstance(args, str):
        raise ValueError(
            "FFmpeg args must be a list, not a string. "
            "Passing a string would enable shell injection risk."
        )
    for i, a in enumerate(args):
        if a is None:
            raise ValueError(f"FFmpeg args[{i}] is None — check argument construction.")


def _terminate_process(proc: subprocess.Popen) -> None:
    try:
        proc.terminate()
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
    except Exception as exc:
        logger.warning("Error terminating FFmpeg process: %s", exc)
