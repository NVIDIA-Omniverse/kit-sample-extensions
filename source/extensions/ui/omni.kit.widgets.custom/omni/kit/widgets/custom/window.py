# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
from typing import Tuple, Union

import carb
import carb.input
from omni import ui
from omni.kit.menu.utils import MenuItemDescription

from .constant import *
from .rectangle import *
from .style import DefaultWidgetStyle, get_ui_style
from .utils import get_icon_path, merge_dicts
from .widgets import *


class Rect:
    def __init__(self, left, width, top, height):
        self._left = left
        self._right = left + width
        self._top = top
        self._bottom = top + height

    def is_inside(self, x, y):
        if x < self._left:
            return False
        if x > self._right:
            return False
        if y < self._top:
            return False
        if y > self._bottom:
            return False
        return True

    @property
    def left(self):
        return self._left

    @property
    def top(self):
        return self._top

    @property
    def right(self):
        return self._right

    @property
    def bottom(self):
        return self._bottom

    @property
    def width(self):
        return self._right - self._left

    @property
    def height(self):
        return self._bottom - self._top


class WindowRect(Rect):
    def __init__(self, window: ui.Window):
        width = window.width
        height = window.height
        if width == 0:
            # TODO: here is a work around for window width is 0.
            width = window.frame.computed_width
        if height == 0:
            # TODO: here is a work around for window height is 0.
            height = window.frame.computed_height
        super().__init__(window.position_x, width, window.position_y, height)


class WidgetRect(Rect):
    def __init__(self, widget: ui.Widget):
        super().__init__(
            widget.screen_position_x, widget.computed_width, widget.screen_position_y, widget.computed_height
        )


