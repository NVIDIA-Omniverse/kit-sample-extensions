import os
import time
import unittest
from pathlib import Path
from typing import Union

import AnimationSchema
import carb
import omni.kit.property.usd
import omni.kit.ui_test as ui_test
import omni.kit.window.property as p
import omni.ui as ui
from omni.anim.curve.core import get_curve_plugin, get_curvekey_clipboard
from omni.kit.test.async_unittest import LogErrorChecker
from omni.kit.test_suite.helpers import wait_stage_loading
from omni.kit.viewport.utility import get_active_viewport
from omni.timeline import get_timeline_interface
from pxr import Sdf, Usd

from ..scripts.context_menu import clear_animation_data_clipboard
from ..scripts.extension import get_instance
from .visual_test_base import AnimationVisualTestBase


# Old API replacements
def _get_keys(prim, curve_name):
    curve = get_curve_plugin().get_curves(str(prim.GetPath())).get(curve_name)
    if curve is None:
        return None

    times = []
    values = []

    for key in curve.keys:
        times.append(key.time)
        values.append(key.value)

    return times, values


def has_entry_enabled(entry: str, menu_root: ui.Widget) -> bool:
    for menu_item in ui.Inspector.get_children(menu_root):
        if isinstance(menu_item, ui.MenuItem) and menu_item.enabled and menu_item.text == entry:
            return True

    return False


class PosVecHelper:
    """
    A utility to help transforming the Vec2 positions
    """

    def __init__(self, x: int, y: int) -> None:
        self.x = x
        self.y = y

    def to_vec2(self) -> ui_test.Vec2:
        return ui_test.Vec2(self.x, self.y)

    def __neg__(this):
        return PosVecHelper(-this.x, -this.y)

    def __add__(this, that):
        assert isinstance(that, PosVecHelper)
        return PosVecHelper(this.x + that.x, this.y + that.y)

    def __sub__(this, that):
        assert isinstance(that, PosVecHelper)
        return this + (-that)

    def __mul__(this, that):
        assert isinstance(that, int)
        return PosVecHelper(this.x * that, this.y * that)


class AnimCurveTestUtility:
    """
    This function will check if a prim contains all the default curves, and the curves
    are empty.
    """

    def _check_empty_default_curves(self, prim):
        self._check_default_curve_name(prim)
        self._check_default_curve_length(prim, 0)

    """
    This function will check if a prim contains all the default curves.
    """

    def _check_default_curve_name(self, prim):
        curve_names = get_curve_plugin().get_curves(str(prim.GetPath()))
        self.assertIsNotNone(curve_names)
        self.assertEqual(len(curve_names), len(DEFAULT_CURVE_NAMES))
        for name in DEFAULT_CURVE_NAMES:
            self.assertIn(name, curve_names)

    """
    This function will check the length of the default curves of a prim.
    """

    def _check_default_curve_length(self, prim, length: int):
        for name in DEFAULT_CURVE_NAMES:
            rtn = _get_keys(prim, name)
            self.assertIsNotNone(rtn, msg="Curve %s." % name)
            key_times, key_values = rtn
            self.assertEqual(len(key_times), length)
            self.assertEqual(len(key_values), length)

    """
    This function will check if the target curves are contained in the prim as specified.
    target: {
        curve_name [Str]: {
            time [Int]: value [Any],
            ...
        },
        ...
    }
    Note: If the key of a curve is {}, i.e. an empty dict, it means an empty curve
    """

    def _check_curves(self, prim, target: dict, places=None):
        for curve_name, target_curves in target.items():
            rtn = _get_keys(prim, curve_name)
            self.assertIsNotNone(rtn, msg="Curve %s." % curve_name)
            key_times, key_values = rtn
            self.assertEqual(len(key_times), len(target_curves), msg="len(key_times) of %s" % curve_name)
            self.assertEqual(len(key_values), len(target_curves), msg="len(key_values) of %s" % curve_name)

            for time, value, (t_time, t_value) in zip(key_times, key_values, target_curves.items()):
                # t_time is Usd.TimeCode, so we will convert it to the new format
                t_time = round(
                    t_time * get_curve_plugin().get_ticks_per_second() / prim.GetStage().GetTimeCodesPerSecond()
                )
                if places is None:
                    self.assertAlmostEqual(time, t_time, msg="key_time of %s" % curve_name)
                    self.assertAlmostEqual(value, t_value, msg="key_value of %s" % curve_name)
                else:
                    self.assertAlmostEqual(time, t_time, msg="key_time of %s" % curve_name, places=places)
                    self.assertAlmostEqual(value, t_value, msg="key_value of %s" % curve_name, places=places)

    """
    This function will check if the prim contains and only contains the curves given in the target.
    target: {
        curve_name [Str]: {
            time [Int]: value [Any],
            ...
        },
        ...
    }
    """

    def _check_curves_strict(self, prim, target: dict):
        curves = get_curve_plugin().get_curves(str(prim.GetPath()))
        self.assertIsNotNone(curves)
        self.assertEqual(len(curves), len(target), "The number of curves does not match.")
        self._check_curves(prim, target)


