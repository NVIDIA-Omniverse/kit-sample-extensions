"""Async helpers with error logging."""

# pylint: disable=relative-beyond-top-level

import asyncio

import omni.kit.app

from ..config.logging import log_exception, logger


async def wait_for_updates(
    condition,
    *,
    max_updates: int = 60,
    timeout_message: str | None = None,
) -> bool:
    """Wait up to max_updates frames for a condition to be true."""
    if condition():
        return True
    for _ in range(max_updates):
        await omni.kit.app.get_app().next_update_async()
        if condition():
            return True
    if timeout_message:
        logger.warning("%s", timeout_message)
    return condition()


def ensure_future_logged(awaitable, label: str) -> asyncio.Task | None:
    """Schedule an awaitable on Kit's current loop and log unexpected failures.

    OmniUI can invoke callbacks between asyncio loop iterations.  The loop is
    valid in that state, but ``get_running_loop()`` rejects it.  ``ensure_future``
    intentionally accepts Kit's current (temporarily idle) loop so the work runs
    on the next update.
    """
    try:
        task = asyncio.ensure_future(awaitable)
    except RuntimeError as exc:
        # A genuinely missing current loop cannot run the awaitable.  Close
        # coroutine objects to avoid a secondary "was never awaited" warning.
        if asyncio.iscoroutine(awaitable):
            awaitable.close()
        logger.warning("async %s not scheduled: %s", label, exc)
        return None

    def _log_task_result(done_task: asyncio.Task) -> None:
        """Log unhandled task exceptions while ignoring expected cancellation."""
        try:
            done_task.result()
        except asyncio.CancelledError:
            # Cancellation is expected when callers supersede pending work.
            return
        except Exception as exc:  # pylint: disable=broad-exception-caught
            log_exception(logger, "async operation failed", action=label, exc=exc)

    task.add_done_callback(_log_task_result)
    return task


def cancel_task(task: asyncio.Task | None) -> None:
    """Cancel a task when still pending."""
    if task and not task.done():
        task.cancel()
