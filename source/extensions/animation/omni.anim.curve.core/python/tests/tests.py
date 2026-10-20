import os
import platform
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Union

import AnimationSchema
import AnimationSchemaTools
import omni.kit.property.usd
import omni.kit.ui_test as ui_test
import omni.kit.window.property as p
import omni.ui as ui
from omni.kit.test_suite.helpers import wait_stage_loading
from omni.kit.viewport.utility import get_active_viewport
from omni.timeline import get_timeline_interface
from pxr import Gf, Sdf, Usd, UsdGeom

from ..scripts import utils
from ..scripts.commands import AnimCurveCommandBase
from ..scripts.keySelection import *
from ..scripts.utils import get_curvekey_clipboard, set_curvekey_clipboard
from .log_error_checker import LogErrorChecker
from .visual_test_base import AnimationVisualTestBase


# Old API replacements
def _get_keys(prim, curve_name):
    times = []
    values = []

    curve = utils.curve_plugin.get_curves(str(prim.GetPath())).get(curve_name)
    if curve is not None:
        for key in curve.keys:
            times.append(key.time)
            values.append(key.value)

    return times, values


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
        curve_names = utils.get_curves(prim=prim)
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
                t_time = utils.time_code_to_key_time(prim, t_time)
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
        curves = utils.get_curve_plugin().get_curves(str(prim.GetPath()))
        self.assertIsNotNone(curves)
        self.assertEqual(len(curves), len(target), "The number of curves does not match.")
        self._check_curves(prim, target)


class AnimCurveCommandBaseTestUtility(AnimCurveCommandBase):
    """
    This class is for testing purposes only.
    """

    def __init__(
        self,
        _name: str = "AnimCurveCommandBaseTestUtility",
        stage: Union[Usd.Stage, None] = None,
        paths: Union[list, None] = None,
        time: Union[Usd.TimeCode, None] = None,
        test_stage: str = "none",
    ):
        super().__init__(_name, stage, paths, time)
        self._test_stage = test_stage

    def _do(self) -> Union[bool, list]:
        if self._test_stage == "base_do":
            return super()._do()
        elif self._test_stage == "parse_path":
            rtn_values = []
            for path in self._paths:
                rtn = self._parse_path(path)
                if rtn is None:  # error occurs
                    return False
                else:  # no error
                    rtn_values.append(rtn)
                    # uncomment when debugging
                    # prim_path, attr_token, comp_len, comp_idx, is_prim_path, is_comp_path = rtn
                    # carb.log_warn((prim_path, attr_token, comp_len, comp_idx, is_prim_path, is_comp_path))
            return rtn_values
        else:
            return True


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


