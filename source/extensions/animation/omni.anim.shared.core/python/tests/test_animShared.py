import asyncio
import math
import os

import carb
import numpy as np
import omni.graph.core as og
import omni.graph.core.tests as ogts
import omni.kit.app
import omni.kit.commands
import omni.kit.test
import omni.timeline
from omni.anim.shared.core import get_ext
from omni.anim.shared.core.scripts.kit_utils import get_points_attr, get_prim_io, get_time_node, get_xform_attr
from pxr import Gf

REL_TOL = 1e-03  # delta judge if close

# Kit 111: upper bound for Runtime Core to publish the stage with the edits a test authored (renderer bring-up in a
# fresh process compiles shaders on a cold cache), as Kit's own graph tests allow.
RUNTIME_WAIT_S = 180.0


class TestAnimShared(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        path_to_file = os.path.join(get_ext().get_ext_path(), "data", "usd", "cube_timesample.usda")
        self._usd_context = omni.usd.get_context()
        carb.settings.get_settings().set("/app/player/playComputegraph", True)
        await self._usd_context.open_stage_async(path_to_file)

        self._stage = self._usd_context.get_stage()

    async def tearDown(self):
        self._usd_context = None
        self._stage = None

    async def test_time_node(self):
        fps = self._stage.GetFramesPerSecond()
        # create the node
        tn = get_time_node()
        omni.timeline.get_timeline_interface().set_current_time(1.0)
        await omni.kit.app.get_app().next_update_async()

        time_attr = og.Controller.attribute("outputs:time", tn)
        time_val = og.Controller.get(time_attr)
        frame_attr = og.Controller.attribute("outputs:frame", tn)
        frame_val = og.Controller.get(frame_attr)
        assert math.isclose(time_val, 1.0, rel_tol=REL_TOL)
        assert math.isclose(frame_val, fps, rel_tol=REL_TOL)

    async def test_get_xform_node(self):

        np.random.seed(1)

        def random_mat():

            q = Gf.Quatd(np.random.rand(), np.random.rand(), np.random.rand(), np.random.rand())
            q.Normalize()
            rm = Gf.Matrix4d()
            rm.SetRotate(q)
            sm = Gf.Matrix4d()
            sm.SetScale(Gf.Vec3d(np.random.rand(), np.random.rand(), np.random.rand()))
            mtx = sm * rm
            mtx.SetTranslateOnly(Gf.Vec3d(np.random.rand(), np.random.rand(), np.random.rand()))
            return mtx

        def transform_prim(prim, mtx):
            omni.kit.commands.execute("TransformPrimCommand", path=prim.GetPath(), new_transform_matrix=mtx)

        def check_matrix(attr, node, mtx):
            attribute = og.Controller.attribute(attr, node)
            vals = np.array(og.Controller.get(attribute))
            expected = np.array(mtx).reshape(-1)
            self.assertAlmostEqual(((vals - expected) ** 2).sum(), 0)

        xform_prim = self._stage.DefinePrim(f"{self._stage.GetDefaultPrim().GetPath()}/xform", "Xform")
        cube_prim = self._stage.DefinePrim(f"{self._stage.GetDefaultPrim().GetPath()}/xform/cube", "Cube")
        cube_get_xform_node, cube_get_xform_output = get_xform_attr(cube_prim)

        xform_mat = random_mat()
        cube_mat = random_mat()
        cube_world_mat = cube_mat * xform_mat

        # Both the prim and its parent are pure usd:
        transform_prim(xform_prim, xform_mat)
        transform_prim(cube_prim, cube_mat)

        # Kit 111: Get Xform reads the runtime scene (OVStage). Authored USD reaches it when Runtime Core syncs the
        # edits for a reader, and the node registers as a reader only in its first evaluation, which then reads a scene
        # without the prims just authored ("could not find the prim in ovstage"). Wait for Runtime Core to take them in,
        # graphs held, as Kit's own graph tests do.
        await ogts.wait_for_runtime_stage(timeout=RUNTIME_WAIT_S)

        # local mode off: should just return the cube's world matrix:
        og.Controller(cube_get_xform_node.get_attribute("inputs:useLocal")).set(False)
        await omni.kit.app.get_app().next_update_async()
        check_matrix(cube_get_xform_output, cube_get_xform_node, cube_world_mat)

        # local mode on: should just return cube_mat, which is the cube's object matrix:
        og.Controller(cube_get_xform_node.get_attribute("inputs:useLocal")).set(True)
        await omni.kit.app.get_app().next_update_async()
        check_matrix(cube_get_xform_output, cube_get_xform_node, cube_mat)

        # Authoring notices update the node's private populated instance.
        # Runtime-only writes, reset stacks and hierarchy propagation are tested
        # directly against the same implementation in shared_transform.cpp.
        cube_mat = random_mat()
        transform_prim(cube_prim, cube_mat)
        og.Controller(cube_get_xform_node.get_attribute("inputs:useLocal")).set(False)
        await omni.kit.app.get_app().next_update_async()
        check_matrix(cube_get_xform_output, cube_get_xform_node, cube_mat * xform_mat)
        og.Controller(cube_get_xform_node.get_attribute("inputs:useLocal")).set(True)
        await omni.kit.app.get_app().next_update_async()
        check_matrix(cube_get_xform_output, cube_get_xform_node, cube_mat)

        xform_mat = random_mat()
        transform_prim(xform_prim, xform_mat)
        og.Controller(cube_get_xform_node.get_attribute("inputs:useLocal")).set(False)
        await omni.kit.app.get_app().next_update_async()
        check_matrix(cube_get_xform_output, cube_get_xform_node, cube_mat * xform_mat)
        og.Controller(cube_get_xform_node.get_attribute("inputs:useLocal")).set(True)
        await omni.kit.app.get_app().next_update_async()
        check_matrix(cube_get_xform_output, cube_get_xform_node, cube_mat)

    async def test_set_xform_node(self):
        # create the prim
        cube_prim = self._stage.DefinePrim(f"{self._stage.GetDefaultPrim().GetPath()}/cube2", "Cube")

        set_xform_node = get_prim_io(cube_prim, "omni.anim.SetXform", input_attr="inputs:prim")
        og.Controller(set_xform_node.get_attribute("inputs:transform")).set(
            [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 50, 0, 0, 0]
        )

        await omni.kit.app.get_app().next_update_async()
        vals = cube_prim.GetAttribute("xformOp:translate").Get()
        assert math.isclose(vals[0], 50, rel_tol=REL_TOL)
