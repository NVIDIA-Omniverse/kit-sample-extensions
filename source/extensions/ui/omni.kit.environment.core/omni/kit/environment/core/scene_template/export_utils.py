# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["export", "ExportPrimUSD"]

import asyncio
from functools import partial
from pathlib import Path
from typing import Callable, Optional

import carb
import carb.settings
import carb.tokens
import omni.client
import omni.kit.commands
import omni.usd
from omni.kit.notification_manager import NotificationStatus, post_notification
from omni.kit.viewport.utility import get_active_viewport
from pxr import Sdf, Usd, UsdGeom, UsdShade, UsdUI

from ..constants import ENVIRONMENT_PRIM_ROOT
from .prompt_ui import Prompt

last_dir = None

SETTING_POPUPLATE_MDL_INPUTS_ON_LOAD = "/exts/omni.usd/mdl/populateInputsOnLoaded"
INPUTS_Z_UP = "inputs:z_up"


async def import_from_usd(path: str, url: str, apply_camera: bool = True) -> None:
    """
    Import prim from external USD file
    Args:
        path [str]: Prim path
        url [str]: External USD file
    """

    stage = omni.usd.get_context().get_stage()
    axis = UsdGeom.GetStageUpAxis(stage)
    z_up = axis == "Z"

    # OM-103030: In living mode, add template in live layer
    target_layer = stage.GetEditTarget().GetLayer()

    # Set material inputs to be populated when loaded
    # Otherwise could not read z up attribute
    settings = carb.settings.get_settings()
    saved_mdl_on_load = settings.get(SETTING_POPUPLATE_MDL_INPUTS_ON_LOAD)
    if not saved_mdl_on_load:
        settings.set(SETTING_POPUPLATE_MDL_INPUTS_ON_LOAD, True)

    temp_stage = Usd.Stage.CreateInMemory()
    current_stage = omni.usd.get_context().get_stage()
    temp_root_layer = temp_stage.GetRootLayer()
    temp_root_layer.subLayerPaths.append(url)

    # Only fetch shaders in template
    template_shaders = []
    prim_range = temp_stage.Traverse(
        Usd.TraverseInstanceProxies(Usd.PrimIsActive and Usd.PrimIsDefined and Usd.PrimIsLoaded)
    )
    for prim in prim_range:
        if prim.IsA(UsdShade.Shader):
            template_shaders.append(prim.GetPath())

    temp_root_layer.subLayerPaths.insert(0, current_stage.GetRootLayer().identifier)

    omni.usd.stitch_prim_specs(temp_stage, path, target_layer)
    temp_stage = None

    # Waiting for material inputs loaded
    for _ in range(2):
        await omni.kit.app.get_app().next_update_async()

    # For shaders in template, set Z up if shader has this attribute
    for shader_path in template_shaders:
        shader_prim = current_stage.GetPrimAtPath(shader_path)
        if shader_prim:
            # Here do not use load_mdl_parameters_for_prim_async because sometimes there will be error
            # When new stage and load
            # await omni.usd.get_context().load_mdl_parameters_for_prim_async(shader_prim)
            if shader_prim.HasAttribute(INPUTS_Z_UP):
                attr = shader_prim.GetAttribute(INPUTS_Z_UP)
                if attr:
                    carb.log_info(f"Set z_up: {z_up} for {shader_prim}")
                    attr.Set(z_up)

    # Restore setting
    if not saved_mdl_on_load:
        settings.set(SETTING_POPUPLATE_MDL_INPUTS_ON_LOAD, saved_mdl_on_load)

    if apply_camera:
        camera_paths = []

        def on_prim_spec_path(prim_spec_path):
            if prim_spec_path.IsPropertyPath():
                return

            if prim_spec_path == Sdf.Path.absoluteRootPath:
                return

            prim_spec: Sdf.PrimSpec = target_layer.GetPrimAtPath(prim_spec_path)
            if not prim_spec:
                return

            if "Camera" == prim_spec.typeName:
                camera_paths.append(prim_spec_path)

        target_layer.Traverse(path, on_prim_spec_path)
        if camera_paths:
            carb.log_info(f"Set camera to {camera_paths[0]}")
            viewport_api = get_active_viewport(omni.usd.get_context())
            if viewport_api:
                viewport_api.camera_path = camera_paths[0]


async def import_from_usd_async(path: str, url: str, prompt_message: str) -> None:
    with Prompt("Please Wait", prompt_message, [], [], modal=True):
        for _ in range(2):
            await omni.kit.app.get_app().next_update_async()

        await import_from_usd(path, url)