class AnimCurveTests(AnimationVisualTestBase, AnimCurveTestUtility):
    """
    Setup will set the
        1. self._GOLDEN_IMG_DIR
        2. self_MAP_DIR
        They will be served as the root folder of the golden image and USD map
    """

    async def setUp(self):
        await super().setUp()
        module_root = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
        self._GOLDEN_IMG_DIR = module_root.joinpath("data/golden_img")
        self._MAP_DIR = module_root.joinpath("data/test_map")

    """
    The first test case load a simple animated cube. Advance the time and compare the rendered result in VIEWPORT
    """
    # async def test_anim_curve_basic(self):

    #     #Setup the viewport, rendering settings
    #     await self.setup_viewport_test()

    #     #Load the USD map
    #     await self.load_stage(map_name="basic_curve_cube.usda")

    #     #warm up
    #     await wait_stage_loading()

    #     #Advance to frame 30
    #     await self.advance_n_frames(30)

    #     await wait_stage_loading()

    #     # Compare with the golden image, image assumes png format
    #     await self.do_visual_test(img_name="anim_curve_basic")

    """
    SetAnimCurveKeys test case 1.1: prims' path - when there are no existing curves
    """

    async def test_anim_curve_set_key_prim_path(self):
        await self.load_stage(map_name="basic_cube.usda")
        await wait_stage_loading()
        await self.advance_n_frames(30)
        await wait_stage_loading()

        stage = omni.usd.get_context().get_stage()

        prim = stage.GetPrimAtPath("/World/Cube")

        # check if there are no existing curves
        curve_names = utils.get_curves(prim=prim)
        self.assertIsNone(curve_names)

        # Set
        (result, err) = omni.kit.commands.execute("SetAnimCurveKeys", paths=["/World/Cube"])
        # self.assertTrue(result) # command execution no exception from the command framework
        # self.assertTrue(err)    # SetAnimCurveKeys command no error

        # Test if default curves of length 1 are created
        self._check_default_curve_name(prim)
        self._check_default_curve_length(prim, 1)
        # Check the contents
        target = {
            # "size:x": {30: 100},
            "visibility:x": {30: 0},
            "xformOp:rotateXYZ:x": {30: 0},
            "xformOp:rotateXYZ:y": {30: 0},
            "xformOp:rotateXYZ:z": {30: 0},
            "xformOp:scale:x": {30: 0.5},
            "xformOp:scale:y": {30: 0.5},
            "xformOp:scale:z": {30: 0.5},
            "xformOp:translate:x": {30: 0},
            "xformOp:translate:y": {30: 0},
            "xformOp:translate:z": {30: 0},
        }
        self._check_curves(prim, target)

    """
    SetAnimCurveKeys test case 1.1: prims' path - when there are existing curves
    """

    async def test_anim_curve_set_key_prim_path_with_existing_curves(self):
        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()
        await self.advance_n_frames(30)
        await wait_stage_loading()

        stage = omni.usd.get_context().get_stage()

        prim = stage.GetPrimAtPath("/World/Cube")

        # check if there are no existing curves
        curve_names = utils.get_curves(prim=prim)
        self.assertIsNotNone(curve_names)

        # Set
        (result, err) = omni.kit.commands.execute("SetAnimCurveKeys", paths=["/World/Cube"])
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # SetAnimCurveKeys command no error

        # Check the contents
        target = {
            "size:x": {20: 130, 30: 130},
            "visibility:x": {30: 0},
            "xformOp:rotateXYZ:x": {30: 0},
            "xformOp:rotateXYZ:y": {30: 0},
            "xformOp:rotateXYZ:z": {30: 0},
            "xformOp:scale:x": {30: 1},
            "xformOp:scale:y": {30: 1},
            "xformOp:scale:z": {30: 1},
            "xformOp:translate:x": {30: 0},
            "xformOp:translate:y": {30: 0},
            "xformOp:translate:z": {30: 0},
        }
        self._check_curves(prim, target)

    """
    SetAnimCurveKeys test case 2: curves' path
    """

    async def test_anim_curve_set_key_curve_path(self):
        await self.load_stage(map_name="basic_cube.usda")
        await wait_stage_loading()
        await self.advance_n_frames(10)
        await wait_stage_loading()

        stage = omni.usd.get_context().get_stage()

        prim = stage.GetPrimAtPath("/World/Cube")

        # Test Case 2.1: When there are no existing curves
        # check if there are no existing curves
        curve_names = utils.get_curves(prim=prim)
        self.assertIsNone(curve_names)

        # Add .size attribute
        (result, err) = omni.kit.commands.execute("SetAnimCurveKeys", paths=["/World/Cube.size"])
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # SetAnimCurveKeys command no error
        target = {
            "size:x": {10: 100},
        }
        self._check_curves(prim, target)

        # xformOp:scale
        await self.advance_n_frames(10)  # actually, it's `move_forward_time_in_frame`. so, 10+10
        await wait_stage_loading()
        (result, err) = omni.kit.commands.execute("SetAnimCurveKeys", paths=["/World/Cube.xformOp:scale"])
        self.assertTrue(result)
        self.assertTrue(err)
        target = {
            "size:x": {10: 100},
            "xformOp:scale:x": {20: 0.5},
            "xformOp:scale:y": {20: 0.5},
            "xformOp:scale:z": {20: 0.5},
        }
        self._check_curves(prim, target)

        # xformOp:scale|x, value = 2.0
        await self.advance_n_frames(10)
        await wait_stage_loading()  # 10+10+10
        (result, err) = omni.kit.commands.execute("SetAnimCurveKeys", paths=["/World/Cube.xformOp:scale|x"], value=2.0)
        self.assertTrue(result)
        self.assertTrue(err)
        target = {
            "size:x": {10: 100},
            "xformOp:scale:x": {20: 0.5, 30: 2},
            "xformOp:scale:y": {20: 0.5},
            "xformOp:scale:z": {20: 0.5},
        }
        self._check_curves(prim, target)

        # xformOp:scale|x, value = None (it should be 2.0, since it was set 2.0 last time)
        await wait_stage_loading()
        await self.advance_n_frames(10)  # 10+10+10+10

        # Triggers update 3 times to wait for graph to write back to USD for Kit 105
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()

        (result, err) = omni.kit.commands.execute("SetAnimCurveKeys", paths=["/World/Cube.xformOp:scale|x"])
        self.assertTrue(result)
        self.assertTrue(err)
        target = {
            "size:x": {10: 100},
            "xformOp:scale:x": {20: 0.5, 30: 2, 40: 2},
            "xformOp:scale:y": {20: 0.5},
            "xformOp:scale:z": {20: 0.5},
        }
        self._check_curves(prim, target)

        # test case for `time` parameter
        (result, err) = omni.kit.commands.execute(
            "SetAnimCurveKeys", paths=["/World/Cube.xformOp:scale|x"], time=Usd.TimeCode(50)
        )
        self.assertTrue(result)
        self.assertTrue(err)
        target = {
            "size:x": {10: 100},
            "xformOp:scale:x": {20: 0.5, 30: 2, 40: 2, 50: 2},
            "xformOp:scale:y": {20: 0.5},
            "xformOp:scale:z": {20: 0.5},
        }

        self._check_curves(prim, target)

    """
    SetAnimCurveKeys test case 3: paths == None
    """

    async def test_anim_curve_set_key_none_path(self):
        await self.load_stage(map_name="basic_cube.usda")
        await wait_stage_loading()
        await self.advance_n_frames(30)
        await wait_stage_loading()
        stage = omni.usd.get_context().get_stage()
        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)
        await wait_stage_loading()

        prim = stage.GetPrimAtPath("/World/Cube")

        # check if there are no existing curves
        curve_names = utils.get_curves(prim=prim)
        self.assertIsNone(curve_names)

        # Set
        (result, err) = omni.kit.commands.execute("SetAnimCurveKeys", paths=None)
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # SetAnimCurveKeys command no error

        # Test if default curves of length 1 are created
        self._check_default_curve_name(prim)
        self._check_default_curve_length(prim, 1)
        # Check the contents
        target = {
            "visibility:x": {30: 0},
            "xformOp:rotateXYZ:x": {30: 0},
            "xformOp:rotateXYZ:y": {30: 0},
            "xformOp:rotateXYZ:z": {30: 0},
            "xformOp:scale:x": {30: 0.5},
            "xformOp:scale:y": {30: 0.5},
            "xformOp:scale:z": {30: 0.5},
            "xformOp:translate:x": {30: 0},
            "xformOp:translate:y": {30: 0},
            "xformOp:translate:z": {30: 0},
        }
        self._check_curves(prim, target)

    """
    SetAnimCurveKeys test case 4: a combination of curves' path
    """

    async def test_anim_curve_set_key_combination(self):
        await self.load_stage(map_name="basic_cube.usda")
        await wait_stage_loading()
        await self.advance_n_frames(30)
        await wait_stage_loading()

        stage = omni.usd.get_context().get_stage()

        prim = stage.GetPrimAtPath("/World/Cube")

        # check if there are no existing curves
        curve_names = utils.get_curves(prim=prim)
        self.assertIsNone(curve_names)

        # Set
        paths = [
            "/World/Cube.xformOp:rotateXYZ|x",
            "/World/Cube.xformOp:rotateXYZ|y",
            "/World/Cube.xformOp:rotateXYZ|z",
            "/World/Cube.size",  # the same as /World/Cube.size|x
        ]
        (result, err) = omni.kit.commands.execute("SetAnimCurveKeys", paths=paths, value=3.1415926)
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # SetAnimCurveKeys command no error

        # Check the contents
        target = {
            "size:x": {30: 3.1415926},
            "xformOp:rotateXYZ:x": {30: 3.1415926},
            "xformOp:rotateXYZ:y": {30: 3.1415926},
            "xformOp:rotateXYZ:z": {30: 3.1415926},
        }
        self._check_curves(prim, target)

    """
    SetAnimCurveKeys test case 6: Test inTangentType, outTangentType, and tangentBreakDown
    """

    async def test_anim_curve_set_key_tangent_properties(self):
        await self.load_stage(map_name="basic_cube.usda")
        await wait_stage_loading()
        await self.advance_n_frames(30)
        await wait_stage_loading()

        stage = omni.usd.get_context().get_stage()

        prim = stage.GetPrimAtPath("/World/Cube")

        # check if there are no existing curves
        curve_names = utils.get_curves(prim=prim)
        self.assertIsNone(curve_names)

        # Set - Prim Path
        paths = [
            "/World/Cube",
        ]
        (result, err) = omni.kit.commands.execute(
            "SetAnimCurveKeys",
            paths=paths,
            time=0,
            inTangentType="fixed",
            outTangentType="smooth",
            tangentBreakDown=False,
        )
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # SetAnimCurveKeys command no error

        # Set - Attribute Path
        paths = [
            "/World/Cube.xformOp:rotateXYZ|z",
            "/World/Cube.size",  # the same as /World/Cube.size|x
        ]
        (result, err) = omni.kit.commands.execute(
            "SetAnimCurveKeys",
            paths=paths,
            value=3.1415926,
            inTangentType="step",
            outTangentType="auto",
            tangentBreakDown=True,
        )  # step inTangentType is meaningless and will fallback to auto silently
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # SetAnimCurveKeys command no error

        # Check the values
        target = {
            "size:x": {30: 3.1415926},
            "visibility:x": {0: 0},
            "xformOp:rotateXYZ:x": {0: 0},
            "xformOp:rotateXYZ:y": {0: 0},
            "xformOp:rotateXYZ:z": {0: 0, 30: 3.1415926},
            "xformOp:scale:x": {0: 0.5},
            "xformOp:scale:y": {0: 0.5},
            "xformOp:scale:z": {0: 0.5},
            "xformOp:translate:x": {0: 0},
            "xformOp:translate:y": {0: 0},
            "xformOp:translate:z": {0: 0},
        }
        self._check_curves(prim, target)

        # Check the tangent properties
        curve_api = AnimationSchema.AnimationCurveAPI.Get(prim.GetStage(), utils.get_animation_prim_path(prim))
        self.assertTrue(curve_api)

        existing_key = curve_api.GetKeys("size:x")[0]
        self.assertTrue(existing_key.tangentBroken)
        self.assertEqual(existing_key.inTangent.type, "auto")  # step inTangentType is not allowed, fallback to auto
        self.assertEqual(existing_key.outTangent.type, "auto")

        existing_key = curve_api.GetKeys("xformOp:rotateXYZ:z")[0]
        self.assertFalse(existing_key.tangentBroken)
        self.assertEqual(existing_key.inTangent.type, "fixed")
        self.assertEqual(existing_key.outTangent.type, "smooth")

        existing_key = curve_api.GetKeys("xformOp:rotateXYZ:z")[1]
        self.assertTrue(existing_key.tangentBroken)
        self.assertEqual(existing_key.inTangent.type, "auto")  # step inTangentType is not allowed, fallback to auto
        self.assertEqual(existing_key.outTangent.type, "auto")

    """
    SetAnimCurveKeys test case 7: PreserveShape
    """

    async def test_anim_curve_set_key_preserve_shape(self):
        await self.load_stage(map_name="curve_cube_preserve_shape.usda")
        await wait_stage_loading()

        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath("/World/Cube")
        paths = ["/World/Cube.xformOp:translate|x"]
        timeline_iface = get_timeline_interface()

        time_codes = list(range(-5, 85))
        attr = prim.GetAttribute("xformOp:translate")
        # origin_values = []  # this is EXACTLY how target_values are produced
        # for t in time_codes:
        #     timeline_iface.set_current_time(t / 24)  # current_frame / FPS
        #     await ui_test.human_delay()
        #     origin_values.append(attr.Get()[0])
        # print(f'test_anim_curve_set_key_preserve_shape: origin_values: {origin_values}')

        target_values = [
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            -4.122206322888159,
            -6.6823424154604805,
            -7.086924472127416,
            -4.742468687299416,
            0.9445087446130678,
            10.567491629199587,
            24.719963772049702,
            43.99540897875292,
            68.98731105489885,
            100.289153806077,
            136.0302606007778,
            173.00137810028554,
            210.20363136876563,
            246.8814281989383,
            282.30895192917694,
            315.62726312742717,
            345.61329818214796,
            370.16567627283007,
            384.62767884498265,
            370.6647721830309,
            289.46973071396275,
            217.41872990081723,
            171.7436627431238,
            146.04017405732668,
            134.89004118304186,
            134.7362058716233,
            143.20923396815695,
            158.66400223903406,
            179.91190184999502,
            206.06440936015574,
            302.9663331901474,
            396.1145747069079,
            484.13510879628734,
            564.7052987145888,
            633.401492590733,
            680.030528669422,
            671.5637171297933,
            503.30806152514765,
            385.03385120976753,
            358.8886546027529,
            351.9274363522272,
            339.405882213502,
            322.7605601365262,
            303.47437307430744,
            283.02727697106627,
            262.8492924567048,
            244.2797070656161,
            228.53525712781388,
            216.68862751179608,
            209.65723282270187,
            209.65723282270187,
            209.65723282270187,
            209.65723282270187,
            209.65723282270187,
            209.65723282270187,
            209.65723282270187,
            209.65723282270187,
            209.65723282270187,
            209.65723282270187,
            209.65723282270187,
            278.4624234468157,
            318.38642245251185,
            334.5259111725128,
            331.9775709395425,
            315.83808308632376,
            291.2041230514592,
            263.17237823515,
            236.8395284099107,
            217.30225334825653,
            209.65723282270187,
            203.63677669055204,
            187.29553861757424,
            163.21371408897545,
            133.97149858996238,
            102.14908760574272,
            70.32667662152308,
            41.08446112251003,
            17.002636593911248,
            0.6613985209334317,
            -5.359057611216393,
            -5.359057611216393,
            -5.359057611216393,
            -5.359057611216393,
            -5.359057611216393,
        ]

        for time in range(5, 80, 10):
            timeline_iface.set_current_time(time / 24)
            await ui_test.human_delay()

            (result, err) = omni.kit.commands.execute(
                "SetAnimCurveKeys",
                paths=paths,
            )  # preserveCurveShape=True by default
            self.assertTrue(result)  # command execution no exception from the command framework
            self.assertTrue(err)  # SetAnimCurveKeys command no error

        # check the values after adding keys. Compare with the target_values
        for t, target_value in zip(time_codes, target_values):
            timeline_iface.set_current_time(t / 24)  # current_frame / FPS
            await ui_test.human_delay()
            current_value = attr.Get()[0]
            self.assertAlmostEqual(
                current_value,
                target_value,
                msg="At time %d, current value is %f. Should be %f." % (t, current_value, target_value),
                places=4,
            )
        # reset the timeline to 0
        timeline_iface.set_current_time(0)  # current_frame / FPS
        await ui_test.human_delay()

    async def test_anim_curve_set_curve_default_tangent_type(self):
        # set up a cube with one key/curve
        await self._context.new_stage_async()
        stage = self._context.get_stage()
        cube = UsdGeom.Cube.Define(stage, "/World/Cube")
        cube.CreateSizeAttr(100)
        result = omni.kit.commands.execute("SetAnimCurveKeys", paths=["/World/Cube.size"])
        self.assertTrue(result)

        curve_api = AnimationSchema.AnimationCurveAPI.Get(stage, utils.get_animation_prim_path(cube.GetPrim()))
        self.assertTrue(curve_api)

        def verify_set_default_tangent(target_path: str):
            class ExpectedResult:
                def __init__(self, in_tangent, out_tangent):
                    self.in_tangent = in_tangent
                    self.out_tangent = out_tangent

            tangent_types = {
                "auto": ExpectedResult("auto", "auto"),
                "smooth": ExpectedResult("smooth", "smooth"),
                "linear": ExpectedResult("linear", "linear"),
                "fixed": ExpectedResult("fixed", "fixed"),
                # inTangentType can not be "step".
                # See add_key function in omni.anim.curve.core/python/scripts/utils.py
                "step": ExpectedResult("auto", "step"),
            }
            for default_tangent, expected_result in tangent_types.items():
                result = omni.kit.commands.execute(
                    "SetAnimCurveDefaultTangentType", paths=[target_path], default_tangent_type=default_tangent
                )
                self.assertTrue(result)
                # override the existing key
                result = omni.kit.commands.execute("SetAnimCurveKeys", paths=["/World/Cube.size"])
                self.assertTrue(result)
                key = curve_api.GetKeys("size:x")[0]
                self.assertEqual(key.inTangent.type, expected_result.in_tangent)
                self.assertEqual(key.outTangent.type, expected_result.out_tangent)

        for path in ["/World/Cube", "/World/Cube.size", "/World/Cube.size|x"]:
            verify_set_default_tangent(path)

    async def test_anim_curve_set_curve_infinity_type(self):
        # set up a cube with one key/curve
        await self._context.new_stage_async()
        stage = self._context.get_stage()
        cube = UsdGeom.Cube.Define(stage, "/World/Cube")
        cube.CreateSizeAttr(100)
        result = omni.kit.commands.execute("SetAnimCurveKeys", paths=["/World/Cube.size"])
        self.assertTrue(result)

        infinity_types = ["constant", "cycle", "cycleRelative", "linear", "oscillate"]

        def verify_set_curve_pre_infinity_type(target_path: str):
            for infinity_type in infinity_types:
                result = omni.kit.commands.execute(
                    "SetAnimCurveInfinityType", paths=[target_path], is_post_infinity=False, infinity_type=infinity_type
                )
                curves = utils.get_curve_plugin().get_curves("/World/Cube")
                curve = curves["size:x"]
                self.assertTrue(result)
                self.assertEqual(infinity_type, curve.pre_infinity_type)

        def verify_set_curve_post_infinity_type(target_path: str):
            for infinity_type in infinity_types:
                result = omni.kit.commands.execute(
                    "SetAnimCurveInfinityType", paths=[target_path], is_post_infinity=True, infinity_type=infinity_type
                )
                self.assertTrue(result)

                curves = utils.get_curve_plugin().get_curves("/World/Cube")
                curve = curves["size:x"]
                self.assertEqual(infinity_type, curve.post_infinity_type)

        for path in ["/World/Cube", "/World/Cube.size", "/World/Cube.size|x"]:
            verify_set_curve_pre_infinity_type(path)
            verify_set_curve_post_infinity_type(path)

    async def test_anim_curve_infinity_type_survives_stage_reload(self):
        await self.load_stage(map_name="basic_curve_cube.usda")

        stage = self._context.get_stage()
        node_path = "/World/PushGraph/CubeCurveNode"
        curve_prefix = "xformOp:translate:x:"
        curve_name = "xformOp:translate:x"
        curve_command_path = "/World/Cube.xformOp:translate|x"
        curve_path = "/World/Cube.xformOp:translate:x"

        node = stage.GetPrimAtPath(node_path)
        self.assertTrue(node.GetAttribute(f"{curve_prefix}times"))

        result = omni.kit.commands.execute(
            "SetAnimCurveInfinityType",
            paths=[curve_command_path],
            is_post_infinity=True,
            infinity_type="cycle",
        )
        self.assertTrue(result)

        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()

        self.assertEqual("cycle", node.GetAttribute(f"{curve_prefix}postInfinityType").Get())

        with tempfile.NamedTemporaryFile(suffix=".usda", delete=False) as temp_file:
            temp_usda = temp_file.name
        try:
            stage.GetRootLayer().Export(temp_usda)

            await self._context.new_stage_async()
            result, _ = await self._context.open_stage_async(temp_usda, omni.usd.UsdContextInitialLoadSet.LOAD_ALL)
            self.assertTrue(result)
            await wait_stage_loading()

            curves = utils.get_curve_plugin().get_curves("/World/Cube")
            self.assertIn(curve_name, curves)
            self.assertEqual("cycle", curves[curve_name].post_infinity_type)

            reloaded_stage = self._context.get_stage()
            reloaded_node = reloaded_stage.GetPrimAtPath(node_path)
            self.assertEqual("cycle", reloaded_node.GetAttribute(f"{curve_prefix}postInfinityType").Get())

            fps = reloaded_stage.GetTimeCodesPerSecond()
            last_key_value = curves[curve_name].keys[-1].value
            first_key_value = curves[curve_name].keys[0].value

            # Past the authored range: cycle should repeat from the first key, not hold the last key.
            eval_time = 150.0 / fps
            cycled_value = utils.get_curve_plugin().evaluate(curve_path, eval_time)
            self.assertAlmostEqual(first_key_value, cycled_value, places=3)
            self.assertNotAlmostEqual(last_key_value, cycled_value, places=3)
        finally:
            if os.path.exists(temp_usda):
                os.unlink(temp_usda)

    async def test_anim_curve_remove_prim_with_animation(self):
        # set up a cube with one key/curve
        await self._context.new_stage_async()
        stage = self._context.get_stage()
        cube = UsdGeom.Cube.Define(stage, "/World/Cube")
        cube.CreateSizeAttr(100)
        result = omni.kit.commands.execute("SetAnimCurveKeys", paths=["/World/Cube.size"])
        self.assertTrue(result)
        curves = utils.get_curve_plugin().get_curves("/World/Cube")
        self.assertIsNotNone(curves)
        self.assertEqual(len(curves), 1)

        omni.kit.commands.execute("DeletePrims", paths=["/World/Cube"])

        prim = stage.GetPrimAtPath("/World/Cube")
        self.assertFalse(prim.IsValid())
        # animation curves should be removed with the prim
        curves = utils.get_curves(prim)
        self.assertTrue(curves is None or len(curves) == 0)
        curves = utils.get_curve_plugin().get_curves("/World/Cube")
        self.assertTrue(curves is None or len(curves) == 0)

    """
    RemoveAnimCurveKeys test case 1: prims' path or curves' path
    """

    async def test_anim_curve_remove_key_prim_curve_path(self):
        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()
        await self.advance_n_frames(20)
        await wait_stage_loading()

        stage = omni.usd.get_context().get_stage()

        prim = stage.GetPrimAtPath("/World/Cube")

        # Remove - prim's path
        (result, err) = omni.kit.commands.execute("RemoveAnimCurveKeys", paths=["/World/Cube"], stage=stage)
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # RemoveAnimCurveKeys command no error

        # Check the contents
        target = {
            "size:x": {},
        }
        self._check_curves(prim, target)

        # Remove - prim's path - do it again, should not remove anything more
        (result, err) = omni.kit.commands.execute("RemoveAnimCurveKeys", paths=["/World/Cube"], stage=stage)
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertFalse(err)  # Return False if no keys is removed or there are errors generated

        # Check the contents
        target = {
            "size:x": {},
        }
        self._check_curves(prim, target)

        # Remove - curves' path - xformOp:translate
        prim = stage.GetPrimAtPath("/World/Sphere")
        (result, err) = omni.kit.commands.execute(
            "RemoveAnimCurveKeys", paths=["/World/Sphere.xformOp:translate"], stage=stage
        )
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # RemoveAnimCurveKeys command no error

        # Check the contents
        target = {
            "xformOp:translate:x": {},
            "xformOp:translate:y": {},
            "xformOp:translate:z": {},
        }
        # self._check_curves(prim, target)  # FIXME@tutian

        # Remove - curves' path - xformOp:rotateXYZ|x
        prim = stage.GetPrimAtPath("/World/Capsule")
        (result, err) = omni.kit.commands.execute(
            "RemoveAnimCurveKeys", paths=["/World/Capsule.xformOp:rotateXYZ|x"], stage=stage
        )
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # RemoveAnimCurveKeys command no error

        # Check the contents
        target = {
            "xformOp:rotateXYZ:x": {},
            "xformOp:rotateXYZ:y": {20: 30},
            "xformOp:rotateXYZ:z": {20: 60},
        }
        self._check_curves(prim, target)

    """
    RemoveAnimCurveKeys test case 2: a combination of prims' paths and curves' paths
    """

    async def test_anim_curve_remove_key_combination(self):
        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()
        await self.advance_n_frames(20)
        await wait_stage_loading()

        stage = omni.usd.get_context().get_stage()

        # Remove - prim's path
        paths = [
            "/World/Cube",
            "/World/Sphere.xformOp:translate",
            "/World/Capsule.xformOp:rotateXYZ|x",
        ]
        (result, err) = omni.kit.commands.execute("RemoveAnimCurveKeys", paths=paths, stage=stage)
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # RemoveAnimCurveKeys command no error

        # Check the contents
        prim = stage.GetPrimAtPath("/World/Cube")
        target = {
            "size:x": {},
        }
        self._check_curves(prim, target)
        prim = stage.GetPrimAtPath("/World/Sphere")
        target = {
            "xformOp:translate:x": {},
            "xformOp:translate:y": {},
            "xformOp:translate:z": {},
        }
        # self._check_curves(prim, target)  # FIXME@tutian
        prim = stage.GetPrimAtPath("/World/Capsule")
        target = {
            "xformOp:rotateXYZ:x": {},
            "xformOp:rotateXYZ:y": {20: 30},
            "xformOp:rotateXYZ:z": {20: 60},
        }
        self._check_curves(prim, target)

    """
    RemoveAnimCurveKeys test case 3: `paths` == None
    """

    async def test_anim_curve_remove_key_none_path(self):
        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()
        await self.advance_n_frames(20)
        await wait_stage_loading()

        stage = omni.usd.get_context().get_stage()

        # Remove - prim's path
        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)
        (result, err) = omni.kit.commands.execute("RemoveAnimCurveKeys", paths=None, stage=stage)
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # RemoveAnimCurveKeys command no error

        # Check the contents
        prim = stage.GetPrimAtPath("/World/Cube")
        target = {
            "size:x": {},
        }
        self._check_curves(prim, target)

    """
    RemoveAnimCurveKeys test case 4: `time` parameter
    """

    async def test_anim_curve_remove_key_time(self):
        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()

        stage = omni.usd.get_context().get_stage()

        # with time=10, nothing should be removed
        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)
        (result, err) = omni.kit.commands.execute(
            "RemoveAnimCurveKeys", paths=None, stage=stage, time=Usd.TimeCode(10.0)
        )
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertFalse(err)  # Return False if nothing is removed

        # Check the contents -
        prim = stage.GetPrimAtPath("/World/Cube")
        target = {
            "size:x": {20: 130.0},
        }
        self._check_curves(prim, target)

        # time=20
        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)
        (result, err) = omni.kit.commands.execute(
            "RemoveAnimCurveKeys", paths=None, stage=stage, time=Usd.TimeCode(20.0)
        )
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # RemoveAnimCurveKeys command no error

        # Check the contents - should not remove anything
        prim = stage.GetPrimAtPath("/World/Cube")
        target = {
            "size:x": {},
        }
        self._check_curves(prim, target)

    """
    PasteAnimCurveKeys test case 1: Copy from one prim, paste to the prims in `paths`
    """

    async def test_anim_curve_paste_key_command_prim_path(self):
        # Load the USD map
        # "/World/Cube.size" has a key at time 20 with a value 130
        # "/World/Sphere.xformOp:translate:x", has a key at 20 with a value of 100
        # "/World/Sphere.xformOp:translate:y", has a key at 20 with a value of 120
        # "/World/Sphere.xformOp:translate:z", has a key at 20 with a value of -200
        # "/World/Capsulre.xformOp:rotateXYZ:x", has a key at 20 with a value of 45
        # "/World/Capsulre.xformOp:rotateXYZ:y", has a key at 20 with a value of 30
        # "/World/Capsulre.xformOp:rotateXYZ:z", has a key at 20 with a value of 60
        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()

        # Copy the /World/Cube key from 20 to clipboard
        stage = omni.usd.get_context().get_stage()
        set_curvekey_clipboard(stage, ["/World/Sphere"], Usd.TimeCode(20))

        # Paste clipboard to shpere and cube time 40
        (result, err) = omni.kit.commands.execute(
            "PasteAnimCurveKeys", paths=["/World/Capsule", "/World/Cube"], time=Usd.TimeCode(40)
        )
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # PasteAnimCurveKeys command no error

        prim = stage.GetPrimAtPath("/World/Capsule")
        target = {
            "xformOp:rotateXYZ:x": {20: 45},
            "xformOp:rotateXYZ:y": {20: 30},
            "xformOp:rotateXYZ:z": {20: 60},
            "xformOp:translate:x": {40.0: 100.0},
            "xformOp:translate:y": {40.0: 120.0},
            "xformOp:translate:z": {40.0: -200.0},
        }
        self._check_curves(prim, target)

        prim = stage.GetPrimAtPath("/World/Cube")
        target = {
            "size:x": {20: 130},
            "xformOp:translate:x": {40.0: 100.0},
            "xformOp:translate:y": {40.0: 120.0},
            "xformOp:translate:z": {40.0: -200.0},
        }
        self._check_curves(prim, target)

        # Paste again, with `time=None`
        await self.advance_n_frames(50)
        await wait_stage_loading()
        (result, err) = omni.kit.commands.execute("PasteAnimCurveKeys", paths=["/World/Capsule", "/World/Cube"])
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # PasteAnimCurveKeys command no error

        prim = stage.GetPrimAtPath("/World/Capsule")
        target = {
            "xformOp:rotateXYZ:x": {20: 45},
            "xformOp:rotateXYZ:y": {20: 30},
            "xformOp:rotateXYZ:z": {20: 60},
            "xformOp:translate:x": {40.0: 100.0, 50.0: 100.0},
            "xformOp:translate:y": {40.0: 120.0, 50.0: 120.0},
            "xformOp:translate:z": {40.0: -200.0, 50.0: -200},
        }
        self._check_curves(prim, target)

        prim = stage.GetPrimAtPath("/World/Cube")
        target = {
            "size:x": {20: 130},
            "xformOp:translate:x": {40.0: 100.0, 50.0: 100.0},
            "xformOp:translate:y": {40.0: 120.0, 50.0: 120.0},
            "xformOp:translate:z": {40.0: -200.0, 50.0: -200},
        }
        self._check_curves(prim, target)

    """
    PasteAnimCurveKeys test case 2: Copy from one prim, paste to the curves in `paths`
    """

    async def test_anim_curve_paste_key_command_curve_path(self):
        # "/World/Cube.size" has a key at time 20 with a value 130
        # "/World/Sphere.xformOp:translate:x", has a key at 20 with a value of 100
        # "/World/Sphere.xformOp:translate:y", has a key at 20 with a value of 120
        # "/World/Sphere.xformOp:translate:z", has a key at 20 with a value of -200
        # "/World/Capsulre.xformOp:rotateXYZ:x", has a key at 20 with a value of 45
        # "/World/Capsulre.xformOp:rotateXYZ:y", has a key at 20 with a value of 30
        # "/World/Capsulre.xformOp:rotateXYZ:z", has a key at 20 with a value of 60

        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()

        # Copy the /World/Cube key from 20 to clipboard
        stage = omni.usd.get_context().get_stage()
        set_curvekey_clipboard(stage, ["/World/Sphere"], Usd.TimeCode(20))

        paths = ["/World/Capsule.xformOp:rotateXYZ|x", "/World/Cube.xformOp:translate|y"]

        # Paste clipboard to shpere and cube time 40
        (result, err) = omni.kit.commands.execute("PasteAnimCurveKeys", paths=paths, time=Usd.TimeCode(40))
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # PasteAnimCurveKeys command no error

        prim = stage.GetPrimAtPath("/World/Capsule")
        target = {
            "xformOp:rotateXYZ:x": {20: 45, 40.0: 100.0},
            "xformOp:rotateXYZ:y": {20: 30},
            "xformOp:rotateXYZ:z": {20: 60},
        }
        self._check_curves(prim, target)

        prim = stage.GetPrimAtPath("/World/Cube")
        target = {
            "size:x": {20: 130},
            "xformOp:translate:y": {40.0: 120.0},
        }
        self._check_curves(prim, target)

    # For None path, since we have refactored the commands with the base class, it should works as long as the other
    # commands work with paths=None. Explicitly test this command with `paths=None` will not introduce new code paths

    """
    PasteAnimCurveKeys test case 3: Copy from one prim, delete its curves, and paste to the prims or curves in `paths`
    """

    async def test_anim_curve_paste_key_command_copy_delete_and_paste(self):
        # "/World/Cube.size" has a key at time 20 with a value 130
        # "/World/Sphere.xformOp:translate:x", has a key at 20 with a value of 100
        # "/World/Sphere.xformOp:translate:y", has a key at 20 with a value of 120
        # "/World/Sphere.xformOp:translate:z", has a key at 20 with a value of -200
        # "/World/Capsulre.xformOp:rotateXYZ:x", has a key at 20 with a value of 45
        # "/World/Capsulre.xformOp:rotateXYZ:y", has a key at 20 with a value of 30
        # "/World/Capsulre.xformOp:rotateXYZ:z", has a key at 20 with a value of 60

        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()

        # Copy the /World/Cube key from 20 to clipboard
        stage = omni.usd.get_context().get_stage()
        set_curvekey_clipboard(stage, ["/World/Sphere"], Usd.TimeCode(20))

        # Remove all the keys of the prim
        (result, err) = omni.kit.commands.execute("RemoveAnimCurves", paths=["/World/Sphere"])
        self.assertTrue(result)
        self.assertTrue(err)

        # Paste clipboard to prims at time 50
        (result, err) = omni.kit.commands.execute(
            "PasteAnimCurveKeys", paths=["/World/Capsule", "/World/Cube"], time=Usd.TimeCode(50)
        )
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # PasteAnimCurveKeys command no error

        prim = stage.GetPrimAtPath("/World/Capsule")
        target = {
            "xformOp:rotateXYZ:x": {20: 45},
            "xformOp:rotateXYZ:y": {20: 30},
            "xformOp:rotateXYZ:z": {20: 60},
            "xformOp:translate:x": {50.0: 100.0},
            "xformOp:translate:y": {50.0: 120.0},
            "xformOp:translate:z": {50.0: -200.0},
        }
        self._check_curves(prim, target)

        prim = stage.GetPrimAtPath("/World/Cube")
        target = {
            "size:x": {20: 130},
            "xformOp:translate:x": {50.0: 100.0},
            "xformOp:translate:y": {50.0: 120.0},
            "xformOp:translate:z": {50.0: -200.0},
        }
        self._check_curves(prim, target)

        # Paste clipboard to curves at time 40
        paths = ["/World/Capsule.xformOp:rotateXYZ|x", "/World/Cube.xformOp:translate|y"]
        (result, err) = omni.kit.commands.execute("PasteAnimCurveKeys", paths=paths, time=Usd.TimeCode(40))
        self.assertTrue(result)
        self.assertTrue(err)

        prim = stage.GetPrimAtPath("/World/Capsule")
        target = {
            "xformOp:rotateXYZ:x": {20: 45, 40.0: 100.0},
            "xformOp:rotateXYZ:y": {20: 30},
            "xformOp:rotateXYZ:z": {20: 60},
            "xformOp:translate:x": {50.0: 100.0},
            "xformOp:translate:y": {50.0: 120.0},
            "xformOp:translate:z": {50.0: -200.0},
        }
        self._check_curves(prim, target)

        prim = stage.GetPrimAtPath("/World/Cube")
        target = {
            "size:x": {20: 130},
            "xformOp:translate:x": {50.0: 100.0},
            "xformOp:translate:y": {40.0: 120.0, 50.0: 120.0},
            "xformOp:translate:z": {50.0: -200.0},
        }
        self._check_curves(prim, target)

    """
    PasteAnimCurveKeys test case 4: Copy and paste one single curve
    """

    async def test_anim_curve_paste_key_command_one_curve(self):
        cube_size = 100
        cube_path = "/World/Cube"
        cube_size_path = "/World/Cube.size"
        key_time = 20

        async def init_one_key_cube_stage():
            await self._context.new_stage_async()
            stage = self._context.get_stage()
            cube = UsdGeom.Cube.Define(stage, cube_path)
            cube.CreateSizeAttr(cube_size)
            result = omni.kit.commands.execute("SetAnimCurveKeys", paths=[cube_size_path], time=key_time)
            self.assertTrue(result)
            return stage

        # Paste one key to an attribute path
        stage = await init_one_key_cube_stage()
        set_curvekey_clipboard(stage, [cube_path], Usd.TimeCode(key_time))
        paths = [cube_size_path]
        past_to_time = 40
        (result, err) = omni.kit.commands.execute("PasteAnimCurveKeys", paths=paths, time=Usd.TimeCode(past_to_time))
        self.assertTrue(result)
        self.assertTrue(err)

        target = {
            "size:x": {key_time: cube_size, past_to_time: cube_size},
        }
        prim = stage.GetPrimAtPath(cube_path)
        self._check_curves_strict(prim, target)

        # Past one key to a prim path
        stage = await init_one_key_cube_stage()
        set_curvekey_clipboard(stage, [cube_path], Usd.TimeCode(key_time))
        paths = [cube_path]
        (result, err) = omni.kit.commands.execute("PasteAnimCurveKeys", paths=paths, time=Usd.TimeCode(past_to_time))
        self.assertTrue(result)
        self.assertTrue(err)

        prim = stage.GetPrimAtPath(cube_path)
        self._check_curves_strict(prim, target)

        # Past one key to a component path
        stage = await init_one_key_cube_stage()
        set_curvekey_clipboard(stage, [cube_path], Usd.TimeCode(key_time))
        paths = [cube_size_path + "|x"]
        (result, err) = omni.kit.commands.execute("PasteAnimCurveKeys", paths=paths, time=Usd.TimeCode(past_to_time))
        self.assertTrue(result)
        self.assertTrue(err)

        prim = stage.GetPrimAtPath(cube_path)
        self._check_curves_strict(prim, target)

    """
    Add/RemoveAnimCurves test case 1: prims' path
    """

    async def test_anim_curve_add_remove_prim_path(self):

        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()

        stage = omni.usd.get_context().get_stage()

        # Remove
        (result, err) = omni.kit.commands.execute("RemoveAnimCurves", paths=["/World/Cube"])
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # RemoveAnimCurve command no error

        # Test if all curves of /World/Cube are removed
        prim = stage.GetPrimAtPath("/World/Cube")
        curve_names = utils.get_curves(prim=prim)
        self.assertTrue(curve_names is None)

        # Add
        (result, err) = omni.kit.commands.execute("AddAnimCurves", paths=["/World/Cube"])
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # AddAnimCurves command no error

        # Test if the default empty curves are created
        self._check_empty_default_curves(prim)

    """
    Add/RemoveAnimCurves test case 2: curves' path
    """

    async def test_anim_curve_add_remove_curve_path(self):

        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()

        stage = omni.usd.get_context().get_stage()

        """
            Case 2.1: when there are existing curves in a prim
        """
        # Add
        paths = ["/World/Cube.xformOp:translate|x"]
        # Ensure there is no such curve before we add it
        prim = stage.GetPrimAtPath("/World/Cube")
        curve_names = utils.get_curves(prim=prim)
        self.assertTrue("xformOp:translate:x" not in curve_names)

        (result, err) = omni.kit.commands.execute("AddAnimCurves", paths=paths)
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # AddAnimCurves command no error

        # Test if 'xformOp:translate:x' is added
        curve_names = utils.get_curves(prim=prim)
        self.assertTrue("xformOp:translate:x" in curve_names)

        # Remove
        (result, err) = omni.kit.commands.execute("RemoveAnimCurves", paths=paths)
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # RemoveAnimCurve command no error

        curve_names = utils.get_curves(prim=prim)
        self.assertTrue("xformOp:translate:x" not in curve_names)

        """
            Case 2.2: when there are no existing curves in a prim
        """
        # Remove all curves of /World/Cube, which has been tested in test case 1
        (result, err) = omni.kit.commands.execute("RemoveAnimCurves", paths=["/World/Cube"])
        # Add - when there are no existing curves in a prim
        (result, err) = omni.kit.commands.execute("AddAnimCurves", paths=paths)
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # AddAnimCurves command no error

        # Test if 'xformOp:translate:x' is added
        prim = stage.GetPrimAtPath("/World/Cube")
        curve_names = utils.get_curves(prim=prim)
        self.assertTrue(len(curve_names) == 1)
        self.assertTrue(curve_names[0] == "xformOp:translate:x")

        # Remove
        (result, err) = omni.kit.commands.execute("RemoveAnimCurves", paths=paths)
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # RemoveAnimCurve command no error

        curve_names = utils.get_curves(prim=prim)
        self.assertTrue(curve_names is None)

    """
    Add/RemoveAnimCurves test case 3: paths == None
    """

    async def test_anim_curve_add_remove_none_path(self):

        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()

        stage = omni.usd.get_context().get_stage()

        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)
        await wait_stage_loading()

        # Remove
        (result, err) = omni.kit.commands.execute("RemoveAnimCurves", paths=None)
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # RemoveAnimCurve command no error

        # Test if all curves of /World/Cube are removed
        prim = stage.GetPrimAtPath("/World/Cube")
        all_keys = utils.get_curves(prim=prim)
        self.assertTrue(all_keys is None)

        # Add
        (result, err) = omni.kit.commands.execute("AddAnimCurves", paths=None)
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # AddAnimCurves command no error

        # Test if the default empty curves are created
        self._check_empty_default_curves(prim)

    """
    Add/RemoveAnimCurves test case 4: `paths` is a combination of curves' path and prims' path
    """

    async def test_anim_curve_add_remove_combination(self):
        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()

        stage = omni.usd.get_context().get_stage()

        # Remove
        paths = ["/World/Cube", "/World/Sphere.xformOp:translate", "/World/Capsule.xformOp:rotateXYZ|z"]
        (result, err) = omni.kit.commands.execute("RemoveAnimCurves", paths=paths)
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # AddAnimCurves command no error
        # Cube
        prim = stage.GetPrimAtPath("/World/Cube")
        curve_names = utils.get_curves(prim=prim)
        self.assertTrue(curve_names is None)
        # Sphere
        prim = stage.GetPrimAtPath("/World/Sphere")
        curve_names = utils.get_curves(prim=prim)
        self.assertTrue(curve_names is None)
        # Capsule
        prim = stage.GetPrimAtPath("/World/Capsule")
        curve_names = utils.get_curves(prim=prim)
        self.assertTrue("xformOp:rotateXYZ:z" not in curve_names)

        # Add
        paths = ["/World/Cube", "/World/Sphere.xformOp:translate", "/World/Capsule.xformOp:rotateXYZ|z"]
        (result, err) = omni.kit.commands.execute("AddAnimCurves", paths=paths)
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # AddAnimCurves command no error
        # Cube - check if the default empty curves are created
        prim = stage.GetPrimAtPath("/World/Cube")
        self._check_empty_default_curves(prim)
        # Sphere
        prim = stage.GetPrimAtPath("/World/Sphere")
        curve_names = utils.get_curves(prim=prim)
        self.assertTrue("xformOp:translate:x" in curve_names)
        self.assertTrue("xformOp:translate:y" in curve_names)
        self.assertTrue("xformOp:translate:z" in curve_names)
        # Capsule
        prim = stage.GetPrimAtPath("/World/Capsule")
        curve_names = utils.get_curves(prim=prim)
        self.assertTrue("xformOp:rotateXYZ:z" in curve_names)

    async def test_select_key(self):
        await self.load_stage(map_name="basic_curve_cube.usda")
        await wait_stage_loading()

        omni.kit.commands.execute(
            "SelectAnimCurveKeys",
            paths=["/World/Cube.xformOp:translate|xy", "/World/Cube.xformOp:rotateXYZ"],
            times=(0, 100),
            in_tangent=True,
        )
        omni.kit.commands.execute(
            "SelectAnimCurveKeys", paths=["/World/Cube.xformOp:translate"], operation="remove", in_tangent=True
        )
        omni.kit.commands.execute(
            "SelectAnimCurveKeys", paths=["/World/Cube.xformOp:scale"], operation="add", in_tangent=True
        )
        print("Selected keys are " + str(KeySelectionState.global_instance.curves))

        omni.kit.commands.execute("EditAnimCurveKeys", value=123, additive=True, tangent_type="fixed")

        omni.kit.commands.execute("SelectAnimCurveKeys", paths=["/World/Cube.xformOp:translate"], key=True)
        omni.kit.commands.execute("EditAnimCurveKeys", time=10, additive=True)
        print("Moved selected keys are " + str(KeySelectionState.global_instance.curves))

        omni.kit.commands.execute("RemoveAnimCurves", paths=["/World/Cube.xformOp:translate|x"])
        print("After deleting curves, selected keys are " + str(KeySelectionState.global_instance.curves))

    async def test_layers_with_different_tcps(self):
        await self.load_stage(map_name="anim_with_diff_fps/root_30fps.usda")
        await wait_stage_loading()

        await self.advance_n_frames(30)
        await wait_stage_loading()

        stage = omni.usd.get_context().get_stage()

        prim = stage.GetPrimAtPath("/World/Cube")
        self.assertAlmostEqual(prim.GetAttribute("xformOp:translate").Get()[0], 549.4260831124309)

        prim = stage.GetPrimAtPath("/World/Sphere")
        self.assertAlmostEqual(prim.GetAttribute("xformOp:translate").Get()[0], 266.8484549534043)

    async def test_individual_outputs(self):
        await self.load_stage(map_name="basic_curve_cube.usda")
        await wait_stage_loading()

        omni.kit.commands.execute(
            "ChangeProperty", prop_path="/World/PushGraph/CubeCurveNode.inputs:IndividualOutputs", value="*", prev=None
        )

        await self.advance_n_frames(20)

        import omni.graph.core as og

        node = og.get_node_by_path("/World/PushGraph/CubeCurveNode")

        outputs = {
            "xformOp:rotateXYZ:x": 0,
            "xformOp:rotateXYZ:y": 0,
            "xformOp:rotateXYZ:z": 0,
            "xformOp:scale:x": 0.5,
            "xformOp:scale:y": 0.5,
            "xformOp:scale:z": 0.5,
            "xformOp:translate:x": 123.2185185185185,
            "xformOp:translate:y": 52.465777777777795,
            "xformOp:translate:z": 185.70444444444445,
        }

        for name, value in outputs.items():
            attr = node.get_attribute("outputs:" + name)
            print(f"{attr} {attr.get()}")
            self.assertAlmostEqual(attr.get(), value)

            """
    Test adding animation keys to a prim when there is already another prim with animations.

    This test verifies that:
    1. Animation can be successfully added to new prims when other prims already have animation
    2. The system correctly handles multiple prims with animation simultaneously
    """

    async def test_anim_curve_set_key_with_existing_animation_on_other_prim(self):
        # ============================================================================
        # Setup: Load stage with existing animation and advance to target time
        # ============================================================================
        await self.load_stage(map_name="basic_curve_cube.usda")
        await wait_stage_loading()
        await self.advance_n_frames(30)

        stage = omni.usd.get_context().get_stage()

        # ============================================================================
        # Step 1: Verify existing prim has animation
        # ============================================================================
        cube_prim = stage.GetPrimAtPath("/World/Cube")
        cube_curves = utils.get_curves(prim=cube_prim)
        self.assertTrue(cube_curves, "Existing prim should have animation curves")

        # ============================================================================
        # Step 2: Create first new prim and add animation
        # ============================================================================
        sphere = UsdGeom.Sphere.Define(stage, "/World/Sphere")

        (result, err) = omni.kit.commands.execute("SetAnimCurveKeys", paths=["/World/Sphere"])
        self.assertTrue(result, "Command execution should succeed")
        self.assertTrue(err, "SetAnimCurveKeys command should succeed")

        # Verify first new prim has only visibility animation
        sphere_prim = stage.GetPrimAtPath("/World/Sphere")
        sphere_curves = utils.get_curves(prim=sphere_prim)
        self.assertIsNotNone(sphere_curves, "New prim should have animation curves")
        self.assertIn("visibility:x", sphere_curves, "New prim should have visibility animation")
        self.assertEqual(len(sphere_curves), 1, "New prim should have only visibility animation")

        # Verify animation values
        target_sphere = {"visibility:x": {30: 0}}
        self._check_curves(sphere_prim, target_sphere)

        # ============================================================================
        # Step 3: Create second new prim and add animation
        # ============================================================================
        cone = UsdGeom.Cone.Define(stage, "/World/Cone")

        (result, err) = omni.kit.commands.execute("SetAnimCurveKeys", paths=["/World/Cone"])
        self.assertTrue(result, "Command execution should succeed")
        self.assertTrue(err, "SetAnimCurveKeys command should succeed")

        # Verify second new prim has only visibility animation
        cone_prim = stage.GetPrimAtPath("/World/Cone")
        cone_curves = utils.get_curves(prim=cone_prim)
        self.assertIsNotNone(cone_curves, "Second new prim should have animation curves")
        self.assertIn("visibility:x", cone_curves, "Second new prim should have visibility animation")
        self.assertEqual(len(cone_curves), 1, "Second new prim should have only visibility animation")

        # Verify animation values
        target_cone = {"visibility:x": {30: 0}}
        self._check_curves(cone_prim, target_cone)


    async def test_anim_curve_drives_target_without_default_value(self):
        # Curves drive supported targets that have no default value: one with no value at all, one with only time
        # samples. The vector's undriven components keep their time-sampled values.
        await self._context.new_stage_async()
        stage = self._context.get_stage()
        prim = stage.DefinePrim("/Target", "Xform")
        unset = prim.CreateAttribute("unset", Sdf.ValueTypeNames.Double)
        sampled = prim.CreateAttribute("sampled", Sdf.ValueTypeNames.Double3)
        unset.Set(2.0)
        sampled.Set(Gf.Vec3d(3, 20, 30))
        for path, value in (("/Target.unset", 11.0), ("/Target.sampled|x", 13.0)):
            (result, err) = omni.kit.commands.execute(
                "SetAnimCurveKeys", paths=[path], time=Usd.TimeCode(0), value=value
            )
            self.assertTrue(result)
            self.assertTrue(err)

        for layer in (stage.GetRootLayer(), stage.GetSessionLayer()):
            with Usd.EditContext(stage, layer):
                unset.Clear()
                sampled.Clear()
        sampled.Set(Gf.Vec3d(3, 20, 30), Usd.TimeCode(0))
        sampled.Set(Gf.Vec3d(4, 20, 30), Usd.TimeCode(24))

        get_timeline_interface().set_current_time(12 / 24)
        await ui_test.human_delay()

        self.assertEqual(unset.Get(), 11.0)
        self.assertTrue(Gf.IsClose(sampled.Get(Usd.TimeCode(12)), Gf.Vec3d(13, 20, 30), 1e-6))

    async def test_anim_curve_drives_target_when_enabled_after_stage_open(self):
        # Enabling the extension while a stage is open: its curves still drive their targets.
        await self._context.new_stage_async()
        stage = self._context.get_stage()
        attr = stage.DefinePrim("/Target", "Xform").CreateAttribute("value", Sdf.ValueTypeNames.Double)
        attr.Set(1.0)

        # Re-enabling loads fresh copies of the extension's Python modules. This module keeps using the copies it
        # imported, so point those at the fresh state afterwards for the following tests.
        scripts = {name: module for name, module in sys.modules.items() if name.startswith("omni.anim.curve.core.scripts")}
        manager = omni.kit.app.get_app().get_extension_manager()
        try:
            self.assertTrue(manager.set_extension_enabled_immediate("omni.anim.curve.core", False))
            self.assertTrue(manager.set_extension_enabled_immediate("omni.anim.curve.core", True))
            await ui_test.human_delay()

            (result, err) = omni.kit.commands.execute(
                "SetAnimCurveKeys", paths=["/Target.value"], time=Usd.TimeCode(0), value=9.0
            )
            self.assertTrue(result)
            self.assertTrue(err)
            get_timeline_interface().set_current_time(12 / 24)
            await ui_test.human_delay()

            self.assertAlmostEqual(attr.Get(), 9.0)
        finally:
            for name, module in scripts.items():
                fresh = sys.modules.get(name)
                if fresh is None or fresh is module:
                    continue
                for key, value in list(globals().items()):
                    if not key.startswith("__") and getattr(module, key, None) is value and hasattr(fresh, key):
                        globals()[key] = getattr(fresh, key)
                module.__dict__.update({k: v for k, v in vars(fresh).items() if not k.startswith("__")})