class PopupWindow(ui.Window):
    def __init__(self, title: str, *args, **kwargs):
        # Init the variabe, holds the subscription returned handle
        self._input = carb.input.acquire_input_interface()
        self._input_sub_id = None
        self._on_pre_close = None

        # A chained notification, if direved class register visibility_changed_fn
        # we chain it back mine
        self._on_visibility_changed_chained_fn = None

        # Save the visible property, and make it invisible on create
        visible = kwargs.get("visible", True)
        kwargs["visible"] = False

        # Save parent widget, the mouse event in parent will be ignored
        self._parent = kwargs.get("parent", None)
        self._valid_windows = []

        # Here are two kinds of popup window
        # 1. use WINDOW_FLAGS_POPUP, but if have child such as popup menu, parent will disappear when child popup
        # 2. hook mouse, but the mouse position calculats error if outside of viewport (need to be fixed)
        self._has_child = kwargs.get("has_child", False)
        if not self._has_child:
            # Using new window flag instead of hooking mouse event if no child popup
            flags = kwargs.get("flags", 0)
            flags |= ui.WINDOW_FLAGS_POPUP | ui.WINDOW_FLAGS_NO_TITLE_BAR
            kwargs["flags"] = flags

        super().__init__(title, *args, **kwargs)
        super().set_visibility_changed_fn(self._on_visibility_changed)
        if visible:
            self.visible = True

        self._setup_hooks()

    def __del__(self):
        self._realse_hooks()

    def add_valid_window(self, window: ui.Window):
        if window not in self._valid_windows:
            self._valid_windows.append(window)

    def remove_valid_window(self, window: ui.Window):
        if window in self._valid_windows:
            self._valid_windows.remove(window)

    def set_pre_close_fn(self, pre_close_fn: callable):
        """
        Return True means: it is OK to close
        Set this callback function if it needs prevent
        closing in some case.
        """
        self._on_pre_close = pre_close_fn

    # Override the base class's
    def set_visibility_changed_fn(self, on_visibility_changed_fn: callable):
        self._on_visibility_changed_chained_fn = on_visibility_changed_fn

    def _on_visibility_changed(self, visible):
        if visible:
            self._setup_hooks()
        else:
            self._release_hooks()

        # Pass through the chained fn
        if self._on_visibility_changed_chained_fn:
            self._on_visibility_changed_chained_fn(visible)

    def _setup_hooks(self):
        self._input_sub_id = self._input.subscribe_to_input_events(self._on_input_event, order=-10000)

    def _on_input_event(self, event, *_):
        if event.deviceType == carb.input.DeviceType.MOUSE:
            return self._on_global_mouse_event(event.event)
        elif event.deviceType == carb.input.DeviceType.KEYBOARD:
            return self._on_global_keyboard(event.event)
        else:
            return True

    def _release_hooks(self):
        if self._input_sub_id is not None:
            self._input.unsubscribe_to_input_events(self._input_sub_id)
            self._input_sub_id = None

    def _on_global_mouse_event(self, event, *_):
        if not self.visible:
            return True

        # We care only mouse down
        while True:
            if event.type == carb.input.MouseEventType.LEFT_BUTTON_DOWN:
                break
            if event.type == carb.input.MouseEventType.MIDDLE_BUTTON_DOWN:
                break
            if event.type == carb.input.MouseEventType.RIGHT_BUTTON_DOWN:
                break
            # if event.type == carb.input.MouseEventType.MOVE:
            #     break
            return True

        x, y = self._input.get_mouse_coords_normalized(None)
        x *= ui.Workspace.get_main_window_width()
        y *= ui.Workspace.get_main_window_height()

        rect = WindowRect(self)
        if rect.is_inside(x, y):
            return True

        if self._parent is not None:
            # Here widget position is different from window
            rect = WidgetRect(self._parent)
            if rect.is_inside(x, y):
                return True

        for window in self._valid_windows:
            if window is None:
                continue
            rect = WindowRect(window)
            if rect.is_inside(x, y):
                return True

        # Now the click is outside the popup window rect, hide it.
        if (not self._on_pre_close) or self._on_pre_close():
            self.visible = False
            # Also close children
            for window in self._valid_windows:
                if window is not None:
                    window.visible = False
        return True

    def _on_global_keyboard(self, event, *args, **kwargs):
        if not self.visible:
            return True

        if event.type != carb.input.KeyboardEventType.KEY_PRESS:
            return True

        while True:
            # In the following key-press, we will close this popup window:
            if event.input == carb.input.KeyboardInput.SPACE:
                break
            if event.input == carb.input.KeyboardInput.ESCAPE:
                break
            if event.input == carb.input.KeyboardInput.ENTER:
                break
            # Nothing we care key pressed, do nothinng
            return True

        # The key is defined to close the popup window
        if (not self._on_pre_close) or self._on_pre_close():
            self.visible = False
        return True


