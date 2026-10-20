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
import omni.usd

from ..common import (
    MeasureMode,
    MeasureState,
)
from .test_util import TestMeasureBase

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH


class TestMeasureStateMachine(TestMeasureBase):
    async def test_state_change(self):

        def sample_state_fn(state: MeasureState, mode: MeasureMode):
            return

        def sample_mode_fn(mode: MeasureMode):
            return

        from ..manager import StateMachine

        sm = StateMachine()
        self.assertIsNotNone(sm)

        curr_len = len(sm._on_state_changed_evt._event_subscribers)
        ts_id = sm.add_tool_state_changed_fn(sample_state_fn)
        self.assertEqual(len(sm._on_state_changed_evt._event_subscribers), curr_len + 1)

        curr_len = len(sm._on_create_evt._event_subscribers)
        tm_id = sm.add_on_create_mode_fn(sample_mode_fn)
        self.assertEqual(len(sm._on_create_evt._event_subscribers), curr_len + 1)

        curr_len = len(sm._on_edit_evt._event_subscribers)
        em_id = sm.add_on_edit_mode_fn(sample_mode_fn)
        self.assertEqual(len(sm._on_edit_evt._event_subscribers), curr_len + 1)

        sm.set_creation_state(MeasureMode.SELECTED)
        self.assertEqual(sm.tool_mode, MeasureMode.SELECTED)
        self.assertEqual(sm.tool_state, MeasureState.CREATE)

        sm.set_edit_state(MeasureMode.POINT_TO_POINT)
        self.assertEqual(sm.tool_mode, MeasureMode.POINT_TO_POINT)
        self.assertEqual(sm.tool_state, MeasureState.EDIT)

        sm.reset_state_to_default()
        self.assertEqual(sm.tool_state, MeasureState.NONE)
