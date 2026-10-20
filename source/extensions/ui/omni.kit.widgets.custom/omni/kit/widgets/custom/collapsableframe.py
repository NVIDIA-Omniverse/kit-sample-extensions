# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import copy
from typing import Dict

from omni import ui
from omni.kit.widget.settings import get_style

from .constant import COLORS, DarkColors, LightColors
from .style import get_ui_style


class Colors:
    Text = ui.color.shade(0xFFCCCCCC, light=0xFF535354)


class SimpleCollapsableFrame(ui.CollapsableFrame):
    UI_STYLE = {
        "HStack": {"margin_height": 5},
        "Triangle": {"background_color": Colors.Text},
        "Label": {"color": Colors.Text},
    }

    def __init__(self, title, style: Dict = None, **kwargs):
        if "height" not in kwargs:
            kwargs["height"] = 0

        ui_style = copy.copy(get_style())
        if style is not None:
            ui_style.update(style)

        def custom_header(collapsed, title):
            triangle_alignment = ui.Alignment.RIGHT_CENTER
            triangle_width = 4
            triangle_height = 6
            if not collapsed:
                triangle_alignment = ui.Alignment.CENTER_BOTTOM
                triangle_width = 7
                triangle_height = 5

            with ui.HStack(height=20, style=self.UI_STYLE):
                ui.Spacer(width=5)
                with ui.VStack(width=15):
                    ui.Spacer()
                    ui.Triangle(alignment=triangle_alignment, width=triangle_width, height=triangle_height)
                    ui.Spacer()

                ui.Label(title, name="title", width=0)

        super().__init__(title, build_header_fn=custom_header, style=ui_style, **kwargs)


class ExpandPanel:
    def __init__(self, title, title_width: float = 0, expand: bool = False, **kwargs):
        self._panel = SimpleCollapsableFrame(title, **kwargs)
        with self._panel:
            self._stack = ui.VStack(height=0, spacing=5, style={"VStack::panel": {"margin_width": 10}})
            self.rebuild()
        self._panel.collapsed = not expand

    def rebuild(self):
        self._stack.clear()
        with self._stack:
            ui.Spacer(height=5)
            self.build_panel()
            ui.Spacer(height=5)

    def show(self, visible=True):
        self._panel.visible = visible


class InfoPanel(ExpandPanel):
    """Sample: InfoPanel().update_data([['Author', 'user'], ['Date', '2021.01.01']])"""

    LIGHT_STYLE = {"Label::readonly": {"color": LightColors.TextDisabled}}
    DARK_STYLE = {"Label::readonly": {"color": DarkColors.TextDisabled}}
    UI_STYLES = {"NvidiaLight": LIGHT_STYLE, "NvidiaDark": DARK_STYLE}

    def __init__(self, expand: bool = True):
        super().__init__("Info", title_width=0, expand=expand)

    def build_panel(self):
        self._data_panel = ui.VStack(spacing=10)

    def update_data(self, attributes):
        self._data_panel.clear()
        with self._data_panel:
            for attribute in attributes:
                with ui.HStack(style=InfoPanel.UI_STYLES[get_ui_style()]):
                    with ui.HStack(width=ui.Percent(50)):
                        ui.Label(attribute[0], alignment=ui.Alignment.RIGHT, name="readonly")
                        ui.Spacer(width=10)
                    with ui.HStack(width=ui.Percent(50)):
                        ui.Spacer(width=10)
                        ui.Label(attribute[1], name="readonly")
