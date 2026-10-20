"""
Module for implementing fast navigation functionality in USD Explorer.

This module provides a fast navigation mode for viewport rendering that improves performance
during camera movements.
"""

import asyncio
from typing import Any, List, Optional

import carb.settings
import omni.kit.app
import omni.kit.menu.utils
from carb.eventdispatcher import get_eventdispatcher
from omni.kit.menu.utils import MenuItemDescription, MenuItemOrder
from omni.kit.viewport.utility import get_active_viewport

SETTING_FAST_NAVIGATION = "/renderer/eco_mode_enable"
SETTING_CAMERA_MOVE_STATE = "/renderer/camera_move_state"
SETTING_CAMERA_MOVE_TEST = "/app/renderer/camera_move_test"


class FastNavigation:
    """
    A class that implements fast navigation mode for improved rendering performance during camera movement.

    This class monitors viewport changes and updates rendering settings accordingly to optimize performance
    during navigation.
    """

    def __init__(self) -> None:
        """Initialize FastNavigation with default settings and menu entries."""
        self._settings: carb.settings.ISettings = carb.settings.get_settings()

        # Disable Fast Navigation for https://nvidia-omniverse.atlassian.net/browse/OM-24911
        self._settings.set("/renderer/eco_mode_enable", False)

        self._stop_max: int = self._settings.get(SETTING_CAMERA_MOVE_TEST)
        self._stop_count: int = 0
        self._last_state: bool = False
        self._last_viewport_view: Any = None
        self._last_viewport_projection: Any = None
        self.__update_subscription: Optional[Any] = None
        self._menu_list: List[MenuItemDescription] = []
        self._update_setting: Optional[omni.kit.app.SettingChangeSubscription] = None

        self.__register_menu()
        self._on_change(None, carb.settings.ChangeEventType.CHANGED)

    def destroy(self) -> None:
        """Cleanup resources used by FastNavigation."""
        self.__deregister_menu()
        self._update_setting = None
        self.__update_subscription = None

    def _on_update(self, event: Any) -> None:
        """
        Handle frame update events to track viewport changes.

        Args:
            event: The update event that triggered this callback.
        """
        enabled = self._settings.get(SETTING_FAST_NAVIGATION)
        if not enabled:
            return

        viewport_api = get_active_viewport()
        if not viewport_api:
            return

        if viewport_api.view != self._last_viewport_view or viewport_api.projection != self._last_viewport_projection:
            self._stop_count = 0
            if not self._last_state:
                self._settings.set(SETTING_CAMERA_MOVE_STATE, True)
                self._last_state = True
        else:
            self._stop_count += 1
            if self._stop_count > self._stop_max and self._last_state:
                self._settings.set(SETTING_CAMERA_MOVE_STATE, False)
                self._last_state = False

        self._last_viewport_view = viewport_api.view
        self._last_viewport_projection = viewport_api.projection

    def __register_menu(self) -> None:
        """Register the Fast Navigation menu item."""

        def _on_toggle_fast_navigation() -> None:
            """Toggle the fast navigation mode setting."""
            enabled = self._settings.get(SETTING_FAST_NAVIGATION)
            self._settings.set(SETTING_FAST_NAVIGATION, not enabled)

        self._menu_list = [
            MenuItemDescription(
                name="Fast Navigation",
                ticked=True,
                ticked_fn=lambda: self._settings.get(SETTING_FAST_NAVIGATION),
                onclick_action=_on_toggle_fast_navigation,
                appear_after=MenuItemOrder.FIRST,
            ),
        ]
        omni.kit.menu.utils.add_menu_items(self._menu_list, "Rendering", -4)

        self._update_setting = omni.kit.app.SettingChangeSubscription(SETTING_FAST_NAVIGATION, self._on_change)

    def __deregister_menu(self) -> None:
        """Remove the Fast Navigation menu item."""
        omni.kit.menu.utils.remove_menu_items(self._menu_list, "Rendering")

    def _on_change(self, value: Any, event_type: carb.settings.ChangeEventType) -> None:
        """
        Handle setting change events for fast navigation.

        Args:
            value: The new value of the setting.
            event_type: The type of change event.
        """
        if event_type == carb.settings.ChangeEventType.CHANGED:

            async def __update_menu_async() -> None:
                """Asynchronously update the menus after a setting change."""
                app = omni.kit.app.get_app()
                await app.next_update_async()
                omni.kit.menu.utils.rebuild_menus()

            asyncio.ensure_future(__update_menu_async())

            enabled = self._settings.get(SETTING_FAST_NAVIGATION)
            if enabled:
                # Save current viewport view and projection
                viewport_api = get_active_viewport()
                if viewport_api:
                    self._last_viewport_view = viewport_api.view
                    self._last_viewport_projection = viewport_api.projection
                else:
                    self._last_viewport_view = None
                    self._last_viewport_projection = None

                # Start tracking viewport changes
                if self.__update_subscription is None:
                    self.__update_subscription = get_eventdispatcher().observe_event(
                        observer_name="omni.kit.usd_explorer.render:FastNavigation",
                        event_name=omni.kit.app.GLOBAL_EVENT_UPDATE,
                        on_event=self._on_update,
                    )
            else:
                if self.__update_subscription:
                    self.__update_subscription = None
