import asyncio
from enum import IntEnum
from typing import Dict, Optional

import carb
import carb.input
import carb.settings
import omni.kit.app
import omni.ui as ui
from omni.kit.viewport.menubar.core.viewport_menu_model import AbstractViewportMenuItem, ViewportMenuModel

from ..constant import NAVIGATION_IS_LARGE, NAVIGATION_LARGE_SIZE, NAVIGATION_SMALL_SIZE
from ..navigation_tooltip import ViewportNavigationTooltip
from ..style import BUTTON_RECT_STYLE


class MouseKey(IntEnum):
    NONE = -1
    LEFT = 0
    RIGHT = 1
    MIDDLE = 2


class ViewportNavigationButton(AbstractViewportMenuItem):
    """
    Build a button in navigation menubar:
        true_image: show in button when the state is true
        false_image: show in button when the state is false
    """

    def __init__(
        self,
        name,
        size,
        visible_setting_path: Optional[str] = None,
        order_setting_path: Optional[str] = None,
        state=True,
        clicked_fn=None,
        auto_spin=True,
        build_tooltip_fn=lambda: (0, 0),
        show_label=True,
        has_triangle=False,
        build_menu_fn=None,
        build_window_fn=None,
        style={},
        alignment=ui.Alignment.LEFT_BOTTOM,
    ):
        self._name = name
        self._label = ""
        self._state = state
        self._on_clicked_fn = clicked_fn
        self._auto_spin = auto_spin
        self._size = size
        self._style = style
        self._has_triangle = has_triangle
        self._build_menu_internal = build_menu_fn
        self._build_window_fn = build_window_fn
        self._triangle_size = 6
        self._menu = None
        self._window = None
        self._alignment = alignment
        self._settings = carb.settings.get_settings()
        self._is_large = self._settings.get(NAVIGATION_IS_LARGE)
        if self._is_large:
            self._size = self._settings.get(NAVIGATION_LARGE_SIZE)
        else:
            self._size = self._settings.get(NAVIGATION_SMALL_SIZE)
        self._bkground_widget = None
        self._highlight_widget = None
        self._image_widget = None
        # OM-70677's comment: should give a larger space for a longer name label
        if len(self._name) > 8:
            self._width = self._size + 10
        elif len(self._name) > 7:
            self._width = self._size + 8
        else:
            self._width = self._size

        self._input = carb.input.acquire_input_interface()
        self._build_tooltip_fn = build_tooltip_fn
        self._show_label = show_label
        self._show_menu_task = None
        self._left_click_blocker = False

        super().__init__(
            name,
            visible_setting_path=visible_setting_path,
            order_setting_path=order_setting_path,
        )
        # When visible and order changed, trigger UI updates
        self._visible_sub = self.visible_model.subscribe_value_changed_fn(lambda m: self._invalidate())
        self._order_sub = self.order_model.subscribe_value_changed_fn(lambda m: self._invalidate())

        self._size_setting = omni.kit.app.SettingChangeSubscription(NAVIGATION_IS_LARGE, self._on_size_change)

    def _on_size_change(self, value, event_type) -> None:
        if event_type == carb.settings.ChangeEventType.CHANGED:
            is_large = self._settings.get(NAVIGATION_IS_LARGE)
            if is_large:
                self._size = self._settings.get(NAVIGATION_LARGE_SIZE)
                self._show_label = True
            else:
                self._size = self._settings.get(NAVIGATION_SMALL_SIZE)
                self._show_label = False

    def build_fn(self, factory: Dict):
        """Reimplement it to have own customized item"""

        padding_x = 2
        padding_y = 2
        self._width_container = ui.VStack(width=self._width)
        with self._width_container:
            with ui.HStack(width=self._width):
                # ui.Alignment.H_CENTER not works well for ZStack
                ui.Spacer()
                self._container = ui.ZStack(
                    spacing=0,
                    width=self._size,
                    height=self._size,
                    opaque_for_mouse_events=False,
                    alignment=ui.Alignment.H_CENTER,
                )
                ui.Spacer()
            if self._show_label:
                self._label = self._name if not self._label else self._label
                self._label_widget = ui.Label(self._label.title(), alignment=ui.Alignment.H_CENTER)
        with self._container:
            if self._has_triangle:
                with ui.VStack():
                    with ui.HStack():
                        ui.Spacer()
                        with ui.VStack(width=self._triangle_size):
                            ui.Spacer()
                            ui.Triangle(
                                width=self._triangle_size,
                                height=self._triangle_size,
                                alignment=ui.Alignment.RIGHT_TOP,
                                style_type_name_override="MenuBar.Item.Triangle",
                            )
                        ui.Spacer(width=2)
                    ui.Spacer(height=2)
            self._bkground_widget = ui.Rectangle(
                name="nv_button",
                width=self._size,
                height=self._size,
                mouse_pressed_fn=(lambda x, y, key, m: self._on_mouse_pressed(x, y, key)),
                mouse_released_fn=(lambda x, y, key, m: self._on_mouse_released(x, y, key)),
                mouse_hovered_fn=self._on_mouse_hovered,
                opaque_for_mouse_events=False,
                style=BUTTON_RECT_STYLE,
            )

            self._highlight_widget = ui.Rectangle(
                name="nv_highlight",
                width=self._size,
                height=self._size,
                style={**BUTTON_RECT_STYLE, **self._style},
            )

            self._image_widget = ui.Button(
                name=self._name,
                width=self._size,
                height=self._size,
                checked=self._state,
                style=self._style,
                fill_policy=ui.FillPolicy.STRETCH,
                style_type_name_override="Navigation.Button",
            )

    def _build_menu(self):
        self._menu = ui.Menu("Button_Menu_" + str(hash(self)), menu_compatibility=False, style=self._style)
        with self._menu:
            self._menu_items = self._build_menu_internal()

    def invalidate(self):
        if self._menu:
            self._menu.invalidate()

    def destroy(self):
        self._image_widget = None
        self._size_setting = None
        self._visible_sub = None
        self._order_sub = None
        self._onclick_fn = None
        self._show_menu_task = None
        self._left_click_blocker = None
        if self._menu:
            self._menu.hide()
            self._menu = None
        if self._window:
            self._window.visible = False
            self._window = None
        super().destroy()

    @property
    def hotkey(self) -> Optional[str]:
        return None

    @property
    def tooltip(self) -> Optional[str]:
        return None

    @property
    def visible(self) -> bool:
        return self.visible_model.as_bool

    @visible.setter
    def visible(self, value: bool) -> None:
        self.visible_model.set_value(value)
        if self._menu:
            self._menu.hide()

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self.set_state(value)

    @property
    def screen_position_x(self):
        return self._bkground_widget.screen_position_x

    @property
    def screen_position_y(self):
        return self._bkground_widget.screen_position_y

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._bkground_widget.computed_height

    @property
    def auto_spin(self):
        return self._auto_spin

    @auto_spin.setter
    def auto_spin(self, value):
        self._auto_spin = value

    @property
    def enabled(self):
        return self._container.enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._container.enabled = value
        if not value:
            self.state = False

    @property
    def menu_item(self) -> ui.Menu:
        return self._menu

    @property
    def window(self) -> ui.Window:
        return self._window

    @property
    def label(self) -> str:
        return self._label

    @label.setter
    def label(self, value: str) -> None:
        async def _update_label(value):
            self._label = value
            self._label_widget.text = self._label
            self.visible = False
            self.visible = True
            await omni.kit.app.get_app().next_update_async()

        asyncio.ensure_future(_update_label(value))

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        # OM-76364 - The capture button label only refereshes on View mode change. Setting to be static "Capture".
        async def _update_image(value):
            self._name = value
            self.visible = False
            self.visible = True
            await omni.kit.app.get_app().next_update_async()

        if self._image_widget:
            self._image_widget.name = value

        asyncio.ensure_future(_update_image(value))

    @property
    def checked(self) -> bool:
        return self._checked

    @checked.setter
    def checked(self, value: bool) -> None:
        self._checked = value
        if self._image_widget:
            self._image_widget.checked = value
        if self._highlight_widget:
            self._highlight_widget.checked = value

    @property
    def style(self):
        return self._style

    @style.setter
    def style(self, value):
        self._style.clear()
        self._style.update(value)
        if self._image_widget:
            self._image_widget.style = self._style

    def _on_mouse_pressed(self, x, y, key):
        self._left_click_blocker = False
        if not self.enabled:
            return
        if key == MouseKey.RIGHT:
            self._left_click_blocker = True
            self.on_right_clicked_fn()
        if key == MouseKey.LEFT:
            self._show_menu_task = asyncio.ensure_future(self._schedule_show_menu())

    def _on_mouse_released(self, x, y, key):
        if key == MouseKey.LEFT and self._show_menu_task:
            self._show_menu_task.cancel()
        if not self._left_click_blocker:
            if self._auto_spin:
                self.set_state(not self._state)
            if self._on_clicked_fn:
                self._on_clicked_fn(self._state)
            ViewportNavigationTooltip.hide(self._name)
        self._left_click_blocker = False

    async def _schedule_show_menu(self):
        await asyncio.sleep(0.3)
        self.on_right_clicked_fn()
        self.show_menu_task = None
        self._left_click_blocker = True

    def on_right_clicked_fn(self):
        """Show flyout window/menu"""
        if self._build_menu_internal:
            self._show_menu()
        elif self._build_window_fn:
            self._show_window()

    def _show_menu(self):
        if self._menu is None:
            self._build_menu()

        x, y = (0, 0)
        if self._alignment == ui.Alignment.RIGHT_BOTTOM:
            x = self._container.screen_position_x + self._container.computed_content_width
            y = self._container.screen_position_y + self._container.computed_content_height

            if self._menu_items:
                menu_window_width = self._menu_items[0].computed_content_width
                if menu_window_width <= 0:
                    self._menu.show_at(-500, -100)
                    self._menu.hide()

                    async def __delay_change_menu_window_position(x, y):
                        await omni.kit.app.get_app().next_update_async()
                        x -= self._menu_items[0].computed_content_width
                        self._menu.show_at(x, y)

                    asyncio.ensure_future(__delay_change_menu_window_position(x, y))
                    return
                else:
                    x -= self._menu_items[0].computed_content_width

        elif self._alignment == ui.Alignment.LEFT_BOTTOM:
            x = self._container.screen_position_x
            y = self._container.screen_position_y + self._container.computed_content_height

        self._menu.show_at(x, y)

    def _show_window(self):
        if self._window is None:
            self._window = self._build_window_fn()

        x, y = (0, 0)
        if self._alignment == ui.Alignment.RIGHT_BOTTOM:
            x = self._container.screen_position_x + self._container.computed_content_width
            y = self._container.screen_position_y + self._container.computed_content_height

            if self._window:
                window_width = self._window.frame.computed_width
                if window_width <= 0:
                    self._window.position_x = -500
                    self._window.position_y = -100
                    self._window.visible = True

                    async def __delay_change_window_position(x, y):
                        while self._window.frame.computed_width <= 0:
                            await omni.kit.app.get_app().next_update_async()
                        x -= self._window.frame.computed_width
                        self._window.position_x = x
                        self._window.position_y = y
                        self._window.visible = True

                    asyncio.ensure_future(__delay_change_window_position(x, y))
                    return
                else:
                    x -= window_width

        elif self._alignment == ui.Alignment.LEFT_BOTTOM:
            x = self._container.screen_position_x
            y = self._container.screen_position_y + self._container.computed_content_height

        # Markup and waypoint list window should not change their position
        else:
            self._window.visible = True
            return

        self._window.position_x = x
        self._window.position_y = y
        self._window.visible = True

    def _on_mouse_hovered(self, hovered):
        if hovered:
            flags = self._input.get_mouse_button_flags(None, carb.input.MouseInput.LEFT_BUTTON)
            if (flags & (carb.input.BUTTON_FLAG_DOWN | carb.input.BUTTON_FLAG_PRESSED)) == 0:
                ViewportNavigationTooltip.show(self, self._name, self._build_tooltip_fn)
        else:
            ViewportNavigationTooltip.hide(self._name)

    def set_state(self, state):
        self._state = state
        if self._image_widget:
            self._image_widget.checked = state

    def set_highlight(self, state):
        if self._highlight_widget:
            self._highlight_widget.checked = state

    def _invalidate(self) -> None:
        ViewportMenuModel()._item_changed(None)
