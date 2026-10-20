# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

from typing import Dict, List, Optional, Union

from omni import ui

from .style import ICON_PATH


class BrowserToolBarButtonDesc:
    """
    Represent a button in browser toolbar
    Args:
        image_url (Optional[str]): Image url of button. None means spacer.
        clicked_fn (callable): Function called when button clicked. Default None. Function signure:
            void clicked_fn()
        tooltips (Optinal[str]): Button tooltips. Default None.
    """

    def __init__(self, image_url: Optional[str], clicked_fn: callable = None, tooltips: Optional[str] = None):
        self.image_url = image_url
        self.clicked_fn = clicked_fn
        self.tooltips = tooltips


class BrowserToolBarBase:
    """
    Represent a base tool bar for browser.
    Args:
        descs (List[BrowserToolBarButtonDesc]): Default buttons to show on tool bar.
    """

    def __init__(self, descs: List[BrowserToolBarButtonDesc]):
        self._buttons: Dict[BrowserToolBarButtonDesc, ui.Button] = {}
        self._button_descs: List[BrowserToolBarButtonDesc] = []
        self._button_descs.extend(descs)

        self.widget = ui.HStack(height=0, spacing=4)
        self._spacer_visible = True
        self._spacers: List[ui.Spacer] = []
        self._build_buttons()

    @property
    def visible(self) -> bool:
        """
        Toolbar visibility.
        """
        return self.widget.visible

    @visible.setter
    def visible(self, value) -> None:
        self.widget.visible = value

    @property
    def computed_height(self):
        return self.widget.computed_height

    @property
    def spacer_visible(self) -> bool:
        """Visibility of spacers in toolbar"""
        return self._spacer_visible

    @spacer_visible.setter
    def spacer_visible(self, visible) -> None:
        if visible != self._spacer_visible:
            self._spacer_visible = visible
            for spacer in self._spacers:
                spacer.visible = visible

    @property
    def width(self):
        return self.widget.computed_width if self.widget else 0

    @property
    def position_x(self):
        return self.widget.screen_position_x if self.widget else 0

    def destroy(self) -> None:
        for desc in self._buttons:
            self._buttons[desc] = None
        self.widget = None

    def append_buttons(self, button_descs: Union[BrowserToolBarButtonDesc, List[BrowserToolBarButtonDesc]]) -> None:
        """
        Append buttons to toolbar.
        Args:
            button_descs (Union[BrowserToolBarButtonDesc, \
                List[BrowserToolBarButtonDesc]]): Desc of buttons to be appended.
        """
        if isinstance(button_descs, list):
            self._button_descs.extend(button_descs)
        else:
            self._button_descs.append(button_descs)
        self._build_buttons()

    def get_button(self, desc: BrowserToolBarButtonDesc) -> Optional[ui.Button]:
        """
        Get toolbar button by desc. Return None if not found.
        Args:
            desc (BrowserToolBarButtonDesc): Button description.
        """
        return self._buttons[desc] if desc in self._buttons else None

    def _build_buttons(self):
        self.widget.clear()
        self._buttons.clear()
        self._spacers.clear()
        with self.widget:
            for desc in self._button_descs:
                if desc.image_url:
                    with ui.VStack(width=26):
                        ui.Spacer()
                        self._buttons[desc] = ui.Button(
                            image_url=desc.image_url,
                            image_width=20,
                            image_height=20,
                            width=26,
                            height=26,
                            clicked_fn=desc.clicked_fn,
                            style_type_name_override="ToolBar.Button",
                            tooltip=desc.tooltips if desc.tooltips else "",
                        )
                        ui.Spacer()
                else:
                    spacer = ui.Spacer()
                    self._spacers.append(spacer)


class BrowserPropertyToolBar(BrowserToolBarBase):
    """
    Represent a tool bar with a button to display a Property widget (window).
    Args:
        on_toggle_property_fn (callable): Function called when show/hide property button clicked. Function signure:
            void on_toggle_property_fn()
    """

    def __init__(self, on_toggle_property_fn: callable):
        self._on_toggle_property_fn = on_toggle_property_fn
        self._property_button_desc = BrowserToolBarButtonDesc(
            f"{ICON_PATH}/property_dark.svg",
            clicked_fn=self._on_toggle_property_fn,
            tooltips="Show/Hide property widget",
        )
        super().__init__([BrowserToolBarButtonDesc(""), self._property_button_desc])

    def destroy(self):
        super().destroy()

    @property
    def btn_property(self) -> ui.Button:
        return self.get_button(self._property_button_desc)