class AnimCurveTestsInvalidParam(AnimationVisualTestBase, AnimCurveTestUtility):
    fail_on_log_error = False

    """
        Setup will set the
            1. self._GOLDEN_IMG_DIR
            2. self_MAP_DIR
            They will be served as the root folder of the golden image and USD map
    """

    async def setUp(self):
        await super().setUp()
        module_root = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
        self._GOLDEN_IMG_DIR = module_root.joinpath("data/golden_img")
        self._MAP_DIR = module_root.joinpath("data/test_map")

    """
    Add/RemoveAnimCurves test case 5: `paths` is invalid
    """

    async def test_anim_curve_add_remove_invalid(self):
        # Setup the log checker
        await omni.kit.app.get_app().next_update_async()  # Make sure log buffer pumped
        log_error_checker = LogErrorChecker()

        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()

        self.assertTrue(log_error_checker._error_count == 0)

        # Invalid path
        (result, err) = omni.kit.commands.execute("RemoveAnimCurves", paths=0)
        self.assertTrue(result)
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 1)

        (result, err) = omni.kit.commands.execute("AddAnimCurves", paths=0)
        self.assertTrue(result)
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 2)

        # A combination of valid and invalid path
        (result, err) = omni.kit.commands.execute("RemoveAnimCurves", paths=["World/Cube", 0])
        self.assertTrue(result)
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 3)

        (result, err) = omni.kit.commands.execute("AddAnimCurves", paths=["World/Cube", 0])
        self.assertTrue(result)
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 4)

        # shutdown the checker
        await omni.kit.app.get_app().next_update_async()
        log_error_checker.shutdown()

    """
    SetAnimCurveKeys test case 5: `paths` is invalid
    """

    async def test_anim_curve_set_key_invalid(self):
        # Setup the log checker
        await omni.kit.app.get_app().next_update_async()  # Make sure log buffer pumped
        log_error_checker = LogErrorChecker()

        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()

        self.assertTrue(log_error_checker._error_count == 0)

        # Invalid path
        (result, err) = omni.kit.commands.execute("SetAnimCurveKeys", paths=0)
        self.assertTrue(result)
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 1)

        (result, err) = omni.kit.commands.execute("SetAnimCurveKeys", paths=["World/Cube:xformOp:rotateXYZ|x"])
        # It passes our basic sanity checks, but USD backend will raise an error
        self.assertFalse(result)  # Ill-formed SdfPath <World/Cube:xformOp:rotateXYZ>: syntax error
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 2)

        # A combination of valid and invalid path
        (result, err) = omni.kit.commands.execute("SetAnimCurveKeys", paths=["/World/Cube", 0])
        self.assertTrue(result)
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 3)

        # invalid time
        (result, err) = omni.kit.commands.execute("SetAnimCurveKeys", paths=["/World/Cube"], time="invalid time")
        self.assertTrue(result)
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 4)

        # time and value len not match
        (result, err) = omni.kit.commands.execute(
            "SetAnimCurveKeys", paths=["/World/Cube"], time=[0, 1], value=2.0, preserveCurveShape=False
        )
        self.assertTrue(result)
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 5)

        # invalid tangentBreakDown
        (result, err) = omni.kit.commands.execute("SetAnimCurveKeys", paths=["/World/Cube"], tangentBreakDown="invalid")
        self.assertTrue(result)
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 6)

        # invalid in tangent
        (result, err) = omni.kit.commands.execute("SetAnimCurveKeys", paths=["/World/Cube"], inTangentType="invalid")
        self.assertTrue(result)
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 7)

        # invalid out tangent
        (result, err) = omni.kit.commands.execute("SetAnimCurveKeys", paths=["/World/Cube"], outTangentType="invalid")
        self.assertTrue(result)
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 8)

        # prim path, but value is not None!
        (result, err) = omni.kit.commands.execute("SetAnimCurveKeys", paths=["/World/Cube"], value=2.0)
        self.assertTrue(result)
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 9)

        # preserve curve shape while time is not length 1
        (result, err) = omni.kit.commands.execute(
            "SetAnimCurveKeys", paths=["/World/Cube"], time=[0, 1], preserveCurveShape=True
        )
        self.assertTrue(result)
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 10)

        # invalid path
        (result, err) = omni.kit.commands.execute(
            "SetAnimCurveKeys", paths=["/World/Cube:xformOp:rotateXYZ"], value=Gf.Vec3d()
        )
        self.assertTrue(result)
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 11)

        # invalid component path
        (result, err) = omni.kit.commands.execute(
            "SetAnimCurveKeys", paths=["/World/Cube.xformOp:rotateXYZ|w"], value=2.0
        )
        self.assertTrue(result)
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 12)

        # invalid value for rotateXYZ
        (result, err) = omni.kit.commands.execute(
            "SetAnimCurveKeys", paths=["/World/Cube.xformOp:rotateXYZ"], value=Gf.Vec4d()
        )
        self.assertTrue(result)
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 13)

        # invalid value for component path
        (result, err) = omni.kit.commands.execute(
            "SetAnimCurveKeys", paths=["/World/Cube.xformOp:rotateXYZ|x"], value=Gf.Vec4d()
        )

        self.assertTrue(result)
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 14)

        # shutdown the checker
        await omni.kit.app.get_app().next_update_async()
        log_error_checker.shutdown()

    """
    RemoveAnimCurveKeys test case 5: `paths` and other parameters are invalid
    """

    async def test_anim_curve_remove_key_invalid(self):
        # Setup the log checker
        await omni.kit.app.get_app().next_update_async()  # Make sure log buffer pumped
        log_error_checker = LogErrorChecker()

        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()
        stage = omni.usd.get_context().get_stage()

        self.assertTrue(log_error_checker._error_count == 0)

        # Invalid stage
        (result, err) = omni.kit.commands.execute(
            "RemoveAnimCurveKeys", paths=["World/Cube:xformOp:rotateXYZ|x"], stage=1.2
        )
        self.assertTrue(result)  # will not pass sanity check of the CommandBase
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 1)

        # Invalid path
        (result, err) = omni.kit.commands.execute("RemoveAnimCurveKeys", paths=0, stage=stage)
        self.assertTrue(result)
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 2)

        (result, err) = omni.kit.commands.execute(
            "RemoveAnimCurveKeys", paths=["World/Cube:xformOp:rotateXYZ|x"], stage=stage
        )
        self.assertFalse(result)  # It passes our basic sanity checks, but USD backend will raise an error
        self.assertFalse(err)  # Ill-formed SdfPath <World/Cube:xformOp:rotateXYZ>: syntax error. Shall we check it?
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 3)

        # A combination of valid and invalid path
        (result, err) = omni.kit.commands.execute("RemoveAnimCurveKeys", paths=["World/Cube", 0], stage=stage)
        self.assertTrue(result)
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 4)

        # shutdown the checker
        await omni.kit.app.get_app().next_update_async()
        log_error_checker.shutdown()

    """
    PasteAnimCurveKeys test case 4: `paths` is invalid
    """

    async def test_anim_curve_paste_invalid(self):
        # Setup the log checker
        await omni.kit.app.get_app().next_update_async()  # Make sure log buffer pumped
        log_error_checker = LogErrorChecker()

        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()
        stage = omni.usd.get_context().get_stage()
        # Set the clipboard
        set_curvekey_clipboard(stage, ["/World/Sphere"], Usd.TimeCode(20))

        self.assertTrue(log_error_checker._error_count == 0)

        # invalid path
        paths = 3.1415926
        (result, err) = omni.kit.commands.execute("PasteAnimCurveKeys", paths=paths, stage=stage)
        self.assertTrue(result)
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 1)

        # shutdown the checker
        await omni.kit.app.get_app().next_update_async()
        log_error_checker.shutdown()

    """
    PasteAnimCurveKeys test case 5: `paths` contains mixed paths of prims and curves
    """

    async def test_anim_curve_paste_mixed(self):
        # Setup the log checker
        await omni.kit.app.get_app().next_update_async()  # Make sure log buffer pumped
        log_error_checker = LogErrorChecker()

        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()

        stage = omni.usd.get_context().get_stage()
        # Set the clipboard
        set_curvekey_clipboard(stage, ["/World/Sphere"], Usd.TimeCode(20))

        self.assertTrue(log_error_checker._error_count == 0)

        # prim path and curves path both exist in target list
        # an error will be raised. Nothing will be changed.
        paths = ["/World/Cube.xformOp:translate|x", "/World/Cube", "/World/Cube.xformOp:translate|y"]
        (result, err) = omni.kit.commands.execute("PasteAnimCurveKeys", paths=paths, stage=stage, time=Usd.TimeCode(45))
        self.assertTrue(result)
        self.assertFalse(err)
        await wait_stage_loading()
        self.assertTrue(log_error_checker._error_count == 1)
        target = {
            "size:x": {20: 130},
        }
        prim = stage.GetPrimAtPath("/World/Cube")
        self._check_curves(prim, target)

        # shutdown the checker
        await omni.kit.app.get_app().next_update_async()
        log_error_checker.shutdown()


