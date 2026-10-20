## Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##
import glob
import inspect
import os
import platform
import unittest
from pathlib import Path

import carb
import omni.kit.app
import omni.usd
from omni.kit import ui_test
from omni.kit.test.async_unittest import AsyncTestCase
from omni.kit.test_suite.helpers import get_prims, get_test_data_path, wait_stage_loading
from pxr import Sdf, Usd, UsdGeom

from ._utils import ENABLE_NEURAYLIB_UTILS, get_content_browser_path_item, set_content_browser_grid_view


class DragDropUsdLayer(AsyncTestCase):
    def verify_dragged_layers(self, prim_name, file_path, prims):
        if os.path.splitext(file_path)[1] in [".usd", ".usda", ".usdc", ".fbx", ".gltf", ".obj"]:
            self.assertTrue(len(prims) >= 1, f"Expected >= 1 prims after dragging '{file_path}', got {len(prims)}")
        else:
            self.assertTrue(len(prims) == 0, f"Expected 0 prims after dragging '{file_path}', got {len(prims)}")

    async def create_stage(self):
        await omni.usd.get_context().new_stage_async()
        await wait_stage_loading()

        # Create defaultPrim
        usd_context = omni.usd.get_context()
        settings = carb.settings.get_settings()
        default_prim_name = settings.get("/persistent/app/stage/defaultPrimName")
        rootname = f"/{default_prim_name}"
        stage = usd_context.get_stage()
        with Usd.EditContext(stage, stage.GetRootLayer()):
            default_prim = UsdGeom.Xform.Define(stage, Sdf.Path(rootname)).GetPrim()
            stage.SetDefaultPrim(default_prim)

        stage_prims = get_prims(stage)
        return stage, stage_prims

    async def iter_prims_to_drag(self):
        for path in glob.glob(get_test_data_path(__name__, "../*")):
            if not os.path.isfile(path):
                continue
            prim_path = os.path.abspath(path).replace("\\", "/")
            item, file_name = await get_content_browser_path_item(prim_path)
            yield item, file_name, prim_path

    async def test_l1_drag_drop_usd_layer(self):
        await set_content_browser_grid_view(False)

        await ui_test.find("Layer").focus()
        await ui_test.find("Content").focus()

        async for item, file_name, prim_path in self.iter_prims_to_drag():
            if os.path.splitext(file_name)[1] not in [".usd", ".usda", ".usdc", ".fbx", ".gltf", ".obj"]:
                continue

            if file_name.find("mdl") != -1 and not ENABLE_NEURAYLIB_UTILS:
                continue

            # create new stage
            stage, stage_prims = await self.create_stage()

            # get end_pos which is center bottom of window
            layer_tree = ui_test.find("Layer//Frame/**/TreeView[*]")
            end_pos = layer_tree.center

            # drag/drop to centre of viewport
            await item.drag_and_drop(end_pos)

            # verify new prims were created
            self.verify_dragged_layers(Path(prim_path).stem, prim_path, get_prims(stage, stage_prims))
