# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Optional

from omni import ui

from ..models import MaterialPrimDetailItem
from .delegate import MaterialPrimDelegate
from .material_preview_image import MaterialPreviewImage
from .style import FullSwitch


class MaterialPreviewWidget:
    """
    Repesent a widget to preview a material.
    Args:
        delegate (MaterialPrimDelegate): Delegate to get material thumbnail and label.
        on_preview_material_fn (callable): Function called to material preview on/off. Function signure:
            void on_preview_material_fn(item: MaterialPrimDetailItem, on: bool)
    """

    def __init__(self, delegate: MaterialPrimDelegate, on_preview_material_fn: callable):
        self._delegate = delegate
        self._on_preview_material_fn = on_preview_material_fn
        self._item: Optional[MaterialPrimDetailItem] = None

        self._build_ui()

    def destroy(self) -> None:
        if self._image is not None:
            self._image.destroy()
            self._image = None
        self._container = None

    @property
    def visible(self) -> bool:
        return self._container.visible

    def show(self, item: Optional[MaterialPrimDetailItem] = None) -> None:
        """
        Turn material preview on/off.
        Args:
            item (Optional[MaterialPrimDetailItem]): Item to preview material. None to turn off preivew.
        """
        self._container.visible = item is not None
        self._image.visible = item is not None
        if item:
            self._item = item
            self._image.material = item.url
            self._label.text = self._delegate.get_label(item)

    async def capture_thumbnail_async(self):
        if self._item is not None:
            return await self._image.capture_thumbnail_async()
        else:
            return None

    def _build_ui(self):
        self._container = ui.ZStack()
        with self._container:
            ui.Rectangle(style_type_name_override="SingleMaterial.Frame")
            with ui.VStack():
                self._image = MaterialPreviewImage()
                self._label = ui.Label(
                    "", height=26, alignment=ui.Alignment.CENTER, style_type_name_override="SingleMaterial.Label"
                )

            # A mark triangle at top-right
            with ui.VStack(alignment=ui.Alignment.LEFT_BOTTOM):
                ui.Spacer(height=FullSwitch.TrianglePadding)
                with ui.HStack(alignment=ui.Alignment.LEFT_BOTTOM):
                    ui.Spacer()
                    ui.Triangle(
                        width=FullSwitch.TriangleSize,
                        height=FullSwitch.TriangleSize,
                        alignment=ui.Alignment.LEFT_TOP,
                        mouse_pressed_fn=lambda x, y, btn, flags: self._on_preview_off(btn),
                        name="hovered",
                        style_type_name_override="FullSwitch.Triangle",
                    )
                    ui.Spacer(width=FullSwitch.TrianglePadding)

            # Two mark lines at top-right to switch to single material mode.
            with ui.VStack(alignment=ui.Alignment.LEFT_BOTTOM):
                ui.Spacer(height=FullSwitch.TrianglePadding + FullSwitch.LinePadding - FullSwitch.LineWidth)
                with ui.HStack(height=FullSwitch.TriangleSize, alignment=ui.Alignment.LEFT_BOTTOM):
                    ui.Spacer()
                    ui.Line(
                        width=FullSwitch.LineWidth,
                        alignment=ui.Alignment.LEFT,
                        style_type_name_override="FullSwitch.Line",
                    )
                    ui.Spacer(
                        width=FullSwitch.TrianglePadding
                        + FullSwitch.TriangleSize
                        + FullSwitch.LinePadding
                        - FullSwitch.LineWidth
                    )

                with ui.HStack(height=FullSwitch.LineWidth, alignment=ui.Alignment.LEFT_BOTTOM):
                    ui.Spacer()
                    ui.Line(
                        width=FullSwitch.TriangleSize + FullSwitch.LineWidth, style_type_name_override="FullSwitch.Line"
                    )
                    ui.Spacer(width=FullSwitch.TrianglePadding + FullSwitch.LinePadding - FullSwitch.LineWidth)

        self._image.visible = False

    def _on_preview_off(self, btn):
        if btn == 0:
            # Turn off preview mode
            self._on_preview_material_fn(self._item, False)
