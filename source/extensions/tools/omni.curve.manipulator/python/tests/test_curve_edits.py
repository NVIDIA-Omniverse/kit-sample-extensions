# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from pathlib import Path

import carb
import carb.input
import carb.settings
import omni.kit.app
import omni.kit.commands
import omni.kit.undo
import omni.usd
from omni.kit.manipulator.transform.settings_constants import Constants
from pxr import Gf, Usd, UsdGeom

from ..bindings import CurveEditingModeType
from ..scripts.bezier_curve_edits_context import BezierCurveEditsContextManager

CURRENT_PATH = Path(carb.tokens.get_tokens_interface().resolve("${omni.curve.manipulator}/data"))
CURVE_PATH = "/World/BasisCurves"

# This file contains the non-interactive API tests (no viewport involved) for BezierCurveEdits
# If you need to add tests that involves viewport and user inputs, use test_curve_manipulator.py instead


class TestBezierCurveEdits(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._context = omni.usd.get_context()
        await self._context.new_stage_async()
        self._stage = self._context.get_stage()
        self.assertIsNotNone(self._stage)

        self._curve_edits_context = BezierCurveEditsContextManager.get_context()
        self._curve_edits = self._curve_edits_context.curve_edits

    async def tearDown(self): ...

    # Tests all split_at_cvs combinations
    async def test_split_at_cvs_cubic_bezier_vertex(self):
        await self._test_split_at_cvs_impl(UsdGeom.Tokens.bezier, UsdGeom.Tokens.cubic, UsdGeom.Tokens.vertex)

    async def test_split_at_cvs_cubic_bezier_constant(self):
        await self._test_split_at_cvs_impl(UsdGeom.Tokens.bezier, UsdGeom.Tokens.cubic, UsdGeom.Tokens.constant)

    async def test_split_at_cvs_cubic_bezier_varying(self):
        await self._test_split_at_cvs_impl(UsdGeom.Tokens.bezier, UsdGeom.Tokens.cubic, UsdGeom.Tokens.varying)

    async def test_split_at_cvs_linear_vertex(self):
        await self._test_split_at_cvs_impl(UsdGeom.Tokens.bezier, UsdGeom.Tokens.linear, UsdGeom.Tokens.vertex)

    async def test_split_at_cvs_linear_constant(self):
        await self._test_split_at_cvs_impl(UsdGeom.Tokens.bezier, UsdGeom.Tokens.linear, UsdGeom.Tokens.constant)

    async def test_split_at_cvs_linear_varying(self):
        await self._test_split_at_cvs_impl(UsdGeom.Tokens.bezier, UsdGeom.Tokens.linear, UsdGeom.Tokens.varying)

    async def _test_split_at_cvs_impl(self, basis: str, curve_type: str, widths_interpolation: str):
        basis_curves = self._create_test_curves(basis, curve_type, UsdGeom.Tokens.nonperiodic, widths_interpolation)

        # split the curve at these indices
        cv_dict = {basis_curves: [3, 6, 19, 22]}
        self._curve_edits.split_at_anchor_cvs(cv_dict, False)

        self.assertListEqual(list(basis_curves.GetCurveVertexCountsAttr().Get()), [4, 4, 7, 7, 4, 4])

        expected_points = [
            # curve 0
            (-5, 0, 0),
            (-5, 1, 0),
            (-4, 1, 0),
            (-4, 0, 0),
            # curve 1
            (-4, 0, 0),
            (-4, -1, 0),
            (-3, -1, 0),
            (-3, 0, 0),
            # curve 2
            (-3, 0, 0),
            (-3, 1, 0),
            (-2, 1, 0),
            (-2, 0, 0),
            (-2, -1, 0),
            (-1, -1, 0),
            (-1, 0, 0),
            # curve 3
            (1, 0, 0),
            (1, -1, 0),
            (2, -1, 0),
            (2, 0, 0),
            (2, 1, 0),
            (3, 1, 0),
            (3, 0, 0),
            # curve 4
            (3, 0, 0),
            (3, -1, 0),
            (4, -1, 0),
            (4, 0, 0),
            # curve 5
            (4, 0, 0),
            (4, 1, 0),
            (5, 1, 0),
            (5, 0, 0),
        ]
        self.assertListEqual(list(basis_curves.GetPointsAttr().Get()), expected_points)

        curve_type = basis_curves.GetTypeAttr().Get()
        widths_interpolation = basis_curves.GetWidthsInterpolation()
        expected_widths = []
        if widths_interpolation == UsdGeom.Tokens.constant:
            expected_widths = [5]
        elif widths_interpolation == UsdGeom.Tokens.vertex or curve_type == UsdGeom.Tokens.linear:
            expected_widths = [
                1,
                2,
                3,
                4,
                4,
                5,
                6,
                7,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19,
                20,
                20,
                21,
                22,
                23,
                23,
                24,
                25,
                26,
            ]
        elif widths_interpolation == UsdGeom.Tokens.varying:
            expected_widths = [1, 2, 2, 3, 3, 4, 5, 6, 7, 8, 8, 9, 9, 10]

        if expected_widths:
            self.assertListEqual(list(basis_curves.GetWidthsAttr().Get()), expected_widths)

    # Tests all split_at_cvs to new basisCurve combinations
    async def test_split_at_cvs_to_new_cubic_bezier_vertex(self):
        await self._test_split_at_cvs_to_new_impl(UsdGeom.Tokens.bezier, UsdGeom.Tokens.cubic, UsdGeom.Tokens.vertex)

    async def test_split_at_cvs_to_new_cubic_bezier_constant(self):
        await self._test_split_at_cvs_to_new_impl(UsdGeom.Tokens.bezier, UsdGeom.Tokens.cubic, UsdGeom.Tokens.constant)

    async def test_split_at_cvs_to_new_cubic_bezier_varying(self):
        await self._test_split_at_cvs_to_new_impl(UsdGeom.Tokens.bezier, UsdGeom.Tokens.cubic, UsdGeom.Tokens.varying)

    async def test_split_at_cvs_to_new_linear_vertex(self):
        await self._test_split_at_cvs_to_new_impl(UsdGeom.Tokens.bezier, UsdGeom.Tokens.linear, UsdGeom.Tokens.vertex)

    async def test_split_at_cvs_to_new_linear_constant(self):
        await self._test_split_at_cvs_to_new_impl(UsdGeom.Tokens.bezier, UsdGeom.Tokens.linear, UsdGeom.Tokens.constant)

    async def test_split_at_cvs_to_new_linear_varying(self):
        await self._test_split_at_cvs_to_new_impl(UsdGeom.Tokens.bezier, UsdGeom.Tokens.linear, UsdGeom.Tokens.varying)

    async def _test_split_at_cvs_to_new_impl(self, basis: str, curve_type: str, widths_interpolation: str):
        basis_curves = self._create_test_curves(basis, curve_type, UsdGeom.Tokens.nonperiodic, widths_interpolation)

        # split the curve at these indices, it will break the current basis_curves into 5 basisCurves prims
        cv_dict = {basis_curves: [3, 6, 19, 22]}
        self._curve_edits.split_at_anchor_cvs(cv_dict, True)

        expected_vertex_counts = [[4], [4], [7, 7], [4], [4]]

        expected_points = [
            [(-5, 0, 0), (-5, 1, 0), (-4, 1, 0), (-4, 0, 0)],
            [(-4, 0, 0), (-4, -1, 0), (-3, -1, 0), (-3, 0, 0)],
            [
                (-3, 0, 0),
                (-3, 1, 0),
                (-2, 1, 0),
                (-2, 0, 0),
                (-2, -1, 0),
                (-1, -1, 0),
                (-1, 0, 0),
                (1, 0, 0),
                (1, -1, 0),
                (2, -1, 0),
                (2, 0, 0),
                (2, 1, 0),
                (3, 1, 0),
                (3, 0, 0),
            ],
            [(3, 0, 0), (3, -1, 0), (4, -1, 0), (4, 0, 0)],
            [(4, 0, 0), (4, 1, 0), (5, 1, 0), (5, 0, 0)],
        ]

        curve_type = basis_curves.GetTypeAttr().Get()
        widths_interpolation = basis_curves.GetWidthsInterpolation()
        expected_widths = []
        if widths_interpolation == UsdGeom.Tokens.constant:
            expected_widths = [[5], [5], [5], [5], [5]]
        elif widths_interpolation == UsdGeom.Tokens.vertex or curve_type == UsdGeom.Tokens.linear:
            expected_widths = [
                [1, 2, 3, 4],
                [4, 5, 6, 7],
                [7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20],
                [20, 21, 22, 23],
                [23, 24, 25, 26],
            ]
        elif widths_interpolation == UsdGeom.Tokens.varying:
            expected_widths = [[1, 2], [2, 3], [3, 4, 5, 6, 7, 8], [8, 9], [9, 10]]

        basis_curves_list = [basis_curves]
        for i in range(1, 5):
            split_basis_curves = UsdGeom.BasisCurves.Get(self._stage, f"/basis_curves_0{i}")
            self.assertTrue(split_basis_curves)
            basis_curves_list.append(split_basis_curves)

        vertex_counts = []
        points = []
        widths = []
        for basis_curves in basis_curves_list:
            vertex_counts.append(list(basis_curves.GetCurveVertexCountsAttr().Get()))
            points.append(list(basis_curves.GetPointsAttr().Get()))
            widths.append(list(basis_curves.GetWidthsAttr().Get()))

        def check_equal(generated: list[list], expected: list[list]):
            self.assertEqual(len(generated), len(expected))

            for i, gen in enumerate(generated):
                self.assertListEqual(gen, expected[i])

        check_equal(vertex_counts, expected_vertex_counts)
        check_equal(points, expected_points)

        if expected_widths:
            check_equal(widths, expected_widths)

    # Tests all split_at_cvs combinations
    async def test_delete_and_split_at_cvs_cubic_bezier_vertex(self):
        await self._test_delete_and_split_at_cvs_impl(
            UsdGeom.Tokens.bezier, UsdGeom.Tokens.cubic, UsdGeom.Tokens.vertex
        )

    async def test_delete_and_split_at_cvs_cubic_bezier_constant(self):
        await self._test_delete_and_split_at_cvs_impl(
            UsdGeom.Tokens.bezier, UsdGeom.Tokens.cubic, UsdGeom.Tokens.constant
        )

    async def test_delete_and_split_at_cvs_cubic_bezier_varying(self):
        await self._test_delete_and_split_at_cvs_impl(
            UsdGeom.Tokens.bezier, UsdGeom.Tokens.cubic, UsdGeom.Tokens.varying
        )

    async def test_delete_and_split_at_cvs_linear_vertex(self):
        await self._test_delete_and_split_at_cvs_impl(
            UsdGeom.Tokens.bezier, UsdGeom.Tokens.linear, UsdGeom.Tokens.vertex
        )

    async def test_delete_and_split_at_cvs_linear_constant(self):
        await self._test_delete_and_split_at_cvs_impl(
            UsdGeom.Tokens.bezier, UsdGeom.Tokens.linear, UsdGeom.Tokens.constant
        )

    async def test_delete_and_split_at_cvs_linear_varying(self):
        await self._test_delete_and_split_at_cvs_impl(
            UsdGeom.Tokens.bezier, UsdGeom.Tokens.linear, UsdGeom.Tokens.varying
        )

    async def _test_delete_and_split_at_cvs_impl(self, basis: str, curve_type: str, widths_interpolation: str):
        basis_curves = self._create_test_curves(basis, curve_type, UsdGeom.Tokens.nonperiodic, widths_interpolation)

        # delete and split the curve at these indices
        cv_dict = {basis_curves: [6, 19]}
        self._curve_edits.delete_and_split_anchor_cvs(cv_dict, False)

        expected_vertex_counts = {UsdGeom.Tokens.linear: [6, 6, 6, 6], UsdGeom.Tokens.cubic: [4, 4, 4, 4]}
        self.assertListEqual(list(basis_curves.GetCurveVertexCountsAttr().Get()), expected_vertex_counts[curve_type])

        expected_points = {
            UsdGeom.Tokens.linear: [
                # curve 0
                (-5, 0, 0),
                (-5, 1, 0),
                (-4, 1, 0),
                (-4, 0, 0),
                (-4, -1, 0),
                (-3, -1, 0),
                # curve 1
                (-3, 1, 0),
                (-2, 1, 0),
                (-2, 0, 0),
                (-2, -1, 0),
                (-1, -1, 0),
                (-1, 0, 0),
                # curve 2
                (1, 0, 0),
                (1, -1, 0),
                (2, -1, 0),
                (2, 0, 0),
                (2, 1, 0),
                (3, 1, 0),
                # curve 3
                (3, -1, 0),
                (4, -1, 0),
                (4, 0, 0),
                (4, 1, 0),
                (5, 1, 0),
                (5, 0, 0),
            ],
            UsdGeom.Tokens.cubic: [
                # curve 0
                (-5, 0, 0),
                (-5, 1, 0),
                (-4, 1, 0),
                (-4, 0, 0),
                # curve 1
                (-2, 0, 0),
                (-2, -1, 0),
                (-1, -1, 0),
                (-1, 0, 0),
                # curve 2
                (1, 0, 0),
                (1, -1, 0),
                (2, -1, 0),
                (2, 0, 0),
                # curve 3
                (4, 0, 0),
                (4, 1, 0),
                (5, 1, 0),
                (5, 0, 0),
            ],
        }
        self.assertListEqual(list(basis_curves.GetPointsAttr().Get()), expected_points[curve_type])

        curve_type = basis_curves.GetTypeAttr().Get()
        widths_interpolation = basis_curves.GetWidthsInterpolation()
        expected_widths = []
        if widths_interpolation == UsdGeom.Tokens.constant:
            expected_widths = [5]
        elif curve_type == UsdGeom.Tokens.linear:
            expected_widths = [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 21, 22, 23, 24, 25, 26]
        elif widths_interpolation == UsdGeom.Tokens.vertex:
            expected_widths = [1, 2, 3, 4, 10, 11, 12, 13, 14, 15, 16, 17, 23, 24, 25, 26]
        elif widths_interpolation == UsdGeom.Tokens.varying:
            expected_widths = [1, 2, 4, 5, 6, 7, 9, 10]

        if expected_widths:
            self.assertListEqual(list(basis_curves.GetWidthsAttr().Get()), expected_widths)

    # Tests all delete_and_split_at_cvs to new basisCurve combinations
    async def test_delete_and_split_at_cvs_to_new_cubic_bezier_vertex(self):
        await self._test_delete_and_split_at_cvs_to_new_impl(
            UsdGeom.Tokens.bezier, UsdGeom.Tokens.cubic, UsdGeom.Tokens.vertex
        )

    async def test_delete_and_split_at_cvs_to_new_cubic_bezier_constant(self):
        await self._test_delete_and_split_at_cvs_to_new_impl(
            UsdGeom.Tokens.bezier, UsdGeom.Tokens.cubic, UsdGeom.Tokens.constant
        )

    async def test_delete_and_split_at_cvs_to_new_cubic_bezier_varying(self):
        await self._test_delete_and_split_at_cvs_to_new_impl(
            UsdGeom.Tokens.bezier, UsdGeom.Tokens.cubic, UsdGeom.Tokens.varying
        )

    async def test_delete_and_split_at_cvs_to_new_linear_vertex(self):
        await self._test_delete_and_split_at_cvs_to_new_impl(
            UsdGeom.Tokens.bezier, UsdGeom.Tokens.linear, UsdGeom.Tokens.vertex
        )

    async def test_delete_and_split_at_cvs_to_new_linear_constant(self):
        await self._test_delete_and_split_at_cvs_to_new_impl(
            UsdGeom.Tokens.bezier, UsdGeom.Tokens.linear, UsdGeom.Tokens.constant
        )

    async def test_delete_and_split_at_cvs_to_new_linear_varying(self):
        await self._test_delete_and_split_at_cvs_to_new_impl(
            UsdGeom.Tokens.bezier, UsdGeom.Tokens.linear, UsdGeom.Tokens.varying
        )

    async def _test_delete_and_split_at_cvs_to_new_impl(self, basis: str, curve_type: str, widths_interpolation: str):
        basis_curves = self._create_test_curves(basis, curve_type, UsdGeom.Tokens.nonperiodic, widths_interpolation)

        # delete and split the curve at these indices, it will break the current basis_curves into 5 basisCurves prims
        cv_dict = {basis_curves: [6, 19]}
        self._curve_edits.delete_and_split_anchor_cvs(cv_dict, True)

        expected_vertex_counts = {UsdGeom.Tokens.linear: [[6], [6, 6], [6]], UsdGeom.Tokens.cubic: [[4], [4, 4], [4]]}

        expected_points = {
            UsdGeom.Tokens.linear: [
                [(-5, 0, 0), (-5, 1, 0), (-4, 1, 0), (-4, 0, 0), (-4, -1, 0), (-3, -1, 0)],
                [
                    (-3, 1, 0),
                    (-2, 1, 0),
                    (-2, 0, 0),
                    (-2, -1, 0),
                    (-1, -1, 0),
                    (-1, 0, 0),
                    (1, 0, 0),
                    (1, -1, 0),
                    (2, -1, 0),
                    (2, 0, 0),
                    (2, 1, 0),
                    (3, 1, 0),
                ],
                [(3, -1, 0), (4, -1, 0), (4, 0, 0), (4, 1, 0), (5, 1, 0), (5, 0, 0)],
            ],
            UsdGeom.Tokens.cubic: [
                [(-5, 0, 0), (-5, 1, 0), (-4, 1, 0), (-4, 0, 0)],
                [
                    (-2, 0, 0),
                    (-2, -1, 0),
                    (-1, -1, 0),
                    (-1, 0, 0),
                    (1, 0, 0),
                    (1, -1, 0),
                    (2, -1, 0),
                    (2, 0, 0),
                ],
                [(4, 0, 0), (4, 1, 0), (5, 1, 0), (5, 0, 0)],
            ],
        }

        curve_type = basis_curves.GetTypeAttr().Get()
        widths_interpolation = basis_curves.GetWidthsInterpolation()
        expected_widths = []
        if widths_interpolation == UsdGeom.Tokens.constant:
            expected_widths = [[5], [5], [5]]
        elif curve_type == UsdGeom.Tokens.linear:
            expected_widths = [
                [1, 2, 3, 4, 5, 6],
                [8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19],
                [21, 22, 23, 24, 25, 26],
            ]
        elif widths_interpolation == UsdGeom.Tokens.vertex:
            expected_widths = [[1, 2, 3, 4], [10, 11, 12, 13, 14, 15, 16, 17], [23, 24, 25, 26]]
        elif widths_interpolation == UsdGeom.Tokens.varying:
            expected_widths = [[1, 2], [4, 5, 6, 7], [9, 10]]

        basis_curves_list = [basis_curves]
        for i in range(1, 3):
            split_basis_curves = UsdGeom.BasisCurves.Get(self._stage, f"/basis_curves_0{i}")
            self.assertTrue(split_basis_curves)
            basis_curves_list.append(split_basis_curves)

        vertex_counts = []
        points = []
        widths = []
        for basis_curves in basis_curves_list:
            vertex_counts.append(list(basis_curves.GetCurveVertexCountsAttr().Get()))
            points.append(list(basis_curves.GetPointsAttr().Get()))
            widths.append(list(basis_curves.GetWidthsAttr().Get()))

        def check_equal(generated: list[list], expected: list[list]):
            self.assertEqual(len(generated), len(expected))

            for i, gen in enumerate(generated):
                self.assertListEqual(gen, expected[i])

        check_equal(vertex_counts, expected_vertex_counts[curve_type])
        check_equal(points, expected_points[curve_type])

        if expected_widths:
            check_equal(widths, expected_widths)

    def _create_test_curves(
        self, basis: str, curve_type: str, wrap: str, widths_interpolation: str
    ) -> UsdGeom.BasisCurves:
        basis_curves: UsdGeom.BasisCurves = UsdGeom.BasisCurves.Define(self._stage, "/basis_curves")

        basis_curves.GetBasisAttr().Set(basis)
        basis_curves.GetTypeAttr().Set(curve_type)
        basis_curves.GetWrapAttr().Set(wrap)

        points = [
            # curve 0
            (-5, 0, 0),
            (-5, 1, 0),
            (-4, 1, 0),
            (-4, 0, 0),
            (-4, -1, 0),
            (-3, -1, 0),
            (-3, 0, 0),
            (-3, 1, 0),
            (-2, 1, 0),
            (-2, 0, 0),
            (-2, -1, 0),
            (-1, -1, 0),
            (-1, 0, 0),
            # curve 1
            (1, 0, 0),
            (1, -1, 0),
            (2, -1, 0),
            (2, 0, 0),
            (2, 1, 0),
            (3, 1, 0),
            (3, 0, 0),
            (3, -1, 0),
            (4, -1, 0),
            (4, 0, 0),
            (4, 1, 0),
            (5, 1, 0),
            (5, 0, 0),
        ]
        basis_curves.GetPointsAttr().Set(points)

        curve_vertex_counts = [13, 13]
        basis_curves.GetCurveVertexCountsAttr().Set(curve_vertex_counts)

        widths = []
        if widths_interpolation == UsdGeom.Tokens.constant:
            widths = [5]
        elif widths_interpolation == UsdGeom.Tokens.vertex or curve_type == UsdGeom.Tokens.linear:
            widths = [i for i in range(1, len(points) + 1)]  # [1, 2, 3, ... , 25, 26]
        elif widths_interpolation == UsdGeom.Tokens.varying:
            widths = [i for i in range(1, 11)]  # each curve has 5 anchor CV  # [1, 2, 3, ... , 9, 10]

        if widths:
            basis_curves.GetWidthsAttr().Set(widths)
            basis_curves.SetWidthsInterpolation(widths_interpolation)

        extent = UsdGeom.Boundable.ComputeExtentFromPlugins(basis_curves, Usd.TimeCode.Default())
        if extent is not None:
            basis_curves.GetExtentAttr().Set(extent)

        return basis_curves


class TestPeriodicFixUp(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._context = omni.usd.get_context()
        self._settings = carb.settings.get_settings()
        self._usd_scene_dir = CURRENT_PATH.absolute().resolve().joinpath("tests").joinpath("usd")
        self._curve_edits_context = BezierCurveEditsContextManager.get_context()
        self._curve_edits = self._curve_edits_context.curve_edits
        usd_path = self._usd_scene_dir.joinpath("test_scene_bad_periodic.usda")

        self._settings.set("/app/viewport/snapEnabled", False)
        self._settings.set(Constants.TRANSFORM_OP_SETTING, Constants.TRANSFORM_OP_SELECT)

        await self._context.open_stage_async(str(usd_path))
        self._stage = self._context.get_stage()

        self.assertIsNotNone(self._stage)

        self._basis_curves: UsdGeom.BasisCurves = UsdGeom.BasisCurves.Get(self._stage, CURVE_PATH)

        omni.kit.commands.execute(
            "EnableCurveEditing",
            curve_context=self._curve_edits_context.curve_edits.curve_context,
            paths=[CURVE_PATH],
            mode=CurveEditingModeType.DRAG,
        )

        # wait for begin edit event to propagate
        await omni.kit.app.get_app().next_update_async()

    def _compare_lists(self, data, expected):
        try:
            self.assertEqual(len(data), len(expected))
            for i in range(len(data)):
                self.assertTrue(Gf.IsClose(data[i], expected[i], 1e-1))
        except AssertionError as e:
            carb.log_error(f"{data} is not close to expected {expected}")
            raise e

    async def test_fixup_periodic_curve(self):
        points = self._basis_curves.GetPointsAttr().Get()
        expected = [
            (0, 0, 50),
            (-50, 0, 50),
            (-50, 0, 0),
            (-50, 0, -50),
            (-50, 0, -100),
            (50, 0, -100),
            (50, 0, -50),
            (50, 0, 0),
            (50, 0, 50),
            (0, 0, 50),
            (-50, 0, 50),
            (-50, 0, 0),
            (-50, 0, -50),
            (-50, 0, -100),
            (50, 0, -100),
            (50, 0, -50),
            (50, 0, 0),
            (50, 0, 50),
        ]
        self._compare_lists(points, expected)

        normals = self._basis_curves.GetNormalsAttr().Get()
        expected = [
            (1, 0, 0),
            (0, 1, 0),
            (0, 0, 1),
            (1, 0, 0),
            (0, 1, 0),
            (0, 0, 1),
            (1, 0, 0),
            (0, 1, 0),
            (0, 0, 1),
            (0, 1, 0),
            (0, 0, 1),
            (1, 0, 0),
            (0, 1, 0),
            (0, 0, 1),
            (1, 0, 0),
            (0, 1, 0),
            (0, 0, 1),
            (1, 0, 0),
        ]
        self._compare_lists(normals, expected)

        widths = self._basis_curves.GetWidthsAttr().Get()
        expected = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14, 15, 16, 17, 18]
        self._compare_lists(widths, expected)
