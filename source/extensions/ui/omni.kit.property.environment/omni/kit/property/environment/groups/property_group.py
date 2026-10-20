# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Callable, Optional

from omni import ui
from omni.kit.environment.core import PropertyValueModel
from omni.kit.property.usd import PrimSelectionPayload

from ..style import PROPERTY_STYLES

PADDING = 10

# Same settings as omni.kit.window.property.templates
LABEL_WIDTH = 160
LABEL_HEIGHT = 18


class AbstractPropertyGroup:
    """
    Collapsible frame to show group of properties.
    Args:
        title (str): Frame header text.
    """

    def __init__(self, title: str, enable_model: Optional[ui.SimpleBoolModel] = None):
        self._title = title
        self._container = None
        self._enable_model = enable_model

    def destroy(self):
        pass

    def on_new_payload(self, payload: PrimSelectionPayload):
        pass

    def build(self):
        self._container = ui.CollapsableFrame(
            self._title, build_header_fn=self._build_frame_header, collapsed=False, style=PROPERTY_STYLES
        )
        with self._container:
            with ui.HStack():
                ui.Spacer(width=PADDING)
                self._build_widgets()
                ui.Spacer(width=PADDING)

    @property
    def visible(self) -> bool:
        return self._container.visible if self._container else False

    @visible.setter
    def visible(self, value: bool) -> None:
        if self._container:
            self._container.visible = value

    def _build_widgets(self):
        pass

    def _build_extra_header(self):
        pass

    def _build_frame_header(self, collapsed: bool, text: str) -> None:
        """Custom header for CollapsibleFrame"""
        if collapsed:
            alignment = ui.Alignment.RIGHT_CENTER
            width = 5
            height = 7
        else:
            alignment = ui.Alignment.CENTER_BOTTOM
            width = 7
            height = 5

        with ui.HStack(spacing=0):
            with ui.VStack(width=0):
                ui.Spacer()
                ui.Triangle(
                    style_type_name_override="CollapsableFrame.Header", width=width, height=height, alignment=alignment
                )
                ui.Spacer()
            ui.Spacer(width=8)
            ui.Label(text, style_type_name_override="CollapsableFrame.Header")
            ui.Spacer()
            if self._enable_model:
                with ui.VStack(content_clipping=1, width=0):
                    self._create_checkbox(self._enable_model)
                ui.Spacer(width=10)
            self._build_extra_header()

    def _create_label(self, text: str, width: ui.Length = LABEL_WIDTH, alignment=ui.Alignment.LEFT_CENTER):
        ui.Label(
            text, name="label", word_wrap=True, width=width or LABEL_WIDTH, height=LABEL_HEIGHT, alignment=alignment
        )

    def _create_checkbox(self, model: Optional[ui.AbstractValueModel] = None) -> ui.CheckBox:
        # Copy from UsdPropertiesWidgetBuilder._bool_builder
        with ui.VStack(width=10):
            ui.Spacer()
            widget_kwargs = {"width": 10, "height": 0, "name": "greenCheck", "model": model}
            with ui.ZStack():
                with ui.Placer(offset_x=0, offset_y=-2):
                    checkbox = ui.CheckBox(**widget_kwargs)
                with ui.Placer(offset_x=1, offset_y=-1):
                    ui.Rectangle(height=8, width=8, name="mixed_overlay", alignment=ui.Alignment.CENTER, visible=False)
            ui.Spacer()

        return checkbox

    def _create_float_field(self, model: Optional[ui.SimpleFloatModel] = None) -> ui.FloatField:
        return ui.FloatField(model, name="models")

    def _create_float_drag(self, model: Optional[PropertyValueModel] = None, name="models") -> ui.FloatDrag:
        drag = ui.FloatDrag(model, name=name, min=model.min, max=model.max)
        drag.step = max(0.1, (model.max - model.min) / 1000.0)
        return drag

    def _create_int_drag(self, model: Optional[PropertyValueModel] = None, name="models") -> ui.IntDrag:
        kwargs = {}
        if model.min is not None:
            kwargs["min"] = model.min
        if model.max is not None:
            kwargs["max"] = model.max
        drag = ui.IntDrag(model, name="models", **kwargs)
        if model.min is not None and model.max is not None:
            drag.step = max(0.1, (model.max - model.min) / 1000.0)
        return drag

    def _create_float_slider(self, model: Optional[PropertyValueModel] = None, name="models") -> ui.FloatSlider:
        slider = ui.FloatSlider(model, name=name, min=model.min, max=model.max)
        slider.step = max(0.1, (model.max - model.min) / 1000.0)
        return slider

    def _create_button(
        self, text: str, clicked_fn: Callable[[], None], name="", width: ui.Length = ui.Pixel(70)
    ) -> ui.Button:
        return ui.Button(text, clicked_fn=clicked_fn, width=width, name=name)