class AnimCurveCommandBaseTest(AnimationVisualTestBase, AnimCurveTestUtility):
    fail_on_log_error = False
    PARSE_PATH_RTN_NAMES = ("prim_path", "attr_token", "comp_length", "comp_idx", "is_prim_path", "is_comp_path")

    """
        Setup will set the
            1. self._GOLDEN_IMG_DIR
            2. self_MAP_DIR
            They will be served as the root folder of the golden image and USD map
    """

    async def setUp(self):
        await super().setUp()
        module_root = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
        self._GOLDEN_IMG_DIR = module_root.joinpath("data/golden_img")
        self._MAP_DIR = module_root.joinpath("data/test_map")
        # Register the test utility
        omni.kit.commands.register(AnimCurveCommandBaseTestUtility)

    """
    For comparing the return values when test_stage='parse_path'
    The return values should be list of tuples
    """

    def _comp_parse_paths_rtns(self, rtns, target_rtns):
        self.assertEqual(len(rtns), len(target_rtns))
        for rtn, target_rtn in zip(rtns, target_rtns):
            self.assertEqual(len(rtn), len(target_rtn))
            for r, t, n in zip(rtn, target_rtn, self.PARSE_PATH_RTN_NAMES):
                self.assertEqual(r, t, n)

    async def test_anim_curve_base_class(self):
        # Setup the log checker
        await omni.kit.app.get_app().next_update_async()  # Make sure log buffer pumped
        log_error_checker = LogErrorChecker()

        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()

        target_error_count = 0
        self.assertEqual(log_error_checker._error_count, target_error_count)

        """
        Typing
        """
        # __init__: invalid type
        (result, rtn) = omni.kit.commands.execute("AnimCurveCommandBaseTestUtility", _name=3.1415926)
        self.assertTrue(result)
        self.assertFalse(rtn)
        await wait_stage_loading()
        target_error_count += 1
        self.assertEqual(log_error_checker._error_count, target_error_count)

        # __init__: invalid type
        (result, rtn) = omni.kit.commands.execute("AnimCurveCommandBaseTestUtility", stage=3.1415926)
        self.assertTrue(result)
        self.assertFalse(rtn)
        await wait_stage_loading()
        target_error_count += 1
        self.assertEqual(log_error_checker._error_count, target_error_count)

        # __init__: invalid type
        (result, rtn) = omni.kit.commands.execute("AnimCurveCommandBaseTestUtility", paths=3.1415926)
        self.assertTrue(result)
        self.assertFalse(rtn)
        await wait_stage_loading()
        target_error_count += 1
        self.assertEqual(log_error_checker._error_count, target_error_count)

        # __init__: a mixture of valid and invalid type - should raise an error on the first invalid param
        (result, rtn) = omni.kit.commands.execute("AnimCurveCommandBaseTestUtility", stage=None, paths=3.1415926)
        self.assertTrue(result)
        self.assertFalse(rtn)
        await wait_stage_loading()
        target_error_count += 1
        self.assertEqual(log_error_checker._error_count, target_error_count)

        """
        Path - Empty
        """
        # __init__: paths is an empty list
        (result, rtn) = omni.kit.commands.execute("AnimCurveCommandBaseTestUtility", paths=[])
        self.assertTrue(result)
        self.assertFalse(rtn)
        await wait_stage_loading()
        target_error_count += 1
        self.assertEqual(log_error_checker._error_count, target_error_count)

        # do not select a prim and paths == None -> error: paths is empty
        (result, rtn) = omni.kit.commands.execute("AnimCurveCommandBaseTestUtility")
        self.assertTrue(result)
        self.assertFalse(rtn)
        await wait_stage_loading()
        target_error_count += 1
        self.assertEqual(log_error_checker._error_count, target_error_count)

        # select a prim and paths == None -> no error
        omni.usd.get_context().get_selection().set_selected_prim_paths(["/World/Cube"], False)
        await wait_stage_loading()
        (result, rtn) = omni.kit.commands.execute("AnimCurveCommandBaseTestUtility")
        self.assertTrue(result)
        self.assertTrue(rtn)

        """
        Path - Prim
        """

        # __init__: paths to a valid prim
        (result, rtn) = omni.kit.commands.execute(
            "AnimCurveCommandBaseTestUtility", paths=["/World/Cube"], test_stage="parse_path"
        )
        self.assertTrue(result)
        self._comp_parse_paths_rtns(rtn, [(Sdf.Path("/World/Cube"), None, 0, 0, True, False)])
        await wait_stage_loading()
        self.assertEqual(log_error_checker._error_count, target_error_count)

        # __init__: paths to a non-existing prim, but the path format is valid
        # We only provide a basic sanity check here. USD runtime will do the detailed jobs.
        (result, rtn) = omni.kit.commands.execute(
            "AnimCurveCommandBaseTestUtility", paths=["/World/XXube"], test_stage="parse_path"
        )
        self.assertTrue(result)
        self._comp_parse_paths_rtns(rtn, [(Sdf.Path("/World/XXube"), None, 0, 0, True, False)])
        await wait_stage_loading()
        self.assertEqual(log_error_checker._error_count, target_error_count)

        """
        Path - Attribute / Component
        """

        # __init__: paths to an invalid attribute, but the path format is valid
        (result, rtn) = omni.kit.commands.execute(
            "AnimCurveCommandBaseTestUtility", paths=["/World/XXube.some_invalid"], test_stage="parse_path"
        )
        self.assertTrue(result)
        self.assertFalse(rtn)
        await wait_stage_loading()
        target_error_count += 1
        self.assertEqual(log_error_checker._error_count, target_error_count)

        # __init__: paths to an invalid attribute, but the path format is valid
        (result, rtn) = omni.kit.commands.execute(
            "AnimCurveCommandBaseTestUtility", paths=["/World/Cube.some_invalid"], test_stage="parse_path"
        )
        self.assertTrue(result)
        self.assertFalse(rtn)
        await wait_stage_loading()
        target_error_count += 1
        self.assertEqual(log_error_checker._error_count, target_error_count)

        # __init__: paths to an invalid attribute
        (result, rtn) = omni.kit.commands.execute(
            "AnimCurveCommandBaseTestUtility", paths=["/World/Cube.size|q"], test_stage="parse_path"
        )
        self.assertTrue(result)
        self.assertFalse(rtn)
        await wait_stage_loading()
        target_error_count += 1
        self.assertEqual(log_error_checker._error_count, target_error_count)

        # __init__: paths to an invalid attribute
        (result, rtn) = omni.kit.commands.execute(
            "AnimCurveCommandBaseTestUtility", paths=["/World/Cube.xformOp"], test_stage="parse_path"
        )
        self.assertTrue(result)
        self.assertFalse(rtn)
        await wait_stage_loading()
        target_error_count += 1
        self.assertEqual(log_error_checker._error_count, target_error_count)

        # __init__: paths to a valid component
        (result, rtn) = omni.kit.commands.execute(
            "AnimCurveCommandBaseTestUtility", paths=["/World/Cube.size|x"], test_stage="parse_path"
        )
        self.assertTrue(result)
        self._comp_parse_paths_rtns(rtn, [(Sdf.Path("/World/Cube"), "size", 1, 0, False, True)])
        await wait_stage_loading()
        self.assertEqual(log_error_checker._error_count, target_error_count)

        """
        Paths - Combination
        """
        paths = [
            "/World/Cube.size",
            "/World/Cube.size|x",
            "/World/Cube.xformOp:translate",
            "/World/Cube.xformOp:translate|x",
            "/World/Cube.xformOp:translate|y",
        ]
        target_rtn = [
            (Sdf.Path("/World/Cube"), "size", 1, 0, False, False),
            (Sdf.Path("/World/Cube"), "size", 1, 0, False, True),
            (Sdf.Path("/World/Cube"), "xformOp:translate", 3, 0, False, False),
            (Sdf.Path("/World/Cube"), "xformOp:translate", 3, 0, False, True),
            (Sdf.Path("/World/Cube"), "xformOp:translate", 3, 1, False, True),
        ]
        (result, rtn) = omni.kit.commands.execute(
            "AnimCurveCommandBaseTestUtility", paths=paths, test_stage="parse_path"
        )
        self.assertTrue(result)
        self._comp_parse_paths_rtns(rtn, target_rtn)
        await wait_stage_loading()
        self.assertEqual(log_error_checker._error_count, target_error_count)

        """
        The default _do method
        """

        # call the default _do method, will raise NotImplementedError
        (result, rtn) = omni.kit.commands.execute(
            "AnimCurveCommandBaseTestUtility", paths=["/World/Cube"], test_stage="base_do"
        )
        self.assertTrue(result)
        self.assertFalse(rtn)
        await wait_stage_loading()
        target_error_count += 1
        self.assertEqual(log_error_checker._error_count, target_error_count)

        # shutdown the checker
        await omni.kit.app.get_app().next_update_async()
        log_error_checker.shutdown()


