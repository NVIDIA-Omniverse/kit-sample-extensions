# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from omni import ui

from ..models import BaseValueModel
from .style import RESET_BUTTON_STYLE


class ResetButton:
    """A class for adding a reset button to the user interface that restores a model's value to its default state.

    This class creates a user interface element that monitors a BaseValueModel and becomes visible when the current value deviates from its default. When clicked, the button triggers a reset, returning the model to its default value. It supports different data types such as bool, int, float, and string to determine if the value has changed compared to the default.

    Args:
        model (BaseValueModel): The model containing the value and default state which the reset button monitors and restores if altered.
    """

    def __init__(self, model: BaseValueModel):
        self._model = model
        with ui.VStack(width=15, height=20, style=RESET_BUTTON_STYLE):
            ui.Spacer(height=5)
            with ui.ZStack(width=15, height=15):
                with ui.HStack(spacing=0):
                    ui.Spacer()
                    with ui.VStack(width=0):
                        ui.Spacer()
                        ui.Rectangle(width=5, height=5, style_type_name_override="Reset_invalid.Rect")
                        ui.Spacer()
                    ui.Spacer()
                btn = ui.Rectangle(
                    width=12, height=12, style_type_name_override="Reset.Rect", tooltip="Click to reset value"
                )
                btn.visible = False

            btn.set_mouse_pressed_fn(lambda x, y, m, w: self._restore_defaults())
            ui.Spacer()

        self._reset_button = btn

        self._model.add_value_changed_fn(self._on_value_changed)

    def _restore_defaults(self) -> None:
        self._model.reset_value()

    def _on_value_changed(self, model: BaseValueModel) -> None:
        if model.default is not None:
            if isinstance(model.default, bool):
                changed = model.as_bool != model.default
            elif isinstance(model.default, int):
                changed = model.as_int != model.default
            elif isinstance(model.default, float):
                changed = model.as_float != model.default
            else:
                changed = model.as_string != model.default
            self._reset_button.visible = changed
