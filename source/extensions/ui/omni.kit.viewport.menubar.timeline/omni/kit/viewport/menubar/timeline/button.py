from typing import Any, Callable, List, Optional, cast

import carb.settings
import omni.ui as ui
from omni.kit.viewport.menubar.bottom import BG_SIZE, BG_STYLE, BUTTON_SIZE, SPACER_SIZE, VIEWPORT_BOTTOM_MENU_STYLE
from omni.kit.viewport.menubar.core import ViewportMenuItem

SETTINGS_ROOT = "/exts/omni.kit.viewport.menubar.timeline/"
SETTINGS_PATH_TIMELINE_TOGGLE = "/exts/omni.kit.timeline.minibar/visible"
SETTINGS_PATH_MODAL_TOOL_ACTIVE = "/app/tools/modal_tool_active"


# Focused button, has two images to indicate the current focus mode
class TimelineButton(ViewportMenuItem):
    """
    Build a button in viewport bottom menubar:
        Left click: toggle the timeline minibar visibility
    """

    NAME = "Timeline_Toggle"

    class Delegate(ui.MenuDelegate):
        """
        The menu delegate that draws in the menu bar the given icon and
        optionally the text.
        """

        def __init__(
            self,
            images: List[str],
            tooltips: List[str],
            size: int,
            bg_size: int,
            checked: bool = False,
            triggered_fn: Optional[Callable[[], None]] = None,
        ) -> None:
            self._image_widget = None
            self._images = images
            self._tooltips = tooltips
            self._size = size
            self._bg_size = bg_size
            self._checked = checked
            self._triggered_fn = triggered_fn

            super().__init__(propagate=False)

        def build_item(self, _i: ui.MenuItem) -> None:
            with ui.ZStack(width=self._bg_size, height=self._bg_size):
                rc = ui.Rectangle(style=BG_STYLE, width=self._bg_size, height=self._bg_size)
                with ui.HStack():
                    ui.Spacer(width=SPACER_SIZE)
                    with ui.VStack(content_clipping=1):
                        ui.Spacer(height=SPACER_SIZE)
                        self._image_widget = ui.Image(
                            self._images[1] if self._checked else self._images[0],
                            style_type_name_override="Menu.Item.Icon",
                            width=self._size,
                            height=self._size,
                            style=VIEWPORT_BOTTOM_MENU_STYLE,
                        )
                        self._image_widget.checked = self.checked
                # set tooltip when button is initialized
                self._image_widget.set_tooltip(self._tooltips[int(self.checked)])

            if self._triggered_fn:
                rc.set_mouse_released_fn(lambda x, y, b, a: self._on_mouse_released(b))

        @property
        def checked(self) -> bool:
            return self._checked

        @checked.setter
        def checked(self, value: Any) -> None:
            self._checked = value
            idx = 1 if value else 0
            if self._image_widget:
                self._image_widget.source_url = self._images[idx]
                self._image_widget.set_tooltip(self._tooltips[idx])
                self._image_widget.checked = value

        def destroy(self) -> None:
            self._image_widget = None
            self._images.clear()

        def _on_mouse_released(self, button: int) -> None:
            if button == 0:
                if self._triggered_fn and callable(self._triggered_fn):
                    self._triggered_fn()

        def set_tooltip(self, tooltip: str) -> None:
            if self._image_widget:
                self._image_widget.set_tooltip(tooltip)

    def __init__(self, icon_path: str) -> None:
        images = [icon_path + "Play Panel.svg", icon_path + "Play Panel.svg"]
        tooltips = ["Click to show the timeline bar.", "Click to hide the timeline bar."]

        self._delegate = TimelineButton.Delegate(
            images, tooltips, size=BUTTON_SIZE, bg_size=BG_SIZE, triggered_fn=self._on_clicked
        )
        super().__init__(
            name=TimelineButton.NAME,
            delegate=self._delegate,
            order_setting_path=SETTINGS_ROOT + "buttonOrder",
            visible_setting_path=SETTINGS_ROOT + "buttonVisible",
        )

        self._settings = carb.settings.get_settings()
        # To initialize the button state
        self._on_timeline_visibility_changed()
        self._settings_sub = self._settings.subscribe_to_node_change_events(
            SETTINGS_PATH_TIMELINE_TOGGLE, self._on_timeline_visibility_changed
        )
        self._modal_sub = self._settings.subscribe_to_node_change_events(
            SETTINGS_PATH_MODAL_TOOL_ACTIVE, self._on_modal_changed
        )

    def destroy(self) -> None:
        super().destroy()

        if self._delegate is not None:
            self._delegate.destroy()
            self._delegate = cast(TimelineButton.Delegate, None)

        if self._settings_sub:
            self._settings.unsubscribe_to_change_events(self._settings_sub)
            self._settings_sub = None

        if self._modal_sub:
            self._settings.unsubscribe_to_change_events(self._modal_sub)
            self._modal_sub = None

    def _on_clicked(self) -> None:
        value = self._settings.get_as_bool(SETTINGS_PATH_TIMELINE_TOGGLE)
        self._settings.set_bool(SETTINGS_PATH_TIMELINE_TOGGLE, not value)

    def _on_timeline_visibility_changed(self, *_) -> None:
        value = self._settings.get_as_bool(SETTINGS_PATH_TIMELINE_TOGGLE)
        if self._delegate is not None:
            self._delegate.checked = value

    def _on_modal_changed(self, *_) -> None:
        modal_tool_active = self._settings.get_as_bool(SETTINGS_PATH_MODAL_TOOL_ACTIVE)
        self.visible = not modal_tool_active
