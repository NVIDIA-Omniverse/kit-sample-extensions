"""Controller for reading/writing graph-widget visual and behavior settings."""

from typing import Any, Optional, Tuple  # _tree_item, _changed_item, _event_type: carb settings

import carb.settings
from pxr import UsdUI

from ....settings.settings import Settings
from ....utils.lifecycle_registry import LifecycleRegistry

# pylint: disable=no-member


class GraphSettingsController:
    """Observes graph settings and exposes drop behavior helpers."""

    def __init__(self, widget: object) -> None:
        """Initialize and register settings subscriptions used to drive graph behavior."""
        self._widget = widget
        self._settings = carb.settings.get_settings()
        self._lifecycle = LifecycleRegistry()
        for key in (
            Settings.PREVIEW_TEXTURE_INPUT,
            Settings.COLOR_NOODLES,
            Settings.CONFINE_NODEGRAPHS,
            Settings.CONFINE_BACKDROPS,
            Settings.FORCE_CONNECT,
        ):
            sub = self._settings.subscribe_to_tree_change_events(key, self._on_setting_changed)
            self._lifecycle.add_unsubscribe(sub, "unsubscribe_to_tree_change_events")

    def _on_setting_changed(self, _tree_item: Any, _changed_item: Any, _event_type: Any) -> None:
        """Handle settings changes by refreshing the model."""
        if self._widget:
            self._widget.request_model_refresh()

    def _get_position_key(self) -> str:
        """Return the position custom data key for the context."""
        return f"omni:{UsdUI.Tokens.uiNodegraphNodePos}:{self._widget.current_context}"

    def get_backdrop_drop_settings(self) -> Tuple[Optional[str], Optional[str]]:
        """Return (position_key, visibility) for backdrop drops."""
        if not Settings.confine_backdrops():
            return None, None
        return self._get_position_key(), self._widget.current_context

    def get_nodegraph_drop_settings(self) -> Tuple[Optional[str], Optional[str]]:
        """Return (position_key, visibility) for nodegraph drops."""
        if not Settings.confine_nodegraphs():
            return None, None
        return self._get_position_key(), self._widget.current_context

    def destroy(self) -> None:
        """Unsubscribe from settings and release references."""
        if self._lifecycle:
            self._lifecycle.cleanup()
            self._lifecycle = None
        self._settings = None
        self._widget = None
