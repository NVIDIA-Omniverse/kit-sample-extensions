# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

# NOTE:
#   omni.kit.test - std python's unittest module with additional wrapping to add suport for async/await tests
#   For most things refer to unittest docs: https://docs.python.org/3/library/unittest.html
import carb.settings
import omni.kit.app

# Import extension python module we are testing with absolute import path, as if we are external user (other extension)
import omni.kit.markup.playlist
import omni.kit.test
from carb.eventdispatcher import get_eventdispatcher
from omni.kit import ui_test
from omni.kit.markup.core import get_instance as get_markup_instance
from omni.kit.markup.playlist import extension
from omni.kit.playlist.core import get_play_manager
from omni.ui.tests.test_base import OmniUiTest

SETTING_PLAY_NEXT_ENABLED = "/app/markup/playlist/next/enabled"
SETTING_PLAY_PREVIOUS_ENABLED = "/app/markup/playlist/previous/enabled"
SETTING_PLAY_PLAY_ENABLED = "/app/markup/playlist/play/enabled"
SETTING_PLAY_PLAYING = "/app/markup/playlist/playing"


class TestMarkupToolExtension(OmniUiTest):
    async def test_extension(self):
        manager = omni.kit.app.get_app().get_extension_manager()
        ext_id = "omni.kit.markup.playlist"
        self.assertTrue(ext_id)
        self.assertTrue(manager.is_extension_enabled(ext_id))
        manager.set_extension_enabled(ext_id, False)
        await ui_test.human_delay()
        self.assertTrue(not manager.is_extension_enabled(ext_id))
        manager.set_extension_enabled(ext_id, True)
        await ui_test.human_delay()
        self.assertTrue(manager.is_extension_enabled(ext_id))

        self.assertTrue(isinstance(extension.get_instance(), extension.PlaylistMarkupExtension))


class TestPlaylistModel(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._context = omni.usd.get_context()
        await self._context.new_stage_async()
        pass

    # After running each test
    async def tearDown(self):
        pass

    async def test_general(self):
        model = omni.kit.markup.playlist.AllMarkupPlaylistModel()
        self.assertTrue(model.system)
        self.assertTrue(model.name, "All Markups")
        self.assertEqual(len(model.items), 0)

        get_markup_instance().create_markup()
        await ui_test.human_delay(10)
        markups = list(get_markup_instance().get_markups())
        self.assertGreater(len(markups), 0, "create_markup should add a markup")
        m = markups[0]
        get_markup_instance().end_edit_markup(m)
        await ui_test.human_delay(10)

        self.assertEqual(len(model.items), 1)

        get_markup_instance().delete_markup(m)
        await ui_test.human_delay(10)

        self.assertEqual(len(model.items), 0)


class TestPlayControl(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._context = omni.usd.get_context()
        self._settings = carb.settings.get_settings()
        await self._context.new_stage_async()
        pass

    # After running each test
    async def tearDown(self):
        # Stop any in-flight playback so the play_manager's update timer
        # doesn't leak into the next test and trip on a drained item list.
        get_play_manager().stop()
        await ui_test.human_delay(10)

    async def test_event_callbacks(self):

        # create 4 markups:
        get_markup_instance().create_markup()
        get_markup_instance().create_markup()
        get_markup_instance().create_markup()
        get_markup_instance().create_markup()
        m = list(get_markup_instance().get_markups())[-1]
        get_markup_instance().end_edit_markup(m)
        await ui_test.human_delay(10)

        MARKUP_PLAY_NEXT_EVENT = "markup.playlist.NEXT"
        MARKUP_PLAY_PREVIOUS_EVENT = "markup.playlist.PREVIOUS"
        MARKUP_PLAY_PLAY_EVENT = "markup.playlist.PLAY"
        MARKUP_PLAY_STOP_EVENT = "markup.playlist.STOP"

        play_manager = get_play_manager()
        self.assertEqual(play_manager.current_playlist, None)
        self.assertEqual(get_play_manager().is_playing, False)

        # send an event:
        get_eventdispatcher().dispatch_event(MARKUP_PLAY_NEXT_EVENT, {})

        await ui_test.human_delay(10)
        self.assertTrue(isinstance(play_manager.current_playlist, omni.kit.markup.playlist.AllMarkupPlaylistModel))
        self.assertEqual(get_play_manager().is_playing, False)
        self.assertEqual(play_manager.current_playlist.index_model.as_int, 0)

        get_eventdispatcher().dispatch_event(MARKUP_PLAY_PREVIOUS_EVENT, {})

        await ui_test.human_delay(10)
        self.assertEqual(get_play_manager().is_playing, False)
        self.assertEqual(play_manager.current_playlist.index_model.as_int, 3)

        get_eventdispatcher().dispatch_event(MARKUP_PLAY_PLAY_EVENT, {})
        await ui_test.human_delay(10)
        self.assertEqual(get_play_manager().is_playing, True)

        self.assertEqual(self._settings.get(SETTING_PLAY_NEXT_ENABLED), False)
        self.assertEqual(self._settings.get(SETTING_PLAY_PREVIOUS_ENABLED), False)
        self.assertEqual(self._settings.get(SETTING_PLAY_PLAY_ENABLED), True)
        self.assertEqual(self._settings.get(SETTING_PLAY_PLAYING), True)

        get_eventdispatcher().dispatch_event(MARKUP_PLAY_STOP_EVENT, {})
        await ui_test.human_delay(10)
        self.assertEqual(get_play_manager().is_playing, False)

        self.assertEqual(self._settings.get(SETTING_PLAY_NEXT_ENABLED), True)
        self.assertEqual(self._settings.get(SETTING_PLAY_PREVIOUS_ENABLED), True)
        self.assertEqual(self._settings.get(SETTING_PLAY_PLAY_ENABLED), True)
        self.assertEqual(self._settings.get(SETTING_PLAY_PLAYING), False)

        # press play and press a bunch of buttons to excercise some code:
        get_eventdispatcher().dispatch_event(MARKUP_PLAY_PLAY_EVENT, {})

        await ui_test.human_delay(10)

        get_eventdispatcher().dispatch_event(MARKUP_PLAY_PLAY_EVENT, {})

        await ui_test.human_delay(10)

        get_eventdispatcher().dispatch_event(MARKUP_PLAY_NEXT_EVENT, {})

        await ui_test.human_delay(10)

        get_eventdispatcher().dispatch_event(MARKUP_PLAY_PREVIOUS_EVENT, {})

        await ui_test.human_delay(10)
