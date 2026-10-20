# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from pathlib import Path
from typing import Optional, Tuple

import carb
import omni.kit.commands
import omni.kit.material.library
import omni.stageupdate
import omni.usd
from omni import ui
from omni.kit.browser.core import create_drop_helper
from omni.kit.browser.folder.core import FolderDetailDelegate
from omni.kit.viewport.utility import get_active_viewport
from pxr import Sdf, Tf, Usd, UsdShade

from .commands import ChangePrimVarCommand
from .data import MaterialFile, MaterialType, SubMaterial, UsdSubMaterial
from .model import MaterialBrowserModel, MaterialDetailItem

CURRENT_PATH = Path(__file__).parent
ICON_PATH = CURRENT_PATH.parent.parent.parent.parent.joinpath("icons")
MATERIAL_DRAG_PAYLOAD_PREFIX = "material::"


class MaterialDetailDelegate(FolderDetailDelegate):
    """
    Delegate to show material item in detail view
    Args:
        model (MaterialBrowserModel): Material browser model
    """

    def __init__(self, model: MaterialBrowserModel):
        super().__init__(model)
        self._action_item: MaterialDetailItem = None
        self._context_menu: ui.Menu = None

        try:
            # OM-56323: For VP2, create_drop_helper does not work for Model Selection
            # Have to use custom drop delegate instead
            from .drop_delegate import MaterialDragDropObject

            self._drop_helper = MaterialDragDropObject(
                add_outline=True,
                test_accepted_fn=self._on_drop_accepted,
                drop_fn=self._on_drop,
                pick_complete=self._on_pick,
            )
        except ImportError:
            self._drop_helper = None

        if self._drop_helper:
            self._stage_update = omni.stageupdate.get_stage_update_interface()
            self._stage_subscription = None
        else:
            self._stage_update = None
            self._stage_subscription = None

        try:
            from omni.kit.thumbnails.mdl import ThumbnailManager

            self._thumbnail_manager = ThumbnailManager()

        except ImportError:
            carb.log_info(
                "Failed to import thumbnail generation module (omni.kit.thumbnails.mdl). Please enable it first."
            )
            self._thumbnail_manager = None

    def destroy(self) -> None:
        """Destroys the MaterialDetailDelegate instance and releases resources including drop helper, stage subscription, stage update, context menu, and destroys the thumbnail manager if available."""
        self._drop_helper = None
        self._stage_subscription = None
        self._stage_update = None
        self._context_menu = None
        if self._thumbnail_manager is not None:
            self._thumbnail_manager.destroy()
        super().destroy()

    def get_label(self, item: MaterialDetailItem) -> Optional[str]:
        """Get a label for the material detail item.

        Args:
          item (MaterialDetailItem): Material detail item.

        Returns:
          Optional[str]: Derived label for the material detail item, or None if labels are hidden.
        """
        if self.hide_label:
            return None
        elif item.sub_material:
            return item.name
        else:
            return item.name[:-4]

    def get_thumbnail(self, item: MaterialDetailItem) -> str:
        """Get the thumbnail for a material detail item.

        Args:
          item (MaterialDetailItem): Material detail item.

        Returns:
          str: Thumbnail URL for the material detail item. Default to the predefined icon path if not found.
        """
        if item.thumbnail is None:
            return f"{ICON_PATH}/mdl_256.png"
        else:
            return item.thumbnail

    def get_tooltip(self, item: MaterialDetailItem) -> str:  # pragma: no cover
        """Get tooltip for the material detail item.

        Args:
          item (MaterialDetailItem): Material detail item.

        Returns:
          str: Tooltip string combining the item URL and sub material name if present, or the URL alone.
        """
        if item.sub_material:
            return item.url + "@" + item.sub_material.name
        else:
            return item.url

    def on_right_click(self, item: MaterialDetailItem) -> None:
        """Callback when the user right-clicks on a material detail item.

        Display the material context menu for the specified material detail item and set up menu items based on available actions and thumbnail generation capability.

        Args:
          item (MaterialDetailItem): Material detail item that was right clicked.
        """
        self._action_item = item
        # Show context menu to apply material
        if self._context_menu is None:
            self._context_menu = ui.Menu("Material context menu")
            with self._context_menu:
                ui.MenuItem("Apply to Selected", triggered_fn=self._apply_material)
                ui.MenuItem("Add to Stage", triggered_fn=self._add_material)
                if self.can_generate_thumbnail():
                    self._thumbnail_menu = ui.MenuItem("Generate thumbnail", triggered_fn=self._on_generate_thumbnail)
                else:
                    self._thumbnail_menu = None
                ui.MenuItem("Select Bound Objects", triggered_fn=self._select_bound_objects)

        if self._thumbnail_menu is not None:
            self._thumbnail_menu.enabled = True
            list_entry = item.file.list_entry
            if list_entry and not list_entry.access & omni.client.AccessFlags.WRITE:
                self._thumbnail_menu.enabled = False

        self._context_menu.show()

    def on_drag(self, item: MaterialDetailItem) -> str:
        """Callback when the user starts dragging a material detail item.

        Prepare the material detail item for a drag and drop operation by building UI elements and setting stage update subscriptions if needed, then return a drag payload URL.

        Args:
          item (MaterialDetailItem): Material detail item to be dragged.

        Returns:
          str: Drag payload URL constructed from the item URL and sub material details if applicable.
        """
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
            if item.sub_material:
                # For usd file, also show usd file name
                ui.Label(
                    item.url.split("/")[-1] + "@",
                    word_wrap=False,
                    elided_text=True,
                    skip_draw_when_clipped=True,
                    alignment=ui.Alignment.TOP,
                    style_type_name_override="GridView.Item",
                )
            ui.Label(
                item.name,
                word_wrap=False,
                elided_text=True,
                skip_draw_when_clipped=True,
                alignment=ui.Alignment.TOP,
                style_type_name_override="GridView.Item",
            )

        # After dragging, need set doNotCastShadows after material applied to prim in viewport
        if self._stage_update is not None and self._stage_subscription is None:
            self._action_item = item
            self._stage_subscription = self._stage_update.create_stage_update_node(
                "MaterialBrowserDragging", None, None, None, None, self._on_prim_changed, None
            )

        drag_url = item.url
        if self._drop_helper is None:
            return drag_url
        else:
            if item.sub_material:
                # OMPRW-834: There could be @ in file url, so use ? instead
                drag_url += "?" + item.sub_material.url

            return MATERIAL_DRAG_PAYLOAD_PREFIX + drag_url

    def can_generate_thumbnail(self) -> bool:
        """Check if thumbnail generation is available based on the presence of a thumbnail manager.

        Returns:
          bool: True if thumbnail generation is available; False otherwise.
        """
        return self._thumbnail_manager is not None

    def generate_thumbnail(self, item: MaterialDetailItem) -> None:
        """
        Generate thumbnail for detail item.
        Args:
            item (MaterialDetailItem): Detail item to generate thumbnail.
        """
        try:
            from omni.kit.thumbnails.mdl import MdlThumbnailGenerator, UsdThumbnailGenerator

        except ImportError:
            carb.log_info(
                "Failed to import thumbnail generation module (omni.kit.thumbnails.mdl). Please enable it first."
            )
            return

        if self._thumbnail_manager is None:
            return

        # First, update detail view to show empty thumbnail for the item
        item.file.thumbnail = None
        item.thumbnail = None
        self.item_changed(None, item)

        # Add a request to thumbnail manager to generate thumbnail later
        output_url = item.get_default_thumbmail_url()

        if item.file.type == MaterialType.MDL:
            # mdl material
            mtl_name = item.sub_material.name if item.sub_material else None
            self._thumbnail_manager.put(
                MdlThumbnailGenerator(
                    item.url,
                    output_url,
                    mtl_name=mtl_name,
                    on_thumbnail_done_fn=lambda result, url, item=item: self._on_thumbnail_generated(item, result, url),
                )
            )
        else:
            # usd material
            material_prim_path = item.sub_material.url if item.sub_material else None
            self._thumbnail_manager.put(
                UsdThumbnailGenerator(
                    item.url,
                    output_url,
                    material_prim_path=material_prim_path,
                    on_thumbnail_done_fn=lambda result, url, item=item: self._on_thumbnail_generated(item, result, url),
                )
            )

    def _on_prim_changed(self, path: str) -> None:
        usd_context = omni.usd.get_context()
        stage = usd_context.get_stage()
        prim = stage.GetPrimAtPath(path)
        if not prim:
            return

        material, relationship = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
        if material:
            material_name = material.GetPrim().GetPath().pathString
            # Once dragging a material to a prim, will create a new material with name in prim path
            # For example: World/Looks/{name}
            if self._action_item.name[:-4] in material_name:
                carb.log_info(
                    f"[MaterialBrowser] dragging {self._action_item.name} to {path}, set doNotCastShadows={self._action_item.donot_cast_shadows}"
                )
                self._stage_subscription = None
                if self._action_item.donot_cast_shadows is not None:
                    omni.kit.commands.execute(
                        "ChangePrimVarCommand",
                        prim_path=path,
                        primvar_name="doNotCastShadows",
                        value=self._action_item.donot_cast_shadows,
                        type_to_create_if_not_exist=Sdf.ValueTypeNames.Bool,
                    )

    def _apply_material(self) -> None:
        self._model.execute(self._action_item)

    def _select_bound_objects(self) -> None:
        """
        Select prims on stage that are using this material.
        Note we cannot use the material name as a key as:
        1. The material could have been renamed
        2. A material could have been created with a name identical to the one we are searching
           for but is not this material.

        Therefore we check the material source asset and subidentifier to determine if we have a match or not.
        """
        usd_context = omni.usd.get_context()
        stage = usd_context.get_stage()

        usd_context.get_selection().clear_selected_prim_paths()
        paths = set()
        for prim in stage.Traverse():
            if not omni.usd.is_prim_material_supported(prim):
                continue

            material_prim, rel = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial()
            if not material_prim:
                continue

            shader_prim = omni.usd.get_shader_from_material(material_prim, True)
            if not shader_prim:
                continue

            shader_prim = UsdShade.Shader(shader_prim)
            if not shader_prim:
                continue

            source_asset = shader_prim.GetSourceAsset("mdl")
            if not source_asset:
                continue

            item_name = (
                self._action_item.sub_material.name if self._action_item.sub_material else self._action_item.name[:-4]
            )

            resolved_path = source_asset.resolvedPath.replace("\\", "/")
            if (self._action_item.url != resolved_path) or (
                item_name != shader_prim.GetSourceAssetSubIdentifier("mdl")
            ):
                continue

            paths.add(prim.GetPath().pathString)

        usd_context.get_selection().set_selected_prim_paths(list(paths), True)

    def _add_material(self) -> None:
        self._model.create_material(self._action_item)

    def _on_generate_thumbnail(self) -> None:
        self.generate_thumbnail(self._action_item)

    def _on_thumbnail_generated(self, item: MaterialDetailItem, result: bool, thumbnail_url: str) -> None:
        if result:
            # Thumbnail generated, update detail view to display
            item.file.thumbnail = thumbnail_url
            item.thumbnail = thumbnail_url
            self.item_changed(None, item)

    def _on_drop_accepted(self, url):
        return url.startswith(MATERIAL_DRAG_PAYLOAD_PREFIX)

    @staticmethod
    def get_material_info_from_drop(url: str) -> Tuple[str]:
        """Get material url and sub material id from the drag drop URL.

        Extract material URL and sub material id from the drag drop URL by removing the prefix and splitting at the '?' character.

        Args:
          url (str): URL of the dragged item from the material browser.

        Returns:
          Tuple[str]: A tuple containing the material URL and sub material id; if no sub material, the second element is None.
        """
        material_url = url[len(MATERIAL_DRAG_PAYLOAD_PREFIX) :]
        paths = material_url.split("?")
        if len(paths) == 2:
            return paths
        else:
            return (material_url, None)

    def _on_drop(self, url, prim_path, model_path, viewport_name, context_name):
        material_url, sub_material_id = MaterialDetailDelegate.get_material_info_from_drop(url)

        self._dropped = False
        material_path = None
        if prim_path or model_path:
            self._dropped = True
            self._apply_drop_material(prim_path, model_path, material_url, sub_material_id, context_name)
        else:
            # dropped on empty space in viewport
            material_path = MaterialBrowserModel.create_material_by_url(material_url, sub_material_id, context_name)

        # Here must return a the material path for on_pick handle
        return material_path

    def _on_pick(self, material_path, target, context_name):
        # Empty -- This function used to fix OM-52089 but no longer needs
        pass

        # For sub material of vMaterial, nothing picked when dropping, need to pick and apply here
        # if target and not self._dropped:
        #     self._apply_drop_material(target, material_path, context_name)

    def _apply_drop_material(self, prim_path, model_path, material_url, sub_material_id, context_name) -> None:
        def __apply_material(target):
            if target:
                material_path = MaterialBrowserModel.create_material_by_url(material_url, sub_material_id, context_name)
                self._model.bind_material(material_path, [target])
                omni.usd.get_context(context_name).get_selection().set_selected_prim_paths([target], True)

        if prim_path or model_path:
            omni.kit.material.library.drop_material(
                prim_path=prim_path, model_path=model_path, apply_material_fn=__apply_material
            )
