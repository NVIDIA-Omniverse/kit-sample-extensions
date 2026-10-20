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
from typing import List

import carb
import carb.settings
import omni.kit.commands
from omni.kit.notification_manager import NotificationStatus, post_notification
from omni.kit.viewport.utility import get_active_viewport_window
from pxr import Usd, UsdLux

from .constants import ENVIRONMENT_PRIM_ROOT, SKY_PRIM_PATH, EnvironmentSettings, SkyType
from .scene_template import SceneTemplateHelper
from .sky import SkyHelper
from .utils import (
    block_replaced_environment_properties,
    can_remove_environment_content,
    delete_environment_prims,
    get_environment_edit_context,
    restore_environment_prim,
)
from .warning_window import WarningMessage, WarningWindow


def delete_lights(light_prims: List[Usd.Prim]):
    omni.kit.commands.execute("DeletePrimsCommand", paths=[prim.GetPath().pathString for prim in light_prims])
    # Return False to close warning dialog
    return False


# Kit 111's Runtime Core authors a fallback DistantLight (/OVRuntimeDefaultLight) on its own scaffold layer while the
# stage has no light of its own, and removes it once the stage gets one. It marks it with this customData key
# (omni.runtime.core.FALLBACK_LIGHT_CUSTOM_DATA_KEY); it is not one of the stage's lights. Read the key directly so this
# also runs without omni.runtime.core (Kit 110).
_RUNTIME_FALLBACK_LIGHT_KEY = "omni:runtime:fallbackLight"


def _is_runtime_fallback_light(prim) -> bool:
    return bool(prim) and bool(prim.GetCustomDataByKey(_RUNTIME_FALLBACK_LIGHT_KEY))


def check_lights(stage: Usd.Stage, check_env_root: bool = True):
    prims = stage.Traverse(Usd.TraverseInstanceProxies(Usd.PrimIsActive and Usd.PrimIsDefined and Usd.PrimIsLoaded))
    light_prims: List[Usd.Prim] = []
    for prim in prims:
        if _is_runtime_fallback_light(prim):
            continue
        if (
            prim.IsA(UsdLux.DistantLight)
            or prim.IsA(UsdLux.DomeLight)
            or prim.IsA(UsdLux.RectLight)
            or prim.IsA(UsdLux.DiskLight)
            or prim.IsA(UsdLux.SphereLight)
            or prim.IsA(UsdLux.CylinderLight)
        ):
            path = prim.GetPath().pathString
            if path.startswith(ENVIRONMENT_PRIM_ROOT):
                if check_env_root:
                    path = path[len(ENVIRONMENT_PRIM_ROOT) + 1 :]
                    if len(path.split("/")) == 1:
                        # Only check lights under env root
                        light_prims.append(prim)
            else:
                light_prims.append(prim)

    if light_prims:
        messages = [
            WarningMessage(f"{len(light_prims)} extra light(s) found!"),
            "\n",
        ]
        for prim in light_prims:
            messages.append(WarningMessage(f"\t{prim.GetPath().pathString}", highlight=True))
            messages.append("\n")
        messages.extend(["Do you want to delete these exising lights?"])

        warn_window = WarningWindow(
            "Extra Lights Warning",
            messages=messages,
            buttons=[("Delete", lambda p=light_prims: delete_lights(p)), ("Keep", None)],
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


def clean_environment(type: SkyType, url: str) -> None:
    stage = omni.usd.get_context().get_stage()
    if not stage:
        return

    exist_sky_path, exist_asset_path = SkyHelper.find_sky()
    if exist_asset_path:
        if exist_asset_path == url:
            carb.log_warn(f"[Sky Browser] Sky {url} is the current sky, do nothing.")
            return

    # OMPE-64890: removing is authoring too, so it needs the same writable layer as the replacement
    with get_environment_edit_context(stage):
        if type == SkyType.SCENE:
            # For a new scene template, clean old env

            # Remove scene template including sub layer
            SceneTemplateHelper().remove_current_scene_template()

            # Remove env prim
            env_prim = stage.GetPrimAtPath(ENVIRONMENT_PRIM_ROOT)
            if env_prim:
                delete_environment_prims(stage, [ENVIRONMENT_PRIM_ROOT])
        elif exist_sky_path:
            # Clean sky only
            delete_environment_prims(stage, [exist_sky_path])


def apply_environment(stage: Usd.Stage, type: str, url: str) -> str:
    # OMPE-64890: author into a writable layer so a non-writable root layer still applies.
    with get_environment_edit_context(stage):
        # OM-66383: Make sure env root is Xform
        environment_root_prim = stage.GetPrimAtPath(ENVIRONMENT_PRIM_ROOT)
        if not environment_root_prim:
            stage.DefinePrim(ENVIRONMENT_PRIM_ROOT, "Xform")
        # OMPE-64890: unhide the prims this environment authors again
        restore_environment_prim(stage, ENVIRONMENT_PRIM_ROOT)

        if type == SkyType.SCENE:
            carb.log_info(f"[Env] apply template: {url}")
            return SceneTemplateHelper().apply_scene_template(url)

        restore_environment_prim(stage, SKY_PRIM_PATH)
        if type == SkyType.DYNAMIC:
            sky_path = SkyHelper.create_dynamic_sky(url)
        elif type == SkyType.HDRI:
            sky_path = SkyHelper.create_hdri_sky(url)
        else:
            return None

        # OMPE-64890: now that the new sky is authored, block what the previous one still
        # contributes to the prims it reuses
        block_replaced_environment_properties(stage, ENVIRONMENT_PRIM_ROOT)
        block_replaced_environment_properties(stage, sky_path)
        return sky_path


def import_environment(type: SkyType, url: str) -> str:
    """Imports an environment into the current USD stage.

    Cleans the existing environment and, if light warnings are enabled, checks for extra lights before applying the new environment based on the provided type and url. Returns an empty string if no USD stage is available.

    Args:
        type (SkyType): Environment sky type to import.
        url (str): File path or url of the environment to import.

    Returns:
        str: Result of the environment application, or an empty string if no stage is available.
    """
    stage = omni.usd.get_context().get_stage()
    if not stage:
        return ""

    if type == SkyType.SCENE and not can_remove_environment_content(stage):
        # OMPE-64890: a template replaces the whole environment, so the previous one has to be
        # removed. A sky is replaced at a known prim path and can be hidden instead, a template
        # brings arbitrary content and prim metadata cannot be suppressed at all.
        message = "Cannot apply a scene template: this stage is read-only. Save it to a writable location first."
        carb.log_warn(f"[Env] {message}")
        post_notification(message, hide_after_timeout=True, status=NotificationStatus.WARNING)
        return ""

    clean_environment(type, url)

    if carb.settings.get_settings().get(EnvironmentSettings.SHOW_LIGHT_WARNING):
        check_lights(stage)

    apply_environment(stage, type, url)


def register_actions(extension_id):
    try:
        import omni.kit.actions.core

        action_registry = omni.kit.actions.core.get_action_registry()
        actions_tag = "Environment"

        action_registry.register_action(
            extension_id,
            "import",
            lambda type, url: import_environment(type, url),
            display_name="Environment->Import",
            description="Import environment files to stage",
            tag=actions_tag,
        )
    except ImportError:
        pass


def deregister_actions(extension_id):
    try:
        import omni.kit.actions.core

        action_registry = omni.kit.actions.core.get_action_registry()
        action_registry.deregister_all_actions_for_extension(extension_id)
    except ImportError:
        pass
