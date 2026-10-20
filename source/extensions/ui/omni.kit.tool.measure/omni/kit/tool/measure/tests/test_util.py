# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import time
from pathlib import Path

import omni.kit.commands as cmd
import omni.kit.test
import omni.kit.tool.measure
import omni.kit.ui_test as ui_test
import omni.ui
import omni.usd
from omni.kit.tool.measure.manager import ReferenceManager
from omni.ui.tests.test_base import OmniUiTest

GOLDEN_IMG_DIR = Path(f"{Path(__file__).parent.parent.parent.parent.parent.parent}/data/tests/golden_img")
PRIM_PATHS = ["/test_cubeA", "/test_cubeB"]
SKIP_GEOMETRY_SNAP = (
    "Vertex, Edge and Mid Point snaps are currently unsupported in Kit 111: they need the hit mesh face, which only the "
    "OVRTX world-ray raycast query reported, and Kit 111 dropped that query (decision of 7 Oct 2026)."
)


class TestMeasureBase(OmniUiTest):

    # Before running each test
    async def setUp(self):
        await super().setUp()

        self._golden_img_dir = GOLDEN_IMG_DIR.absolute()

        # start test in a fresh scene
        self._ctx = omni.usd.get_context()
        await self._ctx.new_stage_async()

        if layer_window := omni.ui.Workspace.get_window("Layer"):
            layer_window.visible = False

        if content_window := omni.ui.Workspace.get_window("Content"):
            content_window.visible = False
        await ui_test.human_delay()

        self.create_test_cubes()
        self.create_test_light()
        await ui_test.human_delay()

        self._ctx.get_selection().clear_selected_prim_paths()
        await ui_test.human_delay()

        self._extension = omni.kit.tool.measure.get_instance()
        self._rm = ReferenceManager()

        viewport = self._extension.viewport
        self.assertIsNotNone(viewport)

        # Docking, etc.
        omni.ui.Workspace.show_window("Measure", True)
        measure_window = omni.ui.Workspace.get_window("Measure")
        active_view = omni.ui.Workspace.get_window("Viewport")
        dock_space = omni.ui.Workspace.get_window("DockSpace")
        property_window = omni.ui.Workspace.get_window("Property")
        await ui_test.wait_n_updates(3)

        active_view.dock_in(dock_space, omni.ui.DockPosition.LEFT, 0.6)
        measure_window.dock_in(dock_space, omni.ui.DockPosition.RIGHT, 0.4)
        property_window.dock_in(measure_window, omni.ui.DockPosition.BOTTOM, 0.2)

        await ui_test.wait_n_updates(3)

    # After Running Each Test
    async def tearDown(self):
        usd_context = omni.usd.get_context()
        await usd_context.close_stage_async()
        await ui_test.human_delay(10)

        await super().tearDown()

    @property
    def context(self):
        return self._ctx

    @property
    def reference_manager(self):
        return self._rm

    def create_test_cubes(self, prim_paths=PRIM_PATHS, positions=[(250, 0, 0), (0, 0, 250)]):
        """Add two test cubes"""
        for path, pos in zip(prim_paths, positions):
            create_test_object(path, position=pos)

    def create_test_light(self):
        from pxr import UsdLux

        cmd.execute(
            "CreatePrim",
            prim_type="DistantLight",
            attributes={UsdLux.Tokens.inputsAngle: 1.0, UsdLux.Tokens.inputsIntensity: 3000},
        )

    async def finalize_test(self, golden_img_name: str, threshold=None):
        await super().finalize_test(
            threshold=threshold, golden_img_dir=self._golden_img_dir, golden_img_name=golden_img_name + ".png"
        )

    async def dismiss_notification(self):
        await ui_test.emulate_mouse_move(ui_test.Vec2(550, 860))
        await ui_test.human_delay(5)
        await ui_test.emulate_mouse_click()
        await ui_test.human_delay(5)

    async def wait_for_notifications(self, timeout_seconds):
        time_elapsed = 0.0
        time_start = time.time()
        while time_elapsed < timeout_seconds:
            await ui_test.human_delay(5)
            time_elapsed = time.time() - time_start


def create_test_object(prim_path, prim_type="Cube", position=(0, 0, 0)):
    kwargs = {"prim_type": prim_type, "prim_path": prim_path, "attributes": {"size": 100.0}}

    cmd.execute("CreatePrimWithDefaultXform", **kwargs)

    usd_context = omni.usd.get_context()
    prim = usd_context.get_stage().GetPrimAtPath(prim_path)
    prim.GetAttribute("xformOp:translate").Set(position)


def select_test_objects(prim_paths):
    ctx = omni.usd.get_context()

    prim_paths = [prim_paths] if isinstance(prim_paths, str) else prim_paths

    selection = ctx.get_selection()
    selection.set_selected_prim_paths(prim_paths, True)


def world_coord_to_mouse_pos(world_position) -> ui_test.Vec2:
    if (window := omni.ui.Workspace.get_window("Viewport")) is None:
        return ui_test.Vec2(0, 0)

    api = window.viewport_api

    ndc_coord = api.world_to_ndc.Transform(world_position)

    screen_x = (ndc_coord[0] + 1) * 0.5
    screen_y = 1.0 - ((ndc_coord[1] + 1) * 0.5)

    # Apply Window Size
    mouse_x = screen_x * window.width
    mouse_y = screen_y * window.height
    return ui_test.Vec2(mouse_x, mouse_y)


def prim_path_world_pos(prim_path):
    stage = omni.usd.get_context().get_stage()

    prim = stage.GetPrimAtPath(prim_path)
    if (position := prim.GetAttribute("xformOp:translate").Get()) is None:
        return None
    return position


def prim_path_to_mouse_pos(prim_path) -> ui_test.Vec2:
    if (position := prim_path_world_pos(prim_path)) is None:
        return ui_test.Vec2(0, 0)

    return world_coord_to_mouse_pos(position)
