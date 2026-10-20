"""Controller that manages context-switcher state for render contexts."""

from typing import Optional

import omni.kit.app
import omni.ui

from ....config.logging import logger
from ....utils.lifecycle_registry import LifecycleRegistry

# pylint: disable=no-member


class ContextSwitcherController:
    """Handles context switching state. Tabs are rendered by the graph toolbar."""

    def __init__(self, widget: object, context_manager: object) -> None:
        """Initialize context switcher state."""
        self._widget = widget
        self._context_manager = context_manager
        self._lifecycle = LifecycleRegistry()

    @property
    def use_context_tabs(self) -> bool:
        """Context tabs are always enabled."""
        return True

    def refresh_tabs(self) -> None:
        """Refresh context UI by rebuilding the graph toolbar on the next frame."""
        if not self._widget:
            return

        async def _refresh_async() -> None:
            await omni.kit.app.get_app().next_update_async()
            if self._widget:
                self._widget.rebuild_graph_toolbar()

        self._lifecycle.add_task(_refresh_async())

    def destroy(self) -> None:
        """Release resources."""
        self._lifecycle.cleanup()
        self._lifecycle = None
        self._context_manager = None
        self._widget = None
