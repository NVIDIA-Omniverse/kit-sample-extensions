# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import os
from typing import Optional, Tuple

import carb
import carb.settings
import carb.tokens
import omni.client
import omni.kit.commands
import omni.kit.notification_manager as nm
import omni.kit.undo
import omni.usd
from carb.eventdispatcher import get_eventdispatcher
from pxr import Gf, Sdf, UsdGeom, UsdLux

from ..constants import (
    ENVIRONMENT_PRIM_ROOT,
    SKY_PRIM_PATH,
    EnvironmentSettings,
    SkyType,
)
from ..scene_template import SceneTemplateHelper
from .commands import CreateDynamicSkyCommand, CreateHdriSkyCommand


class SkyHelper:
    """
    Helper for environment sky. Use to find or create sky.
    """

    def __init__(self):
        self._settings = carb.settings.get_settings()

        context = omni.usd.get_context()
        self._stage_event_sub = get_eventdispatcher().observe_event(
            observer_name="omni.kit.environment.core.SkyHelper",
            event_name=context.stage_event_name(omni.usd.StageEventType.OPENED),
            on_event=self._on_stage_opened,
        )

    def destroy(self):
        """Destroys the stage event subscription for environment sky updates."""
        self._stage_event_sub = None

    def _on_stage_opened(self, _):
        if self._settings.get(EnvironmentSettings.ENV_AUTO):
            sky_prim_path, _ = SkyHelper.find_sky()
            if sky_prim_path is None:
                self._create_default_sky()

    @staticmethod
    def get_env_file_type(url: str) -> Optional[SkyType]:
        """Detects the environment sky file type based on the provided URL.

        Args:
            url (str): URL of the environment file.

        Returns:
            Optional[SkyType]: Sky file type if detected, otherwise None.
        """
        if not url:
            return None

        if url.lower().endswith(".hdr"):
            type = SkyType.HDRI
        else:
            # Get type from usd contents
            source_layer = Sdf.Layer.FindOrOpen(url)
            if source_layer.GetPrimAtPath(ENVIRONMENT_PRIM_ROOT):
                type = SkyType.SCENE
            else:
                type = SkyType.DYNAMIC
            source_layer = None
        return type

    @staticmethod
    def find_sky(
        root_path: str = ENVIRONMENT_PRIM_ROOT,
    ) -> Tuple[Optional[str], Optional[str]]:
        """Finds the sky prim and its associated asset path from the specified root prim.

        Args:
            root_path (str): Root prim path to search for sky.

        Returns:
            Tuple[Optional[str], Optional[str]]: Sky prim path and sky asset path if found; otherwise, (None, None).
        """
        stage = omni.usd.get_context().get_stage()
        if not stage:
            return (None, None)
        sky_root_prim = stage.GetPrimAtPath(root_path)
        if not sky_root_prim:
            return (None, None)
        children = sky_root_prim.GetChildren()
        for prim in children:
            # check if hdr sky by type name
            if prim.GetTypeName() == "DomeLight":
                prim_path = prim.GetPath().pathString
                sky_path = None
                attr_texture = prim.GetAttribute("texture:file")
                if attr_texture:
                    sky_path = attr_texture.Get().resolvedPath
                return (prim_path, sky_path)

            # check if usd sky by path
            prim_path = prim.GetPath().pathString
            skymatpath = prim_path + "/Looks/SkyMaterial"
            sunlightpath = prim_path + "/AxisNorth/AxisLatitude/AxisSHA/AxisDeclination/DistantLight"
            if stage.GetPrimAtPath(sunlightpath).IsValid() and stage.GetPrimAtPath(skymatpath).IsValid():
                ref_and_layers = omni.usd.get_composed_references_from_prim(prim)
                sky_path = None
                for ref, layer in ref_and_layers:
                    sky_path = ref.assetPath
                return (prim_path, sky_path)
        else:
            # OM-73228: there may be a empty sky prim. Also need to clean up before creating new sky
            sky_prim = stage.GetPrimAtPath(root_path + "/sky")
            if sky_prim:
                return (sky_prim.GetPath().pathString, None)
            return (None, None)

    @staticmethod
    def create_hdri_sky(url: str, sky_path: str = SKY_PRIM_PATH) -> str:
        """Creates an HDRI sky from the provided URL.

        Args:
            url (str): URL to the sky file.
            sky_path (str): Prim path where the sky will be created. Default is SKY_PRIM_PATH.

        Returns:
            str: Prim path if creation is successful; otherwise, an empty string.
        """
        # TODO: use it for sky browser
        result, _ = omni.client.stat(url)
        if result == omni.client.Result.OK:
            omni.kit.commands.execute("CreateHdriSkyCommand", sky_url=url, sky_path=sky_path)
            return sky_path
        else:
            carb.log_error(f"Failed to create sky: {url} {result}")
            return ""

    @staticmethod
    def create_dynamic_sky(url: str, sky_path=SKY_PRIM_PATH) -> str:
        """Creates dynamic sky from the provided URL.

        Args:
            url (str): URL to the sky file.
            sky_path (str): Prim path where the sky will be created. Default is SKY_PRIM_PATH.

        Returns:
            str: Prim path if creation is successful; otherwise, an empty string.
        """
        # TODO: use it for sky browser
        result, _ = omni.client.stat(url)
        if result == omni.client.Result.OK:
            omni.kit.commands.execute("CreateDynamicSkyCommand", sky_url=url, sky_path=sky_path)
            return sky_path
        else:
            carb.log_error(f"Failed to create sky: {url} {result}")
            return ""

    def _create_default_sky(self):
        default_env_url = self._settings.get(EnvironmentSettings.ENV_DEFAULT)
        default_env_url = carb.tokens.get_tokens_interface().resolve(default_env_url)
        # If sky file defined in perssitent not found, change to the one in default setting
        result, entry = omni.client.stat(default_env_url)
        if result != omni.client.Result.OK:
            default_url = self._settings.get(EnvironmentSettings.ENV_DEFAULT[len("/persistent") :])
            carb.log_info(f"{default_env_url} not found, trying default {default_url}.")
            if not default_url:
                carb.log_warn(f"No default sky file found.")
                return
            default_env_url = default_url

        env_type = SkyHelper.get_env_file_type(default_env_url)
        if not env_type:
            return

        if env_type == SkyType.HDRI:
            SkyHelper.create_hdri_sky(default_env_url)
        elif env_type == SkyType.DYNAMIC:
            SkyHelper.create_dynamic_sky(default_env_url)
        elif env_type == SkyType.SCENE:
            SceneTemplateHelper().apply_scene_template(default_env_url)
