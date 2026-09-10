"""
StickerFlow — Background Threading Worker
Runs a callable in a daemon thread and posts progress/result/error
messages back to the UI via a thread-safe queue.

The UI should poll the queue with `root.after()` — never block the main thread.
"""

import logging
import threading
import traceback
from dataclasses import dataclass, field
from enum import Enum, auto
from queue import Queue
from typing import Any, Callable, Optional

logger = logging.getLogger("stickerflow.worker")


class MsgType(Enum):
    PROGRESS = auto()   # {"value": float 0–1, "text": str}
    STATUS = auto()     # {"text": str}
    RESULT = auto()     # {"data": Any}
    ERROR = auto()      # {"message": str, "detail": str}
    CANCELLED = auto()  # {}
    DONE = auto()       # {}


@dataclass
class WorkerMessage:
    msg_type: MsgType
    payload: dict = field(default_factory=dict)


class Worker:
    """
    Wraps a callable to run in a background thread.

    Args:
        target:    The function to execute. It receives *cancel_event* as a
                   keyword argument so it can check for cancellation.
        args:      Positional arguments forwarded to *target*.
        kwargs:    Keyword arguments forwarded to *target*.
        queue:     Queue used to post WorkerMessages to the UI.
    """

    def __init__(
        self,
        target: Callable,
        args: tuple = (),
        kwargs: Optional[dict] = None,
        queue: Optional[Queue] = None,
    ) -> None:
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}
        self._queue: Queue = queue or Queue()
        self._cancel_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def queue(self) -> Queue:
        return self._queue

    @property
    def cancel_event(self) -> threading.Event:
        return self._cancel_event

    def start(self) -> None:
        """Start the worker thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("Worker already running; ignoring start().")
            return
        self._cancel_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.debug("Worker thread started.")

    def cancel(self) -> None:
        """Signal the worker to cancel."""
        self._cancel_event.set()
        logger.debug("Worker cancellation requested.")

    def is_alive(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run(self) -> None:
        try:
            result = self._target(
                *self._args,
                cancel_event=self._cancel_event,
                progress_queue=self._queue,
                **self._kwargs,
            )
            if self._cancel_event.is_set():
                self._post(WorkerMessage(MsgType.CANCELLED))
            else:
                self._post(WorkerMessage(MsgType.RESULT, {"data": result}))
        except Exception as exc:
            detail = traceback.format_exc()
            logger.error("Worker exception: %s", exc, exc_info=True)
            self._post(
                WorkerMessage(
                    MsgType.ERROR,
                    {"message": str(exc), "detail": detail},
                )
            )
        finally:
            self._post(WorkerMessage(MsgType.DONE))

    def _post(self, msg: WorkerMessage) -> None:
        try:
            self._queue.put_nowait(msg)
        except Exception as exc:
            logger.warning("Failed to post worker message: %s", exc)


def post_progress(
    queue: Queue,
    value: float,
    text: str = "",
) -> None:
    """
    Convenience function for worker callables to post progress updates.

    Args:
        queue: The progress_queue received by the worker callable.
        value: Progress value between 0.0 and 1.0.
        text:  Optional status text.
    """
    try:
        queue.put_nowait(
            WorkerMessage(MsgType.PROGRESS, {"value": value, "text": text})
        )
    except Exception:
        pass  # Non-critical; never crash a worker over a progress report


def post_status(queue: Queue, text: str) -> None:
    """Convenience function to post a status-only message."""
    try:
        queue.put_nowait(WorkerMessage(MsgType.STATUS, {"text": text}))
    except Exception:
        pass
