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
import os
import sys
import unittest
from pathlib import Path
from typing import Dict, List

import carb.settings
import carb.tokens
import omni.kit.app
import omni.kit.commands
import omni.usd
from omni.kit.test import AsyncTestCase
from omni.kit.test_suite.helpers import wait_stage_loading
from pxr import Usd

from ..models import MaterialPrimDetailItem, StageMaterialModel

EXTENSION_FOLDER_PATH = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
TEST_DATA_PATH = EXTENSION_FOLDER_PATH.joinpath("data/tests")


class TestMaterialStageModel(AsyncTestCase):
    # Before running each test
    async def setUp(self):
        self._opened = False
        test_stage = TEST_DATA_PATH.joinpath("test_stage_model_materials.usd")

        context = omni.usd.get_context()
        context.open_stage(str(test_stage))

        self._stage = context.get_stage()

        await wait_stage_loading()

        self._stage_model = StageMaterialModel()
        self._stage_model.actived = True
        self._material_paths = ["/World/Xform/OmniGlass", "/World/Looks/OmniSurface"]
        self._prim_paths = ["/World/Xform/Cube", "/World/Cone"]

        self._valid_material_items = await self._get_valid_material_items()

    # After running each test
    async def tearDown(self):
        self._stage_model.destroy()
        self._stage_model = None

    async def test_usdrt_binding(self):
        self._stage_model._material_helper._stage_has_material_binding_api = True
        try:
            test_stage = TEST_DATA_PATH.joinpath("test_stage_model_materials_usdrt.usd")
            context = omni.usd.get_context()
            context.open_stage(str(test_stage))
            await wait_stage_loading()

            # Wait items updated
            await omni.kit.app.get_app().next_update_async()
            items = await self._get_valid_material_items()
            await self._wait_assign_update()
            for item in items:
                self.assertTrue(item.assigned)
        finally:
            self._stage_model._material_helper._stage_has_material_binding_api = False

    async def test_stage_general(self):
        self.assertTrue(self._stage_model.actived)

        items = await self._get_valid_material_items()
        self.assertEqual(len(items), 2)
        for index, item in enumerate(items):
            self.assertEqual(item.prim.GetPath().pathString, self._material_paths[index])

    async def test_stage_selection(self):
        items = await self._get_valid_material_items()
        for item in items:
            # None selected
            self.assertFalse(item.selected)

        # Selection mode
        saved_selection_include_children = self._stage_model.selection_include_children
        self._stage_model.selection_include_children = True

        # Root selected, all materials selected since include children enabled
        selection = omni.usd.get_context().get_selection()
        selection.set_selected_prim_paths(["/World"], True)
        await omni.kit.app.get_app().next_update_async()

        self._stage_model.add_on_selection_changed_fn(self._on_material_selection_changed)
        for item in items:
            self.assertTrue(item.selected)

        # Clear selection
        selection.set_selected_prim_paths([], True)
        await omni.kit.app.get_app().next_update_async()
        for item in items:
            self.assertFalse(item.selected)

        # Select root again, but disable include children
        selection.set_selected_prim_paths(["/World"], True)
        await omni.kit.app.get_app().next_update_async()
        self._stage_model.selection_include_children = False
        await omni.kit.app.get_app().next_update_async()
        for item in items:
            self.assertFalse(item.selected)

        # Select prim with material binded, only one material selected, either include children or not
        self._stage_model.selection_include_children = True
        selection.set_selected_prim_paths(["/World/Cone"], True)
        for i in range(3):
            await omni.kit.app.get_app().next_update_async()
        selected_count = 0
        for item in items:
            if item.selected:
                selected_count += 1
        self.assertEqual(selected_count, 1)

        self._stage_model.selection_include_children = False
        for i in range(3):
            await omni.kit.app.get_app().next_update_async()
        selected_count = 0
        for item in items:
            if item.selected:
                selected_count += 1
        self.assertEqual(selected_count, 1)

        # clean up
        self.assertTrue(self._stage_model.remove_on_selection_changed_fn(self._on_material_selection_changed))
        self.assertFalse(self._stage_model.remove_on_selection_changed_fn(lambda _: print("TEST")))
        self._stage_model.selection_include_children = saved_selection_include_children

    async def test_stage_bind_materials(self):
        # First, all materials are binded
        items = await self._get_valid_material_items()
        for item in items:
            self.assertTrue(item.assigned)

        # Unbind first material
        omni.kit.commands.execute(
            "BindMaterialCommand",
            prim_path=self._prim_paths[0],
            material_path="",
        )
        await self._wait_assign_update()
        self.assertFalse(items[0].assigned)
        self.assertTrue(items[1].assigned)

        # Bind first material again
        omni.kit.commands.execute(
            "BindMaterialCommand",
            prim_path=self._prim_paths[0],
            material_path=self._material_paths[0],
        )
        await self._wait_assign_update()
        self.assertTrue(items[0].assigned)
        self.assertTrue(items[1].assigned)

    async def test_stage_create_payload_materials(self):
        # First, two materials
        items = await self._get_valid_material_items()
        self.assertEqual(len(items), 2)

        # Add payload to stage
        omni.kit.commands.execute(
            "CreatePayloadCommand",
            usd_context=omni.usd.get_context(),
            path_to="/PayloadTest",
            asset_path=str(TEST_DATA_PATH.joinpath("payload.usd")),
        )
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

        items = await self._get_valid_material_items()
        self.assertEqual(len(items), 3)
        self.assertTrue(any(item for item in items if item.name == "CubeMaterial"))

    async def test_stage_change_materials(self):
        # First, two materials
        items = await self._get_valid_material_items()
        self.assertEqual(len(items), 2)

        # Create a new material
        kit_folder = carb.tokens.get_tokens_interface().resolve("${kit}")
        omni_pbr_mtl = os.path.normpath(kit_folder + "/mdl/core/Base/OmniPBR.mdl")
        omni_pbr_path = "/World/Looks/OmniPBR"
        omni.kit.commands.execute(
            "CreateMdlMaterialPrim", mtl_url=omni_pbr_mtl, mtl_name="OmniPBR", mtl_path=omni_pbr_path
        )
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

        items = await self._get_valid_material_items()
        self.assertEqual(len(items), 3)
        self.assertEqual(items[1].name, "OmniPBR")
        self.assertEqual(items[1].prim.GetPath().pathString, omni_pbr_path)
        self.assertFalse(items[1].assigned)

        # Bind new material
        self.assertTrue(items[0].assigned)
        omni.kit.commands.execute(
            "BindMaterialCommand",
            prim_path=self._prim_paths[0],
            material_path=omni_pbr_path,
        )
        await self._wait_assign_update()
        self.assertFalse(items[0].assigned)
        self.assertTrue(items[1].assigned)

        # Delete prim where new material bind
        self._stage.RemovePrim(self._prim_paths[0])
        await self._wait_assign_update()
        self.assertFalse(items[0].assigned)
        self.assertFalse(items[1].assigned)

        # Delete created material
        self._stage.RemovePrim(omni_pbr_path)
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        items = await self._get_valid_material_items()
        self.assertEqual(len(items), 2)
        self.assertFalse(any(item for item in items if item.name == "OmniPBR"))

    async def test_stage_picking(self):
        self._stage_model.start_pick(self._on_materials_picked)

        selection = omni.usd.get_context().get_selection()
        selection.set_selected_prim_paths(self._prim_paths, True)

        self._stage_model.stop_pick()
        # If stop pick, selection is reset
        selected_prims = selection.get_selected_prim_paths()
        self.assertEqual(selected_prims, [])

    async def _get_valid_material_items(self) -> List[MaterialPrimDetailItem]:
        collect_items = self._stage_model.get_item_children()
        # 1 default collection
        self.assertEqual(len(collect_items), 1)
        category_items = self._stage_model.get_item_children(collect_items[0])
        # 1 default category
        self.assertEqual(len(category_items), 1)
        material_items: List[MaterialPrimDetailItem] = self._stage_model.get_item_children(category_items[0])
        # 2 material items and 1 item for "Create New"
        self.assertEqual(material_items[0].name, "Create New")

        await self._wait_assign_update()
        return material_items[1:]

    async def _wait_assign_update(self):
        await asyncio.sleep(0.5)

    def _on_material_selection_changed(self, selected_materials):
        for material_item in self._valid_material_items:
            material_item.selected = material_item.prim in selected_materials

    def _on_materials_picked(self, picked_material_prims: Dict[Usd.Prim, any]):
        self.assertEqual(len(picked_material_prims), 2)
        for prim, status in picked_material_prims.items:
            self.assertTrue(prim.GetPath().pathString in self._prim_paths)
            # In pick mode, item selected status is set to True
            self.assertTrue(status.selected)
