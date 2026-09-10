"""
StickerFlow — WhatsApp-Compatible Sticker Asset Studio
Main entry point. Initializes logging, loads settings, launches the UI.
"""

import sys
import queue
import tkinter as tk

from utils.logger import setup_logger
from utils.paths import get_log_dir
from core.settings import UserSettings


def main() -> None:
    """Application entry point."""
    log_dir = get_log_dir()
    logger = setup_logger(log_dir)
    logger.info("StickerFlow starting up.")

    # Load user settings (FFmpeg path, output dir, WhatsApp targets, etc.)
    settings = UserSettings()

    # Build the message queue for thread → UI communication
    msg_queue: queue.Queue = queue.Queue()

    # Import UI here (after logging is ready) so any import errors are logged
    try:
        from ui.app import StickerFlowApp
    except Exception as exc:
        logger.critical("Failed to import UI module: %s", exc, exc_info=True)
        sys.exit(1)

    root = tk.Tk()
    root.withdraw()  # Hide root; StickerFlowApp manages its own CTk window

    try:
        app = StickerFlowApp(settings=settings, msg_queue=msg_queue, logger=logger)
        app.run()
    except Exception as exc:
        logger.critical("Unhandled exception in main loop: %s", exc, exc_info=True)
        sys.exit(1)
    finally:
        logger.info("StickerFlow shut down.")


if __name__ == "__main__":
    main()
