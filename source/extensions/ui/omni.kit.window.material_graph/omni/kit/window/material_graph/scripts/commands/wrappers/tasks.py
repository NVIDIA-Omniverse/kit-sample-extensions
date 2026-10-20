"""Task tracking utilities for command-launched background coroutines."""

import asyncio
import weakref
from typing import Optional

from ...config.logging import log_exception, logger


class _CommandTaskManager:
    """Track command tasks and clean them up safely."""

    def __init__(self) -> None:
        """Initialize weak task storage used for background command tasks."""
        self._tasks: "weakref.WeakSet[asyncio.Task]" = weakref.WeakSet()

    def track(self, task: Optional[asyncio.Task]) -> None:
        """Track a task for cleanup."""
        if not task:
            return
        self._tasks.add(task)
        task.add_done_callback(self._on_task_done)

    def cleanup(self) -> None:
        """Cancel any tracked command tasks."""
        for task in list(self._tasks):
            if not task or task.done():
                continue
            task.cancel()
            try:
                if task.done():
                    task.exception()
            except (asyncio.CancelledError, asyncio.InvalidStateError) as exc:
                logger.debug("task cancel/exception during cleanup: %s", exc)
                continue
        self._tasks = weakref.WeakSet()

    def _on_task_done(self, task: asyncio.Task) -> None:
        """Observe completion failures and remove completed tasks from tracking."""
        try:
            task.result()
        except asyncio.CancelledError:
            pass
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_exception(logger, "command task failed", action="background_command", exc=exc)
        self._tasks.discard(task)


_COMMAND_TASK_MANAGER = _CommandTaskManager()


def cleanup_command_tasks() -> None:
    """Cancel any tracked command tasks."""
    _COMMAND_TASK_MANAGER.cleanup()


def track_command_task(task: Optional[asyncio.Task]) -> None:
    """Track a command-scoped task for cleanup."""
    _COMMAND_TASK_MANAGER.track(task)
