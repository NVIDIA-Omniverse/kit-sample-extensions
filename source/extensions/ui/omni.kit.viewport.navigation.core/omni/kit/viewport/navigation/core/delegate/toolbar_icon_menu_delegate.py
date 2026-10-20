# Copyright (c) 2021-2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["ToolBarIconMenuDelegate"]

from typing import Callable, Optional

import omni.ui as ui


class ToolBarIconMenuDelegate(ui.MenuDelegate):
    """
    The menu delegate that draws in the Toolbar the given icon.
    """

    def __init__(
        self,
        name: str,
        text: bool = False,
        width: ui.Length = 38,
        height: ui.Length = 38,
        has_triangle: bool = False,
        triangle_size: float = 6,
        checked: bool = False,
        enabled: bool = True,
        triggered_fn: Callable[[None], None] = None,
        right_clicked_fn: Callable[[None], None] = None,
        tooltip: Optional[str] = None,
    ):
        super().__init__(propagate=False)
        self._name = name
        self._text = text
        self._width = width
        self._icon_width = width
        self._height = height
        self._checked = checked
        self._enabled = enabled
        self._has_title = True
        self.__label = None
        self.__tooltip = tooltip or ""

        self._triggered_fn = triggered_fn
        self._right_clicked_fn = right_clicked_fn

        self._container: Optional[ui.Widget] = None
        self.__label_size = 0

    def build_title(self, item: ui.MenuItem):
        if self._has_title:
            super().build_title(item)

    def build_item(self, item: ui.MenuItem):
        icon_type = "Menu.Item.Icon"
        self._container = ui.ZStack(checked=self._checked, height=self._height)
        with self._container:
            ui.Rectangle(style_type_name_override="Menubar.Hover")
            with ui.HStack(height=self._height):
                ui.Spacer()
                self.icon = self._build_icon()
                ui.Spacer()

        if self._triggered_fn or self._right_clicked_fn:
            self._container.set_mouse_released_fn(lambda x, y, b, a: self._on_mouse_released(b))

    @property
    def text_size(self) -> float:
        """
        Size of text displayed.
        """
        return self.__label_size

    @property
    def has_title(self) -> bool:
        return self._has_title

    @has_title.setter
    def has_title(self, value: bool) -> None:
        self._has_title = value

    @property
    def text_visible(self) -> bool:
        return self._text

    @text_visible.setter
    def text_visible(self, value: bool) -> None:
        # Here only set status but need menu invilidate outside to refresh
        self._text = value

    @property
    def checked(self) -> bool:
        return self._container.checked

    @checked.setter
    def checked(self, value) -> None:
        self._checked = value
        if self._container:
            self._container.checked = value

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value) -> None:
        self._enabled = value
        if self._container:
            self._container.enabled = value

    @property
    def text(self):
        return self.__label.text if self.__label else ""

    @text.setter
    def text(self, txt: str):
        if self.__label:
            self.__label.text = str(txt)

    def destroy(self):
        pass

    def _on_mouse_released(self, button: int) -> None:
        if button == 0:
            if self._triggered_fn:
                self._triggered_fn()
        elif button == 1:
            if self._right_clicked_fn:
                self._right_clicked_fn()

    def _build_icon(self):
        return ui.ImageWithProvider(
            style_type_name_override="Menu.Item.Icon",
            name=self._name,
            width=self._icon_width - 10,
            height=self._height - 10,
            tooltip=self.__tooltip,
        )
