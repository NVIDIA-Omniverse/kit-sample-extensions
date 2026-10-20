# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Callable, Dict

import carb.settings
import omni.ui as ui

from .style import get_style


class ZoomBar:
    """
    Reprent a bar with a slider for icon size and a button to switch icon/detail mode.

    Keyword args:
        min (int): Min value of the slider. Default 0.
        max (int): Max value of the slider. Default 5.
        value (int): Initial value of the slider. Default 2.
        width (int): Width of the slider, in pixels. Default 150.
        icon_mode (bool): Show in icon mode or detail mode. Default False means show in detail mode.
        on_view_mode_chagned_fn (callable): Function called when view mode changed. Default None, also means view mode will never be changed. Function signure:
            void on_view_mode_changed_fn(icon_mode: bool)
        on_value_changed_fn (callable): Function called when slider value changed. Default None. Function signure:
            void on_value_changed_fn(value: int)
        style (dict): Custom style of the control. Default {}} to use default style.
    """

    def __init__(
        self,
        min: int = 0,
        max: int = 5,
        value: int = 2,
        width: int = 150,
        icon_mode: bool = False,
        on_view_mode_changed_fn: callable = None,
        on_value_changed_fn: callable = None,
        style: Dict = {},
    ):
        self._min_value = min
        self._max_value = max
        self._value = value
        self._width = width
        self._icon_mode = icon_mode
        self._on_view_mode_changed_fn = on_view_mode_changed_fn
        self._on_value_changed_fn = on_value_changed_fn
        self._additional_style = style

        settings = carb.settings.get_settings()
        self._theme = settings.get_as_string("/persistent/app/window/uiStyle") or "NvidiaDark"

        self._build_ui()

    def destroy(self):
        """Clears internal callback functions and view mode button reference in the ZoomBar."""
        self._on_view_mode_changed_fn = None
        self._on_value_changed_fn = None
        self._view_mode_button = None

    @property
    def model(self) -> ui.AbstractValueModel:
        """Gets the slider model from the ZoomBar.

        Returns:
            ui.AbstractValueModel: The model of the int slider widget.
        """
        return self._slider.model

    def set_on_hovered_fn(self, on_hovered_fn: Callable[[bool], None]) -> None:
        """Set callback function when hovered state changed.

        Args:
            on_hovered_fn (Callable[[bool], None]): Function called when the mouse hover state changes.
        """
        self._container.set_mouse_hovered_fn(on_hovered_fn)

    def _build_ui(self):
        self._container = ui.HStack(height=0, style=get_style())
        with self._container:
            ui.Spacer()
            with ui.ZStack(width=0, style=self._additional_style, content_clipping=1):
                ui.Rectangle(height=20, style_type_name_override="ZoomBar")
                with ui.VStack():
                    ui.Spacer(height=3)
                    with ui.HStack(content_clipping=True, spacing=3):
                        ui.Spacer(width=3)
                        # Slider for icon size
                        self._slider = ui.IntSlider(
                            min=self._min_value,
                            max=self._max_value,
                            width=self._width,
                            style_type_name_override="ZoomBar.Slider",
                        )
                        # Image button to switch icon/detail mode
                        self._view_mode_button = ui.Button(
                            width=16,
                            style_type_name_override=self._get_view_mode_button_style_type_name(),
                            clicked_fn=self._on_change_view_mode,
                        )
                        ui.Spacer(width=3)
                    ui.Spacer(height=3)
            ui.Spacer(width=16)
        # Set initial value
        self._slider.model.add_value_changed_fn(self._on_value_changed)
        self._slider.model.set_value(self._value)

    def _get_view_mode_button_style_type_name(self) -> str:
        if self._icon_mode:
            return "ZoomBar.Button.Thumbnail"
        else:
            return "ZoomBar.Button.List"

    def _on_value_changed(self, model: ui.SimpleIntModel):
        scale = model.get_value_as_int()
        if self._on_value_changed_fn:
            self._on_value_changed_fn(scale)

    def _on_change_view_mode(self):
        # If no callback function, never change the view mode
        if self._on_view_mode_changed_fn:
            self._icon_mode = not self._icon_mode
            self._view_mode_button.style_type_name_override = self._get_view_mode_button_style_type_name()
            self._on_view_mode_changed_fn(self._icon_mode)
