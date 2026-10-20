# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from pathlib import Path

import omni.kit.ui_test as ui_test
from omni.kit.viewport.utility.camera_state import ViewportCameraState

from ..common import (
    MeasureMode,
)
from .test_util import PRIM_PATHS, TestMeasureBase, select_test_objects

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH


class TestMeasureFrame(TestMeasureBase):
    async def setUp(self):
        await super().setUp()

        self._extension._show_window(None, True)
        await ui_test.human_delay(8)

    async def tearDown(self):
        self._extension._show_window(None, False)
        await super().tearDown()
        await ui_test.human_delay(8)

    async def test_frame(self):
        # Select objects and test to be sure both objects are selected
        select_test_objects(PRIM_PATHS)
        await ui_test.wait_n_updates(10)

        selection = self._ctx.get_selection()
        self.assertEqual(len(selection.get_selected_prim_paths()), 2)

        ### Run the measure tool, simulating the button press in the UI [CENTER]
        await ui_test.human_delay(5)
        self._extension._measure_panel._pn_global._on_measure_selected()
        await ui_test.human_delay(5)

        # Ensure the measurement was created by checking the Measurement Manager
        from ..manager import MeasurementManager

        measurements = MeasurementManager()._model.get_items()
        self.assertEqual(len(measurements), 1)
        measure_prim = measurements[0]
        self.assertEqual(
            measure_prim.payload.tool_mode,
            MeasureMode.SELECTED,
            "Failed to find Measurement with mode SELECTED after creation!",
        )

        # Get Active Viewport Camera
        camera_state = ViewportCameraState()

        # Capture the midpoint vector of the measurement
        self.assertTrue(len(measure_prim.payload.computed_points) == 2)
        pt_a, pt_b = measure_prim.payload.computed_points[:2]
        midpoint = (pt_a + pt_b) / 2

        # Compute the length of the camera vector to midpoint pre-frame
        pre_pt_a_length = (camera_state.position_world - pt_a).GetLength()
        pre_pt_b_length = (camera_state.position_world - pt_b).GetLength()
        pre_frame_length = (camera_state.position_world - midpoint).GetLength()

        # Frame Selection, Hide Selection, Hide All
        uuid = measure_prim.payload.uuid
        MeasurementManager().frame_measurement(uuid)
        self._extension._show_window(None, False)
        await ui_test.human_delay(5)

        post_pt_a_length = (camera_state.position_world - pt_a).GetLength()
        post_pt_b_length = (camera_state.position_world - pt_b).GetLength()
        post_frame_length = (camera_state.position_world - midpoint).GetLength()

        # Compare all point lengths to ensure we're framed closer than the original measurement view
        self.assertTrue(pre_pt_a_length > post_pt_a_length)
        self.assertTrue(pre_pt_b_length > post_pt_b_length)
        self.assertTrue(pre_frame_length > post_frame_length)
