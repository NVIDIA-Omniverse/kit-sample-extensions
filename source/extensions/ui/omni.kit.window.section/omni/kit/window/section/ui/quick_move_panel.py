# Copyright (c) 2018-2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import carb.settings
import omni.ui as ui
import omni.usd
from omni.kit.widgets.custom import ExpandPanel, SpaceComboBox

from ..common import DEFAULT_SECTION_TOP, SETTING_SECTION_DIRECTION, SectionManager, WidgetAlignment
from .constant import CONTROL_HEIGHT, PANEL_PADDING_INNER_X, PANEL_SPACING_Y

AXISES = ["X", "Y", "Z"]
ROTATION_DEGREES_STRING = ["5°", "10°", "15°", "30°", "45°", "90°"]
ROTATION_DEGREES_NUMBER = ["5", "10", "15", "30", "45", "90"]


class QuickMovePanel(ExpandPanel):
    def __init__(self):
        super().__init__("Quick Move", 0, True)

        self._settings = carb.settings.get_settings()

    def build_panel(self):
        with ui.VStack():
            with ui.HStack(height=CONTROL_HEIGHT):
                ui.Spacer(width=PANEL_PADDING_INNER_X)
                with ui.VStack(spacing=PANEL_SPACING_Y):
                    with ui.HStack():
                        ui.Label("Align Section to...", height=CONTROL_HEIGHT, name="label")
                        ui.Spacer()
                        ui.Button(
                            "X",
                            width=24,
                            height=CONTROL_HEIGHT,
                            name="align_x",
                            tooltip="Aligns to Y/Z plane",
                            clicked_fn=self._align_x,
                        )
                        ui.Spacer(width=10)
                        ui.Button(
                            "Y",
                            width=24,
                            height=CONTROL_HEIGHT,
                            name="align_y",
                            tooltip="Aligns to X/Z plane",
                            clicked_fn=self._align_y,
                        )
                        ui.Spacer(width=10)
                        ui.Button(
                            "Z",
                            width=24,
                            height=CONTROL_HEIGHT,
                            name="align_z",
                            tooltip="Aligns to X/Y plane",
                            clicked_fn=self._align_z,
                        )
                    with ui.HStack(tooltip="Rotation is applied on the Section Tools Local Axis"):
                        ui.Label("Set Rotation", height=CONTROL_HEIGHT, name="label")
                        ui.Spacer()
                        ROTATE_ICON_SIZE = 18
                        with ui.VStack(height=CONTROL_HEIGHT, width=2 * ROTATE_ICON_SIZE):
                            ui.Spacer()
                            with ui.HStack(height=ROTATE_ICON_SIZE, spacing=5):
                                ui.Button(
                                    image_width=24,
                                    iamge_height=24,
                                    width=24,
                                    height=24,
                                    name="counter_clockwise",
                                    clicked_fn=self._on_rotate_counter_clockwise,
                                )
                                ui.Button(
                                    image_width=24,
                                    image_height=24,
                                    width=24,
                                    height=24,
                                    name="clockwise",
                                    clicked_fn=self._on_rotate_clockwise,
                                )
                            ui.Spacer()
                        ui.Spacer(width=5)
                        self._axis_combobox = SpaceComboBox(0, *AXISES, width=50, height=CONTROL_HEIGHT)
                        ui.Spacer(width=5)
                        self._degree_combobox = SpaceComboBox(
                            0, *ROTATION_DEGREES_STRING, width=60, height=CONTROL_HEIGHT
                        )
                ui.Spacer(width=PANEL_PADDING_INNER_X)

            ui.Spacer(height=15)
            with ui.HStack(height=CONTROL_HEIGHT):
                ui.Spacer(width=PANEL_PADDING_INNER_X - 10)
                ui.Button(
                    "Inverse Cut Direction",
                    height=CONTROL_HEIGHT,
                    name="control",
                    clicked_fn=self._inverse_cut_direction,
                )
                ui.Spacer(width=PANEL_PADDING_INNER_X)

        self._rotation_axis = AXISES[0]
        self._axis_combobox.model.add_item_changed_fn(self._on_axis_changed)
        self._rotation_degree = ROTATION_DEGREES_NUMBER[0]
        self._degree_combobox.model.add_item_changed_fn(self._on_degree_changed)

        # Default to 45
        self._degree_combobox.model.current_index = 4

    def _align_x(self):
        SectionManager().align_widget(WidgetAlignment.X)

    def _align_y(self):
        SectionManager().align_widget(WidgetAlignment.Y)

    def _align_z(self):
        SectionManager().align_widget(WidgetAlignment.Z)

    def _on_rotate_clockwise(self):
        self._rotate(True)

    def _on_rotate_counter_clockwise(self):
        self._rotate(False)

    def _rotate(self, clockwise):
        if self._rotation_axis == "X":
            align = WidgetAlignment.X
        elif self._rotation_axis == "Y":
            align = WidgetAlignment.Y
        else:
            align = WidgetAlignment.Z
        angle = float(self._rotation_degree)
        if clockwise:
            angle *= -1.0
        SectionManager().rotate_widget(align, angle)

    def _on_axis_changed(self, model, item):
        index = model.get_item_value_model().as_int
        self._rotation_axis = AXISES[index]

    def _on_degree_changed(self, model, item):
        index = model.get_item_value_model().as_int
        self._rotation_degree = ROTATION_DEGREES_NUMBER[index]

    def _inverse_cut_direction(self) -> None:
        new_direction = 1 - self._settings.get(SETTING_SECTION_DIRECTION)
        self._settings.set(SETTING_SECTION_DIRECTION, new_direction)
