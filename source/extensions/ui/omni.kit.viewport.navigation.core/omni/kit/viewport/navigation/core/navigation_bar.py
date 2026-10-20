import asyncio
from contextlib import suppress

import carb.settings
import omni.kit.app
import omni.ui as ui
from omni.kit.viewport.menubar.core import ViewportMenubar, ViewportMenuItem
from omni.kit.viewport.menubar.core.viewport_menu_model import ViewportMenuModel

from .constant import (
    NAVIGATION_COMPUTED_WIDTH,
    NAVIGATION_IS_LARGE,
    NAVIGATION_IS_VISIBLE,
    NAVIGATION_TOOL_BOTTOM_OFFSET,
    NAVIGATION_TOOL_BOTTOM_SPACING,
    SETTINGS_PATH_MODAL_TOOL_ACTIVE,
    SETTINGS_ROOT,
    VIEWPORT_TOOLS_BOTTOM_OFFSET_PATH,
)
from .navigation_tooltip import ViewportNavigationTooltip
from .style import BOTTOMBAR_STYLE, WINDOW_STYLE

__all__ = ["NavigationBar"]


PANEL_PADDING_X = 4
PANEL_PADDING_Y = 4
LABEL_HEIGHT = 18


class ViewportMenuBlank(ViewportMenuItem):
    """A simple spacer with fixed width"""

    def __init__(self, order_setting_path: str):
        super().__init__(order_setting_path=order_setting_path)

    def build_fn(self, factory):
        pass

    @property
    def computed_width(self) -> float:
        return PANEL_PADDING_X

    @property
    def width(self) -> float:
        return PANEL_PADDING_X


class WindowClientRect:
    def __init__(self):
        style = {"Rectangle::position": {"background_color": 0x00000000, "border_width": 0, "border_radius": 0}}
        with ui.Placer(offset_x=0, offset_y=0, draggable=False, style=style):
            self._position = ui.Rectangle(name="position", width=ui.Percent(100), height=ui.Percent(100), style=style)

    @property
    def left(self):
        return self._position.screen_position_x

    @property
    def top(self):
        return self._position.screen_position_y

    @property
    def width(self):
        w = self._position.computed_width - 4
        return w

    @property
    def height(self):
        return self._position.computed_height


