## Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

import inspect
import os
import pathlib

import omni.kit
import omni.kit.app
import omni.kit.menu
import omni.ui as ui
import omni.usd
from omni.kit import ui_test
from omni.scene.visualization.ui.scripts import common
from omni.ui.tests.test_base import OmniUiTest
from pxr import Sdf, Usd

EXTENSION_FOLDER_PATH = pathlib.Path(
    omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
)
TEST_DATA_PATH = EXTENSION_FOLDER_PATH.joinpath("data/tests")

OUTPUT_DIR = pathlib.Path(omni.kit.test.get_test_output_path()).resolve().absolute()


class TestSceneVizActions(OmniUiTest):
    async def setUp(self):
        self._usd_context = omni.usd.get_context()
        await self._usd_context.new_stage_async()
        self._stage = self._usd_context.get_stage()
        self.assertIsNotNone(self._stage)

        await omni.kit.app.get_app().next_update_async()

        stage_panel = ui_test.find("Stage")
        self.assertIsNotNone(stage_panel)
        await stage_panel.focus()
        self._viewport = ui_test.find("Viewport")
        self.assertIsNotNone(self._viewport)
        await self._viewport.focus()

        omni.kit.menu.utils.refresh_menu_items("Create")
        await ui_test.human_delay(10)

    async def tearDown(self):
        await self._usd_context.new_stage_async()
        self._viewport = None
        self._usd_context = None

    async def test_visualization_options(self):

        # Make and select a mesh
        await ui_test.menu_click("Create")
        await ui_test.human_delay(10)

        await ui_test.menu_click("Create/Mesh")
        await ui_test.human_delay(10)

        await ui_test.menu_click("Create/Mesh/Sphere")
        await ui_test.human_delay(10)

        paths = self._usd_context.get_selection().get_selected_prim_paths()
        self.assertTrue(
            len(paths) == 1, "Exactly one prim should be selected, but {} prims are selected.".format(len(paths))
        )
        prim_path = paths[0]

        # XXX this schema *should* be applied by the core extension when the first
        # visualization attribute is enabled. But for some reason the schema only
        # appears in this test if I apply it explicitly.
        schema_name = "OmniSceneVisualizationAPI"
        api = Usd.SchemaRegistry.GetAPITypeFromSchemaTypeName(schema_name)
        prim = self._stage.GetPrimAtPath(prim_path)
        prim.ApplyAPI(api)
        self.assertEqual(prim.GetAppliedSchemas(), [schema_name])

        # Test actions
        omni.kit.actions.core.execute_action("omni.scene.visualization.ui", "scene_visualization_toggle_points")
        await ui_test.human_delay(10)

        omni.kit.actions.core.execute_action("omni.scene.visualization.ui", "scene_visualization_toggle_normals")
        await ui_test.human_delay(10)

        omni.kit.actions.core.execute_action("omni.scene.visualization.ui", "scene_visualization_toggle_wireframe")
        await ui_test.human_delay(10)

        omni.kit.actions.core.execute_action("omni.scene.visualization.ui", "scene_visualization_toggle_tangents")
        await ui_test.human_delay(10)

        omni.kit.actions.core.execute_action("omni.scene.visualization.ui", "scene_visualization_toggle_vertex_color")
        await ui_test.human_delay(10)

        prim = self._stage.GetPrimAtPath(prim_path)
        self.assertTrue(prim.IsValid(), "Invalid prim at path: {}".format(prim_path))

        for attr_name in common.VISUALIZATION_ATTRIBUTES:
            attr = prim.GetAttribute(attr_name)
            self.assertTrue(attr.IsValid(), "Failed to create valid attribute: {}".format(attr_name))
            self.assertTrue(
                attr.Get(), "Scene visualization attribute {} not enabled after being set.".format(attr_name)
            )
