# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["TestMinibar"]

import carb.settings
import omni.kit.app
import omni.kit.collaboration.presence_layer as pl
import omni.kit.ui_test as ui_test
import omni.kit.usd.layers as layers
import omni.timeline
import omni.timeline.live_session
import omni.ui
import omni.usd
from omni.kit.ui_test.vec2 import Vec2
from omni.kit.usd.layers.tests.mock_utils import MockLiveSyncingApi, _mock_logged_user_id, _mock_logged_user_name
from omni.kit.viewport.utility import get_active_viewport_and_window
from omni.ui.tests.test_base import OmniUiTest
from pxr import Sdf, Usd

from ..live_session import TimelineLiveSession
from ..minibar_scene import (
    MINIBAR_SCALE_WITH_NAVBAR,
    MINIBAR_VISIBLE_PATH,
    MODAL_TOOL_ACTIVE_PATH,
    NAVBAR_WIDTH_PATH,
    TOOL_OFFSET_SETTINGS_PATH,
)
from ..style import MINIBAR_MAX_WIDTH, MINIBAR_MIN_WIDTH, MINIBAR_WIDTH


class TestMinibar(OmniUiTest):
    async def setUp(self):
        self._context = omni.usd.get_context()
        self._layers = layers.get_layers(self._context)
        self._live_syncing = self._layers.get_live_syncing()
        await self._context.new_stage_async()

    async def tearDown(self):
        self._live_syncing.stop_all_live_sessions()
        self._layers.get_event_stream().pump()

        if self._context.get_stage():
            await self._context.close_stage_async()

        await self._wait()

    async def test_general(self):
        # init timeline
        timeline = omni.timeline.get_timeline_interface()
        timeline.set_start_time(0)
        timeline.set_end_time(2)
        timeline.set_current_time(0)
        await ui_test.human_delay(10)

        fps = timeline.get_time_codes_per_seconds()

        # show minibar
        center = Vec2(400, 750)
        await ui_test.emulate_mouse_move(center)

        # play
        self._api, self._window = get_active_viewport_and_window()
        play_button = ui_test.find(f"{self._window.name}//Frame/**/ToolButton[*].name=='play'")
        self.assertIsNotNone(play_button)
        await play_button.click()

        # wait until end time plus a few more frames, pause
        end_time = timeline.get_end_time()
        frames = int(end_time * fps + 10)
        await ui_test.human_delay(frames)
        await play_button.click()

        # check time loo.ped
        current_time = timeline.get_current_time()
        self.assertNotEqual(current_time, end_time)
        start_time = timeline.get_start_time()
        self.assertNotEqual(current_time, start_time)

        # turn loop off
        loop_button = ui_test.find(f"{self._window.name}//Frame/**/ToolButton[*].name=='loop'")
        self.assertIsNotNone(loop_button)
        await loop_button.click()

        # play again, verify time is not looping
        await play_button.click()
        await ui_test.human_delay(frames)
        current_time = timeline.get_current_time()
        self.assertEqual(current_time, end_time)

        timeline.set_current_time(0)

        start_widget = ui_test.find(f"{self._window.name}//Frame/**/IntField[*].identifier=='startwidget'")
        self.assertIsNotNone(start_widget)
        timeline.set_start_time(0)
        await ui_test.human_delay(10)
        start_time = timeline.get_start_time()
        self.assertEqual(start_time, 0)
        await start_widget.input("42")
        await ui_test.human_delay(10)
        start_time = timeline.get_start_time()
        self.assertEqual(start_time, 42.0 / fps)
        timeline.set_start_time(0)
        await ui_test.human_delay(10)
        start_time = timeline.get_start_time()
        self.assertEqual(start_time, 0)

        end_widget = ui_test.find(f"{self._window.name}//Frame/**/IntField[*].identifier=='endwidget'")
        self.assertIsNotNone(end_widget)
        timeline.set_end_time(100)
        await ui_test.human_delay(10)
        end_time = timeline.get_end_time()
        self.assertEqual(end_time, 100)
        await ui_test.human_delay(10)
        await end_widget.focus()
        await ui_test.human_delay(10)
        await ui_test.emulate_key_combo("CTRL+A")
        await ui_test.human_delay(10)
        await end_widget.input("42")
        await ui_test.human_delay(10)
        end_time = timeline.get_end_time()
        self.assertEqual(end_time, 42.0 / fps)
        timeline.set_end_time(10)
        await ui_test.human_delay(10)
        end_time = timeline.get_end_time()
        self.assertEqual(end_time, 10)

    async def test_auto_scale(self):
        # init timeline
        timeline = omni.timeline.get_timeline_interface()
        timeline.set_start_time(0)
        timeline.set_end_time(2)
        timeline.set_current_time(0)
        await ui_test.human_delay(10)

        # show minibar
        center = Vec2(400, 750)
        await ui_test.emulate_mouse_move(center)

        self._api, self._window = get_active_viewport_and_window()
        frame = ui_test.find(f"{self._window.name}//Frame/**/ZStack[*].name=='timeline_minibar_frame'")

        # initial width
        default_width = MINIBAR_WIDTH
        self.assertAlmostEqual(frame._widget.width.value, default_width)

        settings = carb.settings.acquire_settings_interface()

        # auto-scale is off by default
        self.assertFalse(settings.get_as_bool(MINIBAR_SCALE_WITH_NAVBAR))

        # no scaling when setting is off
        new_width = (MINIBAR_MIN_WIDTH + MINIBAR_MAX_WIDTH) / 2
        settings.set(NAVBAR_WIDTH_PATH, new_width)
        self.assertAlmostEqual(frame._widget.width.value, default_width)

        # turn on auto-scaling => rescale immediately
        settings.set(MINIBAR_SCALE_WITH_NAVBAR, True)
        await ui_test.human_delay(10)
        frame = ui_test.find(f"{self._window.name}//Frame/**/ZStack[*].name=='timeline_minibar_frame'")
        self.assertAlmostEqual(frame._widget.width.value, new_width)

        # change the setting => rescale
        new_width = MINIBAR_MIN_WIDTH + 10
        settings.set(NAVBAR_WIDTH_PATH, new_width)
        await ui_test.human_delay(5)
        frame = ui_test.find(f"{self._window.name}//Frame/**/ZStack[*].name=='timeline_minibar_frame'")
        self.assertAlmostEqual(frame._widget.width.value, new_width)

        # min/max
        new_width = MINIBAR_MIN_WIDTH - 10
        settings.set(NAVBAR_WIDTH_PATH, new_width)
        await ui_test.human_delay(5)
        frame = ui_test.find(f"{self._window.name}//Frame/**/ZStack[*].name=='timeline_minibar_frame'")
        self.assertAlmostEqual(frame._widget.width.value, MINIBAR_MIN_WIDTH)

        new_width = MINIBAR_MAX_WIDTH + 10
        settings.set(NAVBAR_WIDTH_PATH, new_width)
        await ui_test.human_delay(5)
        frame = ui_test.find(f"{self._window.name}//Frame/**/ZStack[*].name=='timeline_minibar_frame'")
        self.assertAlmostEqual(frame._widget.width.value, MINIBAR_MAX_WIDTH)

        # turn off auto-scaling => changes no longer apply. set to min, but expect max (the old value)
        settings.set(MINIBAR_SCALE_WITH_NAVBAR, False)
        new_width = MINIBAR_MIN_WIDTH
        settings.set(NAVBAR_WIDTH_PATH, new_width)
        await ui_test.human_delay(5)
        frame = ui_test.find(f"{self._window.name}//Frame/**/ZStack[*].name=='timeline_minibar_frame'")
        self.assertAlmostEqual(frame._widget.width.value, MINIBAR_MAX_WIDTH)

    async def test_toolbar_push(self):
        # init timeline
        timeline = omni.timeline.get_timeline_interface()
        timeline.set_start_time(0)
        timeline.set_end_time(2)
        timeline.set_current_time(0)
        await ui_test.human_delay(10)

        settings = carb.settings.acquire_settings_interface()

        # Make sure setting is defined
        settings.set_default_int(TOOL_OFFSET_SETTINGS_PATH, 0)

        # Hide the minibar
        settings.set_bool(MINIBAR_VISIBLE_PATH, False)

        # Show, needs to raise the tool offset
        old_offset = settings.get(TOOL_OFFSET_SETTINGS_PATH)
        settings.set_bool(MINIBAR_VISIBLE_PATH, True)
        await ui_test.human_delay(10)
        new_offset = settings.get(TOOL_OFFSET_SETTINGS_PATH)
        self.assertLess(old_offset, new_offset)

        # Hide, offset should jump back
        settings.set_bool(MINIBAR_VISIBLE_PATH, False)
        await ui_test.human_delay(10)
        new_offset = settings.get(TOOL_OFFSET_SETTINGS_PATH)
        self.assertAlmostEqual(old_offset, new_offset)

    async def test_modal(self):
        # init timeline
        timeline = omni.timeline.get_timeline_interface()
        timeline.set_start_time(0)
        timeline.set_end_time(2)
        timeline.set_current_time(0)
        timeline.set_looping(True)
        await ui_test.human_delay(10)

        settings = carb.settings.acquire_settings_interface()

        # Show the minibar
        settings.set_bool(MINIBAR_VISIBLE_PATH, True)
        await ui_test.human_delay(10)

        # Turn on modal
        settings.set_bool(MODAL_TOOL_ACTIVE_PATH, True)
        await ui_test.human_delay(10)
        self.assertFalse(settings.get(MINIBAR_VISIBLE_PATH))

        # Pause the timeline when modal is turned on
        settings.set_bool(MODAL_TOOL_ACTIVE_PATH, False)
        await ui_test.human_delay(3)
        settings.set_bool(MINIBAR_VISIBLE_PATH, True)
        await ui_test.human_delay(10)
        timeline.play()
        await ui_test.human_delay(3)
        settings.set_bool(MODAL_TOOL_ACTIVE_PATH, True)
        await ui_test.human_delay(10)
        self.assertFalse(timeline.is_playing())

        timeline.stop()

    async def _wait(self, frames=10):
        for _ in range(frames):
            await omni.kit.app.get_app().next_update_async()

    async def _clean_up(self):
        self._stage = None
        self._fake_layer.Clear()

    async def _join_fake_session(self):
        stage_url = "omniverse://__faked_omniverse_server__/test/test.usd"
        self._fake_layer = Sdf.Layer.New(Sdf.FileFormat.FindByExtension(".usd"), stage_url)
        self._stage = Usd.Stage.Open(self._fake_layer)
        self._context = omni.usd.get_context()
        await self._context.attach_stage_async(self._stage)

        session = self._live_syncing.find_live_session_by_name(stage_url, "test")
        if not session:
            session = self._live_syncing.create_live_session("test", stage_url)

        self.assertTrue(session, "Failed to create live session.")
        self.assertTrue(self._live_syncing.join_live_session(session))
        await self._wait()
        self.assertTrue(self._live_syncing.is_in_live_session())

        presence_layer = pl.get_presence_layer_interface(self._context)
        self.assertIsNotNone(presence_layer)
        self.assertIsNotNone(presence_layer.get_shared_data_stage())
        await self._wait()

    def _validate_UI(
        self,
        bar_enabled: bool,
        presenter_widget_visible: bool,
        presenter_circle_color: int = 0xFFFF0000,
        presenter_short_name: str = "",
    ):
        # default UI
        _, window = get_active_viewport_and_window()
        minibar_widget = ui_test.find(f"{window.name}//Frame/**/HStack[*].identifier=='TimelineMiniBar'")
        self.assertIsNotNone(minibar_widget)
        self.assertEqual(minibar_widget.widget.enabled, bar_enabled)

        presenter_widget = ui_test.find(f"{window.name}//Frame/**/HStack[*].identifier=='presenter_widget'")
        self.assertIsNotNone(presenter_widget)
        self.assertEqual(presenter_widget.widget.visible, presenter_widget_visible)

        if not presenter_widget_visible:
            return

        presenter_circle = ui_test.find(f"{window.name}//Frame/**/Circle[*].tooltip=='presenter'")
        self.assertIsNotNone(presenter_circle)
        self.assertEqual(presenter_circle.widget.style["Circle"], {"background_color": presenter_circle_color})

        presenter_label = ui_test.find(f"{window.name}//Frame/**/Label[*].name=='short_name'")
        self.assertIsNotNone(presenter_label)
        self.assertEqual(presenter_label.widget.text, presenter_short_name)

    def _change_presenter(self, new_presenter: layers.LiveSessionUser):
        should_not_be_presenter_and_synced_called = False

        def should_not_be_presenter_and_synced(is_presenter: bool, is_synced: bool):
            self.assertFalse(is_presenter)
            self.assertTrue(is_synced)
            nonlocal should_not_be_presenter_and_synced_called
            should_not_be_presenter_and_synced_called = True

        self._timeline_live_session.register_status_changed_fn(should_not_be_presenter_and_synced)
        omni.timeline.live_session.get_session_state().add_users([new_presenter])
        omni.timeline.live_session.get_timeline_session().presenter = new_presenter
        self.assertFalse(self._timeline_live_session.am_i_presenter())
        self.assertEqual(self._timeline_live_session.get_presenter_user_name(), new_presenter.user_name)
        self.assertEqual(
            self._timeline_live_session.get_presenter_user_short_name(),
            layers.get_short_user_name(new_presenter.user_name),
        )
        self.assertEqual(
            self._timeline_live_session.get_presenter_user_color(), omni.ui.color(*new_presenter.user_color)
        )
        self.assertTrue(should_not_be_presenter_and_synced_called)

        # listener UI
        self._validate_UI(
            False, True, omni.ui.color(*new_presenter.user_color), layers.get_short_user_name(new_presenter.user_name)
        )

        # clean up state
        self._timeline_live_session.deregister_status_changed_fn(should_not_be_presenter_and_synced)

    def _toggle_sync(self, sync: bool, is_presenter: bool, current_presenter: layers.LiveSessionUser):
        should_be_presenter_and_check_synced_called = False

        def should_be_presenter_and_check_synced(is_presenter: bool, is_synced: bool):
            self.assertEqual(is_presenter, is_presenter)
            self.assertEqual(is_synced, sync)
            nonlocal should_be_presenter_and_check_synced_called
            should_be_presenter_and_check_synced_called = True

        self._timeline_live_session.register_status_changed_fn(should_be_presenter_and_check_synced)
        omni.timeline.live_session.get_timeline_session().enable_sync(sync)
        self.assertEqual(self._timeline_live_session.is_sync_enabled(), sync)
        self.assertTrue(should_be_presenter_and_check_synced_called)

        # presenter user circle will be displayed if myself is not the presenter
        is_listener = sync and not is_presenter
        self._validate_UI(
            is_presenter or not sync,
            is_listener,
            omni.ui.color(*current_presenter.user_color),
            layers.get_short_user_name(current_presenter.user_name),
        )

        # clean up state
        self._timeline_live_session.deregister_status_changed_fn(should_be_presenter_and_check_synced)

    @MockLiveSyncingApi
    async def test_live_session(self):
        self._timeline_live_session = TimelineLiveSession()
        self.assertFalse(self._timeline_live_session.am_i_presenter())
        self.assertFalse(self._timeline_live_session.is_sync_enabled())
        self.assertEqual(self._timeline_live_session.get_presenter_user_name(), "")
        self.assertEqual(self._timeline_live_session.get_presenter_user_short_name(), "")
        self.assertEqual(self._timeline_live_session.get_presenter_user_color(), omni.ui.color("#000000"))

        # default UI
        self._validate_UI(True, False)

        should_be_presenter_and_synced_called = False

        def should_be_presenter_and_synced(is_presenter: bool, is_synced: bool):
            self.assertTrue(is_presenter)
            self.assertTrue(is_synced)
            nonlocal should_be_presenter_and_synced_called
            should_be_presenter_and_synced_called = True

        self._timeline_live_session.register_status_changed_fn(should_be_presenter_and_synced)

        await self._join_fake_session()

        self.assertTrue(self._timeline_live_session.am_i_presenter())
        self.assertTrue(self._timeline_live_session.is_sync_enabled())
        self.assertTrue(should_be_presenter_and_synced_called)

        # presenter UI
        # presenter user circle will be displayed if myself is not the presenter
        self._validate_UI(True, False)

        # deregister before changing state so assertion won't fail
        self._timeline_live_session.deregister_status_changed_fn(should_be_presenter_and_synced)

        # toggle sync if myself is the presetner
        presenter = layers.LiveSessionUser(
            _mock_logged_user_name, _mock_logged_user_id, "omni.kit.timeline.minibar_test"
        )
        self._toggle_sync(False, True, presenter)
        self._toggle_sync(True, True, presenter)
        self._toggle_sync(False, True, presenter)
        self._toggle_sync(True, True, presenter)

        # change presenter
        current_presenter = layers.LiveSessionUser(
            "new_presenter_name", "new_presenter_id", "omni.kit.timeline.minibar_test"
        )
        self._change_presenter(current_presenter)

        # change presenter 2
        current_presenter = layers.LiveSessionUser(
            "new_presenter_name_2", "new_presenter_id_2", "omni.kit.timeline.minibar_test"
        )
        self._change_presenter(current_presenter)

        # toggle sync if myself is not the presetner
        self._toggle_sync(False, False, current_presenter)
        self._toggle_sync(True, False, current_presenter)
        self._toggle_sync(False, False, current_presenter)
        self._toggle_sync(True, False, current_presenter)

        # change presenter back to the owner
        self._timeline_live_session.register_status_changed_fn(should_be_presenter_and_synced)
        omni.timeline.live_session.get_timeline_session().presenter = presenter
        self.assertTrue(self._timeline_live_session.am_i_presenter())
        presenter_name = presenter.user_name
        self.assertEqual(self._timeline_live_session.get_presenter_user_name(), presenter_name)
        self.assertEqual(
            self._timeline_live_session.get_presenter_user_short_name(), layers.get_short_user_name(presenter_name)
        )
        self.assertEqual(self._timeline_live_session.get_presenter_user_color(), omni.ui.color(*presenter.user_color))
        self.assertTrue(should_be_presenter_and_synced_called)

        # presenter UI
        # presenter user circle will be displayed if myself is not the presenter
        self._validate_UI(True, False, current_presenter)

        self._timeline_live_session.deregister_status_changed_fn(should_be_presenter_and_synced)

        # change presenter 3
        current_presenter = layers.LiveSessionUser(
            "new_presenter_name_3", "new_presenter_id_3", "omni.kit.timeline.minibar_test"
        )
        self._change_presenter(current_presenter)

        # This test cannot proceed until the bug in MockLiveSyncingApi is resolved.
        self._timeline_live_session.register_status_changed_fn(
            lambda is_presenter, is_synced: (self.assertFalse(is_presenter), self.assertFalse(is_synced))
        )
        await self._clean_up()
