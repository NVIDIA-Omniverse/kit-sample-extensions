# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["MdlThumbnailGenerator"]

from typing import Optional, Tuple

import carb
import omni.kit.commands
import omni.usd
from pxr import Tf, UsdShade

from .constants import (
    DEFAULT_TEMPLATE_PATH,
    PERSISTENT_MDL_RENDER_MODE,
    PERSISTENT_MDL_RENDER_SAMPLES,
    PERSISTENT_MDL_STDIN,
    PERSISTENT_MDL_TEMPLATE_PATH,
    SETTING_MDL_TEMPLATE_PATH,
)
from .viewport_thumbnail_generator import ViewportThumbnailGenerator


class MdlThumbnailGenerator(ViewportThumbnailGenerator):
    """
    Generate MDL thumbnail

    Args:
        mdl_url (str): Url of mdl material to generate thumbnail
        output_url (str): Url of generated thumbnail

    Keyword args:
        mtl_name (Optional[str]): Mdl subid. Using name from url if None. Default None.
        template_url (Optional[str]): Url of template to generate thumbnail. Default None use setting PERSISTENT_MDL_TEMPLATE_PATH.
        stdin (Optional[str]): Prim to bind material when generating thumbnail. Default None use setting PERSISTENT_MDL_STDIN.
        render_mode (str): Render mode when generating thumbnail. Default None use setting PERSISTENT_MDL_RENDER_MODE.
        width (int): Width of generated thumbnail, in pixels. Default 256.
        height (int): Height of generate thumbnail, in pixels. Default 256.
        on_thumbnail_done_fn (callable): Function called when thumbnail generation is done. Function signture:
            void on_thumbnail_done_fn(result: bool, url: str)
    """

    def __init__(
        self,
        mdl_url: str,
        output_url: str,
        mtl_name: Optional[str] = None,
        template_url: Optional[str] = None,
        stdin: Optional[str] = None,
        render_mode: Optional[str] = None,
        width: int = 256,
        height: int = 256,
        on_thumbnail_done_fn: callable = None,
    ):
        settings = carb.settings.get_settings()
        if template_url is None:
            template_url = settings.get(PERSISTENT_MDL_TEMPLATE_PATH)

            # OM-56997: if template file not found in setting, change to default one
            result, _ = omni.client.stat(template_url)
            if result != omni.client.Result.OK:
                default_url = settings.get(SETTING_MDL_TEMPLATE_PATH)
                if not default_url:
                    default_url = DEFAULT_TEMPLATE_PATH
                carb.log_info(f"{template_url} not found, change to default {default_url}.")
                template_url = default_url

        if stdin is None:
            stdin = settings.get(PERSISTENT_MDL_STDIN)

        if render_mode is None:
            render_mode = settings.get(PERSISTENT_MDL_RENDER_MODE)

        super().__init__(
            template_url,
            output_url,
            width=width,
            height=height,
            render_mode=render_mode,
            iterations=settings.get(PERSISTENT_MDL_RENDER_SAMPLES),
            on_thumbnail_done_fn=on_thumbnail_done_fn,
        )
        self._mdl_url = mdl_url
        self._mtl_name = mtl_name or self._mdl_url.split("/")[-1][:-4]
        self._stdin = stdin

    def prepare_thumbnail(self) -> Tuple[str]:
        """Create and bind material

        Returns:
            Tuple[str]: A tuple containing the prim path and the material prim path.
        """
        stage = self._usd_context.get_stage()

        mtl_path = omni.usd.get_stage_next_free_path(
            stage, f"/Root/Looks/{Tf.MakeValidIdentifier(self._mtl_name)}", False
        )
        carb.log_info(f"[Thumbnail] Create material {mtl_path} for {self._mdl_url}")
        omni.kit.commands.execute(
            "CreateMdlMaterialPrimCommand",
            mtl_url=self._mdl_url,
            mtl_name=self._mtl_name,
            mtl_path=mtl_path,
            stage=stage,
        )
        carb.log_info(f"[Thumbnail] Bind material to {self._stdin}")
        omni.kit.commands.execute(
            "BindMaterialCommand",
            prim_path=self._stdin,
            material_path=mtl_path,
            strength=UsdShade.Tokens.strongerThanDescendants,
            stage=stage,
        )
        return (self._stdin, mtl_path)