class TestPropertySchemeDelegate(p.PropertySchemeDelegate):
    """
    Make sure property window tests have consistent widget ordering.
    """

    def get_widgets(self, payload):
        widgets_to_build = ["path", "transform", "geometry", "geometry_imageable", "kind"]
        return widgets_to_build


DEFAULT_CURVE_NAMES = (
    "visibility:x",
    "xformOp:rotateXYZ:x",
    "xformOp:rotateXYZ:y",
    "xformOp:rotateXYZ:z",
    "xformOp:scale:x",
    "xformOp:scale:y",
    "xformOp:scale:z",
    "xformOp:translate:x",
    "xformOp:translate:y",
    "xformOp:translate:z",
)


class AnimCurvePropertyWindowTests(AnimationVisualTestBase, AnimCurveTestUtility):
    fail_on_log_error = False
    """
    These tests focus on the property window, including Copy/Paste/Remove Keys, etc.
    """

    async def setUp(self):
        await super().setUp()
        module_root = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
        self._GOLDEN_IMG_DIR = module_root.joinpath("data/golden_img")
        self._MAP_DIR = module_root.joinpath("data/test_map")

        pw = p.get_window()
        pw.register_scheme_delegate("prim", "test_prim", TestPropertySchemeDelegate())

    _PROPERTY_WINDOW_WIDTH = 720
    _PROPERTY_WINDOW_HEIGHT = 1000

    # Triggering the menu from the menu bar requires the dependency of omni.kit.mainwindow. However, that approach
    # appears to break several visual tests, due to changes in the order of the CollapsableFrame within the property
    # window.
    _timesample_conversion_menu = get_instance()._timesamples_converter
    _simplification_menu = get_instance()._simplification_menu

    async def restore(self, profile=False):
        pw = p.get_window()
        pw.unregister_scheme_delegate("prim", "test_prim")

        timeline_iface = get_timeline_interface()
        timeline_iface.set_current_time(0)
        await ui_test.human_delay()

        clipboard = get_curvekey_clipboard()
        clipboard.clear()

        return await super().restore(profile)

    @staticmethod
    def show_only_specified_collapsable_property(properties_to_show: set[str]):
        widgets = ui_test.find_all("Property//Frame/**/CollapsableFrame[*]")
        for widget in widgets:
            if widget.widget.title in properties_to_show:
                widget.widget.collapsed = False
            else:
                widget.widget.collapsed = True

    """
    This test focus on the right-click menus.
    """

    async def test_anim_curve_property_right_click_menu(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube_property.usda")

        # select prim and focus property window so the widgets are built
        property_window = ui.Workspace.get_window("Property")
        property_window.visible = True
        property_window.focus()
        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        timeline_iface = get_timeline_interface()

        await wait_stage_loading()

        # Dock the property window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=property_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=self._PROPERTY_WINDOW_WIDTH,
            height=self._PROPERTY_WINDOW_HEIGHT,
        )

        self.show_only_specified_collapsable_property({"Transform"})

        property_window = ui_test.find("Property")
        """
        OM-59405: At frame 5. There are no keys on Rotate property. Remove/Copy key should be disabled.
        """
        timeline_iface.set_current_time(5 / 24)  # current_frame / FPS

        rotate_label = property_window.find("**/Label[*].text=='Rotate'")
        await rotate_label.right_click()

        menu_root = ui.Menu.get_current()
        for entry in ["Remove Key", "Copy Key", "Copy Animation", "Remove Animation"]:
            self.assertFalse(has_entry_enabled(entry, menu_root), f'"{entry}" should be disabled')

        """
        At frame 0. There are keys. Remove/Copy key should be enabled.
        """
        timeline_iface.set_current_time(0 / 24)  # current_frame / FPS

        translate_label = property_window.find("**/Label[*].text=='Translate'")
        await translate_label.right_click()

        menu_root = ui.Menu.get_current()
        for entry in ["Remove Key", "Copy Key", "Copy Animation", "Remove Animation"]:
            self.assertTrue(has_entry_enabled(entry, menu_root), f'"{entry}" should be enabled')

        """
        At frame 10. There are keys for translate|x, but not for y and z
        """
        timeline_iface.set_current_time(10 / 24)  # current_frame / FPS

        transform_frame = ui_test.find("Property//Frame/**/CollapsableFrame[*].title=='Transform'")
        float_drags = transform_frame.find_all("**/FloatDrag[*]")

        translate_x_value = float_drags[0]
        await translate_x_value.right_click()
        menu_root = ui.Menu.get_current()
        for entry in ["Remove Key", "Copy Key", "Set Key", "Copy Animation", "Remove Animation"]:
            self.assertTrue(has_entry_enabled(entry, menu_root), f'"{entry}" should be enabled')

        translate_y_value = float_drags[1]
        await translate_y_value.right_click()
        menu_root = ui.Menu.get_current()
        for entry in ["Remove Key", "Copy Key"]:
            self.assertFalse(has_entry_enabled(entry, menu_root), f'"{entry}" should be disabled')
        for entry in ["Copy Animation", "Remove Animation"]:
            self.assertTrue(has_entry_enabled(entry, menu_root), f'"{entry}" should be enabled')

        translate_z_value = float_drags[2]
        await translate_z_value.right_click()
        menu_root = ui.Menu.get_current()
        for entry in ["Remove Key", "Copy Key"]:
            self.assertFalse(has_entry_enabled(entry, menu_root), f'"{entry}" should be disabled')
        for entry in ["Copy Animation", "Remove Animation"]:
            self.assertTrue(has_entry_enabled(entry, menu_root), f'"{entry}" should be enabled')

        # rotate does not have any animation data
        rotate_x_value = float_drags[3]
        await rotate_x_value.right_click()
        menu_root = ui.Menu.get_current()
        for entry in ["Remove Key", "Copy Key", "Copy Animation", "Remove Animation"]:
            self.assertFalse(has_entry_enabled(entry, menu_root), f'"{entry}" should be disabled')

        timeline_iface.set_current_time(0 / 24)  # reset to zero

    """
    This test focus on the state icon in the property window.
    """

    @unittest.skipIf(os.getenv("ETM_ACTIVE"), "Broken on ETM + Kit SDK 105")
    async def test_anim_curve_property_state_icon(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube_property.usda")

        # select prim and focus property window so the widgets are built
        property_window = ui.Workspace.get_window("Property")
        property_window.visible = True
        property_window.focus()
        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        timeline_iface = get_timeline_interface()

        await wait_stage_loading()

        # Dock the property window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=property_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=self._PROPERTY_WINDOW_WIDTH,
            height=self._PROPERTY_WINDOW_HEIGHT,
        )

        self.show_only_specified_collapsable_property({"Transform"})

        """
        At frame 10/20/30, check the state icons.
        """
        with self.set_crop_for_widget_region_context("Property//Frame/**/CollapsableFrame[*].title=='Transform'"):
            timeline_iface.set_current_time(10 / 24)  # current_frame / FPS
            await omni.kit.app.get_app().next_update_async()
            await ui_test.human_delay()
            await self.do_visual_test(img_name="anim_curve_property_state_icon_10", restore=False)

            timeline_iface.set_current_time(20 / 24)  # current_frame / FPS
            await omni.kit.app.get_app().next_update_async()
            await ui_test.human_delay()
            await self.do_visual_test(img_name="anim_curve_property_state_icon_20", restore=False)

            timeline_iface.set_current_time(30 / 24)  # current_frame / FPS
            await omni.kit.app.get_app().next_update_async()
            await ui_test.human_delay()
            await self.do_visual_test(img_name="anim_curve_property_state_icon_30", restore=False)

        """
        At time 10, click the state icon
        """
        timeline_iface.set_current_time(10 / 24)  # current_frame / FPS
        await omni.kit.app.get_app().next_update_async()
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath("/World/Cube")

        await ui_test.human_delay()

        # click the red state icon, it will remove the key and become grey
        state_icons = ui_test.find_all("Property//Frame/**/control_state_xformOp:translate")
        x_icon = state_icons[0]
        await x_icon.click()
        await ui_test.human_delay()
        target = {
            "xformOp:translate:x": {0: 0},
            "xformOp:translate:y": {0: 0, 20: 70.8288},
            "xformOp:translate:z": {0: 0, 30: 250.701},
            "xformOp:scale:x": {},
            "xformOp:scale:y": {},
            "xformOp:scale:z": {},
        }
        self._check_curves(prim, target)

        # click the grey state icon, it will add a key and become red
        y_icon = state_icons[1]
        await y_icon.click()
        await ui_test.human_delay()
        target = {
            "xformOp:translate:x": {0: 0},
            "xformOp:translate:y": {0: 0, 10: 70.8288 / 2, 20: 70.8288},
            "xformOp:translate:z": {0: 0, 30: 250.701},
            "xformOp:scale:x": {},
            "xformOp:scale:y": {},
            "xformOp:scale:z": {},
        }
        self._check_curves(prim, target)

        timeline_iface.set_current_time(0 / 24)  # current_frame / FPS
        await omni.kit.app.get_app().next_update_async()
        await ui_test.human_delay()

    """
    This test focus on the "Set Key" in the right click menu.
    """

    async def test_anim_curve_property_set_key(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube.usda")

        # select prim and focus property window so the widgets are built
        property_window = ui.Workspace.get_window("Property")
        property_window.visible = True
        property_window.focus()
        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        timeline_iface = get_timeline_interface()

        await wait_stage_loading()

        # Dock the property window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=property_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=self._PROPERTY_WINDOW_WIDTH,
            height=self._PROPERTY_WINDOW_HEIGHT,
        )

        self.show_only_specified_collapsable_property({"Transform"})

        timeline_iface.set_current_time(31 / 24)  # current_frame / FPS
        await ui_test.human_delay()

        property_window = ui_test.find("Property")
        translate_label = property_window.find("**/Label[*].text=='Translate'")
        await translate_label.right_click()
        await ui_test.select_context_menu("Set Key")

        await self.restore()

        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath("/World/Cube")
        target = {
            "xformOp:translate:x": {0: 0, 30: 166.345, 31: 166.345},
            "xformOp:translate:y": {0: 0, 30: 70.8288, 31: 70.8288},
            "xformOp:translate:z": {0: 0, 30: 250.701, 31: 250.701},
            "xformOp:rotateXYZ:x": {0: 0, 30: 0},
            "xformOp:rotateXYZ:y": {0: 0, 30: 0},
            "xformOp:rotateXYZ:z": {0: 0, 30: 0},
            "xformOp:scale:x": {0: 0.5, 30: 0.5},
            "xformOp:scale:y": {0: 0.5, 30: 0.5},
            "xformOp:scale:z": {0: 0.5, 30: 0.5},
        }
        self._check_curves(prim, target)

        timeline_iface.set_current_time(0)  # reset it back to zero

    """
    This test focus on the "Remove Key" in the right click menu.
    """

    async def test_anim_curve_property_remove_key(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube.usda")

        # select prim and focus property window so the widgets are built
        property_window = ui.Workspace.get_window("Property")
        property_window.visible = True
        property_window.focus()
        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await wait_stage_loading()

        # Dock the property window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=property_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=self._PROPERTY_WINDOW_WIDTH,
            height=self._PROPERTY_WINDOW_HEIGHT,
        )

        self.show_only_specified_collapsable_property({"Transform"})

        property_window = ui_test.find("Property")

        translate_label = property_window.find("**/Label[*].text=='Translate'")
        await translate_label.right_click()
        await ui_test.select_context_menu("Remove Key")

        await self.restore()

        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath("/World/Cube")
        target = {
            "xformOp:translate:x": {30: 166.345},
            "xformOp:translate:y": {30: 70.8288},
            "xformOp:translate:z": {30: 250.701},
            "xformOp:rotateXYZ:x": {0: 0, 30: 0},
            "xformOp:rotateXYZ:y": {0: 0, 30: 0},
            "xformOp:rotateXYZ:z": {0: 0, 30: 0},
            "xformOp:scale:x": {0: 0.5, 30: 0.5},
            "xformOp:scale:y": {0: 0.5, 30: 0.5},
            "xformOp:scale:z": {0: 0.5, 30: 0.5},
        }
        self._check_curves(prim, target)

    """
    This test focus on the "Copy/Paste Key" in the right click menu. It's for OM-60790.
    """

    async def test_anim_curve_property_copy_paste_key(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube.usda")

        # select prim and focus property window so the widgets are built
        property_window = ui.Workspace.get_window("Property")
        property_window.visible = True
        property_window.focus()
        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        timeline_iface = get_timeline_interface()

        await wait_stage_loading()

        # Dock the property window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=property_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=self._PROPERTY_WINDOW_WIDTH,
            height=self._PROPERTY_WINDOW_HEIGHT,
        )

        self.show_only_specified_collapsable_property({"Transform"})

        timeline_iface.set_current_time(30 / 24)  # current_frame / FPS

        property_window = ui_test.find("Property")

        translate_label = property_window.find("**/Label[*].text=='Translate'")
        await translate_label.right_click()
        await ui_test.select_context_menu("Copy Key")

        timeline_iface.set_current_time(15 / 24)  # current_frame / FPS

        rotate_label = property_window.find("**/Label[*].text=='Rotate'")
        await rotate_label.right_click()
        await ui_test.select_context_menu("Paste Key")

        await self.restore()

        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath("/World/Cube")
        target = {
            "xformOp:translate:x": {0: 0, 30: 166.345},
            "xformOp:translate:y": {0: 0, 30: 70.8288},
            "xformOp:translate:z": {0: 0, 30: 250.701},
            "xformOp:rotateXYZ:x": {0: 0, 15: 166.345, 30: 0},
            "xformOp:rotateXYZ:y": {0: 0, 15: 70.8288, 30: 0},
            "xformOp:rotateXYZ:z": {0: 0, 15: 250.701, 30: 0},
            "xformOp:scale:x": {0: 0.5, 30: 0.5},
            "xformOp:scale:y": {0: 0.5, 30: 0.5},
            "xformOp:scale:z": {0: 0.5, 30: 0.5},
        }
        self._check_curves(prim, target)

        timeline_iface.set_current_time(0)  # reset it back to zero
        await ui_test.human_delay()

    """
    This test focus on the "Copy/Paste Animation" in the right click menu.
    """

    async def test_anim_curve_property_copy_paste_animation(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube.usda")

        # select prim and focus property window so the widgets are built
        property_window = ui.Workspace.get_window("Property")
        property_window.visible = True
        property_window.focus()
        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await wait_stage_loading()

        # Dock the property window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=property_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=self._PROPERTY_WINDOW_WIDTH,
            height=self._PROPERTY_WINDOW_HEIGHT,
        )  # we should make it tall enough to accomendate the right-click menu

        self.show_only_specified_collapsable_property({"Transform"})

        property_window = ui_test.find("Property")

        translate_label = property_window.find("**/Label[*].text=='Translate'")
        await translate_label.right_click()
        await ui_test.select_context_menu("Copy Animation")

        scale_label = property_window.find("**/Label[*].text=='Scale'")
        await scale_label.right_click()
        await ui_test.select_context_menu("Paste Animation")

        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath("/World/Cube")
        target = {
            "xformOp:translate:x": {0: 0, 30: 166.345},
            "xformOp:translate:y": {0: 0, 30: 70.8288},
            "xformOp:translate:z": {0: 0, 30: 250.701},
            "xformOp:rotateXYZ:x": {0: 0, 30: 0},
            "xformOp:rotateXYZ:y": {0: 0, 30: 0},
            "xformOp:rotateXYZ:z": {0: 0, 30: 0},
            "xformOp:scale:x": {0: 0, 30: 166.345},
            "xformOp:scale:y": {0: 0, 30: 70.8288},
            "xformOp:scale:z": {0: 0, 30: 250.701},
        }
        self._check_curves(prim, target)

        # restore the clipboard
        clear_animation_data_clipboard()

    """
    This test focus on the "Remove Animation" in the right click menu.
    """

    async def test_anim_curve_property_remove_animation(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube.usda")

        # select prim and focus property window so the widgets are built
        property_window = ui.Workspace.get_window("Property")
        property_window.visible = True
        property_window.focus()
        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await wait_stage_loading()

        # Dock the property window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=property_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=self._PROPERTY_WINDOW_WIDTH,
            height=self._PROPERTY_WINDOW_HEIGHT,
        )

        self.show_only_specified_collapsable_property({"Transform"})

        translate_label = ui_test.find("Property//Frame/**/Label[*].text=='Translate'")
        await translate_label.right_click()
        await ui_test.human_delay()

        await ui_test.select_context_menu("Remove Animation")
        await ui_test.human_delay()

        await self.restore()

        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath("/World/Cube")
        target = {
            "xformOp:rotateXYZ:x": {0: 0, 30: 0},
            "xformOp:rotateXYZ:y": {0: 0, 30: 0},
            "xformOp:rotateXYZ:z": {0: 0, 30: 0},
            "xformOp:scale:x": {0: 0.5, 30: 0.5},
            "xformOp:scale:y": {0: 0.5, 30: 0.5},
            "xformOp:scale:z": {0: 0.5, 30: 0.5},
        }
        self._check_curves_strict(prim, target)

    async def test_anim_curve_get_curve_nodes(self):
        await self.load_stage(map_name="move_anim_curve_key.usda")

        nodes = get_curve_plugin().get_curve_nodes(None)
        print(nodes)

        nodes = get_curve_plugin().get_curve_nodes("/World/Cube")
        print(nodes)

        # nodes = utils.curve_plugin.get_curve_nodes(None, "/World/Sphere/animationData")
        # print(nodes)

        nodes = get_curve_plugin().get_curve_nodes("/World/Capsule")
        print(nodes)

    """
    Not every attribute is capable of setting keys.
    For example, the Kind section, Kind attribute is not able to set/copy/remove keys. We also need this false case.
    """

    async def test_anim_curve_property_no_set_key(self):
        # Load the USD map
        await self.load_stage(map_name="basic_curve_cube.usda")

        # select prim and focus property window so the widgets are built
        property_window = ui.Workspace.get_window("Property")
        property_window.visible = True
        property_window.focus()
        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await wait_stage_loading()

        # Dock the property window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=property_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=self._PROPERTY_WINDOW_WIDTH,
            height=self._PROPERTY_WINDOW_HEIGHT,
        )  # we should make it tall enough to accomendate the right-click menu

        self.show_only_specified_collapsable_property({"Kind"})

        property_window = ui_test.find("Property")
        kind_frame = property_window.find("**/CollapsableFrame[*].title=='Kind'")
        choices = kind_frame.find("**/ComboBox[*].name=='choices'")
        await choices.right_click()

        menu_root = ui.Menu.get_current()
        disabled_entries = ["Set Key", "Remove Key", "Copy Key", "Paste Key"]
        for entry in disabled_entries:
            self.assertFalse(has_entry_enabled(entry, menu_root), f'"{entry}" should be disabled')

    """
    We need a special case for the visibility attribute. We just fixed a bug for 103.5 in OM-59479.
    Need to make sure it doesn't make any regression.
    """

    @unittest.skipIf(os.getenv("ETM_ACTIVE"), "Broken on ETM + Kit SDK 105")
    async def test_anim_curve_property_visibility_attribute(self):
        # Load the USD map
        await self.load_stage(map_name="visibility.usda")

        # select prim and focus property window so the widgets are built
        property_window = ui.Workspace.get_window("Property")
        property_window.visible = True
        property_window.focus()
        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)

        await wait_stage_loading()

        # Dock the property window to the top and occupy the entire main window for capturing
        await self.setup_docked_test(
            docked_window=property_window,
            restore_window=ui.Workspace.get_window("Content"),
            restore_position=ui.DockPosition.SAME,
            width=self._PROPERTY_WINDOW_WIDTH,
            height=self._PROPERTY_WINDOW_HEIGHT,
        )  # we should make it tall enough to accomendate the right-click menu

        self.show_only_specified_collapsable_property({"Visual"})

        """
        At frame 15/30, check the state icons.
        """
        timeline_iface = get_timeline_interface()
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath("/World/Cube")

        with self.set_crop_for_widget_region_context("Property//Frame/**/CollapsableFrame[*].title=='Visual'"):
            timeline_iface.set_current_time(15 / 24)  # current_frame / FPS
            await ui_test.human_delay()
            await self.do_visual_test(img_name="anim_curve_property_visibility_state_icon_15", restore=False)

            timeline_iface.set_current_time(30 / 24)  # current_frame / FPS
            await ui_test.human_delay()
            await self.do_visual_test(img_name="anim_curve_property_visibility_state_icon_30", restore=False)

        # click the red state icon, it will remove the key and become grey
        state_icon = ui_test.find("Property//Frame/**/control_state_visibility")
        await state_icon.click()
        await ui_test.human_delay()
        target = {
            "visibility:x": {0: 0},
        }
        self._check_curves(prim, target)

        # click the grey state icon, it will add a key and become red
        await state_icon.click()
        await ui_test.human_delay()
        target = {
            "visibility:x": {0: 0, 30: 0},
        }
        self._check_curves(prim, target)

        timeline_iface.set_current_time(0 / 24)  # current_frame / FPS
        await ui_test.human_delay()

    async def test_anim_curve_timesample_conversion_menu(self):
        # trigger the menu
        self._timesample_conversion_menu._show_menu(None, None)

        # check visibility
        time_sample_to_curve_window = ui_test.find("USD TimeSample to Curves")
        self.assertIsNotNone(time_sample_to_curve_window)
        self.assertTrue(time_sample_to_curve_window.window.visible)

        async def verify_error_window_trigger():
            omni.usd.get_context().get_selection().set_selected_prim_paths([], False)
            convert_button = time_sample_to_curve_window.find("**/Button[*].text=='Convert'")
            self.assertIsNotNone(convert_button)
            await convert_button.click()
            error_window = ui_test.find("Error###Timesample Conversion Menu")
            self.assertIsNotNone(error_window)
            self.assertTrue(error_window.window.visible)
            return error_window

        async def verify_error_window_close(error_window):
            close_button = error_window.find("**/Button[*].text=='Close'")
            self.assertIsNotNone(close_button)
            await close_button.click()
            self.assertFalse(error_window.window.visible)

        error_window = await verify_error_window_trigger()
        await verify_error_window_close(error_window)
        error_window = await verify_error_window_trigger()
        await verify_error_window_close(error_window)

    async def test_anim_curve_curve_simplification_menu(self):
        # trigger the menu
        self._simplification_menu._show_menu(None, None)

        # check visibility
        simplification_window = ui_test.find("Animation Curve Simplification")
        self.assertIsNotNone(simplification_window)
        self.assertTrue(simplification_window.window.visible)

        async def verify_error_window_trigger():
            omni.usd.get_context().get_selection().set_selected_prim_paths([], False)
            apply_button = simplification_window.find("**/Button[*].text=='Apply'")
            self.assertIsNotNone(apply_button)
            await apply_button.click()
            error_window = ui_test.find("Error###Simplification Menu")
            self.assertIsNotNone(error_window)
            self.assertTrue(error_window.window.visible)
            return error_window

        async def verify_error_window_close(error_window):
            close_button = error_window.find("**/Button[*].text=='Close'")
            self.assertIsNotNone(close_button)
            await close_button.click()
            self.assertFalse(error_window.window.visible)

        error_window = await verify_error_window_trigger()
        await verify_error_window_close(error_window)
        error_window = await verify_error_window_trigger()
        await verify_error_window_close(error_window)

        # close the window
        cancel_button = simplification_window.find("**/Button[*].text=='Cancel'")
        self.assertIsNotNone(cancel_button)
        await cancel_button.click()
        self.assertFalse(simplification_window.window.visible)