class NavigationBar(ViewportMenubar):
    def __init__(self, name: str, spacing: int = 5):
        self._settings = carb.settings.get_settings()
        self._spacing = spacing
        self._menu_items = []
        self._factory = {}
        self._hide_title = self._settings.get(NAVIGATION_IS_LARGE)
        self._panel_stack = None
        self._create_from_toolbar_menu = False
        super().__init__(name, direction=ui.Direction.LEFT_TO_RIGHT, spacing=spacing, style=BOTTOMBAR_STYLE)
        self._size_setting = omni.kit.app.SettingChangeSubscription(NAVIGATION_IS_LARGE, self._on_size_change)
        self._visible_sub = self.visible_model.subscribe_value_changed_fn(lambda m: self._invalidate())
        self._visibility_sub = self._settings.subscribe_to_node_change_events(
            NAVIGATION_IS_VISIBLE, self._on_visibility_changed
        )
        self._modal_sub = self._settings.subscribe_to_node_change_events(
            SETTINGS_PATH_MODAL_TOOL_ACTIVE, self._on_modal_changed
        )
        self._bottom_offset_sub = self._settings.subscribe_to_node_change_events(
            VIEWPORT_TOOLS_BOTTOM_OFFSET_PATH, self._bottom_offset_changed
        )
        with self:
            # At the right most (order = 1000), put a blank item
            # This is used to ensure that we have a spacing at the right most.
            setting_path = SETTINGS_ROOT + "rightSpacingOrder"
            carb.settings.get_settings().set_int(setting_path, 1200)
            ViewportMenuBlank(order_setting_path=setting_path)
        # set initial visibility depending on modal setting and nav bar visible setting
        self._modal_tool_active = self._settings.get_as_bool(SETTINGS_PATH_MODAL_TOOL_ACTIVE) or False
        visible = self._settings.get_as_bool(NAVIGATION_IS_VISIBLE) and not self._modal_tool_active
        self.visible_model.set_value(visible)
        self._settings.set_bool(NAVIGATION_IS_VISIBLE, visible)
        self._visible_if_no_modal = visible

    def destroy(self):
        self._visible_sub = None
        if self._visibility_sub:
            self._settings.unsubscribe_to_change_events(self._visibility_sub)
            self._visibility_sub = None
        if self._modal_sub:
            self._settings.unsubscribe_to_change_events(self._modal_sub)
            self._modal_sub = None
        if self._bottom_offset_sub:
            self._settings.unsubscribe_to_change_events(self._bottom_offset_sub)
            self._bottom_offset_sub = None
        super().destroy()

    def _invalidate(self):
        ViewportMenuModel()._item_changed(None)

    def _on_size_change(self, value, event_type) -> None:
        if event_type == carb.settings.ChangeEventType.CHANGED:
            self._hide_title = self._settings.get(NAVIGATION_IS_LARGE)
            self.rebuild()

    def _init_x(self, *args):
        if not self._panel_stack:
            return
        if self._navigation_frame.computed_width > self._panel_stack.computed_width:
            offset_x = (self._navigation_frame.computed_width - self._panel_stack.computed_width) / 2
            self._panel_placer.offset_x = offset_x

    def _init_y(self, *args):
        if not self._panel_stack:
            return
        bottom_offset = self._settings.get(VIEWPORT_TOOLS_BOTTOM_OFFSET_PATH)
        bottom_offset = bottom_offset if bottom_offset is not None else 0
        bottom_spacing = self._settings.get(NAVIGATION_TOOL_BOTTOM_SPACING)
        if bottom_offset > 0 and bottom_spacing is not None:
            bottom_offset = bottom_offset + bottom_spacing
        bottom_blank = self._settings.get(NAVIGATION_TOOL_BOTTOM_OFFSET) + bottom_offset

        if self._navigation_frame.computed_height > self._panel_stack.computed_height + bottom_blank:
            self._panel_placer.offset_y = (
                self._navigation_frame.computed_height - self._panel_stack.computed_height - bottom_blank
            )

    def _on_computed_content_size_changed(self):
        async def __delay_set_offset():
            # OMFP-3379: _bottom_offset_changed before nav panel build
            if not self._panel_stack:
                return
            self._init_x()
            self._init_y()
            self._settings.set(NAVIGATION_COMPUTED_WIDTH, self._panel_stack.computed_content_width)

        asyncio.ensure_future(__delay_set_offset())

    def _on_visibility_changed(self, event_item, _event_type) -> None:
        if bool(event_item.get_dict()):
            self.show()
            return
        self.hide()

    def _on_modal_changed(self, *_) -> None:
        modal_tool_active = self._settings.get_as_bool(SETTINGS_PATH_MODAL_TOOL_ACTIVE)
        if self._modal_tool_active == modal_tool_active:
            # callback is also called when the same value is set
            return
        self._modal_tool_active = modal_tool_active
        if modal_tool_active:
            self._visible_if_no_modal = self.visible_model.as_bool
            self.hide()
        elif self._visible_if_no_modal:
            self.show()

    def _bottom_offset_changed(self, event_item, _event_type) -> None:
        self._on_computed_content_size_changed()

    def _check_pos_x(self, x_len):
        x = float(x_len)
        if x < 0:
            self._panel_placer.offset_x = 0
        if x + self._panel_stack.computed_width > self._navigation_frame.computed_width:
            self._panel_placer.offset_x = max(
                self._navigation_frame.computed_width - self._panel_stack.computed_width, 0
            )

    def _check_pos_y(self, y_len):
        y = float(y_len)
        if y < 0:
            self._panel_placer.offset_y = 0
        if y + self._panel_stack.computed_height > self._navigation_frame.computed_height:
            self._panel_placer.offset_y = max(
                self._navigation_frame.computed_height - self._panel_stack.computed_height, 0
            )

    def rebuild(self):
        if self._navigation_frame:
            asyncio.ensure_future(self.rebuild_async())
            self._on_computed_content_size_changed()

    async def rebuild_async(self):
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        self._panel_stack.clear()
        with self._panel_stack:
            ui.Rectangle(name="background", width=self.compute_bar_width(self._menu_items))
            with ui.VStack():
                if not self._hide_title:
                    self._title = ui.HStack()
                    with self._title:
                        ui.Rectangle(height=15)
                        # TODO: add close button here
                else:
                    ui.Rectangle(name="window_dimension", height=5)
                super().build_fn(self._menu_items, self._factory)
                ui.Rectangle(name="window_dimension", height=5)
        self._init_x()
        self._init_y()

    def hide(self):
        # OM-61703: when invisible the nav bar, disable turntable when turntable in navigation bar
        with suppress(ModuleNotFoundError):
            from omni.kit.tool.turntable import TURNTABLE_ACTIVATED_PATH
            from omni.kit.tool.turntable import get_instance as get_turntable_instance

            # close the turntable window if it active
            self._turntable_instance = get_turntable_instance()
            if self._turntable_instance and self._settings.get(TURNTABLE_ACTIVATED_PATH):
                self._turntable_instance.swap_state()
            # clear the turntable button state in nav bar
            self._settings.set(TURNTABLE_ACTIVATED_PATH, False)

        if self.visible_model.as_bool:
            self.visible_model.set_value(False)
            self._settings.set(NAVIGATION_IS_VISIBLE, False)

    def show(self):
        if not self.visible_model.as_bool:
            self.visible_model.set_value(True)
            self._settings.set(NAVIGATION_IS_VISIBLE, True)

    def create_from_toolbar_menu(self, value):
        self._create_from_toolbar_menu = value

    def build_fn(self, menu_items, factory):
        self._menu_items = menu_items
        self._factory = factory
        if len(menu_items) == 1:
            # OMPE-30520: that means there only one ViewportMenuBlank item, should not build the navigation bar
            return
        self._navigation_frame = ui.Frame(witdth=ui.Percent(100), identifier="_navigation_bar_frame")
        self._navigation_frame.set_computed_content_size_changed_fn(self._on_computed_content_size_changed)

        with self._navigation_frame:
            panel_draggable = True
            with ui.ZStack(width=ui.Percent(100), height=ui.Percent(100), spacing=0):
                self._window_rect = WindowClientRect()
                self._panel_placer = ui.Placer(
                    offset_x=0,
                    offset_y=0,
                    height=0,
                    width=0,
                    draggable=panel_draggable,
                    drag_axis=ui.Axis.XY,
                    stable_size=True,
                )
                with self._panel_placer:
                    self._panel_stack = ui.ZStack(width=0, height=0, spacing=0)
                    self._panel_stack.set_mouse_hovered_fn(
                        lambda hov: self._settings.set_bool("/exts/omni.kit.viewport.navigation.core/hovered", hov)
                    )
                ViewportNavigationTooltip.create(
                    PANEL_PADDING_Y + 1, PANEL_PADDING_Y * 2 + 1 + LABEL_HEIGHT, self._window_rect
                )
                ViewportNavigationTooltip.set_visible(False)
                self._panel_placer.set_offset_x_changed_fn(self._check_pos_x)
                self._panel_placer.set_offset_y_changed_fn(self._check_pos_y)
            self._panel_stack.set_style(WINDOW_STYLE)
            if self._create_from_toolbar_menu:
                self._navigation_frame.visible = False
                return
            with self._panel_stack:
                ui.Rectangle(name="background", width=self.compute_bar_width(menu_items))
                with ui.VStack():
                    if not self._hide_title:
                        self._title = ui.HStack()
                        with self._title:
                            ui.Rectangle(height=15)
                            # TODO: add close button here
                    else:
                        ui.Rectangle(name="window_dimension", height=8)
                    with ui.HStack():
                        ui.Spacer(width=8)
                        super().build_fn(menu_items, factory)
                        ui.Spacer(width=8)
                    ui.Rectangle(name="window_dimension", height=8)

    def build_menu_items(self):
        super().build_fn(self._menu_items, self._factory)

    def compute_bar_width(self, items) -> int:
        if self._direction == ui.Direction.TOP_TO_BOTTOM:
            return 50
        return sum([item.width + 4 for item in items if item.visible]) + 16


def get_navigation_bar_name():
    """Get the bottom bar name if there is an instance of bottom bar"""
    return Extension.NAVIGATION_BAR_NAME
