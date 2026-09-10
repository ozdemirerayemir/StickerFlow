"""
StickerFlow — Temporary File Manager
Provides a context manager that creates an app-specific temp directory
and cleans it up on exit, cancellation, or error.
"""

import logging
import shutil
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from config import TEMP_DIR_NAME

logger = logging.getLogger("stickerflow.temp")


def get_temp_base() -> Path:
    """Return the base temp directory for StickerFlow (created if missing)."""
    base = Path(tempfile.gettempdir()) / TEMP_DIR_NAME
    base.mkdir(parents=True, exist_ok=True)
    return base


@contextmanager
def temp_workspace() -> Generator[Path, None, None]:
    """
    Context manager that yields a unique temporary workspace directory.
    The directory and all its contents are deleted when the block exits,
    regardless of success or failure.

    Usage::

        with temp_workspace() as workspace:
            tmp_file = workspace / "frame.png"
            ...  # do work
        # workspace is cleaned up here
    """
    workspace = get_temp_base() / str(uuid.uuid4())
    workspace.mkdir(parents=True, exist_ok=True)
    logger.debug("Created temp workspace: %s", workspace.name)
    try:
        yield workspace
    finally:
        _cleanup(workspace)


def _cleanup(path: Path) -> None:
    """Remove *path* and all its contents, logging any errors."""
    try:
        if path.exists():
            shutil.rmtree(path)
            logger.debug("Cleaned up temp workspace: %s", path.name)
    except Exception as exc:
        logger.warning("Failed to clean up temp path %s: %s", path.name, exc)


def cleanup_all() -> None:
    """
    Remove the entire StickerFlow temp base directory.
    Called on application shutdown.
    """
    base = Path(tempfile.gettempdir()) / TEMP_DIR_NAME
    _cleanup(base)