class TitleWindowBase:
    LIGHT_STYLE = {
        "Rectangle::title_button": {"background_color": COLORS.TRANSPARENT, "border_radius": 2.0},
        "Rectangle::title_button:hovered": {"background_color": LightColors.ButtonHovered},
        "Rectangle::title_button:pressed": {"background_color": LightColors.ButtonPressed},
        "Rectangle::title_rect": {
            "background_color": COLORS.TRANSPARENT,
            "border_color": COLORS.CLR_A,
            "border_width": 0.5,
            "border_radius": 0,
        },
    }
    DARK_STYLE = {
        "Rectangle::title_button": {"background_color": COLORS.TRANSPARENT, "border_radius": 2.0},
        "Rectangle::title_button:hovered": {"background_color": DarkColors.ButtonHovered},
        "Rectangle::title_button:pressed": {"background_color": DarkColors.ButtonPressed},
        "Rectangle::title_rect": {
            "background_color": COLORS.TRANSPARENT,
            "border_color": COLORS.CLR_2,
            "border_width": 0.5,
            "border_radius": 0,
        },
    }
    UI_STYLES = {"NvidiaLight": LIGHT_STYLE, "NvidiaDark": DARK_STYLE}

    TITLEBAR_HEIGHT = 22

    def __init__(
        self,
        title,
        dock_preference,
        title_icon,
        width=0,
        height=0,
        resizable=False,
        has_option=False,
        has_help=False,
        has_close=True,
        popup=False,
        title_internal=None,
        build_custom_titlebar_fn=False,
        menu_path=None,
        menu_hotkey=None,
        appear_after="",
        **kwargs,
    ):
        self._title = title
        self._icon = title_icon
        self._resizable = resizable
        self._has_option = has_option
        self._has_help = has_help
        self._has_close = has_close
        self._build_custom_titlebar_fn = build_custom_titlebar_fn
        self._close_button = None

        self._stage_sub = None
        self._ui_style = "undefined"
        self._icon_widget = None

        if not title_internal:
            title_internal = title

        if popup:
            self._window = PopupWindow(
                title_internal,
                dock_preference,
                width=width,
                height=height,
                padding_x=kwargs.pop("padding_x", 0),
                padding_y=kwargs.pop("padding_y", 0),
                flags=self._get_window_flags(),
                visible=False,
                **kwargs,
            )
        else:
            self._window = ui.Window(
                title_internal,
                dock_preference,
                width=width,
                height=height,
                padding_x=kwargs.pop("padding_x", 0),
                padding_y=kwargs.pop("padding_y", 0),
                flags=self._get_window_flags(),
                visible=False,
                **kwargs,
            )

        if menu_path is not None:
            use_editor_menu = kwargs.get("use_editor_menu", False)
            self._menu_helper = WindowMenuHelper(
                self, menu_path, hotkey=menu_hotkey, appear_after=appear_after, use_editor_menu=use_editor_menu
            )
        else:
            self._menu_helper = None

        self.set_visibility_changed_fn(self.on_show)

        self._build_ui()
        self._window.set_docked_changed_fn(self._on_docked_changed)

        self.set_ui_style(get_ui_style())

    def __del__(self):
        self.destroy()

    def set_ui_style(self, ui_style):
        if self._ui_style == ui_style:
            return

        self._ui_style = ui_style
        style = DefaultWidgetStyle.get_style(ui_style)
        style = merge_dicts(style, TitleWindowBase.UI_STYLES[ui_style])
        style = merge_dicts(style, self._get_content_style(ui_style))
        self._window.frame.set_style(style)

    def get_window_handle(self):
        return self._window

    def set_title_icon(self, icon_path):
        if self._icon_widget:
            self._icon_widget.source_url = icon_path

    @omni.kit.app.deprecated("No UI style event")
    def listen_ui_style(self, listen_or_not):
        carb.log_info("No UI style event, deprecated.")

    def show(self, visible=True, x=0, y=0):
        if self._window:
            self._window.visible = visible
            if visible and x > 0 and y > 0:
                self._window.position_x = x
                self._window.position_y = y

    def is_visible(self):
        if self._window:
            return self._window.visible
        else:
            return False

    def set_visibility_changed_fn(self, on_visibility_changed_fn: callable = None):
        if self._menu_helper is not None:
            self._menu_helper.set_visibility_changed_fn(on_visibility_changed_fn)
        else:
            self._window.set_visibility_changed_fn(on_visibility_changed_fn)

    def dock(self, window_name, ratio=0.311, position=ui.DockPosition.RIGHT):
        if not self._window.docked:
            viewport = ui.Workspace.get_window("Viewport")
            if viewport:
                self._window.dock_in(viewport, position, ratio)
        return self._window.docked

    def destroy(self):
        if self._menu_helper is not None:
            self._menu_helper.destroy()
        if self._window is not None:
            self._window.visible = False
            self._window = None

    def _build_ui(self):
        with self._window.frame:
            with ui.VStack(spacing=0):
                self._build_title_bar()
                self._build_content()

    def _build_title_bar(self):
        ICON_SIZE = 12

        with ui.ZStack(height=TitleWindowBase.TITLEBAR_HEIGHT):
            # Lay 1: a rectangle for borders of title
            ui.Rectangle(height=TitleWindowBase.TITLEBAR_HEIGHT, name="title_rect")

            # Layer 2: All the icons/buttons
            with ui.HStack(height=TitleWindowBase.TITLEBAR_HEIGHT):
                # a) Panel/extension icon
                if self._icon:
                    ui.Spacer(width=5)
                    with ui.VStack():
                        ui.Spacer()
                        self._icon_widget = ui.Image(
                            self._icon, width=18, height=18, style_type_name_override="Image.Title"
                        )
                        ui.Spacer()

                # b) Sapce
                ui.Spacer()

                # c) Custom icons/buttons, if any
                if self._build_custom_titlebar_fn:
                    self._build_custom_titlebar_fn()

                # d) options, help, close buttons (if any)
                if self._has_option:
                    self._build_title_icon(get_icon_path("TitlebarOptions.svg"), ICON_SIZE, self._on_options)
                if self._has_help:
                    self._build_title_icon(get_icon_path("TitlebarHelp.svg"), ICON_SIZE, self._on_help)
                if self._has_close:
                    btn = self._build_title_icon(get_icon_path("TitlebarClose.svg"), ICON_SIZE, self._on_close)
                    self._close_button = btn

                # e) right space
                ui.Spacer(width=5)

            # Lay 3, this is the top layer, it draws the title string
            with ui.HStack(height=TitleWindowBase.TITLEBAR_HEIGHT):
                ui.Spacer()
                with ui.VStack(width=0):
                    ui.Spacer(width=0, height=3)
                    ui.Label(self._title, name="title", alignment=ui.Alignment.LEFT)
                    ui.Spacer(width=0)
                ui.Spacer()

        ui.Spacer(height=10)

    def _build_title_icon(self, icon, size, clicked_fn: callable):
        button_stack = ui.ZStack(width=20, height=TitleWindowBase.TITLEBAR_HEIGHT)
        with button_stack:
            OpaqueRectangle(name="title_button", width=20, height=TitleWindowBase.TITLEBAR_HEIGHT)
            with ui.VStack(width=20, height=TitleWindowBase.TITLEBAR_HEIGHT):
                ui.Spacer()
                with ui.HStack(width=20, height=size):
                    ui.Spacer()
                    ui.Image(
                        icon,
                        width=size,
                        height=size,
                        fill_policy=ui.FillPolicy.STRETCH,
                        mouse_pressed_fn=lambda x, y, btn, a: clicked_fn(btn),
                        opaque_for_mouse_events=False,
                    )
                    ui.Spacer()
                ui.Spacer()
        return button_stack

    def _get_content_style(self, ui_style):
        # This function should be overided.
        return {}

    def _get_window_flags(self):
        # This function can be overided.
        flags = ui.WINDOW_FLAGS_NO_COLLAPSE | ui.WINDOW_FLAGS_NO_TITLE_BAR | ui.WINDOW_FLAGS_NO_SCROLLBAR
        if not self._resizable:
            flags |= ui.WINDOW_FLAGS_NO_RESIZE

        return flags

    def _build_content(self):
        # This function should be overided.
        carb.log_error("ViewWindow._build_content, derived class should override this function")

    def _on_options(self, btn):
        # This function can be overided in case the derived has option.
        carb.log_error("ViewWindow._on_options, derived class should override this function")

    def _on_help(self, btn):
        # This function can be overided in case the derived has help.
        carb.log_error("ViewWindow._on_help, derived class should override this function")

    def _on_close(self, btn):
        if btn != MouseKey.LEFT:
            return
        if self._window:
            self._window.visible = False

    def _on_docked_changed(self, docked):
        if self._close_button:
            self._close_button.visible = not docked

    def on_closed(self):
        # This function can be overided in case the derived need to deal with on_closed.
        pass

    def on_show(self, visible):
        # This function can be overided in case the derived need to deal with on_closed.
        pass

    @property
    def title(self):
        return self._title


