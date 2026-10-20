# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Optional, Tuple

import carb
import omni.kit.commands
import omni.usd
from pxr import Tf, UsdShade

from .constants import (
    PERSISTENT_USD_RENDER_MODE,
    PERSISTENT_USD_RENDER_SAMPLES,
    PERSISTENT_USD_STDIN,
    PERSISTENT_USD_TEMPLATE_PATH,
)
from .viewport_thumbnail_generator import ViewportThumbnailGenerator


class UsdThumbnailGenerator(ViewportThumbnailGenerator):
    """
    Generate usd thumbnail

    Args:
        usd_url (str): Url of usd material to generate thumbnail
        output_url (str): Url of generated thumbnail

    Keyword args:
        template_url (Optional[str]): Url of template to generate thumbnail. Default None use PERSISTENT_USD_TEMPLATE_PATH.
        stdin (Optional[str]): Prim to bind material when generating thumbnail. Default None use PERSISTENT_USD_STDIN.
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
        material_prim_path: Optional[str] = None,
        template_url: Optional[str] = None,
        stdin: Optional[str] = None,
        width: int = 256,
        height: int = 256,
        on_thumbnail_done_fn: callable = None,
    ):
        settings = carb.settings.get_settings()
        if template_url is None:
            template_url = settings.get(PERSISTENT_USD_TEMPLATE_PATH)
        if stdin is None:
            stdin = settings.get(PERSISTENT_USD_STDIN)
        super().__init__(
            template_url,
            output_url,
            width=width,
            height=height,
            render_mode=settings.get(PERSISTENT_USD_RENDER_MODE),
            iterations=settings.get(PERSISTENT_USD_RENDER_SAMPLES),
            on_thumbnail_done_fn=on_thumbnail_done_fn,
        )
        self._usd_url = usd_url
        self._material_prim_path = material_prim_path
        self._stdin = stdin

    def prepare_thumbnail(self) -> Tuple[str]:
        """Create and bind material.

        Returns:
            Tuple[str]: A tuple containing the prim path where the material is bound and the created material reference path.
        """
        stage = self._usd_context.get_stage()

        if self._material_prim_path is None:
            prim_name = self._usd_url.split("/")[-1][:-4]
        else:
            prim_name = self._material_prim_path.split("/")[-1]
        path_to = omni.usd.get_stage_next_free_path(stage, f"/Root/Looks/{Tf.MakeValidIdentifier(prim_name)}", False)

        carb.log_info(f"[Thumbnail] Create material {path_to} for {self._usd_url}@{self._material_prim_path}")
        omni.kit.commands.execute(
            "CreateReferenceCommand",
            path_to=path_to,
            asset_path=self._usd_url,
            prim_path=self._material_prim_path,
            usd_context=self._usd_context,
        )

        carb.log_info(f"[Thumbnail] Bind material to {self._stdin}")
        omni.kit.commands.execute(
            "BindMaterialCommand",
            prim_path=self._stdin,
            material_path=path_to,
            strength=UsdShade.Tokens.strongerThanDescendants,
            stage=stage,
        )
        return (self._stdin, path_to)
