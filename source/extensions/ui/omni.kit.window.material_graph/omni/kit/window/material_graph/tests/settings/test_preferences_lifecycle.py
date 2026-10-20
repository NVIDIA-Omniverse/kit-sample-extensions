# pylint: disable=relative-beyond-top-level,protected-access
import asyncio
from unittest.mock import MagicMock, patch

from ...scripts.extension import GraphExtension
from ...scripts.preferences.page import MaterialGraphPreferences
from ..base import MaterialGraphTestBase


class TestPreferencesLifecycle(MaterialGraphTestBase):
    """Tests for preferences lifecycle helpers."""

    async def test_destroy_cleans_up_lifecycle(self) -> None:
        """Destroy should clean up lifecycle and clear reference."""
        prefs = MaterialGraphPreferences(GraphExtension._WINDOW_NAME)
        lifecycle = MagicMock()
        prefs._lifecycle = lifecycle
        prefs.destroy()
        lifecycle.cleanup.assert_called()
        self.assertIsNone(prefs._lifecycle)

    async def test_schedule_refresh_no_lifecycle(self) -> None:
        """schedule_refresh should no-op when lifecycle is missing."""
        prefs = MaterialGraphPreferences(GraphExtension._WINDOW_NAME)
        prefs._lifecycle = None
        prefs.schedule_refresh(lambda: None)

    async def test_schedule_refresh_adds_task(self) -> None:
        """schedule_refresh should add a deferred task."""
        prefs = MaterialGraphPreferences(GraphExtension._WINDOW_NAME)
        prefs._lifecycle = MagicMock()
        prefs.schedule_refresh(lambda: None)
        prefs._lifecycle.add_task.assert_called()

    async def test_schedule_refresh_defers_and_coalesces_ui_rebuilds(self) -> None:
        """Only the latest refresh runs, after OmniUI has left its callback."""
        prefs = MaterialGraphPreferences(GraphExtension._WINDOW_NAME)
        first_refresh = MagicMock()
        latest_refresh = MagicMock()
        app = MagicMock()

        async def _next_update():
            return None

        app.next_update_async = _next_update
        with patch("omni.kit.app.get_app", return_value=app):
            prefs.schedule_refresh(first_refresh)
            first_task = prefs._refresh_task
            prefs.schedule_refresh(latest_refresh)
            latest_task = prefs._refresh_task

            await latest_task

        self.assertTrue(first_task.cancelled())
        first_refresh.assert_not_called()
        latest_refresh.assert_called_once_with()
        prefs.destroy()

    async def test_destroy_cancels_a_pending_real_refresh_task(self) -> None:
        """Closing preferences must prevent a deferred callback touching dead widgets."""
        prefs = MaterialGraphPreferences(GraphExtension._WINDOW_NAME)
        refresh = MagicMock()
        gate = asyncio.Event()
        app = MagicMock()

        async def _next_update() -> None:
            await gate.wait()

        app.next_update_async = _next_update
        with patch("omni.kit.app.get_app", return_value=app):
            prefs.schedule_refresh(refresh)
            task = prefs._refresh_task
            self.assertIsNotNone(task)
            self.assertFalse(task.done())
            prefs.destroy()
            await asyncio.sleep(0)

        self.assertTrue(task.cancelled())
        refresh.assert_not_called()