class AnimCurveExtractTests(AnimationVisualTestBase, AnimCurveTestUtility):
    """
    Setup will set the
        1. self._GOLDEN_IMG_DIR
        2. self_MAP_DIR
        They will be served as the root folder of the golden image and USD map
    """

    async def setUp(self):
        await super().setUp()
        module_root = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
        self._GOLDEN_IMG_DIR = module_root.joinpath("data/golden_img")
        self._MAP_DIR = module_root.joinpath("data/test_map")

    def _unpack(self, attr, values, packed_values):
        components = [":x", ":y", ":z"]
        for i in range(0, 3):
            component = attr + components[i]
            values[component] = {}
        for key in packed_values[attr]:
            for i in range(0, 3):
                component = attr + components[i]
                values[component][key] = packed_values[attr][key][i]

    def _check_curve_times(self, prim, target: dict, places=None):
        for curve_name, target_keys in target.items():
            rtn = _get_keys(prim, curve_name)
            self.assertIsNotNone(rtn, msg="Curve %s." % curve_name)
            key_times, key_values = rtn
            self.assertEqual(len(key_times), len(target_keys), msg="len(key_times) of %s" % curve_name)

            for time, t_time in zip(key_times, target_keys):
                # t_time is Usd.TimeCode, so we will convert it to the new format
                t_time = utils.time_code_to_key_time(prim, t_time)
                if places is None:
                    self.assertAlmostEqual(time, t_time, msg="key_time of %s" % curve_name)
                else:
                    self.assertAlmostEqual(time, t_time, msg="key_time of %s" % curve_name, places=places)

    async def _load(self):
        await self.load_stage(map_name="timesample_cube_simple.usda")
        await wait_stage_loading()

        # make sure timeline position does not affect curve conversion
        await self.advance_n_frames(30)

        await wait_stage_loading()

        self.stage = omni.usd.get_context().get_stage()
        self.prim = self.stage.GetPrimAtPath("/World/Cube")

        # check if there are no existing curves
        curve_names = utils.get_curves(prim=self.prim)
        self.assertIsNone(curve_names)

    """
    ExtractAnimCurves test
    """

    async def _extraction_test(
        self,
        source_fps,
        target_fps,
        target_key_count,
        time_offset=0,
        target_times=None,
        target_values=None,
        sparse=False,
    ):
        await self._load()

        # set the desired FPS in the timeline
        fps_old = omni.timeline.get_timeline_interface().get_time_codes_per_seconds()
        omni.timeline.get_timeline_interface().set_time_codes_per_second(target_fps)
        await omni.kit.app.get_app().next_update_async()

        # Set
        (result, err) = omni.kit.commands.execute(
            "ExtractAnimCurves",
            paths=["/World/Cube"],
            sparse=sparse,
            recursive=False,
            attribute_mask=None,
            source_frame_rate=source_fps,
            start_time=time_offset,
            max_error_percent=0.1,
        )
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # AddAnimCurves command no error
        await wait_stage_loading()

        # Test if curves of length 20 are created
        self._check_default_curve_name(self.prim)
        if target_key_count is not None:
            self._check_default_curve_length(self.prim, target_key_count)

        if target_times is not None:
            target_times_dict = {
                "visibility:x": target_times,
                "xformOp:rotateXYZ:x": target_times,
                "xformOp:rotateXYZ:y": target_times,
                "xformOp:rotateXYZ:z": target_times,
                "xformOp:scale:x": target_times,
                "xformOp:scale:y": target_times,
                "xformOp:scale:z": target_times,
                "xformOp:translate:x": target_times,
                "xformOp:translate:y": target_times,
                "xformOp:translate:z": target_times,
            }
            # Check the contents
            self._check_curve_times(self.prim, target_times_dict)

        if target_values is not None:
            # Check the contents
            self._check_curves(self.prim, target_values, 5)

        omni.timeline.get_timeline_interface().set_time_codes_per_second(fps_old)
        await omni.kit.app.get_app().next_update_async()

    async def test_anim_curve_extract_dense_values(self):
        target_packed = {
            "visibility": {10: 0, 11: 0, 12: 1, 13: 0, 14: 1, 15: 1, 16: 1, 17: 0, 18: 0, 19: 0, 20: 0},
            "xformOp:rotateXYZ": {
                10: (7.136664, -8.296526, -0.2170769),
                11: (7.8595524, -9.123268, -0.2965203),
                12: (8.585358, -9.948952, -0.38673946),
                13: (9.314399, -10.773438, -0.4878357),
                14: (10.047, -11.59659, -0.59992045),
                15: (10.783488, -12.418264, -0.7231152),
                16: (11.524196, -13.2383175, -0.85755193),
                17: (12.269461, -14.056602, -1.0033729),
                18: (13.019626, -14.872967, -1.160731),
                19: (13.775039, -15.687261, -1.3297898),
                20: (14.536054, -16.499325, -1.5107238),
            },
            "xformOp:scale": {
                10: (1, 1, 1.1),
                11: (1.05, 1, 1),
                12: (1.07, 1, 1),
                13: (1.15, 1, 1),
                14: (1.3, 1, 1),
                15: (1.2, 1, 1),
                16: (1.25, 1, 1),
                17: (1.23, 1, 1),
                18: (1.22, 1, 1),
                19: (1.21, 1, 1),
                20: (1.2, 1, 1.2),
            },
            "xformOp:translate": {
                10: (1.4002360272614458, 1.3519514162350323, 0.700358582723578),
                11: (1.549011877570895, 1.4955969999876604, 0.7747720684771235),
                12: (1.698644591280108, 1.6400698997529297, 0.8496141331449113),
                13: (1.848950554803422, 1.7851928335281322, 0.9247929383881754),
                14: (1.999746154555172, 1.9307885193105578, 1.000216645868149),
                15: (2.1508477769496945, 2.0766796750974987, 1.0757934172460661),
                16: (2.3020718084013274, 2.2226890188862454, 1.151431414183161),
                17: (2.4532346353244048, 2.3686392686740887, 1.2270387983406668),
                18: (2.604152644133264, 2.5143531424583205, 1.302523731379818),
                19: (2.7546422212422415, 2.659653358236232, 1.377794374961848),
                20: (2.9045197530656726, 2.8043626340051127, 1.4527588907479905),
            },
        }

        target = {}
        target["visibility:x"] = target_packed["visibility"]
        self._unpack("xformOp:rotateXYZ", target, target_packed)
        self._unpack("xformOp:scale", target, target_packed)
        self._unpack("xformOp:translate", target, target_packed)

        await self._extraction_test(30, 30, 11, 0, None, target)

    async def test_anim_curve_extract_dense_times(self):
        target_times = list(range(20, 40))
        await self._extraction_test(30, 60, 20, 0, target_times)

        target_times = list(range(5, 11))
        await self._extraction_test(60, 30, 6, 0, target_times)

        target_times = list(range(0, 11))
        start_time = -10.0 / 30
        await self._extraction_test(30, 30, 11, start_time, target_times)

    async def test_anim_curve_extract_sparse_values(self):
        target = {
            "visibility:x": {
                10.0: 0.0,
                12.0: 1.0,
                13.0: 0.0,
                14.0: 1.0,
                17.0: 0.0,
                20.0: 0.0,
            },
            "xformOp:rotateXYZ:x": {
                10.0: 7.136663913726807,
                16.0: 11.524195671081543,
                20.0: 14.536053657531738,
            },
            "xformOp:rotateXYZ:y": {
                10.0: -8.296525955200195,
                19.0: -15.687260627746582,
                20.0: -16.499324798583984,
            },
            "xformOp:rotateXYZ:z": {
                10.0: -0.21707689762115479,
                11.0: -0.29652029275894165,
                12.0: -0.38673946261405945,
                13.0: -0.48783570528030396,
                14.0: -0.5999204516410828,
                15.0: -0.7231152057647705,
                16.0: -0.8575519323348999,
                17.0: -1.0033729076385498,
                18.0: -1.1607309579849243,
                19.0: -1.3297897577285767,
                20.0: -1.5107238292694092,
            },
            "xformOp:scale:x": {
                10.0: 1.0,
                11.0: 1.0499999523162842,
                12.0: 1.0700000524520874,
                13.0: 1.149999976158142,
                14.0: 1.2999999523162842,
                15.0: 1.2000000476837158,
                16.0: 1.25,
                17.0: 1.2300000190734863,
                18.0: 1.2200000286102295,
                20.0: 1.2000000476837158,
            },
            "xformOp:scale:y": {
                10.0: 1.0,
                20.0: 1.0,
            },
            "xformOp:scale:z": {
                10.0: 1.100000023841858,
                11.0: 1.0,
                12.0: 1.0,
                18.0: 1.0,
                19.0: 1.0,
                20.0: 1.2000000476837158,
            },
            "xformOp:translate:x": {
                10.0: 1.4002360272614458,
                18.0: 2.604152644133264,
                20.0: 2.9045197530656726,
            },
            "xformOp:translate:y": {
                10.0: 1.3519514162350323,
                18.0: 2.5143531424583205,
                20.0: 2.8043626340051127,
            },
            "xformOp:translate:z": {
                10.0: 0.700358582723578,
                18.0: 1.302523731379818,
                20.0: 1.4527588907479905,
            },
        }
        await self._extraction_test(30, 30, None, 0, None, target, True)


