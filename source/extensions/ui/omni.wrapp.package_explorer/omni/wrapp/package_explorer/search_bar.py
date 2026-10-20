import asyncio
from typing import Callable, Optional

import omni.kit.app
from omni import ui
from omni.kit.browser.core import BrowserSearchBar
from omni.kit.widget.searchfield import SearchField

from .style import ICON_PATH, UI_STYLES
from .utils import REFRESH_ANIMATION_TIMEOUT, call_async


class WrappBrowserSearchBar(BrowserSearchBar):
    """
    Represent a search bar for browser widget.
    Keyword args:
        enable_navigation_visibility (bool): True to show navigation butoon, False to hide. Default True.
        options_menu (Optional[OptionsMenu]): Options menu displayed when option button clicked. If None, no option button displayed. Default is standard options menu.
        style (Dict): Extra ui style for search bar. Default is empty.
        subscribe_edit_changed (bool): Default True to search when input changed. False only search when input ended.
    """

    def __init__(
        self,
        enable_navigation_visibility: bool = True,
        style={},
        subscribe_edit_changed=True,
        refresh_browser_fn: Optional[Callable[[], None]] = None,
        open_settings_fn: Optional[Callable[[], None]] = None,
        browser_widget: Optional["WrappBrowserWidget"] = None,
    ):
        """Initialize the WrappBrowserSearchBar"""
        self._refresh_browser_fn = refresh_browser_fn
        self._open_settings_fn = open_settings_fn
        self._rotate_future = None
        self._keep_rotating = False
        self._refresh_transform = None
        self._refresh_container = None
        self._browser_widget = browser_widget
        self._browser_model = browser_widget.model if browser_widget else None

        super().__init__(
            enable_navigation_visibility=enable_navigation_visibility,
            style=style,
            subscribe_edit_changed=subscribe_edit_changed,
        )
        if self._browser_model:
            self._browser_model.set_start_refreshing_callback_fn(self._start_rotation_animation, "search_bar_refresh")

    def _build_ui(self):
        self._frame = ui.Frame(style=UI_STYLES)
        with self._frame:
            with ui.HStack(spacing=4, height=0, style=self._extra_ui_style):

                if self._enable_navigation_visibility:
                    with ui.VStack(width=26):
                        ui.Spacer()
                        self._show_navigation_button = ui.Button(
                            image_width=20,
                            image_height=20,
                            width=26,
                            height=26,
                            spacing=2,
                            selected=self._navigation_visible,
                            name="navigation",
                            clicked_fn=self._trigger_show_navigation,
                            style_type_name_override="SearchBar.Button",
                            tooltip="Show/Hide Repository Navigation Tree",
                        )
                        ui.Spacer()

                self._search_field = SearchField(
                    on_search_fn=self._on_search,
                    subscribe_edit_changed=self._subscribe_edit_changed,
                    style=self._extra_ui_style,
                )

                with ui.VStack(width=26):
                    ui.Spacer()
                    self._refresh_container = ui.ZStack(width=26, height=26)
                    with self._refresh_container:
                        self._refresh_button = ui.Button(
                            image_width=20,
                            image_height=20,
                            width=26,
                            height=26,
                            name="refresh",
                            clicked_fn=self._refresh_browser,
                            style_type_name_override="SearchBar.Button",
                            tooltip="Refresh Package Explorer",
                        )
                        # Animated refresh icon using SceneView
                        with ui.scene.SceneView(width=26, height=26).scene:
                            self._refresh_transform = ui.scene.Transform()
                            with self._refresh_transform:
                                ui.scene.Image(f"{ICON_PATH}/refresh.svg", width=1.4, height=1.4)
                    ui.Spacer()

                with ui.VStack(width=26):
                    ui.Spacer()
                    self._options_button = ui.Button(
                        image_width=20,
                        image_height=20,
                        width=26,
                        height=26,
                        name="settings",
                        clicked_fn=self._open_settings,
                        style_type_name_override="SearchBar.Button",
                        tooltip="Open Package Explorer Settings",
                    )
                    ui.Spacer()

    def _refresh_browser(self) -> None:
        if self._refresh_browser_fn:
            self._refresh_browser_fn()

    def _open_settings(self) -> None:
        if self._open_settings_fn:
            self._open_settings_fn()

    def _enable_refresh_button(self, enabled: bool):
        self._refresh_button.enabled = enabled
        self._refresh_button.tooltip = "Refresh Package Explorer" if enabled else "Refreshing..."

    def _start_rotation_animation(self):
        """Start the spinning animation."""
        self._keep_rotating = True
        if self._rotate_future:
            return  # Already animating

        async def _rotate():
            self._enable_refresh_button(False)
            angle = [0]
            elapsed_time = 0.0
            max_rotation_time = REFRESH_ANIMATION_TIMEOUT  # Maximum rotation time in seconds
            while self._keep_rotating:
                delta = await omni.kit.app.get_app().next_update_async()
                angle[0] -= delta * 3.0
                elapsed_time += delta
                transform = ui.scene.Matrix44.get_rotation_matrix(0, 0, angle[0])
                self._refresh_transform.transform = transform

                if self._browser_model and not self._browser_model.is_in_traversing():
                    break

                # Stop animation if max rotation time exceeded
                if elapsed_time >= max_rotation_time:
                    break
            self._stop_rotation_animation()

        self._rotate_future = call_async(_rotate())

    def _stop_rotation_animation(self):
        """Stop the spinning animation."""
        self._enable_refresh_button(True)
        self._keep_rotating = False
        self._rotate_future = None
        # Reset rotation to identity
        if self._refresh_transform:
            self._refresh_transform.transform = ui.scene.Matrix44.get_rotation_matrix(0, 0, 0)

    async def _stop_after_delay(self, delay: float = 0):
        """Stop animation after a delay (use if refresh doesn't have callback)."""
        await asyncio.sleep(delay)
        self._stop_rotation_animation()
