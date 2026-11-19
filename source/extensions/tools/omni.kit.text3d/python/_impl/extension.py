# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import os
from contextlib import suppress
from pathlib import Path

import carb.settings
import omni.ext
import omni.kit.commands
import omni.usd
from pxr import Sdf, Usd

SETTING_ROOT = "/exts/omni.kit.text3d/"

# -----------------------------------------------------------------------------


class TextGeneratorExtension(omni.ext.IExt):
    """The entry point for the extension"""

    def __init__(self):
        super().__init__()
        self._settings = carb.settings.get_settings()
        self._create_menu_items = []  # List[MenuItemListDescription]
        self._menus_enabled = self._settings.get(SETTING_ROOT + "menus/enable")

    def on_startup(self, ext_id):
        if self._menus_enabled:
            self._register_create_menu()

    def on_shutdown(self):
        if self._menus_enabled:
            with suppress(ImportError):
                from omni.kit.menu.utils import remove_menu_items

                remove_menu_items(self._create_menu_items, "Create")
        self._create_menu_items = []

    def _register_create_menu(self):
        """Adds Create->3d Text menu entry"""
        with suppress(ImportError):
            import omni.kit.menu.utils

            original_svg_color = self._settings.get("/exts/omni.kit.menu.create/original_svg_color")
            self._create_menu_items = [
                omni.kit.menu.utils.MenuItemDescription(
                    name="Text",
                    glyph="text.svg",
                    appear_after=["Xform"],
                    onclick_fn=self._on_create_text,
                    original_svg_color=original_svg_color,
                )
            ]
            omni.kit.menu.utils.add_menu_items(self._create_menu_items, "Create", -9)

    def _on_create_text(self):
        """Called by Create menu entry to place a new 3d text"""
        create_text_prim(omni.usd.get_context().get_stage(), Sdf.Path("Text"))


def create_text_prim(stage: Usd.Stage, target_prim_path: Sdf.Path) -> str:
    """Reads the packaged usd text asset into the stage

    Args:
        stage (Usd.Stage): The stage to add the prim to.
        target_prim_path (Sdf.Path): The path of the new text prim, relative to default prim if there is one

    Returns:
        (str): The absolute path of the top Xform of the new text prim
    """
    path_to_usda = Path(os.path.dirname(__file__)).parent.parent.parent.parent / "data" / "text_generator.usda"

    if stage.HasDefaultPrim():
        prim_path = omni.usd.get_stage_next_free_path(
            stage,
            stage.GetDefaultPrim()
            .GetPath()
            .AppendPath(target_prim_path.MakeRelativePath(Sdf.Path.absoluteRootPath))
            .pathString,
            False,
        )
    else:
        prim_path = omni.usd.get_stage_next_free_path(stage, target_prim_path.pathString, False)

    path_to_usd = path_to_usda.as_posix()

    omni.kit.commands.execute(
        "Create3dTextCommand",
        target_prim_path=prim_path,
        path_to_usd=path_to_usd,
        source_prim_path="/Text",
        stage=stage,
    )
    return prim_path
