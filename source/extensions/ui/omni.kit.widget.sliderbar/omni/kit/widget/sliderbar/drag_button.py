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


class ImageAlignment:
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class ArrowAlignment:
    CENTER = "CENTER"
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class DragButton:
    """
    Represents a dragable button, combined with a label to show text, image and a triangle as arrow to show the direction.
    Args:
        image_alignment (ImageAlignment): Button image alignment.
        arrow_alignment (ArrowAlignment): Arrow alignment.

    """

    def __init__(
        self,
        image_alignment: ImageAlignment = ImageAlignment.LEFT,
        arrow_alignment: ArrowAlignment = ArrowAlignment.LEFT,
        height: ui.Length = ui.Pixel(25),
        arrow_width: ui.Length = ui.Pixel(8),
        arrow_height: ui.Length = ui.Pixel(8),
        image_width: ui.Length = ui.Pixel(8),
    ):
        self._overlap = 3
        self._image_alignment = image_alignment
        self._arrow_alignment = arrow_alignment
        self._height = height
        self._arrow_width = arrow_width
        self._arrow_height = arrow_height
        self._image_width = image_width

        self._button_height = height - self._arrow_height + self._overlap

        self._build_ui()

    def _build_ui(self):
        self._container = ui.ZStack(width=0)
        with self._container:
            with ui.VStack():
                ui.Spacer(height=self._height - self._arrow_height)
                if self._arrow_alignment == ArrowAlignment.LEFT:
                    ui.Triangle(
                        name="drag",
                        width=self._arrow_width,
                        height=self._arrow_height,
                        alignment=ui.Alignment.LEFT_BOTTOM,
                    )
                elif self._arrow_alignment == ArrowAlignment.RIGHT:
                    with ui.HStack():
                        ui.Spacer()
                        ui.Triangle(
                            name="drag",
                            width=self._arrow_width,
                            height=self._arrow_height,
                            alignment=ui.Alignment.RIGHT_BOTTOM,
                        )
                elif self._arrow_alignment == ArrowAlignment.CENTER:
                    with ui.HStack():
                        ui.Spacer()
                        ui.Triangle(
                            name="drag",
                            width=self._arrow_width,
                            height=self._arrow_height,
                            alignment=ui.Alignment.CENTER_BOTTOM,
                        )
                        ui.Spacer()
            with ui.ZStack(width=0, height=self._button_height):
                self._rect = ui.Rectangle(name="drag")
                with ui.HStack(height=self._button_height, spacing=10):
                    ui.Spacer(width=0)
                    if self._image_alignment == ImageAlignment.LEFT:
                        self._reset = ui.Image(width=self._image_width, name="slider_left")
                    self._label = ui.Label("8:00 AM", name="drag", width=0, alignment=ui.Alignment.CENTER)
                    if self._image_alignment == ImageAlignment.RIGHT:
                        self._reset = ui.Image(width=self._image_width, name="slider_right")
                    ui.Spacer(width=0)

    def set_mouse_event_fn(self, dbclicked_fn, pressed_fn, moved_fn, released_fn, on_reset_position):
        if self._rect:
            self._rect.set_mouse_double_clicked_fn(dbclicked_fn)
            self._rect.set_mouse_pressed_fn(pressed_fn)
            self._rect.set_mouse_moved_fn(moved_fn)
            self._rect.set_mouse_released_fn(released_fn)
            self._reset.set_mouse_pressed_fn(on_reset_position)

    @property
    def width(self):
        return self._container.computed_content_width

    @property
    def offset_arrow(self):
        if self._arrow_alignment == ArrowAlignment.LEFT:
            return 0
        elif self._arrow_alignment == ArrowAlignment.RIGHT:
            return self.width
        elif self._arrow_alignment == ArrowAlignment.CENTER:
            return self.width / 2
        else:
            return 0

    @property
    def text(self) -> str:
        return self._label.text

    @text.setter
    def text(self, value) -> None:
        self._label.text = value

    def set_text(self, text):
        self._label.text = text
