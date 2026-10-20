import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ...scripts.config.paths import Paths
from ...scripts.extension import GraphExtension
from ...scripts.utils.lifecycle_registry import LifecycleRegistry
from ..base import MaterialGraphTestBase

# pylint: disable=protected-access,broad-exception-caught


class TestLifecycleRegistry(MaterialGraphTestBase):
    """LifecycleRegistry tracks async tasks and cleanup callbacks so the extension can cancel or
    release them on shutdown. We test add_task wrapping, cleanup cancelling tasks, cleanup_async,
    cleanup callbacks, add_unsubscribe with missing or release method, task failure logging, and
    extension subscription/unregister cleanup."""

    async def test_add_task_wraps_coroutine(self) -> None:
        """add_task wraps coroutine and runs it."""
        lifecycle = LifecycleRegistry()
        ran = {"value": False}

        async def _worker() -> None:
            """Async worker that flips a flag."""
            await asyncio.sleep(0)
            ran["value"] = True

        task = lifecycle.add_task(_worker())
        self.assertIsNotNone(task)
        self.assertTrue(isinstance(task, asyncio.Task))
        await task
        self.assertTrue(ran["value"])
        await asyncio.sleep(0)
        self.assertEqual(lifecycle._tasks, [])

    async def test_add_task_accepts_none_and_existing_task(self) -> None:
        """Optional work is ignored while an existing task retains its identity."""
        lifecycle = LifecycleRegistry()
        self.assertIsNone(lifecycle.add_task(None))

        task = asyncio.create_task(asyncio.sleep(0))
        self.assertIs(lifecycle.add_task(task, label="existing"), task)
        await task
        await asyncio.sleep(0)
        self.assertEqual(lifecycle._tasks, [])

    async def test_completed_task_is_not_retained_after_failure(self) -> None:
        """Failed tasks should be logged without leaking lifecycle references."""
        lifecycle = LifecycleRegistry()

        async def _worker() -> None:
            raise OSError("injected failure")

        with patch(f"{Paths.MODULE_ID}.scripts.utils.lifecycle_registry.log_exception") as log_failure:
            task = lifecycle.add_task(_worker(), label="retention-test")
            with self.assertRaises(OSError):
                await task
            await asyncio.sleep(0)
        log_failure.assert_called_once()
        self.assertEqual(lifecycle._tasks, [])

    async def test_cleanup_cancels_pending_tasks(self) -> None:
        """cleanup cancels pending tasks."""
        lifecycle = LifecycleRegistry()
        gate = asyncio.Event()

        async def _blocker() -> None:
            """Wait on the gate to stay pending."""
            await gate.wait()

        task = lifecycle.add_task(_blocker())
        self.assertIsNotNone(task)
        lifecycle.cleanup()
        await self.wait_n_updates(1)
        self.assertTrue(task.cancelled() or task.done())

    async def test_cleanup_async_waits_for_tasks(self) -> None:
        """cleanup_async awaits task cancellation."""
        lifecycle = LifecycleRegistry()
        gate = asyncio.Event()

        async def _blocker() -> None:
            """Wait on the gate to stay pending."""
            await gate.wait()

        task = lifecycle.add_task(_blocker())
        self.assertIsNotNone(task)
        await lifecycle.cleanup_async()
        self.assertTrue(task.cancelled() or task.done())

    async def test_cleanup_executes_callbacks(self) -> None:
        """cleanup runs registered callbacks."""
        lifecycle = LifecycleRegistry()
        called = {"value": False}

        def _cleanup() -> None:
            """Flip a flag when invoked."""
            called["value"] = True

        lifecycle.add_cleanup(_cleanup)
        lifecycle.cleanup()
        self.assertTrue(called["value"])

    async def test_add_unsubscribe_missing_method_safe(self) -> None:
        """add_unsubscribe tolerates missing method."""
        lifecycle = LifecycleRegistry()

        class Dummy:
            """Dummy object without unsubscribe method."""

            ...

        lifecycle.add_unsubscribe(Dummy(), method_name="unsubscribe")
        lifecycle.cleanup()

    async def test_cleanup_subscription_release(self) -> None:
        """add_unsubscribe calls release on cleanup."""
        lifecycle = LifecycleRegistry()
        called = {"value": False}

        class Dummy:
            """Dummy subscription with release method."""

            def release(self) -> None:
                """Record release calls."""
                called["value"] = True

        lifecycle.add_unsubscribe(Dummy(), method_name="release")
        lifecycle.cleanup()
        self.assertTrue(called["value"])

    async def test_unsubscribe_fallback_and_cleanup_error_policy(self) -> None:
        """Fallback unsubscribe works and cleanup errors follow the requested policy."""
        lifecycle = LifecycleRegistry()
        subscription = SimpleNamespace(unsubscribe=MagicMock())
        lifecycle.add_unsubscribe(subscription, method_name="release")
        lifecycle.cleanup()
        subscription.unsubscribe.assert_called_once_with()

        lifecycle.add_cleanup(MagicMock(side_effect=RuntimeError("injected")))
        lifecycle.cleanup()
        lifecycle.add_cleanup(MagicMock(side_effect=ValueError("injected")))
        with self.assertRaises(ValueError):
            lifecycle.cleanup(raise_on_error=True)

    async def test_cancelled_task_and_async_cleanup_failures_are_contained(self) -> None:
        """Cancellation is routine and async cleanup can contain or propagate failures."""
        lifecycle = LifecycleRegistry()
        cancelled = asyncio.create_task(asyncio.sleep(10))
        lifecycle.add_task(cancelled, label="cancelled")
        cancelled.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await cancelled
        await asyncio.sleep(0)
        self.assertEqual(lifecycle._tasks, [])

        async def _fail() -> None:
            raise RuntimeError("injected")

        failed = asyncio.create_task(_fail())
        lifecycle._tasks.append(failed)
        await asyncio.sleep(0)
        await lifecycle.cleanup_async()

        failed = asyncio.create_task(_fail())
        lifecycle._tasks.append(failed)
        await asyncio.sleep(0)
        with self.assertRaises(RuntimeError):
            await lifecycle.cleanup_async(raise_on_error=True)

    async def test_add_task_logs_failures(self) -> None:
        """add_task logs when task raises."""
        lifecycle = LifecycleRegistry()

        async def _boom() -> None:
            raise KeyError("boom")

        with patch(
            f"{Paths.MODULE_ID}.scripts.utils.lifecycle_registry.log_exception",
            autospec=True,
        ) as log_failure:
            task = lifecycle.add_task(_boom(), label="boom-task")
            self.assertIsNotNone(task)
            try:
                await task
            except KeyError:
                pass
        log_failure.assert_called_once()
        self.assertEqual(log_failure.call_args.kwargs["action"], "boom-task")
        self.assertIsInstance(log_failure.call_args.kwargs["exc"], KeyError)

    async def test_extension_subscription_cleanup(self) -> None:
        """Extension cleanup calls unsubscribe/release and clears the handle."""
        ext_instance = GraphExtension()
        called = {"unsubscribe": False, "release": False}

        class SubUnsub:
            """Subscription stub with unsubscribe."""

            def unsubscribe(self) -> None:
                """Record unsubscribe calls."""
                called["unsubscribe"] = True

        class SubRelease:
            """Subscription stub with release."""

            def release(self) -> None:
                """Record release calls."""
                called["release"] = True

        ext_instance._extension_subscription = (SubUnsub(), SubRelease())
        ext_instance._cleanup_extension_subscriptions()
        self.assertTrue(called["unsubscribe"])
        self.assertTrue(called["release"])
        self.assertIsNone(ext_instance._extension_subscription)

    async def test_extension_unregister_stage_menu(self) -> None:
        """Unregister stage menu releases and clears handles."""
        ext_instance = GraphExtension()
        called = {"stage": False, "thumb": False}

        class Dummy:
            """Context menu stub that records releases."""

            def __init__(self, key: str) -> None:
                """Initialize with a key name."""
                self._key = key

            def release(self) -> None:
                """Record release calls."""
                called[self._key] = True

        ext_instance._stage_context_menu = Dummy("stage")
        ext_instance._thumb_context_menu = Dummy("thumb")
        ext_instance._unregister_stage_menu()
        self.assertTrue(called["stage"])
        self.assertTrue(called["thumb"])
        self.assertIsNone(ext_instance._stage_context_menu)
        self.assertIsNone(ext_instance._thumb_context_menu)
