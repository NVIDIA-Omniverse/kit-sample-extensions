# pylint: disable=relative-beyond-top-level
import asyncio
from unittest.mock import patch

import omni.kit.test

from ...scripts.config.paths import Paths
from ...scripts.utils.async_utils import ensure_future_logged, wait_for_updates


class _DummyApp:
    def __init__(self, state):
        self._state = state

    async def next_update_async(self):
        self._state["count"] += 1


class TestAsyncUtils(omni.kit.test.AsyncTestCase):
    """wait_for_updates polls the app update loop until a condition is true or timeout; ensure_future_logged
    schedules a coroutine and logs if it fails. We test resolution, timeout logging, and failure
    logging, using a stubbed app and patched logger where needed."""

    async def test_wait_for_updates_resolves(self) -> None:
        """wait_for_updates resolves when condition true."""
        # Patch omni.kit.app.get_app to use our dummy app so we control update count.
        state = {"count": 0}
        app = _DummyApp(state)
        condition = lambda: state["count"] >= 2
        with patch("omni.kit.app.get_app", return_value=app):
            self.assertTrue(await wait_for_updates(condition, max_updates=5))
        self.assertEqual(state["count"], 2)

    async def test_wait_for_updates_logs_timeout(self) -> None:
        """wait_for_updates logs on timeout."""
        # Patch get_app and logger.warning to assert timeout message is logged.
        state = {"count": 0}
        app = _DummyApp(state)
        condition = lambda: False
        with (
            patch("omni.kit.app.get_app", return_value=app),
            patch(
                f"{Paths.MODULE_ID}.scripts.utils.async_utils.logger.warning",
                autospec=True,
            ) as log_warn,
        ):
            self.assertFalse(await wait_for_updates(condition, max_updates=2, timeout_message="timeout"))
        log_warn.assert_called_once()

    async def test_ensure_future_logged_reports_failures(self) -> None:
        """ensure_future_logged records arbitrary task failures with a traceback."""

        async def _boom():
            raise KeyError("boom")

        with patch(
            f"{Paths.MODULE_ID}.scripts.utils.async_utils.log_exception",
            autospec=True,
        ) as log_failure:
            task = ensure_future_logged(_boom(), "test")
            try:
                await task
            except KeyError:
                pass
        log_failure.assert_called_once()
        self.assertIsInstance(log_failure.call_args.kwargs["exc"], KeyError)

    async def test_ensure_future_logged_accepts_idle_current_loop(self) -> None:
        """Work scheduled between Kit loop ticks runs on the next loop iteration."""

        def _schedule_on_idle_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def _answer():
                return 42

            try:
                task = ensure_future_logged(_answer(), "idle loop")
                was_running = loop.is_running()
                return was_running, loop.run_until_complete(task)
            finally:
                asyncio.set_event_loop(None)
                loop.close()

        was_running, result = await asyncio.to_thread(_schedule_on_idle_loop)

        self.assertFalse(was_running)
        self.assertEqual(result, 42)

    async def test_ensure_future_logged_handles_missing_running_loop(self) -> None:
        """ensure_future_logged returns None and logs when no current loop exists."""

        async def _noop():
            return None

        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.utils.async_utils.asyncio.ensure_future",
                side_effect=RuntimeError("no running event loop"),
            ),
            patch(
                f"{Paths.MODULE_ID}.scripts.utils.async_utils.logger.warning",
                autospec=True,
            ) as log_warn,
        ):
            task = ensure_future_logged(_noop(), "texture menu show")

        self.assertIsNone(task)
        log_warn.assert_called_once()
