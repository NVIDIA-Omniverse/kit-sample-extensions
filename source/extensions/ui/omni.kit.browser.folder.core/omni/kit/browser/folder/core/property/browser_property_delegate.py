# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

__all__ = ["BrowserPropertyDelegate"]

import abc
from typing import List, Optional

import omni.ui as ui

from ..models import FileDetailItem

# Use same value from omni.kit.window.property.templates
LABEL_WIDTH = 160
LABEL_HEIGHT = 18
HORIZONTAL_SPACING = 4


class BrowserPropertyDelegate(abc.ABC):
    """Base class for item property delegates"""

    def __init__(self):
        pass

    def __del__(self):
        self.destroy()

    def destroy(self):
        pass

    @abc.abstractmethod
    def accepted(self, detail_items: List[FileDetailItem]) -> bool:
        """
        Check if detail item could be shown by this delegate.
        Args:
            detail_items (List[FileDetailItem]): Detail item to be shown.
        """
        return False

    @abc.abstractmethod
    def build_widgets(self, detail_items: List[FileDetailItem]) -> None:
        """
        Build widgets to Show detail items.
        Args:
            detail_item (List[FileDetailItem]): Detail item to be shown.
        """
        pass

    def _build_label(
        self, text: str, width: Optional[ui.Length] = LABEL_WIDTH, alignment=ui.Alignment.LEFT_CENTER
    ) -> ui.Label:
        return ui.Label(
            text,
            name="label",
            word_wrap=True,
            width=width if width is not None else LABEL_WIDTH,
            height=LABEL_HEIGHT,
            alignment=alignment,
        )

    def _build_combobox(self, text: str, *args, **kwargs) -> ui.ComboBox:
        with ui.HStack(spacing=HORIZONTAL_SPACING, padding=10):
            ui.Label(text, style_type_name_override="Asset.Label", width=100)

            return ui.ComboBox(*args, name="choices", **kwargs)

    def _build_checkbox(self, model: Optional[ui.AbstractValueModel] = None) -> ui.CheckBox:
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

        return checkbox  # noqa: R504

    def _build_string_field(self, model: Optional[ui.SimpleStringModel] = None, text: str = "") -> ui.StringField:
        if text:
            with ui.HStack(spacing=HORIZONTAL_SPACING):
                self._build_label(text)
                field = ui.StringField(model, name="models")
            return field
        else:
            return ui.StringField(model, name="models")

    def _build_float_field(self, model: Optional[ui.SimpleFloatModel] = None) -> ui.FloatField:
        return ui.FloatField(model, name="models")

    def _build_float_drag(self, model: Optional[ui.AbstractValueModel] = None, name="models") -> ui.FloatDrag:
        drag = ui.FloatDrag(model, name=name, min=model.min, max=model.max)
        drag.step = max(0.1, (model.max - model.min) / 1000.0)
        return drag

    def _build_int_drag(self, model: Optional[ui.AbstractValueModel] = None, name="models") -> ui.IntDrag:
        kwargs = {}
        if model.min is not None:
            kwargs["min"] = model.min
        if model.max is not None:
            kwargs["max"] = model.max
        drag = ui.IntDrag(model, name="models", **kwargs)
        if model.min is not None and model.max is not None:
            drag.step = max(0.1, (model.max - model.min) / 1000.0)
        return drag

    def _build_float_slider(self, model: Optional[ui.AbstractValueModel] = None, name="models") -> ui.FloatSlider:
        slider = ui.FloatSlider(model, name=name, min=model.min, max=model.max)
        slider.step = max(0.1, (model.max - model.min) / 1000.0)
        return slider
