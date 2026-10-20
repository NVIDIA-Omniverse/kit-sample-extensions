import asyncio

import omni.anim.shared.core.scripts.kit_utils as kit_utils
import omni.graph.core as og
import omni.kit.test
import omni.timeline
from pxr import UsdGeom


class TRS(object):
    """
    simple tranform object used for comparing if 2 transforms almost equal
    for now only supports translate, rotate and scale.
    TODO: we must use quaternion to compare rotations
    """

    def __init__(self, t=(0.0, 0.0, 0.0), r=(0.0, 0.0, 0.0), s=(1.0, 1.0, 1.0)):
        self.t = t
        self.r = r
        self.s = s
        self.EPSILON = 1e-3

    def __repr__(self):
        return f"[{self.t}, {self.r}, {self.s}]"

    def equals(self, other):
        if all([self.translate_equals(other), self.rotate_equals(other), self.scale_equals(other)]):
            return True

    def translate_equals(self, other):
        if all([abs(x - y) < self.EPSILON for x, y in zip(self.t, other.t)]):
            return True

    def rotate_equals(self, other):
        if all([abs(x - y) < self.EPSILON for x, y in zip(self.r, other.r)]):
            return True

    def scale_equals(self, other):
        if all([abs(x - y) < self.EPSILON for x, y in zip(self.s, other.s)]):
            return True


class TestDecomposeMatrix(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        await omni.usd.get_context().new_stage_async()

    async def tearDown(self):
        await omni.usd.get_context().new_stage_async()

    async def run_test_case(self, given: TRS, expected: TRS):
        """
        main test function for decomposeMatrix.
        it takes in "given" transform, applies decomposeMatrix and compares
        result of decomposeMatrix to the "expected" transform.
        """
        # create a new stage
        await omni.usd.get_context().new_stage_async()
        stage = omni.usd.get_context().get_stage()

        # create xform
        in_prim = stage.DefinePrim("/in_xform", "Xform")
        in_xform = UsdGeom.Xform(in_prim)

        # create decomposeMatrix
        await omni.kit.app.get_app().next_update_async()
        graph = kit_utils.get_graph(graph_type="PushGraph")
        in_xform_node, _ = kit_utils.get_xform_attr(in_prim, graph=graph)
        dmx_ogn = kit_utils.create_node("omni.anim.DecomposeMatrix", name="decompose", graph=graph)
        og.Controller.connect(in_xform_node.get_attribute("outputs:transform"), dmx_ogn.get_attribute("inputs:matrix"))

        # change inputs
        await omni.kit.app.get_app().next_update_async()
        in_xform.AddTranslateOp().Set(given.t)
        in_xform.AddRotateXYZOp().Set(given.r)
        in_xform.AddScaleOp().Set(given.s)

        # get outputs and compare
        await omni.kit.app.get_app().next_update_async()
        result = TRS()
        result.t = dmx_ogn.get_attribute("outputs:translate").get()
        result.r = dmx_ogn.get_attribute("outputs:rotate").get()
        result.s = dmx_ogn.get_attribute("outputs:scale").get()

        # check
        assert expected.equals(result), f"{result} doesn't match expected values {expected}"

    async def test_translate(self):
        given = TRS(t=(10000.0, -10000.0, 500000))
        expected = TRS(t=(10000.0, -10000.0, 500000))
        await self.run_test_case(given, expected)

    async def test_rotate_45(self):
        given = TRS(r=(0.0, 45.0, 0.0))
        expected = TRS(r=(0.0, 45.0, 0.0))
        await self.run_test_case(given, expected)

    async def test_rotate_close_to_180(self):
        given = TRS(r=(170.0, 170.0, 170.0))
        expected = TRS(r=(-10.0, 10.0, -10.0))
        await self.run_test_case(given, expected)

    async def test_rotate_negative(self):
        given = TRS(r=(-170.0, -170.0, 170.0))
        expected = TRS(r=(10.0, -10.0, -10.0))
        await self.run_test_case(given, expected)

    async def test_scale(self):
        given = TRS(s=(10.0, 10.0, 10.0))
        expected = TRS(s=(10.0, 10.0, 10.0))
        await self.run_test_case(given, expected)

    async def test_scale_nonuniform(self):
        given = TRS(s=(10.0, 20.0, 30.0))
        expected = TRS(s=(10.0, 20.0, 30.0))
        await self.run_test_case(given, expected)

    async def test_scale_negative(self):
        given = TRS(s=(-10.0, -10.0, -10.0))
        expected = TRS(r=(0, 0, -180), s=(10.0, 10.0, 10.0))
        await self.run_test_case(given, expected)

    async def test_scale_negative_nonuniform(self):
        given = TRS(s=(-10.0, -20.0, -30.0))
        expected = TRS(r=(0, 0, -180), s=(10.0, 20.0, 30.0))
        await self.run_test_case(given, expected)

    async def test_translate_rotate(self):
        given = TRS(t=(-10.0, -20.0, -30.0), r=(-10.0, -20.0, -30.0))
        expected = TRS(t=(-10.0, -20.0, -30.0), r=(-10.0, -20.0, -30.0))
        await self.run_test_case(given, expected)

    async def test_translate_rotate_scale(self):
        given = TRS(t=(-10.0, -20.0, -30.0), r=(-10.0, -20.0, -30.0), s=(-10.0, -20.0, -30.0))
        expected = TRS(t=(-10.0, -20.0, -30.0), r=(10.0, 20.0, 150.0), s=(10.0, 20.0, 30.0))
        await self.run_test_case(given, expected)