def export(path: str, prim: Usd.Prim) -> None:
    """
    Export prim to external USD file
    Args:
        path [str]: Path to external USD file
        prim [Usd.Prim]: Prim to export
    """
    filename = Path(path).stem

    # TODO: stage.Flatten() is extreamly slow
    source_layer = prim.GetStage().Flatten()
    target_layer = Sdf.Layer.FindOrOpen(path)
    if not target_layer:
        target_layer = Sdf.Layer.CreateNew(path)
    source_path = prim.GetPath()
    target_path = Sdf.Path.absoluteRootPath.AppendChild(source_path.name)

    all_external_references = set([])

    def on_prim_spec_path(root_path, prim_spec_path):
        if prim_spec_path.IsPropertyPath():
            return

        if prim_spec_path == Sdf.Path.absoluteRootPath:
            return

        prim_spec = source_layer.GetPrimAtPath(prim_spec_path)
        if not prim_spec or not prim_spec.HasInfo(Sdf.PrimSpec.ReferencesKey):
            return

        op = prim_spec.GetInfo(Sdf.PrimSpec.ReferencesKey)
        items = []
        items = op.ApplyOperations(items)

        for item in items:
            if not item.primPath.HasPrefix(root_path) and item.primPath:
                all_external_references.add(item.primPath)

    # Traverse the source prim tree to find all references that are outside of the source tree.
    source_layer.Traverse(source_path, partial(on_prim_spec_path, source_path))

    # Copy dependencies
    for path in all_external_references:
        Sdf.CreatePrimInLayer(target_layer, path)
        Sdf.CopySpec(source_layer, path, target_layer, path)

    Sdf.CreatePrimInLayer(target_layer, target_path)
    Sdf.CopySpec(source_layer, source_path, target_layer, target_path)
    stage = omni.usd.get_context().get_stage()
    target_stage = Usd.Stage.Open(target_layer)
    axis = UsdGeom.GetStageUpAxis(stage)
    UsdGeom.SetStageUpAxis(target_stage, axis)

    # Set default prim name
    target_layer.defaultPrim = target_path.name

    # Edit UI info of compound
    spec = target_layer.GetPrimAtPath(target_path)
    attributes = spec.attributes

    if UsdUI.Tokens.uiDisplayGroup not in attributes:
        attr = Sdf.AttributeSpec(spec, UsdUI.Tokens.uiDisplayGroup, Sdf.ValueTypeNames.Token)
        attr.default = "Material Graphs"

    if UsdUI.Tokens.uiDisplayName not in attributes:
        attr = Sdf.AttributeSpec(spec, UsdUI.Tokens.uiDisplayName, Sdf.ValueTypeNames.Token)
        attr.default = target_path.name

    if "ui:order" not in attributes:
        attr = Sdf.AttributeSpec(spec, "ui:order", Sdf.ValueTypeNames.Int)
        attr.default = 1024

    # Save
    target_layer.Save()


async def export_async(path: str, prim: Usd.Prim, prompt_message: Optional[str] = None):
    with Prompt("Please Wait", prompt_message, [], [], modal=True):
        for _ in range(2):
            await omni.kit.app.get_app().next_update_async()

        export(path, prim)


class ExportPrimUSD:
    EXPORT_USD_EXTS = ("usd", "usda", "usdc")

    def __init__(self, select_msg="Save As", save_msg="Save", save_dir=None, postfix_name=None, prompt=False):
        self._prim = None
        self._dialog = None
        self._select_msg = select_msg
        self._save_msg = save_msg
        self._save_dir = save_dir
        self._postfix_name = postfix_name
        self._last_dir = None
        self._prompt = prompt

    def destroy(self):
        self._prim = None
        if self._dialog:
            self._dialog.destroy()
            self._dialog = None

    def export(self, prim, callback: Callable[[str], None]):
        self.destroy()

        self._prim = prim

        write_dir = self._save_dir
        if not write_dir:
            write_dir = last_dir if last_dir else ""

        try:
            from omni.kit.window.filepicker import FilePickerDialog

            usd_filter_descriptions = [f"{ext.upper()} (*.{ext})" for ext in self.EXPORT_USD_EXTS]
            usd_filter_descriptions.append("All Files (*)")
            self._dialog = FilePickerDialog(
                self._select_msg,
                apply_button_label=self._save_msg,
                current_directory=write_dir,
                click_apply_handler=lambda f, d, c=callback: self.__on_apply_save(f, d, c),
                item_filter_options=usd_filter_descriptions,
                item_filter_fn=self.__on_filter_item,
            )

            return self._dialog
        except:
            carb.log_info(f"Failed to import omni.kit.window.filepicker")
            return None

    def __on_filter_item(self, item: "FileBrowserItem") -> bool:
        if not item or item.is_folder:
            return True
        if self._dialog.current_filter_option < len(self.EXPORT_USD_EXTS):
            # Show only files with listed extensions
            return item.path.endswith("." + self.EXPORT_USD_EXTS[self._dialog.current_filter_option])
        else:
            # Show All Files (*)
            return True

    def __on_apply_save(self, filename: str, dir: str, callback: Callable[[str], None] = None):
        """Called when the user presses the Save button in the dialog"""
        global last_dir
        last_dir = dir

        if not filename:
            return

        # Get the file extension from the filter
        if not filename.lower().endswith(self.EXPORT_USD_EXTS):
            if self._dialog.current_filter_option < len(self.EXPORT_USD_EXTS):
                filename += "." + self.EXPORT_USD_EXTS[self._dialog.current_filter_option]
        # Add postfix name
        if self._postfix_name:
            filename = filename.replace(".usd", f".{self._postfix_name}.usd")

        path = omni.client.combine_urls(dir + "/", filename)
        self._dialog.hide()

        # check dest file
        result, list_entry = omni.client.stat(path)
        if result == omni.client.Result.OK:
            if not list_entry.access & omni.client.AccessFlags.WRITE:
                post_notification(
                    f"Scene template '{path}' is readonly, save to another one!",
                    hide_after_timeout=True,
                    status=NotificationStatus.WARNING,
                )
                return

        if self._prompt:

            async def __export_async():
                await export_async(f"{path}", self._prim, prompt_message=f"Saving {path} ...")
                if callback is not None:
                    callback(path)

                self._prim = None

            asyncio.ensure_future(__export_async())

        else:
            export(f"{path}", self._prim)
            if callback is not None:
                callback(path)

            self._prim = None
