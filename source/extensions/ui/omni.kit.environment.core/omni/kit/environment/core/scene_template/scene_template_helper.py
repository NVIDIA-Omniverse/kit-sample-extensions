# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
from typing import Callable, List, Optional

import carb
import carb.settings
import omni.client
import omni.kit.commands
import omni.usd
from omni.kit.viewport.utility import get_active_viewport, get_active_viewport_window
from pxr import Gf, Sdf, Usd, UsdGeom

from ..constants import ENVIRONMENT_PRIM_ROOT, EnvironmentProperties
from ..singleton import Singleton
from ..utils import get_environment_edit_target_layer
from ..warning_window import WarningWindow
from .export_utils import ExportPrimUSD, export, export_async, import_from_usd_async


@Singleton
class SceneTemplateHelper:
    """SceneTemplateHelper is a helper class that manages scene template operations for environment in USD stages.

    This class retrieves, updates, and applies scene template URLs from a USD stage. It supports saving the current scene template, loading a new one, and applying associated render settings when required. Callback functions can be registered to perform additional actions after a scene template is applied.

    Args:
        context_name (str): Identifier for the USD context used for stage retrieval.
    """

    def __init__(self, context_name: str = ""):
        self._usd_context = omni.usd.get_context(context_name)
        self._on_apply_scene_template_fns: List[Callable[[str], None]] = []

    def __del__(self):
        self._on_apply_scene_template_fns.clear()

    def add_on_apply_scene_template_fn(self, on_apply_scene_template_fn: Callable[[str], None]) -> None:
        """Adds a callback function to be triggered after applying a scene template.

        If the function already exists, it is not added again.

        Args:
            on_apply_scene_template_fn (Callable[[str], None]): Callback function triggered with the scene template URL.
        """
        if on_apply_scene_template_fn in self._on_apply_scene_template_fns:
            return
        else:
            self._on_apply_scene_template_fns.append(on_apply_scene_template_fn)

    def get_scene_template_url(self, stage: Usd.Stage = None) -> str:
        """Retrieves the scene template URL from the stage's environment property.

        If stage is not provided, the current stage from the USD context is used.

        Args:
            stage (Usd.Stage, optional): Stage from which to retrieve the scene template URL.

        Returns:
            str: Scene template URL or an empty string if not defined.
        """
        if not stage:
            stage = self._usd_context.get_stage()

        scene_template_prop = stage.GetPropertyAtPath(EnvironmentProperties.SCENE_TEMPLATE)
        return scene_template_prop.Get() if scene_template_prop else ""

    def save_scene_template_url(self, url: str, stage: Usd.Stage = None):
        """Updates the stage by setting the scene template URL.

        Args:
            url (str): Scene template URL to save.
            stage (Usd.Stage, optional): Stage to update with the new scene template URL.
        """
        if not stage:
            stage = self._usd_context.get_stage()

        prop = stage.GetPropertyAtPath(EnvironmentProperties.SCENE_TEMPLATE)
        if prop:
            # Marks stage dirty manually since settings change are not synced to USD until user saves.
            omni.usd.get_context().set_pending_edit(True)
            prop.Set(url)
        else:
            prim_path, attr_name = EnvironmentProperties.SCENE_TEMPLATE.split(".")
            prim = stage.GetPrimAtPath(prim_path)
            if prim:
                prim.CreateAttribute(attr_name, Sdf.ValueTypeNames.String).Set(url)
            else:
                carb.log_info(f"[{EnvironmentProperties.SCENE_TEMPLATE}] Cannot set value since prim does not exists!")

    def get_scene_template_layer(self, stage: Usd.Stage = None) -> Sdf.Layer:
        """Gets the scene template layer from the stage.

        Args:
            stage (Usd.Stage, optional): Stage used to retrieve the scene template layer.

        Returns:
            Sdf.Layer: Scene template layer or the current edit target layer if scene template is not set.
        """
        scene_template = self.get_scene_template_url(stage=stage)
        if scene_template:
            current_layer = Sdf.Layer.Find(scene_template)
        else:
            current_layer = stage.GetEditTarget().GetLayer()

        return current_layer

    def get_edit_context(self, stage: Optional[Usd.Stage] = None) -> Usd.EditContext:
        """Gets edit context for scene template from stage.

        Args:
            stage (Usd.Stage, optional): Stage for creating the edit context.

        Returns:
            Usd.EditContext: Edit context corresponding to the scene template layer.
        """
        if not stage:
            stage = self._usd_context.get_stage()

        layer = self.get_scene_template_layer(stage=stage)
        return Usd.EditContext(stage, layer)

    def save(self, url: Optional[str] = None, on_save_done: Callable = None) -> bool:
        """Saves the environment prim by exporting its content to the specified scene template URL. Returns False if the environment prim does not exist or if the URL is missing.

        Args:
            url (Optional[str]): Scene template URL for saving; if None, the existing URL is used.
            on_save_done (Callable): Callback function executed after saving is complete.

        Returns:
            bool: Returns False if the environment prim does not exist or if the URL is missing. Otherwise, returns True.
        """
        if url is None:
            url = self.get_scene_template_url()
            if not url:
                carb.log_error("No scene template to save!")
                return False

        env_prim = self._usd_context.get_stage().GetPrimAtPath(ENVIRONMENT_PRIM_ROOT)
        if not env_prim:
            return False

        async def __save_sync():
            await export_async(url, env_prim, f"Saving {url}...")
            if on_save_done:
                on_save_done()

        asyncio.ensure_future(__save_sync())

        return True

    def save_as(self, on_save_done: Callable = None):
        """Exports the environment prim as a new scene template.

        Opens a dialog to prompt for a new URL and updates the scene template URL upon successful export.

        Args:
            on_save_done (Callable): Callback function that receives the new URL after saving.

        Returns:
            Any: Result from exporting the new scene template, or None if the environment prim is missing.
        """
        env_prim = self._usd_context.get_stage().GetPrimAtPath(ENVIRONMENT_PRIM_ROOT)
        if env_prim:

            def __saved(url):
                self.save_scene_template_url(url)
                if on_save_done:
                    on_save_done(url)

            return ExportPrimUSD(
                select_msg="Save Environment As New Scene Template", save_msg="Save", save_dir="", prompt=True
            ).export(env_prim, __saved)
        return None

    def apply_scene_template(self, url) -> str:
        """Applies the scene template from the given URL.

        If render settings are available, prompts the user to choose whether to import them.

        Args:
            url (str): Scene template URL to apply.

        Returns:
            str: ENVIRONMENT_PRIM_ROOT identifier.
        """
        carb.log_info(f"Apply scene template: {url}")
        render_settings = self._get_render_settings(url)
        if render_settings:
            warn_window = WarningWindow(
                "Apply Scene Template",
                always_show_option=False,
                messages="Do you want to import the render settings from the template environment?\nThis will replace the current render settings.",
                buttons=[
                    ("Yes", lambda u=url, s=render_settings: self.__apply_scene_template(u, s)),
                    ("No", lambda u=url: self.__apply_scene_template(u)),
                ],
            )

            viewport_window = get_active_viewport_window()
            if viewport_window:

                async def __adjust_position():
                    while warn_window.frame.computed_width < 10:
                        await omni.kit.app.get_app().next_update_async()
                    warn_window.position_x = (
                        viewport_window.position_x + (viewport_window.width - warn_window.frame.computed_width) / 2
                    )
                    warn_window.position_y = (
                        viewport_window.position_y + (viewport_window.height - warn_window.frame.computed_height) / 2
                    )

                asyncio.ensure_future(__adjust_position())
        else:
            self.__apply_scene_template(url)

        return ENVIRONMENT_PRIM_ROOT

    def __apply_scene_template(self, url: str, render_settings: Optional[dict] = None):
        stage = self._usd_context.get_stage()
        if not stage.GetPrimAtPath(ENVIRONMENT_PRIM_ROOT):
            # OM-62555 / OM-57577: create ENV in the .live file in a live session, else in the root
            with Usd.EditContext(stage, get_environment_edit_target_layer(stage)):
                stage.DefinePrim(ENVIRONMENT_PRIM_ROOT, "Xform")

        async def __apply():
            await import_from_usd_async(ENVIRONMENT_PRIM_ROOT, url, f"Loading {url}...")
            stage = self._usd_context.get_stage()
            self._set_stage_up(stage, url, ENVIRONMENT_PRIM_ROOT)
            self.save_scene_template_url(url)

            for fn in self._on_apply_scene_template_fns:
                fn(url)

            if render_settings:
                await omni.kit.app.get_app().next_update_async()
                self._apply_render_settings(render_settings)

        asyncio.ensure_future(__apply())

    def remove_current_scene_template(self) -> None:
        """Removes the current scene template by clearing the scene template URL if it exists."""
        url = self.get_scene_template_url()
        if not url:
            return

        self.save_scene_template_url("")

    def _set_stage_up(self, stage: Usd.Stage, url: str, path: str):
        # Traverse prims in sublayer and update transform if UpAxis is different in sublayer and stage
        ref_stage = Usd.Stage.Open(url)
        if ref_stage:
            ref_up = UsdGeom.GetStageUpAxis(ref_stage)
            curr_up = UsdGeom.GetStageUpAxis(stage)

            if ref_up != curr_up:
                adj_mat = Gf.Matrix4d()
                if ref_up == "Y":
                    adj_mat = Gf.Matrix4d(
                        0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0
                    )
                elif ref_up == "Z":
                    adj_mat = Gf.Matrix4d(
                        0.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0
                    )
                if adj_mat != Gf.Matrix4d():
                    adj_prim_paths: List[str] = []

                    env_prim = stage.GetPrimAtPath(path)
                    for prim in env_prim.GetAllChildren():
                        if prim.IsA(UsdGeom.Xformable):
                            adj_prim_paths.append(prim.GetPath().pathString)

                    if adj_prim_paths:
                        adj_prim_paths.sort()
                        done_prim_paths: List[str] = []
                        for path in adj_prim_paths:
                            for done in done_prim_paths:
                                if path.startswith(done):
                                    # Once parent prim adjusted, do nothing to children
                                    break
                            else:
                                prim = stage.GetPrimAtPath(path)
                                ref_xform_mat = UsdGeom.Xformable(prim).GetLocalTransformation()
                                ref_xform_mat = ref_xform_mat * adj_mat
                                omni.kit.commands.execute(
                                    "TransformPrim", path=prim.GetPrimPath(), new_transform_matrix=ref_xform_mat
                                )
                                done_prim_paths.append(path)

    def _get_render_settings(self, url: str) -> Optional[dict]:
        # Get renderer settings with current render mode
        # Now supports "rt" and "pt" only
        vp = get_active_viewport()
        if not vp:
            return None
        engine = vp.hydra_engine
        if engine != "rtx":
            return None
        rtx_mode = {
            "RaytracedLighting": "rt",
            "PathTracing": "pt",
            "RealTimePathTracing": "rtpt",
        }.get(carb.settings.get_settings().get("/rtx/rendermode"), None)

        if rtx_mode is None:
            return None

        pos = url.rfind(".")
        file_name = url[0:pos]
        render_setting_file = file_name + "_" + rtx_mode + ".usd"
        result, _ = omni.client.stat(render_setting_file)
        if result == omni.client.Result.OK:
            carb.log_info(f"- Trying to load render settings: {render_setting_file}")
            stage = Usd.Stage.Open(render_setting_file)
            if stage:
                settings = stage.GetMetadataByDictKey("customLayerData", "renderSettings")
                stage = None
                return settings

        return None

    def _apply_render_settings(self, render_settings: dict) -> None:
        # Restore all render settings to default
        try:
            import omni.rtx.window.settings

            omni.kit.commands.execute("RestoreDefaultRenderSettingSection", path="/rtx")
        except ImportError:
            pass

        # Apply new settings
        settings = carb.settings.get_settings()
        for key, value in render_settings.items():
            key = "/" + key.replace(":", "/")

            if type(value) == str or type(value) == int or type(value) == bool or type(value) == float:
                settings.set(key, value)
            else:
                value_array = [value[i] for i in range(len(value))]
                settings.set(key, value_array)
