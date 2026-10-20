import carb
import omni.kit.app
import omni.kit.commands
import omni.kit.ui_test as ui_test
import omni.usd
from omni.kit.menu.utils import MenuItemDescription, MenuLayout
from omni.kit.test.async_unittest import AsyncTestCase
from omni.kit.viewport.utility import get_active_viewport
from pxr import Gf, Sdf, UsdGeom

from ..scripts.viewport.viewport_mods import ViewportWatcher


class TestFocusViewport(AsyncTestCase):
    fail_on_log_error = False

    def get_stage_prims(self):
        stage = omni.usd.get_context().get_stage()
        return [prim.GetPath().pathString for prim in stage.TraverseAll() if not omni.usd.is_hidden_type(prim)]

    async def create_prim_at_position(tester, prim_type, prim_path, position: Gf.Vec3d):
        # Create prim
        omni.kit.commands.execute("CreatePrimWithDefaultXform", prim_type=prim_type)
        # select prim
        clip_target = [prim_path]
        omni.usd.get_context().get_selection().set_selected_prim_paths(clip_target, True)
        await ui_test.human_delay()
        tester.assertTrue(omni.usd.get_context().get_selection().get_selected_prim_paths() == clip_target)

        # Move the prim to new position
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath(prim_path)
        prim_x = UsdGeom.Xformable(prim)
        prim_x.ClearXformOpOrder()
        prim_translate_op = prim_x.AddTranslateOp()
        prim_translate_op.Set(position)
        return prim

    async def buildTestStage(tester):
        await omni.usd.get_context().new_stage_async()
        await ui_test.human_delay()
        # verify no prims
        prim_list = tester.get_stage_prims()
        tester.assertTrue(prim_list == [])

        ## create prims
        tester._sphere = await tester.create_prim_at_position("Sphere", "/Sphere", Gf.Vec3d(0, 1000, 0))
        tester._xform = await tester.create_prim_at_position("Xform", "/Xform", Gf.Vec3d(0, 500, 0))
        tester._cube = await tester.create_prim_at_position("Cube", "/Cube", Gf.Vec3d(0, 2000, 0))
        # Create camera
        tester._camera = await tester.create_prim_at_position("Camera", "/Camera", Gf.Vec3d(0, 0, 0))

        # verify prims were created
        await ui_test.human_delay()
        prim_list = tester.get_stage_prims()
        tester.assertTrue(prim_list == ["/Sphere", "/Xform", "/Cube", "/Camera"])

        # Select camera
        viewport_api = get_active_viewport()
        viewport_camera = viewport_api.camera_path
        viewport_api.camera_path = "/Camera"
        camera = viewport_api.camera_path
        tester.assertTrue(camera != viewport_camera)
        # prim_pos = omni.kit.viewport.utility.camera_state.ViewportCameraState(camera_path=camera).position_world

        # Get camera focus distance
        camera_g = UsdGeom.Camera(tester._camera)
        cam_focus_dist = tester._camera.GetAttribute("focusDistance")
        old_dist = cam_focus_dist.Get()

        # Call focus here on Sphere TODO -- Right now we're just calling on a position, but we need to call it on the object!
        # These tests should all change to USDRT or Fabric soon!
        watcher = ViewportWatcher()
        watcher.focus_on_pos_list([(0, 1000, 0)])

        # Get new camera focus distance
        new_dist = cam_focus_dist.Get()
        carb.log_warn(f"Camera focalDist={cam_focus_dist} old_dist={old_dist} new_dist={new_dist}")
        tester.assertAlmostEqual(new_dist, 1000)

        # Call focus on Cube

        # Call focus here

        # Get new camera focus distance

    # Before running each test
    async def setUp(tester):
        return

    async def test_focus_on_viewport(self):
        # TODO More work to do on these tests.  Improve coverage, switch to USDRT
        await omni.kit.app.get_app().next_update_async()
        await self.buildTestStage()

        await omni.kit.app.get_app().next_update_async()

        # use menu
        # await ui_test.menu_click("Edit/Select/Select All")

        # verify all prims are selected
        # tester.assertTrue(omni.usd.get_context().get_selection().get_selected_prim_paths() == prim_list)

    async def tearDown(self):
        # Unbuild level
        return


class TestFocusTarget(AsyncTestCase):
    fail_on_log_error = False

    # Before running each test
    async def setUp(self):
        return

    async def test_focus_on_target(self):
        await omni.kit.app.get_app().next_update_async()
        clip_target = []
        self.assertIsNotNone(clip_target)

    async def tearDown(self):
        return

    async def edit_test_hotkey_func_edit_focus(tester, menu_item: MenuItemDescription):
        from pathlib import Path

        import omni.kit.viewport_legacy

        # get file path
        extension_path = omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
        await omni.usd.get_context().open_stage_async(
            str(Path(extension_path).joinpath("data").joinpath("tests").joinpath("stages").joinpath("focus_prims.usda"))
        )

        # test focus
        stage = omni.usd.get_context().get_stage()
        viewport_api = get_active_viewport()
        prim_pos = viewport_api.transform.Transform(Gf.Vec3d(0, 0, 0))
        for prim_path in ["/World/Cone", "/World/Cube", "/World/Sphere", "/World/defaultLight"]:
            # select prim
            omni.usd.get_context().get_selection().set_selected_prim_paths([prim_path], True)

            # hotkey
            await ui_test.emulate_keyboard_press(menu_item.hotkey[1], menu_item.hotkey[0])
            await ui_test.human_delay(50)

            # verify camera has moved
            pos = viewport_api.transform.Transform(Gf.Vec3d(0, 0, 0))
            tester.assertFalse(pos == prim_pos)
