"""Toolbar menu builder utilities for constructing context and action menus."""

from typing import Callable

import omni.ui

# pylint: disable=no-member

_MENU_SPACER: int = 5


class ToolbarMenuBuilder:
    """Builds toolbar context menus."""

    def __init__(self, window_name: str) -> None:
        """Initialize the menu builder."""
        self._window_name = window_name
        self._menu = None

    def _ensure_menu(self) -> omni.ui.Menu:
        """Create a fresh menu before populating it.

        OmniUI containers cannot be cleared while a button event is being
        dispatched.  Toolbar menus are opened from button callbacks, so
        replacing the short-lived menu is safer than mutating its children.
        """
        if self._menu:
            self._menu.hide()
        self._menu = omni.ui.Menu("Toolbar Context")
        return self._menu

    def _build_edit_items(self) -> None:
        """Populate the current menu context with Edit section items."""
        from omni.kit.window.preferences import PreferenceBuilder, get_page_list, select_page, show_preferences_window

        window_name = self._window_name

        def show_material_preference() -> None:
            for page in get_page_list():
                if page.get_title() == window_name:
                    show_preferences_window()
                    preference_window = omni.ui.Workspace.get_window(PreferenceBuilder.WINDOW_NAME)
                    if preference_window:
                        select_page(page)
                        preference_window.focus()
                    break

        omni.ui.MenuItem("Preferences...", triggered_fn=show_material_preference)

    def _build_view_items(
        self,
        has_model: bool,
        on_layout: Callable,
        on_frame: Callable,
        on_expansion: Callable = None,
    ) -> None:
        """Populate the current menu context with View section items."""
        omni.ui.MenuItem("Auto Layout Nodes", triggered_fn=on_layout, enabled=has_model, hotkey_text="Ctrl+L")
        omni.ui.Spacer(height=omni.ui.Pixel(_MENU_SPACER))
        omni.ui.MenuItem("Frame Nodes", triggered_fn=on_frame, enabled=has_model, hotkey_text="F")
        if on_expansion:
            omni.ui.Spacer(height=omni.ui.Pixel(_MENU_SPACER))
            with omni.ui.Menu("Expansion State"):
                omni.ui.MenuItem(
                    "Expand All", triggered_fn=lambda: on_expansion("open"), enabled=has_model, hotkey_text="1"
                )
                omni.ui.Spacer(height=omni.ui.Pixel(_MENU_SPACER))
                omni.ui.MenuItem(
                    "Minimize All", triggered_fn=lambda: on_expansion("minimized"), enabled=has_model, hotkey_text="2"
                )
                omni.ui.Spacer(height=omni.ui.Pixel(_MENU_SPACER))
                omni.ui.MenuItem(
                    "Close All", triggered_fn=lambda: on_expansion("closed"), enabled=has_model, hotkey_text="3"
                )

    def show_edit_menu(self) -> None:
        """Show the standalone edit menu."""
        menu = self._ensure_menu()
        with menu:
            self._build_edit_items()
        menu.show()

    def show_view_menu(
        self,
        has_model: bool,
        on_layout: Callable,
        on_frame: Callable,
        on_expansion: Callable = None,
    ) -> None:
        """Show the standalone view menu."""
        menu = self._ensure_menu()
        with menu:
            self._build_view_items(has_model, on_layout, on_frame, on_expansion)
        menu.show()

    def show_overflow_menu(
        self,
        has_model: bool,
        on_layout: Callable,
        on_frame: Callable,
        on_expansion: Callable = None,
        on_help: Callable = None,
    ) -> None:
        """Show combined Edit + View + Help overflow menu."""
        menu = self._ensure_menu()
        with menu:
            with omni.ui.Menu("Edit"):
                self._build_edit_items()
            omni.ui.Spacer(height=omni.ui.Pixel(_MENU_SPACER))
            with omni.ui.Menu("View"):
                self._build_view_items(has_model, on_layout, on_frame, on_expansion)
            if on_help:
                omni.ui.Spacer(height=omni.ui.Pixel(_MENU_SPACER))
                omni.ui.MenuItem("Help / Documentation", triggered_fn=on_help)
        menu.show()
