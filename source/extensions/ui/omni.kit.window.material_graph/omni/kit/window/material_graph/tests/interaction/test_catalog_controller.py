import asyncio
from unittest.mock import MagicMock, patch

from ...scripts.settings.settings import Settings
from ...scripts.ui.controllers.catalog.visibility import CatalogController
from ...scripts.utils.lifecycle_registry import LifecycleRegistry
from ..base import MaterialGraphTestBase


class TestCatalogController(MaterialGraphTestBase):
    """Catalog controller behavior."""

    async def test_apply_visibility_calls_widget(self) -> None:
        """apply_visibility should update widget visibility."""
        widget = MagicMock()
        with patch.object(Settings, "show_catalog", autospec=True, return_value=True):
            controller = CatalogController(widget)

        async def _noop() -> None:
            return None

        with patch("omni.kit.app.get_app", autospec=True) as get_app:
            get_app.return_value.next_update_async = _noop
            controller.apply_visibility()
            await asyncio.gather(*controller._lifecycle._tasks)

        widget.set_catalog_visible.assert_called_with(True)
        controller.destroy()

    async def test_registers_setting_subscription(self) -> None:
        """Controller should subscribe to show-catalog settings."""
        dummy_settings = MagicMock()
        dummy_settings.subscribe_to_tree_change_events.return_value = MagicMock()
        with patch("carb.settings.get_settings", autospec=True, return_value=dummy_settings):
            controller = CatalogController(MagicMock())
        dummy_settings.subscribe_to_tree_change_events.assert_called_once()
        args, _kwargs = dummy_settings.subscribe_to_tree_change_events.call_args
        self.assertEqual(args[0], Settings.SHOW_CATALOG)
        self.assertTrue(callable(args[1]))
        controller.destroy()
