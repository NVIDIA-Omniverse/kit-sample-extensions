import unittest
from pathlib import Path

import omni.graph.core as og
import omni.graph.core.tests as ogts
import omni.kit.app
import omni.kit.commands
import omni.kit.stage_templates
import omni.kit.test
import omni.timeline
import omni.usd
from pxr import Gf, Sdf, Usd, UsdGeom, Vt

EXTENSION_FOLDER_PATH = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
TEST_DATA_PATH = EXTENSION_FOLDER_PATH.joinpath("data/tests")


class TestCurveNodes(ogts.OmniGraphTestCase):
    ######################################################################
    # WARNING: changing the value of this flag will switch this script
    # from running the tests to overwriting the 'golden' data. If a test
    # is failing, make sure you understand why / whether it's ok to change
    # the ground truth data before running the tests with this flag set
    # to True.
    ######################################################################
    WRITE_TEST_RESULTS = False
    TEST_GRAPH_PATH = "/World/TestGraph"

    async def setUp(self):
        await super().setUp()

        self.smallNumber = 0.001
        self.usd_context = omni.usd.get_context()
        self._usd_path = TEST_DATA_PATH.absolute()
        self.test_file_path = str(self._usd_path.joinpath("curve_node_tests.usda").absolute())
        await self.usd_context.open_stage_async(self.test_file_path)

        self.stage = self.usd_context.get_stage()
        self.assertIsNotNone(self.stage)

        og.Controller.edit({"graph_path": self.TEST_GRAPH_PATH, "evaluator_name": "push"})

    async def tearDown(self):
        if self.WRITE_TEST_RESULTS:
            # If we're overwriting the test data, delete whatever graph we were using
            # before saving the stage
            omni.kit.commands.execute("DeletePrims", paths=[self.TEST_GRAPH_PATH])
            (result, _, _) = await self.usd_context.save_as_stage_async(self.test_file_path)
            self.assertTrue(result, "Failed to save stage at path: {}".format(self.test_file_path))
        await super().tearDown()

    async def test_closest_point_on_curve(self):
        controller = og.Controller()
        keys = og.Controller.Keys
        (
            graph,
            (importNode, closestPointNode),
            _,
            _,
        ) = controller.edit(
            self.TEST_GRAPH_PATH,
            {
                keys.CREATE_NODES: [
                    ("Import", "omni.graph.nodes.ReadPrimsV2"),
                    ("ClosestPoint", "omni.genproc.core.ClosestPointOnCurve"),
                ],
                keys.CONNECT: [("Import.outputs_primsBundle", "ClosestPoint.inputs:curvesBundle")],
                keys.SET_VALUES: [("ClosestPoint.inputs:point", Gf.Vec3f(0, 100, 0))],
            },
        )

        curvePrim = self.stage.GetPrimAtPath("/World/BasisCurves")
        self.assertTrue(curvePrim.IsValid(), "Invalid curve prim")
        importPrim = self.stage.GetPrimAtPath(importNode.get_prim_path())
        self.assertTrue(importPrim.IsValid(), "Invalid import prim")
        rel = importPrim.CreateRelationship("inputs:prims")
        rel.AddTarget(curvePrim.GetPath().pathString)

        await omni.kit.app.get_app().next_update_async()

        attr = closestPointNode.get_attribute("outputs:point")
        value = og.Controller.get(attr)
        test_point = Gf.Vec3f(value.tolist())

        if self.WRITE_TEST_RESULTS:
            resultsPrim = self.stage.DefinePrim("/World/Results/ClosestPointOnCurve")
            attr = resultsPrim.CreateAttribute("point", Sdf.ValueTypeNames.Point3f)
            attr.Set(test_point)
        else:
            resultsPrim = self.stage.GetPrimAtPath("/World/Results/ClosestPointOnCurve")
            self.assertTrue(resultsPrim.IsValid(), "Invalid results prim")
            attr = resultsPrim.GetAttribute("point")
            self.assertTrue(attr.IsValid(), "Invalid results attribute")
            point = attr.Get()
            self.assertTrue(
                Gf.IsClose(point, test_point, self.smallNumber),
                "Test point {} is not close to reference point {}".format(test_point, point),
            )

    async def test_get_curve_data(self):
        controller = og.Controller()
        keys = og.Controller.Keys
        (
            graph,
            (importNode, curveDataNode),
            _,
            _,
        ) = controller.edit(
            self.TEST_GRAPH_PATH,
            {
                keys.CREATE_NODES: [
                    ("Import", "omni.graph.nodes.ReadPrimsV2"),
                    ("GetCurveData", "omni.genproc.core.GetCurveData"),
                ],
                keys.CONNECT: [("Import.outputs_primsBundle", "GetCurveData.inputs:curvesBundle")],
                keys.SET_VALUES: [("GetCurveData.inputs:samplesPerSegment", 3)],
            },
        )

        curvePrim = self.stage.GetPrimAtPath("/World/BasisCurves")
        self.assertTrue(curvePrim.IsValid(), "Invalid curve prim")
        importPrim = self.stage.GetPrimAtPath(importNode.get_prim_path())
        self.assertTrue(importPrim.IsValid(), "Invalid import prim")
        rel = importPrim.CreateRelationship("inputs:prims")
        rel.AddTarget(curvePrim.GetPath().pathString)

        await omni.kit.app.get_app().next_update_async()

        attr = curveDataNode.get_attribute("outputs:points")
        value = og.Controller.get(attr)
        test_points = Vt.Vec3fArray(value.tolist())

        if self.WRITE_TEST_RESULTS:
            resultsPrim = self.stage.DefinePrim("/World/Results/GetCurveData")
            attr = resultsPrim.CreateAttribute("points", Sdf.ValueTypeNames.Point3fArray)
            attr.Set(test_points)
        else:
            resultsPrim = self.stage.GetPrimAtPath("/World/Results/GetCurveData")
            self.assertTrue(resultsPrim.IsValid(), "Invalid results prim")
            attr = resultsPrim.GetAttribute("points")
            self.assertTrue(attr.IsValid(), "Invalid results attribute")
            points = attr.Get()
            self.assertTrue(len(points) == len(test_points))
            for point, test_point in zip(points, test_points):
                self.assertTrue(
                    Gf.IsClose(point, test_point, self.smallNumber),
                    "Test point {} is not close to reference point {}".format(test_point, point),
                )

    async def test_order_matrices_by_distance(self):
        point = Gf.Vec3f(100, 0, 0)
        matricesIn = [
            Gf.Matrix4d(Gf.Rotation(Gf.Vec3d(1, 0, 0), 90), Gf.Vec3d(400, 0, 0)),
            Gf.Matrix4d(Gf.Rotation(Gf.Vec3d(1, 0, 0), 90), Gf.Vec3d(300, 0, 0)),
        ]

        controller = og.Controller()
        keys = og.Controller.Keys
        (
            graph,
            (orderNode,),
            _,
            _,
        ) = controller.edit(
            self.TEST_GRAPH_PATH,
            {
                keys.CREATE_NODES: [("Order", "omni.genproc.core.OrderMatricesByDistance")],
                keys.SET_VALUES: [
                    ("Order.inputs:point", point),
                    ("Order.inputs:matrices", matricesIn),
                ],
            },
        )

        await omni.kit.app.get_app().next_update_async()

        attr = orderNode.get_attribute("outputs:matrices")
        value = og.Controller.get(attr)
        matricesOut = [Gf.Matrix4d(value[0].reshape(4, 4).tolist()), Gf.Matrix4d(value[1].reshape(4, 4).tolist())]

        self.assertTrue(Gf.IsClose(matricesIn[0], matricesOut[1], self.smallNumber), "Matrices not correctly sorted.")
        self.assertTrue(Gf.IsClose(matricesIn[1], matricesOut[0], self.smallNumber), "Matrices not correctly sorted.")

    async def test_order_points_by_distance(self):
        point = Gf.Vec3f(100, 0, 0)
        pointsIn = [Gf.Vec3f(400, 0, 0), Gf.Vec3f(300, 0, 0)]

        controller = og.Controller()
        keys = og.Controller.Keys
        (
            graph,
            (orderNode,),
            _,
            _,
        ) = controller.edit(
            self.TEST_GRAPH_PATH,
            {
                keys.CREATE_NODES: [("Order", "omni.genproc.core.OrderPointsByDistance")],
                keys.SET_VALUES: [
                    ("Order.inputs:point", point),
                    ("Order.inputs:points", pointsIn),
                ],
            },
        )

        await omni.kit.app.get_app().next_update_async()

        attr = orderNode.get_attribute("outputs:points")
        value = og.Controller.get(attr)
        pointsOut = [Gf.Vec3f(value[0].tolist()), Gf.Vec3f(value[1].tolist())]

        self.assertTrue(Gf.IsClose(pointsIn[0], pointsOut[1], self.smallNumber), "Points not correctly sorted.")
        self.assertTrue(Gf.IsClose(pointsIn[1], pointsOut[0], self.smallNumber), "Points not correctly sorted.")

    async def test_point_on_curve(self):
        controller = og.Controller()
        keys = og.Controller.Keys
        (
            graph,
            (importNode, pointNode),
            _,
            _,
        ) = controller.edit(
            self.TEST_GRAPH_PATH,
            {
                keys.CREATE_NODES: [
                    ("Import", "omni.graph.nodes.ReadPrimsV2"),
                    ("PointOnCurve", "omni.genproc.core.PointOnCurve"),
                ],
                keys.CONNECT: [("Import.outputs_primsBundle", "PointOnCurve.inputs:curvesBundle")],
                keys.SET_VALUES: [("PointOnCurve.inputs:uValue", 0.5)],
            },
        )

        curvePrim = self.stage.GetPrimAtPath("/World/BasisCurves")
        self.assertTrue(curvePrim.IsValid(), "Invalid curve prim")
        importPrim = self.stage.GetPrimAtPath(importNode.get_prim_path())
        self.assertTrue(importPrim.IsValid(), "Invalid import prim")
        rel = importPrim.CreateRelationship("inputs:prims")
        rel.AddTarget(curvePrim.GetPath().pathString)

        await omni.kit.app.get_app().next_update_async()

        attr = pointNode.get_attribute("outputs:point")
        value = og.Controller.get(attr)
        test_point = Gf.Vec3f(value.tolist())

        if self.WRITE_TEST_RESULTS:
            resultsPrim = self.stage.DefinePrim("/World/Results/PointOnCurve")
            attr = resultsPrim.CreateAttribute("point", Sdf.ValueTypeNames.Point3f)
            attr.Set(test_point)
        else:
            resultsPrim = self.stage.GetPrimAtPath("/World/Results/PointOnCurve")
            self.assertTrue(resultsPrim.IsValid(), "Invalid results prim")
            attr = resultsPrim.GetAttribute("point")
            self.assertTrue(attr.IsValid(), "Invalid results attribute")
            point = attr.Get()
            self.assertTrue(
                Gf.IsClose(point, test_point, self.smallNumber),
                "Test point {} is not close to reference point {}".format(test_point, point),
            )

    async def test_points_on_curve(self):
        controller = og.Controller()
        keys = og.Controller.Keys
        (
            graph,
            (importNode, pointsNode),
            _,
            _,
        ) = controller.edit(
            self.TEST_GRAPH_PATH,
            {
                keys.CREATE_NODES: [
                    ("Import", "omni.graph.nodes.ReadPrimsV2"),
                    ("PointsOnCurve", "omni.genproc.core.PointsOnCurve"),
                ],
                keys.CONNECT: [("Import.outputs_primsBundle", "PointsOnCurve.inputs:curvesBundle")],
                keys.SET_VALUES: [
                    # rather than set up an array input, we'll just test the random sampling mode...
                    ("PointsOnCurve.inputs:samplingMode", 1)
                ],
            },
        )

        curvePrim = self.stage.GetPrimAtPath("/World/BasisCurves")
        self.assertTrue(curvePrim.IsValid(), "Invalid curve prim")
        importPrim = self.stage.GetPrimAtPath(importNode.get_prim_path())
        self.assertTrue(importPrim.IsValid(), "Invalid import prim")
        rel = importPrim.CreateRelationship("inputs:prims")
        rel.AddTarget(curvePrim.GetPath().pathString)

        await omni.kit.app.get_app().next_update_async()

        attr = pointsNode.get_attribute("outputs:points")
        value = og.Controller.get(attr)
        test_points = Vt.Vec3fArray(value.tolist())

        if self.WRITE_TEST_RESULTS:
            resultsPrim = self.stage.DefinePrim("/World/Results/PointsOnCurve")
            attr = resultsPrim.CreateAttribute("points", Sdf.ValueTypeNames.Point3fArray)
            attr.Set(test_points)
        else:
            resultsPrim = self.stage.GetPrimAtPath("/World/Results/PointsOnCurve")
            self.assertTrue(resultsPrim.IsValid(), "Invalid results prim")
            attr = resultsPrim.GetAttribute("points")
            self.assertTrue(attr.IsValid(), "Invalid results attribute")
            points = attr.Get()
            self.assertTrue(len(points) == len(test_points))
            for point, test_point in zip(points, test_points):
                self.assertTrue(
                    Gf.IsClose(point, test_point, self.smallNumber),
                    "Test point {} is not close to reference point {}".format(test_point, point),
                )

    async def test_tag_points_from_prims(self):
        controller = og.Controller()
        keys = og.Controller.Keys
        (
            graph,
            (importCurveNode, importMeshNode, _, _, tagPointsNode),
            _,
            _,
        ) = controller.edit(
            self.TEST_GRAPH_PATH,
            {
                keys.CREATE_NODES: [
                    ("ImportCurves", "omni.graph.nodes.ReadPrimsV2"),
                    ("ImportMesh", "omni.graph.nodes.ReadPrimsV2"),
                    ("GetCurveData", "omni.genproc.core.GetCurveData"),
                    ("TagPrims", "omni.genproc.core.TagPrims"),
                    ("TagPoints", "omni.genproc.core.TagPointsFromPrims"),
                ],
                keys.CONNECT: [
                    ("ImportCurves.outputs_primsBundle", "GetCurveData.inputs:curvesBundle"),
                    ("ImportMesh.outputs_primsBundle", "TagPrims.inputs:bundle"),
                    ("TagPrims.outputs_bundle", "TagPoints.inputs:bundle"),
                    ("GetCurveData.outputs:points", "TagPoints.inputs:points"),
                ],
                keys.SET_VALUES: [
                    ("GetCurveData.inputs:samplesPerSegment", 5),
                    ("TagPrims.inputs:tagValue", "inside"),
                    ("TagPoints.inputs:defaultTag", "outside"),
                ],
            },
        )

        for primPath, importNode in zip(["/World/BasisCurves", "/World/Cube"], [importCurveNode, importMeshNode]):
            prim = self.stage.GetPrimAtPath(primPath)
            self.assertTrue(prim.IsValid(), "Invalid prim: {}".format(primPath))
            importPrim = self.stage.GetPrimAtPath(importNode.get_prim_path())
            self.assertTrue(importPrim.IsValid(), "Invalid prim: {}".format(importNode.get_prim_path()))
            rel = importPrim.CreateRelationship("inputs:prims")
            rel.AddTarget(primPath)

        await omni.kit.app.get_app().next_update_async()

        attr = tagPointsNode.get_attribute("outputs:tags")
        value = og.Controller.get(attr)
        test_tags = Vt.TokenArray(value)

        if self.WRITE_TEST_RESULTS:
            resultsPrim = self.stage.DefinePrim("/World/Results/TagPointsFromPrims")
            attr = resultsPrim.CreateAttribute("tags", Sdf.ValueTypeNames.TokenArray)
            attr.Set(test_tags)
        else:
            resultsPrim = self.stage.GetPrimAtPath("/World/Results/TagPointsFromPrims")
            self.assertTrue(resultsPrim.IsValid(), "Invalid results prim")
            attr = resultsPrim.GetAttribute("tags")
            self.assertTrue(attr.IsValid(), "Invalid results attribute")
            tags = attr.Get()
            self.assertTrue(
                len(tags) == len(test_tags),
                "Test tags count does not match reference tags count ({} vs {})".format(len(test_tags), len(tags)),
            )
            for tag, test_tag in zip(tags, test_tags):
                self.assertTrue(tag == test_tag, "Test tag {} does not match reference tag {}".format(test_tag, tag))

    @unittest.skip(
        "Skipping test until ReadPrimsV2 output prims-in-bundle match the order in which prims are attached to read node."
    )
    async def test_transforms_to_curve(self):
        controller = og.Controller()
        keys = og.Controller.Keys
        (
            graph,
            (importNode, _, curveDataNode),
            _,
            _,
        ) = controller.edit(
            self.TEST_GRAPH_PATH,
            {
                keys.CREATE_NODES: [
                    ("ImportXformables", "omni.graph.nodes.ReadPrimsV2"),
                    ("XformsToCurve", "omni.genproc.core.TransformsToCurve"),
                    ("GetCurveData", "omni.genproc.core.GetCurveData"),
                ],
                keys.CONNECT: [
                    ("ImportXformables.outputs_primsBundle", "XformsToCurve.inputs:transformBundle"),
                    ("XformsToCurve.outputs_curveBundle", "GetCurveData.inputs:curvesBundle"),
                ],
                keys.SET_VALUES: [("GetCurveData.inputs:samplesPerSegment", 5)],
            },
        )

        importPrim = self.stage.GetPrimAtPath(importNode.get_prim_path())
        self.assertTrue(importPrim.IsValid(), "Invalid import prim")
        for primPath in ["/World/Xform_{:02d}".format(i) for i in range(1, 5)]:
            prim = self.stage.GetPrimAtPath(primPath)
            self.assertTrue(prim.IsValid(), "Invalid prim: {}".format(primPath))
            rel = importPrim.CreateRelationship("inputs:prims")
            rel.AddTarget(primPath)

        await omni.kit.app.get_app().next_update_async()

        attr = curveDataNode.get_attribute("outputs:points")
        value = og.Controller.get(attr)
        test_points = Vt.Vec3fArray(value.tolist())

        if self.WRITE_TEST_RESULTS:
            resultsPrim = self.stage.DefinePrim("/World/Results/TransformsToCurve")
            attr = resultsPrim.CreateAttribute("points", Sdf.ValueTypeNames.Point3fArray)
            attr.Set(test_points)
        else:
            resultsPrim = self.stage.GetPrimAtPath("/World/Results/TransformsToCurve")
            self.assertTrue(resultsPrim.IsValid(), "Invalid results prim")
            attr = resultsPrim.GetAttribute("points")
            self.assertTrue(attr.IsValid(), "Invalid results attribute")
            points = attr.Get()
            self.assertTrue(
                len(points) == len(test_points),
                "Test points count does not match reference points count ({} vs {})".format(
                    len(test_points), len(points)
                ),
            )
            for point, test_point in zip(points, test_points):
                self.assertTrue(
                    Gf.IsClose(point, test_point, self.smallNumber),
                    "Test point {} is not close to reference point {}".format(test_point, point),
                )

    async def test_raycast(self):
        controller = og.Controller()
        keys = og.Controller.Keys
        (
            graph,
            (importSrcNode, importObstaclesNode, raycastNode),
            _,
            _,
        ) = controller.edit(
            self.TEST_GRAPH_PATH,
            {
                keys.CREATE_NODES: [
                    ("ImportSource", "omni.graph.nodes.ReadPrimsV2"),
                    ("ImportObstacles", "omni.graph.nodes.ReadPrimsV2"),
                    ("Raycast", "omni.genproc.core.Raycast"),
                ],
                keys.CONNECT: [
                    ("ImportSource.outputs_primsBundle", "Raycast.inputs:primBundle"),
                    ("ImportObstacles.outputs_primsBundle", "Raycast.inputs:obstacleBundle"),
                ],
                keys.SET_VALUES: [
                    ("Raycast.inputs:direction", [0.0, 0.0, -1.0]),
                    ("Raycast.inputs:closestHitOnly", False),
                ],
            },
        )

        for primPath, importNode in zip(["/World/Cube_01", "/World/Cube_02"], [importSrcNode, importObstaclesNode]):
            prim = self.stage.GetPrimAtPath(primPath)
            self.assertTrue(prim.IsValid(), "Invalid prim: {}".format(primPath))
            importPrim = self.stage.GetPrimAtPath(importNode.get_prim_path())
            self.assertTrue(importPrim.IsValid(), "Invalid prim: {}".format(importNode.get_prim_path()))
            rel = importPrim.CreateRelationship("inputs:prims")
            rel.AddTarget(primPath)

        await omni.kit.app.get_app().next_update_async()

        attr = raycastNode.get_attribute("outputs:points")
        value = og.Controller.get(attr)
        test_points = Vt.Vec3fArray(value.tolist())

        if self.WRITE_TEST_RESULTS:
            resultsPrim = self.stage.DefinePrim("/World/Results/Raycast")
            attr = resultsPrim.CreateAttribute("points", Sdf.ValueTypeNames.Point3fArray)
            attr.Set(test_points)
        else:
            resultsPrim = self.stage.GetPrimAtPath("/World/Results/Raycast")
            self.assertTrue(resultsPrim.IsValid(), "Invalid results prim")
            attr = resultsPrim.GetAttribute("points")
            self.assertTrue(attr.IsValid(), "Invalid results attribute")
            points = attr.Get()
            self.assertTrue(
                len(points) == len(test_points),
                "Test points count does not match reference points count ({} vs {})".format(
                    len(test_points), len(points)
                ),
            )
            for point, test_point in zip(points, test_points):
                self.assertTrue(
                    Gf.IsClose(point, test_point, self.smallNumber),
                    "Test point {} is not close to reference point {}".format(test_point, point),
                )

    async def test_tag_prims_from_ramp(self):
        controller = og.Controller()
        keys = og.Controller.Keys
        (
            graph,
            (importNode, tagNode, curveDataNode),
            _,
            _,
        ) = controller.edit(
            self.TEST_GRAPH_PATH,
            {
                keys.CREATE_NODES: [
                    ("Import", "omni.graph.nodes.ReadPrimsV2"),
                    ("TagPrimsFromRamp", "omni.genproc.core.TagPrimsFromRamp"),
                    ("GetCurveData", "omni.genproc.core.GetCurveData"),
                ],
                keys.CONNECT: [
                    ("Import.outputs_primsBundle", "TagPrimsFromRamp.inputs:bundle"),
                    ("TagPrimsFromRamp.outputs_bundle", "GetCurveData.inputs:curvesBundle"),
                ],
                keys.SET_VALUES: [
                    ("TagPrimsFromRamp.inputs:rampPositions", [0.0, 0.5, 1.0]),
                    ("TagPrimsFromRamp.inputs:rampValues", [0.0, 1.0, 0.0]),
                    ("TagPrimsFromRamp.inputs:rampInterpolations", [1, 1, 1]),
                    ("TagPrimsFromRamp.inputs:rampTags", ["low", "medium", "high"]),
                    ("GetCurveData.inputs:samplesPerSegment", 5),
                ],
            },
        )

        curvePrim = self.stage.GetPrimAtPath("/World/BasisCurves")
        self.assertTrue(curvePrim.IsValid(), "Invalid curve prim")
        importPrim = self.stage.GetPrimAtPath(importNode.get_prim_path())
        self.assertTrue(importPrim.IsValid(), "Invalid import prim")
        rel = importPrim.CreateRelationship("inputs:prims")
        rel.AddTarget(curvePrim.GetPath().pathString)

        await omni.kit.app.get_app().next_update_async()

        attr = curveDataNode.get_attribute("outputs:tags")
        value = og.Controller.get(attr)
        test_tags = Vt.TokenArray(value)

        if self.WRITE_TEST_RESULTS:
            resultsPrim = self.stage.DefinePrim("/World/Results/TagPrimsFromRamp")
            attr = resultsPrim.CreateAttribute("tags", Sdf.ValueTypeNames.TokenArray)
            attr.Set(test_tags)
        else:
            resultsPrim = self.stage.GetPrimAtPath("/World/Results/TagPrimsFromRamp")
            self.assertTrue(resultsPrim.IsValid(), "Invalid results prim")
            attr = resultsPrim.GetAttribute("tags")
            self.assertTrue(attr.IsValid(), "Invalid results attribute")
            tags = attr.Get()
            self.assertTrue(
                len(tags) == len(test_tags),
                "Test tags count does not match reference tags count ({} vs {})".format(len(test_tags), len(tags)),
            )
            for tag, test_tag in zip(tags, test_tags):
                self.assertTrue(tag == test_tag, "Test tag {} does not match reference tag {}".format(test_tag, tag))

    async def test_resample_curves(self):
        # For this test in particular, linux and windows results differ by more than the
        # default small number. So we'll be more generous here:
        self.smallNumber = 0.001

        controller = og.Controller()
        keys = og.Controller.Keys
        (
            graph,
            (importNode, _, curveDataNode),
            _,
            _,
        ) = controller.edit(
            self.TEST_GRAPH_PATH,
            {
                keys.CREATE_NODES: [
                    ("Import", "omni.graph.nodes.ReadPrimsV2"),
                    ("ResampleCurves", "omni.genproc.core.ResampleCurves"),
                    ("GetCurveData", "omni.genproc.core.GetCurveData"),
                ],
                keys.CONNECT: [
                    ("Import.outputs_primsBundle", "ResampleCurves.inputs:curvesBundle"),
                    ("ResampleCurves.outputs_curvesBundle", "GetCurveData.inputs:curvesBundle"),
                ],
                keys.SET_VALUES: [
                    ("ResampleCurves.inputs:numberOfSegments", 2),
                    ("GetCurveData.inputs:samplesPerSegment", 5),
                ],
            },
        )

        curvePrim = self.stage.GetPrimAtPath("/World/BasisCurves")
        self.assertTrue(curvePrim.IsValid(), "Invalid curve prim")
        importPrim = self.stage.GetPrimAtPath(importNode.get_prim_path())
        self.assertTrue(importPrim.IsValid(), "Invalid import prim")
        rel = importPrim.CreateRelationship("inputs:prims")
        rel.AddTarget(curvePrim.GetPath().pathString)

        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()

        attr = curveDataNode.get_attribute("outputs:points")
        value = og.Controller.get(attr)
        test_points = Vt.Vec3fArray(value.tolist())

        if self.WRITE_TEST_RESULTS:
            resultsPrim = self.stage.DefinePrim("/World/Results/ResampleCurves")
            attr = resultsPrim.CreateAttribute("points", Sdf.ValueTypeNames.Point3fArray)
            attr.Set(test_points)
        else:
            resultsPrim = self.stage.GetPrimAtPath("/World/Results/ResampleCurves")
            self.assertTrue(resultsPrim.IsValid(), "Invalid results prim")
            attr = resultsPrim.GetAttribute("points")
            self.assertTrue(attr.IsValid(), "Invalid results attribute")
            points = attr.Get()
            self.assertTrue(
                len(points) == len(test_points),
                "Test points count does not match reference points count ({} vs {})".format(
                    len(test_points), len(points)
                ),
            )
            for point, test_point in zip(points, test_points):
                self.assertTrue(
                    Gf.IsClose(point, test_point, self.smallNumber),
                    "Test point {} is not close to reference point {}".format(test_point, point),
                )

    # NOTE: omitting this test for now; node output is a MPiB object which
    # we don't currently have support for inspecting in python
    # async def test_order_prims_by_distance(self):
    #    pass

    # NOTE: This node is used in the test for TagPointsFromPrims
    # async def test_tag_prims(self):
    #    pass