class AnimCurveMatricesExtractTests(AnimationVisualTestBase, AnimCurveTestUtility):
    async def setUp(self):
        await super().setUp()
        module_root = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
        self._GOLDEN_IMG_DIR = module_root.joinpath("data/golden_img")
        self._MAP_DIR = module_root.joinpath("data/test_map")

        self._prim_path = "/World/Cube"
        self._end_time = 100
        # move along x axis
        self._end_position = Gf.Vec3d(1000, 0, 0)
        # rotate around x axis
        self._rotation_axis = Gf.Vec3d(1, 0, 0)
        self._end_rotation_angle = 100

    async def test_anim_curve_extract_matrices(self):
        await self._init_timesample_transform_animation_stage()

        result = omni.kit.commands.execute(
            "ExtractAnimCurves",
            paths=[self._prim_path],
            sparse=True,
            attribute_mask=None,
            start_time=0,
            compute_tangents=False,
            max_error_percent=1.0,
        )
        self.assertTrue(result)
        self._validate_curves()

    async def test_anim_curve_extract_matrices_compute_tangents(self):
        await self._init_timesample_transform_animation_stage()

        result = omni.kit.commands.execute(
            "ExtractAnimCurves",
            paths=[self._prim_path],
            sparse=True,
            attribute_mask=None,
            start_time=0,
            compute_tangents=True,
            max_error_percent=1.0,
        )
        self.assertTrue(result)
        self._validate_curves()

    async def _init_timesample_transform_animation_stage(self):
        await self._context.new_stage_async()
        stage = self._context.get_stage()
        cube = UsdGeom.Cube.Define(stage, self._prim_path)
        cube.CreateSizeAttr(100.0)
        transform = cube.AddTransformOp()

        # linear interpolation from origin to the end position/rotation
        matrix = Gf.Matrix4d(1)
        for t in range(0, self._end_time + 1):
            matrix.SetTranslate(self._end_position * t / self._end_time)
            rotation_angle = self._end_rotation_angle * t / self._end_time
            rotation = Gf.Rotation(self._rotation_axis, rotation_angle)
            matrix.SetRotateOnly(rotation)
            transform.Set(value=matrix, time=t)

    def _validate_curves(self):
        curves = utils.get_curve_plugin().get_curves(self._prim_path)

        # verify x movement
        translate_x = curves.get("xformOp:translate:x").keys
        self.assertTrue(len(translate_x) >= 2, "need at least two keys to animate")
        self.assertTrue(translate_x[0].time == 0, "should start without offset")
        self.assertTrue(translate_x[0].value == 0, "should start from origin")
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath(self._prim_path)
        end_time = utils.time_code_to_key_time(prim, self._end_time)
        self.assertTrue(translate_x[-1].time == end_time, "end time mismatch")
        self.assertAlmostEqual(translate_x[-1].value, self._end_position[0])

        # verify x rotation
        rotate_x = curves.get("xformOp:rotateXYZ:x").keys
        self.assertTrue(len(rotate_x) >= 2, "need at least two keys to animate")
        self.assertTrue(rotate_x[0].time == 0, "should start without offset")
        self.assertTrue(rotate_x[0].value == 0, "should start from origin")
        self.assertTrue(rotate_x[-1].time == end_time, "end time mismatch")
        self.assertAlmostEqual(rotate_x[-1].value, self._end_rotation_angle)

        # other curves should be flat
        curves.pop("xformOp:translate:x")
        curves.pop("xformOp:rotateXYZ:x")
        for curve in curves.values():
            self._validate_flat_curve(curve)

    def _validate_flat_curve(self, curve):
        if len(curve.keys) == 0:
            return

        first_value = curve.keys[0].value
        for key in curve.keys[1:]:
            self.assertAlmostEqual(first_value, key.value)