class NoTitleWindowBase:
    LIGHT_STYLE = {
        "Rectangle::title_button": {"background_color": COLORS.TRANSPARENT, "border_radius": 2.0},
        "Rectangle::title_button:hovered": {"background_color": LightColors.ButtonHovered},
        "Rectangle::title_button:pressed": {"background_color": LightColors.ButtonPressed},
        "Rectangle::title_rect": {
            "background_color": COLORS.TRANSPARENT,
            "border_color": COLORS.CLR_A,
            "border_width": 0.5,
            "border_radius": 0,
        },
    }
    DARK_STYLE = {
        "Rectangle::title_button": {"background_color": COLORS.TRANSPARENT, "border_radius": 2.0},
        "Rectangle::title_button:hovered": {"background_color": DarkColors.ButtonHovered},
        "Rectangle::title_button:pressed": {"background_color": DarkColors.ButtonPressed},
        "Rectangle::title_rect": {
            "background_color": COLORS.TRANSPARENT,
            "border_color": COLORS.CLR_2,
            "border_width": 0.5,
            "border_radius": 0,
        },
    }
    UI_STYLES = {"NvidiaLight": LIGHT_STYLE, "NvidiaDark": DARK_STYLE}

    def __init__(
        self,
        title=None,
        dock_preference=ui.DockPreference.DISABLED,
        title_icon=None,
        width=0,
        height=0,
        title_internal=None,
        build_custom_titlebar_fn=False,
        padding=0,
    ):
        self._title = title
        self._icon = title_icon
        self._close_button = None

        self._ui_style = "undefined"
        self._icon_widget = None

        if not title_internal:
            title_internal = title if title is not None else "NoTitleWindow_" + str(hash(self))

        self._window = ui.Window(
            title_internal,
            dock_preference,
            width=width,
            height=height,
            padding_x=padding,
            padding_y=padding,
            flags=self._get_window_flags(),
            visible=False,
            visibility_changed_fn=lambda visible: self.on_show(visible),
        )

        self._build_ui()
        self._window.set_docked_changed_fn(self._on_docked_changed)

    def set_ui_style(self, ui_style):
        if self._ui_style == ui_style:
            return

        self._ui_style = ui_style
        style = DefaultWidgetStyle.get_style(ui_style)
        style = merge_dicts(style, NoTitleWindowBase.UI_STYLES[ui_style])
        style = merge_dicts(style, self._get_content_style(ui_style))
        self._window.frame.set_style(style)

    def get_window_handle(self):
        return self._window

    @omni.kit.app.deprecated("No UI style event")
    def listen_ui_style(self, listen_or_not):
        carb.log_info("No UI style event, deprecated.")

    def show(self, show=True, x=0, y=0):
        if self._window:
            self._window.visible = show
            if show and x > 0 and y > 0:
                self._window.position_x = x
                self._window.position_y = y

    def is_visible(self):
        if self._window:
            return self._window.visible
        else:
            return False

    def dock(self, window_name, ratio=0.311, position=ui.DockPosition.RIGHT):
        if not self._window.docked:
            viewport = ui.Workspace.get_window("Viewport")
            if viewport:
                self._window.dock_in(viewport, position, ratio)
        return self._window.docked

    def destroy(self):
        self._window = None

    def _build_icon(self, icon, size, clicked_fn: callable):
        button_stack = ui.ZStack(width=20, height=22)
        with button_stack:
            OpaqueRectangle(name="title_button", width=20, height=22)
            with ui.VStack(width=20, height=22):
                ui.Spacer()
                with ui.HStack(width=20, height=size):
                    ui.Spacer()
                    img = ui.Image(
                        icon,
                        width=size,
                        height=size,
                        fill_policy=ui.FillPolicy.STRETCH,
                        mouse_pressed_fn=lambda x, y, btn, a: clicked_fn(btn),
                        opaque_for_mouse_events=False,
                    )
                    ui.Spacer()
                ui.Spacer()
        return img

    def _on_close(self, btn):
        if btn != MouseKey.LEFT:
            return
        if self._window:
            self._window.visible = False

    def _build_ui(self):
        with self._window.frame:
            with ui.VStack(spacing=0):
                self._build_content()

    def _get_content_style(self, ui_style):
        # This function should be overided.
        return {}

    def _get_window_flags(self):
        # This function can be overided.
        flags = ui.WINDOW_FLAGS_NO_COLLAPSE | ui.WINDOW_FLAGS_NO_TITLE_BAR | ui.WINDOW_FLAGS_NO_SCROLLBAR
        flags |= ui.WINDOW_FLAGS_NO_RESIZE

        return flags

    def _on_docked_changed(self, docked):
        if self._close_button:
            self._close_button.visible = not docked

    def on_show(self, visible):
        # This function can be overided in case the derived need to deal with on_closed.
        pass


