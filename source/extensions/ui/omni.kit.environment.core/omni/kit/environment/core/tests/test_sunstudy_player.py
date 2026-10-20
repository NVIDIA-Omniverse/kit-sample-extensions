# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from pathlib import Path

import omni.kit.ui_test as ui_test
import omni.ui as ui
from omni.kit.environment.core import (
    CityComboBox,
    Clock,
    PlayButton,
    PlayLoopButton,
    PlayRateButton,
    get_sunstudy_player,
)
from omni.ui.tests.test_base import OmniUiTest

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")


def _golden_name(golden_img_dir: Path, name: str) -> str:
    """Golden image for this Kit: '<name>-111.0.png' where Kit 111 renders differently, else '<name>.png'."""
    import omni.kit.app

    stem = name[: -len(".png")]
    kit_version = float(omni.kit.app.get_app().get_kit_version_short())
    if kit_version >= 111.0 and golden_img_dir.joinpath(f"{stem}-111.0.png").exists():
        return f"{stem}-111.0.png"
    return name


class TestSunstudyPlayerWidget(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._sunstudy_player = get_sunstudy_player()

    # After running each test
    async def tearDown(self):
        self._sunstudy_player = None
        await super().tearDown()

    async def test_play_button(self):
        """Testing general look of play button"""
        window = await self.create_test_window(width=200, height=200)
        with window.frame:
            self._button = PlayButton(self._sunstudy_player)

        await ui_test.human_delay()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="play_button.png")

    async def test_loop_button(self):
        """Testing general look of loop button"""
        window = await self.create_test_window(width=200, height=200)
        with window.frame:
            self._button = PlayLoopButton()

        await ui_test.human_delay()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="loop_button.png")

    async def test_rate_button(self):
        """Testing general look of rate button"""
        window = await self.create_test_window(width=200, height=200)
        with window.frame:
            self._button = PlayRateButton()

        await ui_test.human_delay()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="rate_button.png")

    async def test_city_combobox(self):
        """Testing general look of city combobox"""
        window = await self.create_test_window(width=200, height=200, block_devices=False)
        with window.frame:
            self._button = CityComboBox()

        await ui_test.human_delay()
        await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(185, 15))
        await ui_test.human_delay()
        await self.finalize_test(
            golden_img_dir=self._golden_img_dir, golden_img_name=_golden_name(self._golden_img_dir, "city_combobox.png")
        )

    async def test_clock(self):
        """Testing general look of clock"""
        window = await self.create_test_window(width=200, height=60)
        time_model = ui.SimpleFloatModel(12.59)
        with window.frame:
            self._clock = Clock(time_model)

        await ui_test.human_delay()
        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="clock.png")

        self._clock._on_half_day_spin(0)
        hour, minute, second = self._clock._get_time(time_model)
        self.assertEqual(hour, 0)
        self._clock._on_hour_spin(-1)
        hour, minute, second = self._clock._get_time(time_model)
        self.assertEqual(hour, 23)
        self._clock._on_hour_spin(1)
        hour, minute, second = self._clock._get_time(time_model)
        self.assertEqual(hour, 0)
        self._clock._on_half_day_spin(0)
        hour, minute, second = self._clock._get_time(time_model)
        self.assertEqual(hour, 12)
        self._clock._on_minute_spin(1)
        hour, minute, second = self._clock._get_time(time_model)
        self.assertEqual(minute, 36)
        self._clock._on_minute_spin(-1)
        hour, minute, second = self._clock._get_time(time_model)
        self.assertEqual(minute, 35)
