"""
StickerFlow — Logger
Sets up a rotating file logger + console handler.
Sensitive file paths are masked in log output.
"""

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path


_SENSITIVE_PATH_RE = re.compile(
    r'(?:[A-Za-z]:\\|/home/|/Users/)[^\s"\'<>|*?\\/:]+', re.IGNORECASE
)


class _MaskingFilter(logging.Filter):
    """Replaces full user paths in log messages with a masked placeholder."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = _SENSITIVE_PATH_RE.sub("<path>", record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: _SENSITIVE_PATH_RE.sub("<path>", v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    _SENSITIVE_PATH_RE.sub("<path>", a) if isinstance(a, str) else a
                    for a in record.args
                )
        return True


def setup_logger(log_dir: Path, level: int = logging.DEBUG) -> logging.Logger:
    """
    Configure and return the root application logger.

    Args:
        log_dir: Directory where log files will be written.
        level:   Minimum log level (default DEBUG).

    Returns:
        Configured Logger instance named "stickerflow".
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "stickerflow.log"

    logger = logging.getLogger("stickerflow")
    logger.setLevel(level)

    if logger.handlers:
        # Already configured (e.g., during tests); return as-is.
        return logger

    # ── File handler (rotating, 5 MB × 3 backups) ──────────────────────────
    file_handler = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)
    file_handler.addFilter(_MaskingFilter())

    # ── Console handler (WARNING and above) ─────────────────────────────────
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.WARNING)
    console_fmt = logging.Formatter("[%(levelname)s] %(message)s")
    console_handler.setFormatter(console_fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("Logger initialized. Log file: %s", str(log_file))
    return logger


def get_logger(name: str = "stickerflow") -> logging.Logger:
    """Return a child logger scoped to *name*."""
    return logging.getLogger(name)