class WindowMenuHelper:
    def __init__(
        self,
        window,
        menu_path,
        hotkey: Tuple[int, int] = None,
        appear_after: Union[list, str] = "",
        on_visibility_changed_fn: callable = None,
        use_editor_menu=False,
    ):
        # We should initialize this variable to None because _clear_menu is always called whether _create_menu is called before.
        self._menu_list = None

        if isinstance(window, ui.Window):
            self._window = window
        elif hasattr(window, "get_window_handle"):
            self._window = window.get_window_handle()
        else:
            carb.log_error(f"[WindowMenuHelper] Unknown window type {window}!")
            return

        self._on_visibility_changed_fn = on_visibility_changed_fn
        self._window.set_visibility_changed_fn(self._on_visibility_changed)

        self._use_editor_menu = use_editor_menu
        self._menu_path = menu_path
        if use_editor_menu:
            self._create_editor_menu(menu_path)
        else:
            self._create_menu(menu_path, hotkey=hotkey, appear_after=appear_after)

    def destroy(self):
        self._menu = None
        if not self._use_editor_menu:
            self._clear_menu()
        self._on_visibility_changed_fn = None

    def __del__(self):
        self.destroy()

    def set_visibility_changed_fn(self, on_visibility_changed_fn: callable = None):
        self._on_visibility_changed_fn = on_visibility_changed_fn

    def _create_menu(self, menu_path, hotkey=None, appear_after=""):
        paths = menu_path.split("/")
        if len(paths) == 1:
            menu_title = menu_path
            self._parent_menu_title = "Window"
        else:
            menu_title = paths[-1]
            self._parent_menu_title = paths[0]
        # Add menu
        self._menu_list = [
            MenuItemDescription(
                name=menu_title,
                # glyph="cog.svg",
                appear_after=appear_after,
                ticked=True,
                ticked_fn=self._on_tick,
                onclick_fn=self._on_click,
                hotkey=hotkey,
            )
        ]
        omni.kit.menu.utils.add_menu_items(self._menu_list, self._parent_menu_title, -1)

    def _clear_menu(self):
        if self._menu_list is not None:
            omni.kit.menu.utils.remove_menu_items(self._menu_list, self._parent_menu_title)
            self._menu_list = None

    def _on_tick(self):
        if isinstance(self._window, ui.Window):
            return self._window.visible
        else:
            return self._window.is_visible()

    def _on_click(self, *args):
        if isinstance(self._window, ui.Window):
            self._window.visible = not self._window.visible
        else:
            if self._window.is_visible():
                self._window.hide()
            else:
                self._window.show()

    def _on_visibility_changed(self, visible):
        async def _rebuild_menus():
            await omni.kit.app.get_app().next_update_async()
            omni.kit.menu.utils.rebuild_menus()

        asyncio.ensure_future(_rebuild_menus())
        if self._on_visibility_changed_fn:
            self._on_visibility_changed_fn(visible)

    def _create_editor_menu(self, menu_path):
        carb.log_warn(f"omni.kit.ui.get_editor_menu() has beed deprecated!")
