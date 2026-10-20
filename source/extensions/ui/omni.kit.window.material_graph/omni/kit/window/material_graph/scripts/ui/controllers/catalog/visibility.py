"""Implement material graph extension logic for `ui/controllers/catalog/visibility.py`."""

import asyncio
from typing import Any

import carb.settings
import omni.kit.app

from ....settings.settings import Settings
from ....utils.lifecycle_registry import LifecycleRegistry


class CatalogController:
    """Controls catalog visibility based on settings."""

    def __init__(self, widget: object) -> None:
        """Initialize catalog controller state."""
        self._widget = widget
        self._show_catalog = Settings.show_catalog()
        self._lifecycle = LifecycleRegistry()
        self._settings = carb.settings.get_settings()
        self._settings_sub = self._settings.subscribe_to_tree_change_events(
            Settings.SHOW_CATALOG, self._on_setting_changed
        )
        self._lifecycle.add_unsubscribe(self._settings_sub, "unsubscribe_to_tree_change_events")

    def apply_visibility(self) -> None:
        """Apply catalog visibility on the next UI frame."""
        if not self._lifecycle:
            return

        async def apply_async() -> None:
            """Defer visibility update to the next update."""
            await omni.kit.app.get_app().next_update_async()
            if self._widget:
                self._widget.set_catalog_visible(self._show_catalog)

        self._lifecycle.add_task(apply_async())

    def _on_setting_changed(self, _tree_item: Any, changed_item: Any, _event_type: Any) -> None:
        """Handle catalog visibility setting changes."""
        if not self._lifecycle:
            return
        self._show_catalog = bool(changed_item)
        self.apply_visibility()

    def destroy(self) -> None:
        """Release subscriptions, callbacks, and cached references owned by this controller."""
        self._lifecycle.cleanup()
        self._lifecycle = None
        self._settings_sub = None
        self._settings = None
        self._widget = None
