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
from omni.kit.widget.examples import ExamplePage
from omni.kit.widget.sliderbar import ArrowAlignment, SliderBar, TimeSliderBar


class Colors:
    Background = 0xFF23211F
    Text = 0xFFB7B2AF
    Slider = 0xFF506070


SLIDER_STYLE = {
    "Rectangle::drag": {"background_color": Colors.Background, "border_width": 0, "border_radius": 2},
    "Label::drag": {"color": Colors.Text},
    "Triangle::drag": {"background_color": Colors.Text},
    "Rectangle::end": {"background_color": 0xFF454545},
    "Circle::cursor": {"background_color": Colors.Text},
    "Seperator": {"color": Colors.Text},
    "Rectangle::start": {"background_color": Colors.Background},
    "Rectangle::end": {"background_color": Colors.Slider},
}


class SliderBarPage(ExamplePage):
    def __init__(self):
        super().__init__("SliderBar")

    def destroy(self):
        self._slider_bar_default.destroy()
        self._slider_bar_fixed_width.destroy()
        self._slider_bar_time.destroy()
        self._slider_bar_style.destroy()

    def build_page(self):
        with ui.VStack(spacing=5):
            ui.Label("Default:", height=20)
            self._slider_bar_default = SliderBar()

            ui.Label("Fixed width:", height=20)
            self._slider_bar_fixed_width = SliderBar(width=300, current=24)

            ui.Label("Time:", height=20)
            self._slider_bar_time = TimeSliderBar(padding_width=80, current=12)

            ui.Label("More styles", height=20)
            self._slider_bar_style = TimeSliderBar(
                start=5,
                end=20,
                current=12,
                padding_width=30,
                slider_padding_width=30,
                style=SLIDER_STYLE,
                arrow_height=10,
                start_arrow_alignment=ArrowAlignment.CENTER,
                end_arrow_alignment=ArrowAlignment.CENTER,
            )
