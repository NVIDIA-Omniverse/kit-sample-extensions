from pathlib import Path

import carb.settings
import omni.kit.app
import omni.kit.test
import omni.kit.ui_test as ui_test
import omni.usd
from omni.kit.viewport.utility import get_active_viewport, get_active_viewport_window
from omni.ui.tests.test_base import OmniUiTest
from pxr import Gf, Sdf, Usd

from ..manipulator import SHOW_TITLE_PATH
from ..scene import PrimIcon

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
TEST_OBJECT_PRIM_PATH = "/test_obj"


# -- TRANSITION FOR SUPPORTING BOTH VP1 AND VP2
def is_viewport_legacy():
    viewport_api = get_active_viewport()
    return hasattr(viewport_api, "legacy_window")


# -- TRANSITION END


class TestPrimIcon(OmniUiTest):
    async def setUp(self):
        await super().setUp()
        usd_context = omni.usd.get_context()
        await usd_context.new_stage_async()
        self._settings = carb.settings.get_settings()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._icon_scene = PrimIcon.get_instance()
        await ui_test.human_delay(8)
        await ui_test.wait_n_updates(300)
        if is_viewport_legacy():
            self._golden_img_dir = self._golden_img_dir.joinpath("legacy")

    # After running each test
    async def tearDown(self):
        usd_context = omni.usd.get_context()
        await usd_context.close_stage_async()
        self._icon_scene.clear()
        self._icon_scene.destroy()
        await super().tearDown()

    async def _dock_viewport(self, width=1200, height=900, block_device=False):
        """Utility function to dock viewport window and focus on turntable panel."""
        viewport = get_active_viewport_window()
        await self.docked_test_window(window=viewport, width=width, height=height, block_devices=block_device)
        await ui_test.wait_n_updates()

    async def test_primicon_default(self):
        create_test_object()
        self._settings.set(SHOW_TITLE_PATH, True)
        await ui_test.human_delay()
        await ui_test.wait_n_updates(30)
        path = TEST_DATA_PATH.absolute().joinpath("primicon.png")
        self._icon_scene.add_prim_icon(TEST_OBJECT_PRIM_PATH, str(path))
        await ui_test.wait_n_updates(30)
        model = self._icon_scene.get_model()
        self.assertAlmostEqual(model.get_world_unit(), 0.1)
        self.assertTrue(TEST_OBJECT_PRIM_PATH in model.get_item("").keys())
        save_path = model.get_icon_url(TEST_OBJECT_PRIM_PATH)
        self.assertEqual(save_path, str(path))
        pos = model.get_position(TEST_OBJECT_PRIM_PATH)
        self.assertEqual(Gf.Vec3d(0, 0, 0), Gf.Vec3d(pos))

        pos = self._icon_scene.show_prim_icon(TEST_OBJECT_PRIM_PATH)
        await ui_test.wait_n_updates(30)
        self.assertTrue(model._icons[TEST_OBJECT_PRIM_PATH].visible)
        pos = self._icon_scene.hide_prim_icon(TEST_OBJECT_PRIM_PATH)
        await ui_test.wait_n_updates(30)
        self.assertFalse(model._icons[TEST_OBJECT_PRIM_PATH].visible)

        def click_fn(*_):
            pass

        self._icon_scene.set_icon_click_fn(TEST_OBJECT_PRIM_PATH, click_fn)
        self.assertEqual(model.get_on_click(TEST_OBJECT_PRIM_PATH), click_fn)
        self._icon_scene.remove_prim_icon(TEST_OBJECT_PRIM_PATH)
        await ui_test.wait_n_updates(30)
        self.assertEqual(model.get_icon_url(TEST_OBJECT_PRIM_PATH), "")
        self._icon_scene.destroy()
        await ui_test.wait_n_updates(30)


def create_test_object(prim_path=TEST_OBJECT_PRIM_PATH, prim_type="Cube", attrs=None):
    kwargs = {"prim_type": prim_type, "prim_path": prim_path}
    if attrs:
        kwargs["attributes"] = attrs
    omni.kit.commands.execute("CreatePrimWithDefaultXform", **kwargs)
    stage = omni.usd.get_context().get_stage()
    prim = stage.GetPrimAtPath(prim_path)
    attribute = prim.CreateAttribute("icon_position", Sdf.ValueTypeNames.Float3)
    attribute.Set(Gf.Vec3d(0, 0, 0))
