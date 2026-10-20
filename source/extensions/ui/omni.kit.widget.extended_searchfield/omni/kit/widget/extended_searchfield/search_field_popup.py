# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Any, Callable, Dict, List, Optional, Union

import carb
import omni.kit.app
import omni.ui as ui

from .style import UI_STYLE


class AbstractDialog:
    pass


class SearchFieldPopup(AbstractDialog):
    """Base class for a simple popup dialog with two primary buttons, OK and Cancel."""

    WINDOW_FLAGS = ui.WINDOW_FLAGS_NO_TITLE_BAR
    WINDOW_FLAGS |= ui.WINDOW_FLAGS_NO_SCROLLBAR
    WINDOW_FLAGS |= ui.WINDOW_FLAGS_NO_BACKGROUND
    WINDOW_FLAGS |= ui.WINDOW_FLAGS_NO_DOCKING
    WINDOW_FLAGS |= ui.WINDOW_FLAGS_NO_CLOSE
    WINDOW_FLAGS |= ui.WINDOW_FLAGS_NO_RESIZE
    WINDOW_FLAGS |= ui.WINDOW_FLAGS_NO_MOVE

    BUTTON_HEIGHT = 14
    BUTTON_WIDTH = 14

    def __init__(
        self,
        popup: bool = False,
        width: int = 400,
        title: str = "Message Dialog",
        ok_handler: Callable[[AbstractDialog], None] = None,
        cancel_handler: Callable[[AbstractDialog], None] = None,
        ok_label: str = "Ok",
        cancel_label: str = "Cancel",
        alternate_search_text: str = None,
        button_style: str = "",
    ):
        """
        Inherited args from the base class.

        Keyword Args:
            width (int): Window width. Default 400.
            message (str): Headline message to display. Default None.
            title (str): Title to display. Default `Message Dialog`
            ok_handler (Callable): Function to invoke when Ok button clicked. Function signature:
                void okay_handler(dialog: :obj:`SearchFieldPopup`)
            cancel_handler (Callable):  Function to invoke when Cancel button clicked. Function
                signature: void cancel_handler(dialog: :obj:`SearchFieldPopup`)
            ok_label (str): Alternative text to display on 'Accept' button. Default 'Ok'.
            cancel_label (str): Alternative text to display on 'Cancel' button. Default 'Cancel'.
            alternate_search_text (str): Alternative text to display in the search field when this window is active.
            button_style (str): Overriding style for button that opens the popup
        """
        super().__init__()

        self._window: Optional[ui.Window] = None
        self._theme: str = carb.settings.get_settings().get_as_string("/persistent/app/window/uiStyle") or "NvidiaDark"
        self._style: Dict[str, Any] = UI_STYLE  # [self._theme]
        self._popup: bool = popup

        self._title: str = title
        self._width: int = width
        self._button: Optional[ui.Button] = None
        self._button_style: str = button_style
        self._prefixes: List[str] = []
        self._username: str = ""

        self._click_okay_handler: Callable[[AbstractDialog], None] = ok_handler
        self._click_cancel_handler: Callable[[AbstractDialog], None] = cancel_handler
        self._okay_label: str = ok_label
        self._okay_button: Optional[ui.Button] = None
        self._cancel_label: str = cancel_label
        self._cancel_button: Optional[ui.Button] = None
        self._previous_position_x: int = 0
        self._previous_position_y: int = 0
        self._alternate_search_text: str = alternate_search_text
        self._button_container = None

        self._key_functions: Dict[int, callable] = {
            int(carb.input.KeyboardInput.ENTER): self._on_okay,
            int(carb.input.KeyboardInput.ESCAPE): self._on_cancel,
        }

    def __del__(self):
        self.destroy()

    @property
    def username(self) -> str:
        return self._username

    @username.setter
    def username(self, name: str):
        self._username = name

    @property
    def alternate_search_text(self):
        return self._alternate_search_text

    @property
    def visible(self) -> bool:
        return self._window.visible

    def build_ui_for_prefixes(self, prefixes: list):
        self._prefixes = prefixes
        self._build_ui()

    def build_button(self, clicked_fn):
        """Draw the button that opens this popup"""
        self._button_container = ui.VStack(width=20)
        with self._button_container:
            ui.Spacer(height=6)
            self._button = ui.Button(
                image_height=SearchFieldPopup.BUTTON_HEIGHT,
                image_width=SearchFieldPopup.BUTTON_WIDTH,
                style_type_name_override=self._button_style,
                clicked_fn=clicked_fn,
            )
            ui.Spacer()

    def show_button(self, show: bool) -> None:
        if self._button:
            self._button.visible = show

    def show(self, parent: ui.Widget, offset_x: int = 0, offset_y: int = 0):
        """
        Shows this dialog, optionally offset from the parent widget, if any.

        Args:
            parent (ui.Widget): parent used for positioning
            offset_x (int): X offset. Default 0.
            offset_y (int): Y offset. Default 0.
        """
        # add some padding to make it look better
        padding = 0
        width = self._width
        self._window.position_x = parent.screen_position_x + parent.computed_width - width + offset_x - padding
        self._window.position_y = parent.screen_position_y + offset_y
        self._window.width = width

        self._previous_position_x, self._previous_position_y = self._window.position_x, self._window.position_y
        self._window.set_key_pressed_fn(self._on_key_pressed)
        self._window.visible = True
        self._window.focus()

    def hide(self):
        """Hides this dialog."""
        self._window.visible = False

    @property
    def position_x(self) -> int:
        return self._window.position_x

    @property
    def position_y(self) -> int:
        return self._window.position_y

    def _cancel_handler(self, dialog):
        self.hide()

    def _ok_handler(self, dialog):
        pass

    def _get_field_value(self, field: ui.AbstractField) -> Union[str, int, float, bool]:
        if not field:
            return None
        if isinstance(field, ui.StringField):
            return field.model.get_value_as_string()
        elif type(field) in [ui.IntField, ui.IntDrag, ui.IntSlider]:
            return field.model.get_value_as_int()
        elif type(field) in [ui.FloatField, ui.FloatDrag, ui.FloatSlider]:
            return field.model.get_value_as_float()
        elif isinstance(field, ui.CheckBox):
            return field.model.get_value_as_bool()
        else:
            # TODO: Retrieve values for MultiField
            return None

    async def reset_position(self):
        self._window.visible = True
        self._window.focus()
        await omni.kit.app.get_app().next_update_async()
        self._window.setPosition(self._previous_position_x, self._previous_position_y)

    def _build_ui(self):
        window_flags = self.WINDOW_FLAGS | (ui.WINDOW_FLAGS_POPUP if self._popup else 0)
        self._window = ui.Window(self._title, width=self._width, height=0, auto_resize=True, flags=window_flags)

    def _build_ok_cancel_buttons(self, disable_okay_button: bool = False, disable_cancel_button: bool = False):
        if disable_okay_button and disable_cancel_button:
            return

        with ui.HStack(height=20, spacing=4):
            ui.Spacer()
            if disable_okay_button:
                ui.Spacer()
            else:
                self._okay_button = ui.Button(self._okay_label, width=100, clicked_fn=self._on_okay)

            if disable_cancel_button:
                ui.Spacer()
            else:
                self._cancel_button = ui.Button(self._cancel_label, width=100, clicked_fn=self._on_cancel)

    def _on_okay(self):
        if self._click_okay_handler:
            self._click_okay_handler(self)

    def _on_cancel(self):
        if self._click_cancel_handler:
            self._click_cancel_handler(self)
        else:
            self.hide()

    def _on_key_pressed(self, key, mod, pressed):
        if not pressed:
            return
        func = self._key_functions.get(key)
        if func and mod in (0, ui.Widget.FLAG_WANT_CAPTURE_KEYBOARD):
            func()

    def set_okay_clicked_fn(self, ok_handler: Callable[[AbstractDialog], None]):
        """
        Sets function to invoke when Okay button is clicked.

        Args:
            ok_handler (Callable): Callback with signature: void okay_handler(dialog: :obj:`SearchFieldPopup`)

        """
        self._click_okay_handler = ok_handler

    def set_visibility_changed_fn(self, visibility_changed_handler: Callable[[AbstractDialog], None]):
        self._window.set_visibility_changed_fn(visibility_changed_handler)

    def destroy(self):
        """Destructor"""
        self._window = None
        self._style = None
        self._parent = None
        self._click_okay_handler = None
        self._click_cancel_handler = None
        self._key_functions = None
        self._okay_button = None
        self._cancel_button = None