class AnimCurveFlatCurveSimplifyTests(AnimationVisualTestBase, AnimCurveTestUtility):
    async def setUp(self):
        await super().setUp()
        module_root = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
        self._GOLDEN_IMG_DIR = module_root.joinpath("data/golden_img")
        self._MAP_DIR = module_root.joinpath("data/test_map")

        self._prim_path = "/World/Cube"
        self._attribute = "xformOp:scale|x"
        self._end_time = 50

    async def test_anim_curve_simplify_flat_curve(self):
        await self._init_flat_curve_stage()

        result = omni.kit.commands.execute(
            "SimplifyAnimCurves",
            paths=[self._prim_path],
            attribute_mask=None,
            compute_tangents=True,
            max_error_percent=1.0,
        )
        self.assertTrue(result)
        self._validate_curves()

    async def _init_flat_curve_stage(self):
        await self._context.new_stage_async()
        stage = self._context.get_stage()
        cube = UsdGeom.Cube.Define(stage, self._prim_path)
        cube.CreateSizeAttr(100.0)
        cube.AddScaleOp()

        # set up a dense flat curve
        paths = [self._prim_path + "." + self._attribute]
        for t in range(0, self._end_time + 1):
            result = omni.kit.commands.execute("SetAnimCurveKeys", paths=paths, time=Usd.TimeCode(t))
            self.assertTrue(result)

    def _validate_curves(self):
        curves = utils.get_curve_plugin().get_curves(self._prim_path)
        self.assertEqual(len(curves), 1, "should not have extra curves")

        curve_name = self._attribute.replace("|", ":")
        flat_curve = curves.get(curve_name)
        self.assertIsNotNone(flat_curve)
        keys = flat_curve.keys
        self.assertTrue(len(keys) == 2, "flat curve only need two ends")
        self.assertTrue(keys[0].time == 0, "should start without offset")
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath(self._prim_path)
        end_time = utils.time_code_to_key_time(prim, self._end_time)
        self.assertTrue(keys[-1].time == end_time, "end time mismatch")
        self.assertTrue(keys[0].value == keys[-1].value)


