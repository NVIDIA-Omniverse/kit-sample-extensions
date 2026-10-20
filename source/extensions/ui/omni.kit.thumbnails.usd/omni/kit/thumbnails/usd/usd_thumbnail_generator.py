# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import os.path
from pathlib import Path

import carb
import omni.kit.commands
import omni.usd

from .viewport_thumbnail_generator import ViewportThumbnailGenerator

EXTENSION_FOLDER_PATH = Path(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
DATA_PATH = EXTENSION_FOLDER_PATH.joinpath("data")
DEFAULT_ASSET_TEMPLATE = str(DATA_PATH.joinpath("template_v1.usd"))


class UsdThumbnailGenerator(ViewportThumbnailGenerator):
    """
    Generate Asset thumbnail

    Args:
        usd_url (str): Url of usd asset to generate thumbnail
        output_url (str): Url of generated thumbnail

    Keyword args:
        template_url (str): Url of template to generate thumbnail. Default DEFAULT_ASSET_TEMPLATE.
        render_mode (str): Render mode when generating thumbnail. Default RayTracing.
        width (int): Width of generated thumbnail, in pixels. Default 256.
        height (int): Height of generate thumbnail, in pixels. Default 256.
        on_thumbnail_done_fn (callable): Function called when thumbnail generation is done. Function signture:
            void on_thumbnail_done_fn(result: bool, url: str)
    """

    def __init__(
        self,
        usd_url: str,
        output_url: str,
        template_url: str = DEFAULT_ASSET_TEMPLATE,
        width: int = 256,
        height: int = 256,
        on_thumbnail_done_fn: callable = None,
    ):
        super().__init__(
            template_url,
            output_url,
            width=width,
            height=height,
            render_mode="PathTracing",
            iterations=32,
            on_thumbnail_done_fn=on_thumbnail_done_fn,
        )
        self._usd_url = usd_url

    def __get_framing_params(self):
        try:
            from omni.kit.viewport.window import get_viewport_window_instances

            for window in get_viewport_window_instances():
                viewport_api = window.viewport_api
                return (
                    viewport_api.camera_path,
                    viewport_api.resolution,
                    viewport_api.time,
                    viewport_api.usd_context_name,
                )
        except ImportError:
            pass

        try:
            from omni.kit.viewport.utility import get_active_viewport

            default_viewport = get_active_viewport()
            if default_viewport:
                return (
                    default_viewport.get_active_camera(),
                    default_viewport.get_texture_resolution(),
                    None,
                    default_viewport.usd_context_name,
                )
        except ImportError:
            pass

        return None

    def prepare_thumbnail(self) -> bool:
        """
        Create and bind material.
        """
        import omni.kit.app
        import omni.kit.commands
        import omni.usd

        stage = self._usd_context.get_stage()

        asset_path = "/World/Asset"
        # Check existence to avoid erroring out unit test
        if stage.GetPrimAtPath(asset_path):
            omni.kit.commands.execute("DeletePrimsCommand", stage=stage, paths=[asset_path])

        asset_path = "/World/Asset"
        path_to = omni.usd.get_stage_next_free_path(stage, asset_path, False)
        carb.log_info(f"[Thumbnail] Create material {path_to} for {self._usd_url}")

        try:
            # Zoom tighter than the default...make this configurable
            zoom = 0.28

            camera_path, resolution, time, usd_context_name = self.__get_framing_params()

            omni.kit.undo.begin_group()
            omni.kit.commands.execute(
                "CreateReferenceCommand",
                path_to=path_to,
                asset_path=self._usd_url,
                usd_context=omni.usd.get_context(),
            )

            omni.kit.commands.execute(
                "FramePrimsCommand",
                prim_to_move=camera_path,
                prims_to_frame=[path_to],
                time_code=time,
                usd_context_name=usd_context_name,
                aspect_ratio=resolution[0] / resolution[1],
                zoom=zoom,
            )
        finally:
            omni.kit.undo.end_group()

        return True
