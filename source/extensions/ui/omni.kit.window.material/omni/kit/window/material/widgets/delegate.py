# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Dict, Optional

import carb
import omni.kit.commands
import omni.kit.notification_manager as nm
import omni.usd
from omni import ui
from omni.kit.browser.folder.core import FolderDetailDelegate
from omni.kit.widget.material_preview import UsdBakedPreview
from pxr import Usd

from ..models import MaterialPrimDetailItem, StageMaterialModel
from .capture_thumbnail import CaptureThumbnailManager, CaptureThumbnailRequest
from .new_material_menu import NewMaterialMenu
from .style import ICON_PATH, FullSwitch

SHOW_CAPTURE_THUMBNAIL_MENU_SETTINGS = "/exts/omni.kit.window.material/show_capture_thumbnail_menu"


class MaterialPrimDelegate(FolderDetailDelegate):
    """
    Represent to show detail for a material prim in stage.
    Args:
        stage_model (StageMaterialModel): Stage material model.
        on_preview_material_fn (callable): Function call to preview material on/off. Function signure:
            vois on_preview_material_fn(item: Optional[MaterialPrimDetailItem])
    """

    def __init__(self, stage_model: StageMaterialModel, on_preview_material_fn: callable):
        self._on_preview_material_fn = on_preview_material_fn
        self._stage_model = stage_model
        self._hover_container: Dict[MaterialPrimDetailItem, ui.VStack] = {}
        self._mark_triangle: Dict[MaterialPrimDetailItem, ui.VStack] = {}
        self._capture_providers: Dict[MaterialPrimDetailItem, ui.ByteImageProvider] = {}
        self._capture_thumbnails: Dict[MaterialPrimDetailItem, ui.ImageWithProvider] = {}
        self._file_thumbnails: Dict[MaterialPrimDetailItem, ui.Image] = {}
        self._context_menu = None
        self._capture_thumbnail_manager = CaptureThumbnailManager()
        super().__init__(stage_model)

    def destroy(self) -> None:
        if self._capture_thumbnail_manager is not None:
            self._capture_thumbnail_manager.destroy()
        self._context_menu = None
        self._hover_container.clear()
        self._mark_triangle.clear()
        return super().destroy()

    def get_thumbnail(self, item: MaterialPrimDetailItem) -> str:
        """Set default material thumbnail if thumbnail is None"""
        if item.thumbnail is None:
            return f"{ICON_PATH}/mdl_256.png"
        else:
            return item.thumbnail

    def get_tooltip(self, item: MaterialPrimDetailItem) -> str:
        return item.url

    def get_label(self, item: MaterialPrimDetailItem) -> str:
        return None if self.hide_label else item.name

    def on_right_click(self, item: MaterialPrimDetailItem) -> None:
        if item.prim is None:
            NewMaterialMenu.show()
        else:
            if item in self._hover_container:
                # Clear selected state for hover mark
                # Otherwise will never show hover color in selected state
                self._hover_container[item].selected = False

            """Show material context menu"""
            self._action_item = item
            # Show context menu to apply material
            if self._context_menu is None:
                self._context_menu = ui.Menu("Material Editor context menu")
                with self._context_menu:
                    ui.MenuItem("Assign to Selection", triggered_fn=self._assign_to_selection)
                    if carb.settings.get_settings().get(SHOW_CAPTURE_THUMBNAIL_MENU_SETTINGS):
                        ui.MenuItem("Capture thumbnail", triggered_fn=self._on_capture_thumbnail)
                    ui.MenuItem("Duplicate", triggered_fn=self._on_duplicate)

            self._context_menu.show()

    def on_click(self, item: MaterialPrimDetailItem) -> None:
        if item.prim is None:
            NewMaterialMenu.show()

        # Clear selected state for hover mark
        # Otherwise will never show hover color in selected state
        if item in self._hover_container:
            self._hover_container[item].selected = False

    def on_hover(self, item: MaterialPrimDetailItem, hovered: bool) -> None:
        if item.prim is not None:
            item.hovered = hovered
            if item in self._hover_container:
                self._hover_container[item].visible = hovered
                # Clear selected state for hover mark
                # Otherwise will never show hover color in selected state
                self._hover_container[item].selected = False

                if hovered:
                    self._mark_triangle[item].visible = True
                    self._mark_triangle[item].name = "hovered"
                else:
                    self._mark_triangle[item].name = ""
                    if not item.assigned:
                        self._mark_triangle[item].visible = False

    def on_drag(self, item: MaterialPrimDetailItem) -> str:
        thumbnail = self.get_thumbnail(item)
        with ui.VStack(width=96):
            if thumbnail:
                ui.Spacer(height=2)
                with ui.HStack():
                    ui.Spacer()
                    # TODO: If using ui.ImageWithProvider here and dragging, crash happens when app shutdown.
                    # Now using ui.Image instead.
                    ui.Image(thumbnail, width=96, height=96)
                    ui.Spacer()
            ui.Label(
                item.name,
                word_wrap=False,
                elided_text=True,
                skip_draw_when_clipped=True,
                alignment=ui.Alignment.TOP,
                style_type_name_override="GridView.Item",
            )

        return item.url

    def build_thumbnail(self, item: MaterialPrimDetailItem) -> Optional[ui.Image]:
        """
        Display thumbnail per detail item
        Args:
            item (MaterialPrimDetailItem): detail item to display
        """
        if item.prim is not None:
            return self._build_stage_material_thumbnail(item)
        else:
            return super().build_thumbnail(item)

    def item_changed(self, model: ui.AbstractItemModel, item: Optional[MaterialPrimDetailItem]) -> None:
        super().item_changed(model, item)
        if item is not None:
            if item in self._mark_triangle:
                self._mark_triangle[item].visible = item.assigned

    def capture_thumbnail(self, item: MaterialPrimDetailItem) -> None:
        """
        Capture thumbnail for detail item.
        Args:
            item (MaterialPrimDetailItem): Detail item to capture thumbnail.
        """
        self._capture_thumbnail_manager.put(CaptureThumbnailRequest(item, self.thumbnail_captured))

    def _on_capture_thumbnail(self) -> None:
        self.capture_thumbnail(self._action_item)

    def thumbnail_captured(self, item: MaterialPrimDetailItem, raw_data) -> None:
        data, width, height = raw_data
        self._capture_providers[item].set_bytes_data(data, [width, height])
        self._capture_thumbnails[item].visible = True
        self._file_thumbnails[item].visible = False

    def _assign_to_selection(self) -> None:
        self._model.execute(self._action_item)

    def _on_duplicate(self) -> None:
        # If it's in Auto Authoring mode, it does not permit to
        # duplicate prim if a layer is not writable or it's locked.
        def _introducing_layer_is_readonly(context: omni.usd.UsdContext, prim_path):
            stage = context.get_stage()
            prim = stage.GetPrimAtPath(prim_path)
            if not prim:
                return False

            try:
                import omni.kit.usd.layers as layers

                layers_interface = layers.get_layers(context)
                edit_mode = layers_interface.get_edit_mode()
                if edit_mode == layers.LayerEditMode.AUTO_AUTHORING:
                    layer, _ = omni.usd.get_introducing_layer(prim)
                    if not layer:
                        return False
                    locked = omni.usd.is_layer_locked(context, layer.identifier)
                    writable = omni.usd.is_layer_writable(layer.identifier)

                    return locked or not writable
            except ImportError:
                pass

            return False

        if self._action_item.prim:
            path = self._action_item.prim.GetPath()
            usd_context = omni.usd.get_context()
            if _introducing_layer_is_readonly(usd_context, path):
                error = f"Unable to duplicate prim ({path}) in a read-only layer."
                carb.log_warn(error)
                nm.post_notification(error, hide_after_timeout=False)
            else:
                omni.kit.commands.execute(
                    "CopyPrims",
                    paths_from=[path],
                    duplicate_layers=False,
                    combine_layers=False,
                    flatten_references=False,
                )

    def _build_stage_material_thumbnail(self, item: MaterialPrimDetailItem) -> Optional[ui.Image]:
        with ui.ZStack():
            is_capture_thumbnail_available = self._build_stage_preview_thumbnail_image(item)
            thumbnail = self.get_thumbnail(item)
            self._file_thumbnails[item] = ui.Image(
                thumbnail, fill_policy=ui.FillPolicy.STRETCH, style_type_name_override="GridView.Image"
            )
            # A mark triangle at top-right means assignedk, also shown when hovered.
            with ui.VStack(alignment=ui.Alignment.LEFT_BOTTOM):
                ui.Spacer(height=FullSwitch.TrianglePadding + FullSwitch.LinePadding)
                with ui.HStack(alignment=ui.Alignment.LEFT_BOTTOM):
                    ui.Spacer()
                    self._mark_triangle[item] = ui.Triangle(
                        width=FullSwitch.TriangleSize,
                        height=FullSwitch.TriangleSize,
                        alignment=ui.Alignment.RIGHT_BOTTOM,
                        mouse_pressed_fn=lambda x, y, btn, flags, item=item: self._preview_material(btn, item),
                        name="assigned",
                        style_type_name_override="FullSwitch.Triangle",
                    )
                    ui.Spacer(width=FullSwitch.LinePadding)
                    ui.Spacer(width=FullSwitch.TrianglePadding)

            self._mark_triangle[item].visible = item.assigned

            # Two mark lines at top-right to switch to single material mode.
            # Only visible when hovered.
            self._hover_container[item] = ui.VStack(alignment=ui.Alignment.LEFT_BOTTOM)
            with self._hover_container[item]:
                with ui.VStack(alignment=ui.Alignment.LEFT_BOTTOM):
                    ui.Spacer(height=FullSwitch.TrianglePadding)
                    with ui.HStack(height=FullSwitch.LineWidth, alignment=ui.Alignment.LEFT_BOTTOM):
                        ui.Spacer()
                        ui.Line(width=FullSwitch.TriangleSize, height=2, style_type_name_override="FullSwitch.Line")
                        ui.Spacer(width=FullSwitch.TrianglePadding)

                    with ui.HStack(alignment=ui.Alignment.LEFT_BOTTOM):
                        ui.Spacer()
                        # ui.Spacer(width=3)
                        ui.Line(
                            width=1,
                            height=FullSwitch.TriangleSize,
                            alignment=ui.Alignment.LEFT,
                            style_type_name_override="FullSwitch.Line",
                        )
                        ui.Spacer(width=FullSwitch.TrianglePadding)

            self._hover_container[item].visible = item.hovered

        if is_capture_thumbnail_available:
            self._file_thumbnails[item].visible = False
            self._capture_thumbnails[item].visible = True
        else:
            self._capture_thumbnails[item].visible = False
        return self._file_thumbnails[item]

    def _build_stage_preview_thumbnail_image(self, item: MaterialPrimDetailItem) -> bool:
        is_capture_thumbnail_available = False
        if item.prim:
            baked = UsdBakedPreview(item.prim)
            preview_data = baked.get_baked_preview_data()
            if item not in self._capture_providers:
                self._capture_providers[item] = ui.ByteImageProvider()
            if preview_data is not None:
                data, width, height = preview_data
                self._capture_providers[item].set_bytes_data(data, [width, height])
                is_capture_thumbnail_available = True

            self._capture_thumbnails[item] = ui.ImageWithProvider(
                self._capture_providers[item],
                fill_policy=ui.IwpFillPolicy.IWP_STRETCH,
                style_type_name_override="GridView.Image",
            )

        return is_capture_thumbnail_available

    def _preview_material(self, btn, item: MaterialPrimDetailItem) -> None:
        if btn == 0:
            self._on_preview_material_fn(item)
