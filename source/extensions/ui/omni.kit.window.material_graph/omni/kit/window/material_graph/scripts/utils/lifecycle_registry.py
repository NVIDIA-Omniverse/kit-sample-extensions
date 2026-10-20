"""Implement material graph extension logic for `utils/lifecycle_registry.py`."""

import asyncio
import logging
from typing import Any, Awaitable, Callable, List, Optional, Union

from ..config.logging import LogContext, context_suffix, get_logger, log_exception

logger = get_logger()


class LifecycleRegistry:
    """Tracks async tasks and cleanup callbacks for a lifecycle."""

    def __init__(self) -> None:
        """Initialize lifecycle tracking containers for subscriptions, callbacks, and async tasks."""
        self._tasks: List[asyncio.Task] = []
        self._cleanup: List[Callable[[], None]] = []

    def add_task(
        self,
        task: Optional[Union[asyncio.Task, Awaitable]],
        *,
        label: str = "task",
    ) -> Optional[asyncio.Task]:
        """Track a task or awaitable and return an asyncio.Task."""
        if task and not isinstance(task, asyncio.Task):
            task = asyncio.ensure_future(task)
        if task:
            logger.debug("lifecycle add task%s", context_suffix(LogContext(action="add_task"), file_path=label))
            self._tasks.append(task)
            task.add_done_callback(lambda completed: self._on_task_done(completed, label))
        return task

    def _on_task_done(self, task: asyncio.Task, label: str) -> None:
        """Log completion failures and stop retaining a finished task."""
        self._log_task_exception(task, label)
        try:
            self._tasks.remove(task)
        except ValueError:
            pass

    @staticmethod
    def _log_task_exception(task: asyncio.Task, label: str) -> None:
        """Log unexpected task failures."""
        try:
            task.result()
        except asyncio.CancelledError:
            logger.debug(
                "lifecycle task cancelled%s", context_suffix(LogContext(action="task_cancelled"), file_path=label)
            )
            return
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_exception(logger, "lifecycle task failed", action=label, exc=exc)

    def add_cleanup(self, callback: Optional[Callable[[], None]]) -> None:
        """Register a cleanup callback."""
        if callback:
            self._cleanup.append(callback)

    def add_unsubscribe(self, subscription: Any, method_name: str = "unsubscribe") -> None:
        """Register a cleanup action to unsubscribe a listener."""
        if subscription is None:
            logger.debug("add_unsubscribe skipped: subscription is None")
            return

        def _cleanup():
            """Run best-effort unsubscribe for a tracked subscription object."""
            try:
                if hasattr(subscription, method_name):
                    getattr(subscription, method_name)()
                elif hasattr(subscription, "unsubscribe"):
                    subscription.unsubscribe()
            except AttributeError as exc:
                # Subscription object may not expose expected cleanup hooks in
                # some runtime/test doubles; skip as no-op.
                logger.debug("lifecycle unsubscribe hook missing: %s", exc)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                log_exception(
                    logger,
                    "lifecycle unsubscribe failed",
                    level=logging.WARNING,
                    action=method_name,
                    exc=exc,
                )

        self._cleanup.append(_cleanup)

    def cleanup(self, raise_on_error: bool = False) -> None:
        """Cancel tasks and run cleanup callbacks."""
        logger.debug(
            "lifecycle cleanup start%s",
            context_suffix(
                LogContext(action="cleanup"), file_path=f"tasks={len(self._tasks)} callbacks={len(self._cleanup)}"
            ),
        )
        for task in self._tasks:
            if task and not task.done():
                task.cancel()
            elif task:
                try:
                    task.exception()
                except asyncio.CancelledError:
                    # Cancelled tasks are expected during lifecycle teardown.
                    continue
        self._tasks = []

        for callback in self._cleanup:
            try:
                callback()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                log_exception(
                    logger,
                    "lifecycle cleanup failed",
                    level=logging.WARNING,
                    action="cleanup",
                    exc=exc,
                )
                if raise_on_error:
                    raise
        self._cleanup = []
        logger.debug("lifecycle cleanup end%s", context_suffix(LogContext(action="cleanup_done")))

    async def cleanup_async(self, raise_on_error: bool = False) -> None:
        """Cancel tasks, await completion, and run cleanup callbacks."""
        logger.debug(
            "lifecycle cleanup_async start%s",
            context_suffix(
                LogContext(action="cleanup_async"), file_path=f"tasks={len(self._tasks)} callbacks={len(self._cleanup)}"
            ),
        )
        tasks = [task for task in self._tasks if task]
        for task in tasks:
            if not task.done():
                task.cancel()
        for task in tasks:
            try:
                await task
            except asyncio.CancelledError:
                # Cancelled tasks are expected during lifecycle teardown.
                continue
            except Exception as exc:  # pylint: disable=broad-exception-caught
                log_exception(
                    logger,
                    "lifecycle task cleanup failed",
                    level=logging.WARNING,
                    action="cleanup_async",
                    exc=exc,
                )
                if raise_on_error:
                    raise
        self._tasks = []
        for callback in self._cleanup:
            try:
                callback()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                log_exception(
                    logger,
                    "lifecycle cleanup failed",
                    level=logging.WARNING,
                    action="cleanup_async",
                    exc=exc,
                )
                if raise_on_error:
                    raise
        self._cleanup = []
        logger.debug("lifecycle cleanup_async end%s", context_suffix(LogContext(action="cleanup_async_done")))
