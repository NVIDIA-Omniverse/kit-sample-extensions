# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Tests for ``omni.usd.metrics.assembler.usdgeom``.

These tests reference a tiny on-disk USD layer authored in meters into a stage
authored in centimeters and verify that ``UsdGeomCamera`` scene-unit attributes
are scaled correctly by the Metrics Assembler. They reproduce the failure
mode reported in NVBugs 5494562 / OMPE-61911.
"""

import os

import omni.kit.test
from omni.metrics.assembler.core import get_metrics_assembler_interface
from pxr import Usd, UsdGeom, UsdPhysics, UsdUtils

EPSILON = 1e-3


def _data_path(file_name: str) -> str:
    """Return absolute path to a USDA file under this extension's data folder."""
    here = os.path.abspath(os.path.dirname(__file__))
    # tests/ -> python/ -> source/ -> ext root, then "data/tests/<file>"
    ext_root = os.path.normpath(os.path.join(here, "..", "..", ".."))
    candidate = os.path.normpath(os.path.join(ext_root, "data", "tests", file_name))
    if not os.path.exists(candidate):
        # fall-back: when installed as an extension we are mounted differently
        # and the data folder sits next to the python folder
        alt = os.path.normpath(os.path.join(here, "..", "..", "..", "..", "data", "tests", file_name))
        if os.path.exists(alt):
            return alt.replace("\\", "/")
        # last resort: search upwards
        cur = here
        for _ in range(8):
            cur = os.path.dirname(cur)
            test = os.path.join(cur, "data", "tests", file_name)
            if os.path.exists(test):
                return test.replace("\\", "/")
    return candidate.replace("\\", "/")


class MetricsAssemblerCameraTests(omni.kit.test.AsyncTestCase):
    """Verify that referencing a meters-units camera into a cm stage triggers
    correct unit conversion for scene-unit camera attributes."""

    def _make_cm_stage(self):
        stage = Usd.Stage.CreateInMemory()
        cache = UsdUtils.StageCache.Get()
        cache.Insert(stage)
        stage_id = cache.GetId(stage).ToLongInt()

        UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
        UsdGeom.SetStageMetersPerUnit(stage, 0.01)
        UsdPhysics.SetStageKilogramsPerUnit(stage, 1.0)
        return stage, stage_id

    def _add_camera_reference(self, stage, instance_path="/World/CameraInst"):
        path = _data_path("camera_meters.usda")
        xform = UsdGeom.Xform.Define(stage, instance_path)
        xform.GetPrim().GetReferences().AddReference(path)
        return path

    async def test_camera_focus_distance_scaled(self):
        """``focusDistance`` authored in meters must be scaled to cm on
        reference into a cm stage."""
        stage, stage_id = self._make_cm_stage()
        self._add_camera_reference(stage)

        cam = stage.GetPrimAtPath("/World/CameraInst/Camera")
        fd = cam.GetAttribute("focusDistance")
        # Source value (10 m) before resolve - the reference passes the value
        # through unchanged.
        self.assertAlmostEqual(fd.Get(), 10.0, delta=EPSILON)

        ok = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(ok)

        # After resolve_stage, 10 m must become 1000 cm.
        self.assertAlmostEqual(fd.Get(), 1000.0, delta=EPSILON)

    async def test_camera_clipping_range_scaled(self):
        """``clippingRange`` (Vec2 of near, far) must be scaled component-wise."""
        stage, stage_id = self._make_cm_stage()
        self._add_camera_reference(stage)

        cam = stage.GetPrimAtPath("/World/CameraInst/Camera")
        cr = cam.GetAttribute("clippingRange")
        before = cr.Get()
        self.assertAlmostEqual(before[0], 1.0, delta=EPSILON)
        self.assertAlmostEqual(before[1], 1000.0, delta=EPSILON)

        ok = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(ok)

        after = cr.Get()
        self.assertAlmostEqual(after[0], 100.0, delta=EPSILON)
        self.assertAlmostEqual(after[1], 100000.0, delta=EPSILON)

    async def test_camera_aperture_unchanged(self):
        """Aperture / focal length attributes use the USD 'tenths of stage
        unit' convention and should *not* be scaled by the rules registered
        here. Verifying them keeps the contract explicit so a future rule
        change does not silently break renderer FOV calculations."""
        stage, stage_id = self._make_cm_stage()
        self._add_camera_reference(stage)

        cam = stage.GetPrimAtPath("/World/CameraInst/Camera")
        fl = cam.GetAttribute("focalLength")
        ha = cam.GetAttribute("horizontalAperture")
        va = cam.GetAttribute("verticalAperture")

        ok = get_metrics_assembler_interface().resolve_stage(stage_id)
        self.assertTrue(ok)

        self.assertAlmostEqual(fl.Get(), 0.5, delta=EPSILON)
        self.assertAlmostEqual(ha.Get(), 0.36, delta=EPSILON)
        self.assertAlmostEqual(va.Get(), 0.24, delta=EPSILON)