class AnimCurveMapLoadPerfTests(AnimationVisualTestBase):
    """
    Setup will set the
        1. self._GOLDEN_IMG_DIR
        2. self_MAP_DIR
        They will be served as the root folder of the golden image and USD map
    """

    async def setUp(self):
        await super().setUp()
        module_root = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
        self._GOLDEN_IMG_DIR = module_root.joinpath("data/golden_img")
        self._MAP_DIR = module_root.joinpath("data/test_map")

    async def test_anim_curve_map_load_performance_60k(self):
        viewport_api = get_active_viewport()
        if hasattr(viewport_api, "legacy_window"):
            # the old viewport, VP1
            return
        # Else: the new viewport, VP2

        tic = time.time()
        await self.load_stage(map_name="perf_60k_prims.usd")
        await wait_stage_loading()
        toc = time.time()

        # print('perf_60k_prims:', toc-tic, 'seconds used.')
        # On my desktop with AMD-5800 CPU and RTX 3080 Ti, it takes ~3 sec
        # On TC, it runs much slower, with the old viewport, so we disable this test on the old viewport.
        # Linux x86_64 CI runners (23 runs, 12-13 Oct 2026): 18.3 to 21.2 s, median 18.6 s; 5 of the 23 were over the old
        # 20 s limit (20.02, 20.07, 20.10, 20.91, 21.22 s). 30 s fails a load about 60 % slower than the median.
        # Windows and Linux aarch64 CI runners measured 36 to 45 s (11-13 Oct 2026): 90 s, twice the slowest reading,
        # keeps a real margin there and still fails a load that doubles.
        limit = 30 if (sys.platform.startswith("linux") and platform.machine() == "x86_64") else 90
        self.assertLessEqual(toc - tic, limit, f"perf_60k_prims: failed to load the stage within {limit} s!")


class AnimCurveDuplicationTests(AnimationVisualTestBase, AnimCurveTestUtility):
    """
    Setup will set the
        1. self._GOLDEN_IMG_DIR
        2. self_MAP_DIR
        They will be served as the root folder of the golden image and USD map
    """

    async def setUp(self):
        await super().setUp()
        module_root = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
        self._GOLDEN_IMG_DIR = module_root.joinpath("data/golden_img")
        self._MAP_DIR = module_root.joinpath("data/test_map")

    """
    This test will check if the Duplicate option in a prim's right-click menu correctly dup the curves
    """

    async def test_anim_curve_duplication_basic(self):
        await self.load_stage(map_name="basic_curve_cube.usda")
        await wait_stage_loading()
        stage = omni.usd.get_context().get_stage()

        omni.kit.commands.execute(
            "CopyPrim",
            path_from="/World/Cube",
            path_to="/World/Cube_01",
            exclusive_select=False,
            copy_to_introducing_layer=False,
        )

        prim = stage.GetPrimAtPath("/World/Cube")
        target = {
            "xformOp:translate:x": {0: 0, 30: 166.345},
            "xformOp:translate:y": {0: 0, 30: 70.8288},
            "xformOp:translate:z": {0: 0, 30: 250.701},
            "xformOp:rotateXYZ:x": {0: 0, 30: 0},
            "xformOp:rotateXYZ:y": {0: 0, 30: 0},
            "xformOp:rotateXYZ:z": {0: 0, 30: 0},
            "xformOp:scale:x": {0: 0.5, 30: 0.5},
            "xformOp:scale:y": {0: 0.5, 30: 0.5},
            "xformOp:scale:z": {0: 0.5, 30: 0.5},
        }
        self._check_curves(prim, target)

        prim = stage.GetPrimAtPath("/World/Cube_01")
        target = {
            "xformOp:translate:x": {0: 0, 30: 166.345},
            "xformOp:translate:y": {0: 0, 30: 70.8288},
            "xformOp:translate:z": {0: 0, 30: 250.701},
            "xformOp:rotateXYZ:x": {0: 0, 30: 0},
            "xformOp:rotateXYZ:y": {0: 0, 30: 0},
            "xformOp:rotateXYZ:z": {0: 0, 30: 0},
            "xformOp:scale:x": {0: 0.5, 30: 0.5},
            "xformOp:scale:y": {0: 0.5, 30: 0.5},
            "xformOp:scale:z": {0: 0.5, 30: 0.5},
        }
        self._check_curves(prim, target)


class AnimCurveUndoRedoTest(AnimationVisualTestBase, AnimCurveTestUtility):
    """
    Setup will set the
        1. self._GOLDEN_IMG_DIR
        2. self_MAP_DIR
        They will be served as the root folder of the golden image and USD map
    """

    async def setUp(self):
        await super().setUp()
        module_root = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
        self._GOLDEN_IMG_DIR = module_root.joinpath("data/golden_img")
        self._MAP_DIR = module_root.joinpath("data/test_map")

    """
    RemoveAnimCurves: Undo / Redo test
    """

    async def test_anim_curve_remove_undo_redo(self):

        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()

        stage = omni.usd.get_context().get_stage()

        # Remove
        (result, err) = omni.kit.commands.execute("RemoveAnimCurves", paths=["/World/Cube"])
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # RemoveAnimCurve command no error

        # Test if all curves of /World/Cube are removed
        prim = stage.GetPrimAtPath("/World/Cube")
        curve_names = utils.get_curves(prim=prim)
        self.assertTrue(curve_names is None)

        # Undo
        (result, err) = omni.kit.commands.execute("Undo")
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # Undo command no error

        target = {
            "size:x": {20: 130},
        }
        self._check_curves(prim, target)

        # Redo
        (result, err) = omni.kit.commands.execute("Redo")
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # Redo command no error

        # Test if all curves of /World/Cube are removed
        curve_names = utils.get_curves(prim=prim)
        self.assertTrue(curve_names is None)

    """
    AddAnimCurves: Undo / Redo test
    """

    async def test_anim_curve_add_undo_redo(self):

        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()

        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath("/World/Cube")

        # Add
        (result, err) = omni.kit.commands.execute("AddAnimCurves", paths=["/World/Cube"])
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # AddAnimCurves command no error

        target = {
            "size:x": {20: 130},
            "visibility:x": {},
            "xformOp:rotateXYZ:x": {},
            "xformOp:rotateXYZ:y": {},
            "xformOp:rotateXYZ:z": {},
            "xformOp:translate:x": {},
            "xformOp:translate:y": {},
            "xformOp:translate:z": {},
            "xformOp:scale:x": {},
            "xformOp:scale:y": {},
            "xformOp:scale:z": {},
        }
        self._check_curves(prim, target)

        # Undo
        (result, err) = omni.kit.commands.execute("Undo")
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # Undo command no error

        target_undo = {
            "size:x": {20: 130},
        }
        self._check_curves(prim, target_undo)

        # Redo
        (result, err) = omni.kit.commands.execute("Redo")
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # Redo command no error

        self._check_curves(prim, target)

    """
    SetAnimCurveKeys: Undo / Redo test
    """

    async def test_anim_curve_set_key_undo_redo(self):

        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()
        await self.advance_n_frames(30)
        await wait_stage_loading()

        stage = omni.usd.get_context().get_stage()

        prim = stage.GetPrimAtPath("/World/Cube")

        # check if there are no existing curves
        curve_names = utils.get_curves(prim=prim)
        self.assertIsNotNone(curve_names)

        # Set
        (result, err) = omni.kit.commands.execute("SetAnimCurveKeys", paths=["/World/Cube"])
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # SetAnimCurveKeys command no error

        # Check the contents
        target = {
            "size:x": {20: 130, 30: 130},
            "visibility:x": {30: 0},
            "xformOp:rotateXYZ:x": {30: 0},
            "xformOp:rotateXYZ:y": {30: 0},
            "xformOp:rotateXYZ:z": {30: 0},
            "xformOp:scale:x": {30: 1},
            "xformOp:scale:y": {30: 1},
            "xformOp:scale:z": {30: 1},
            "xformOp:translate:x": {30: 0},
            "xformOp:translate:y": {30: 0},
            "xformOp:translate:z": {30: 0},
        }
        self._check_curves(prim, target)

        # Undo
        (result, err) = omni.kit.commands.execute("Undo")
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # Undo command no error

        target_undo = {
            "size:x": {20: 130},
        }
        self._check_curves(prim, target_undo)

        # Redo
        (result, err) = omni.kit.commands.execute("Redo")
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # Redo command no error

        self._check_curves(prim, target)

    """
    RemoveAnimCurveKeys: Undo / Redo test
    """

    async def test_anim_curve_remove_key_undo_redo(self):
        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()
        await self.advance_n_frames(20)
        await wait_stage_loading()

        stage = omni.usd.get_context().get_stage()

        prim = stage.GetPrimAtPath("/World/Cube")

        # Remove - prim's path
        (result, err) = omni.kit.commands.execute("RemoveAnimCurveKeys", paths=["/World/Cube"], stage=stage)
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # RemoveAnimCurveKeys command no error

        # Check the contents
        target = {
            "size:x": {},
        }
        self._check_curves(prim, target)

        # Undo
        (result, err) = omni.kit.commands.execute("Undo")
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # Undo command no error

        target_undo = {
            "size:x": {20: 130},
        }
        self._check_curves(prim, target_undo)

        # Redo
        (result, err) = omni.kit.commands.execute("Redo")
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # Redo command no error

        self._check_curves(prim, target)

    """
    PasteAnimCurveKeys: Undo / Redo test
    """

    async def test_anim_curve_paste_key_undo_redo(self):

        await self.load_stage(map_name="move_anim_curve_key.usda")
        await wait_stage_loading()

        # Copy the /World/Cube key from 20 to clipboard
        stage = omni.usd.get_context().get_stage()
        set_curvekey_clipboard(stage, ["/World/Sphere"], Usd.TimeCode(20))

        # Paste clipboard to shpere and cube time 40
        (result, err) = omni.kit.commands.execute(
            "PasteAnimCurveKeys", paths=["/World/Capsule", "/World/Cube"], time=Usd.TimeCode(40)
        )
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # PasteAnimCurveKeys command no error

        prim_capsule = stage.GetPrimAtPath("/World/Capsule")
        target_capsule = {
            "xformOp:rotateXYZ:x": {20: 45},
            "xformOp:rotateXYZ:y": {20: 30},
            "xformOp:rotateXYZ:z": {20: 60},
            "xformOp:translate:x": {40.0: 100.0},
            "xformOp:translate:y": {40.0: 120.0},
            "xformOp:translate:z": {40.0: -200.0},
        }
        self._check_curves(prim_capsule, target_capsule)

        prim_cube = stage.GetPrimAtPath("/World/Cube")
        target_cube = {
            "size:x": {20: 130},
            "xformOp:translate:x": {40.0: 100.0},
            "xformOp:translate:y": {40.0: 120.0},
            "xformOp:translate:z": {40.0: -200.0},
        }
        self._check_curves(prim_cube, target_cube)

        # Undo
        (result, err) = omni.kit.commands.execute("Undo")
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # Undo command no error

        target_undo_cube = {
            "size:x": {20: 130},
        }
        self._check_curves(prim_cube, target_undo_cube)

        target_undo_capsule = {
            "xformOp:rotateXYZ:x": {20: 45},
            "xformOp:rotateXYZ:y": {20: 30},
            "xformOp:rotateXYZ:z": {20: 60},
        }
        self._check_curves(prim_capsule, target_undo_capsule)

        # Redo
        (result, err) = omni.kit.commands.execute("Redo")
        self.assertTrue(result)  # command execution no exception from the command framework
        self.assertTrue(err)  # Redo command no error

        self._check_curves(prim_capsule, target_capsule)
        self._check_curves(prim_cube, target_cube)

    """
    This test will check if the Duplicate function is working with undo and redo
    """

    @unittest.skip("Please enable this test when kit-sdk is upgraded.")
    async def test_anim_curve_duplication_undo_redo(self):
        await self.load_stage(map_name="basic_curve_cube.usda")
        await wait_stage_loading()
        stage = omni.usd.get_context().get_stage()

        omni.kit.commands.execute(
            "CopyPrim",
            path_from="/World/Cube",
            path_to="/World/Cube_01",
            exclusive_select=False,
            copy_to_introducing_layer=False,
        )
        await ui_test.human_delay(30)

        omni.kit.commands.execute("Undo")
        await ui_test.human_delay(30)

        omni.kit.commands.execute("Redo")
        await ui_test.human_delay(30)

        prim = stage.GetPrimAtPath("/World/Cube")
        dup_prim = stage.GetPrimAtPath("/World/Cube_01")

        await self.advance_n_frames(30)

        translation_x_0 = prim.GetAttribute("xformOp:translate").Get()[0]
        self.assertAlmostEqual(translation_x_0, 166.345, places=3)

        translation_x_0 = dup_prim.GetAttribute("xformOp:translate").Get()[0]
        self.assertAlmostEqual(
            translation_x_0, 166.345, places=3, msg="The duplicated prim's animation is not workking correctly."
        )
