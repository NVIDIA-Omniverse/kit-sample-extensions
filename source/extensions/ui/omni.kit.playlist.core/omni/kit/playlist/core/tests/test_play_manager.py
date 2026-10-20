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

import omni.kit.app
import omni.usd
from omni.kit.playlist.core import PlaylistModel, PlayMode, enum_playlist_cards, get_play_manager
from omni.kit.test_suite.helpers import wait_stage_loading

EXTENSION_FOLDER_PATH = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
TEST_DATA_PATH = EXTENSION_FOLDER_PATH.joinpath("data/tests/stage")


class TestPlayManager(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._context = omni.usd.get_context()

        await self._context.open_stage_async(f"{TEST_DATA_PATH}/playlist.usd")
        await wait_stage_loading()

    # After running each test
    async def tearDown(self):
        pass

    async def test_play_manager(self):
        play_manager = get_play_manager()
        self.assertIsNone(play_manager.current_playlist, None)
        self.assertFalse(play_manager.is_playing)
        # Create playlist model
        model = PlaylistModel(
            "TestPlayManager", transition_type=PlayMode.TRANSITION_SMOOTH, transition_time=1, item_time=0.5
        )

        # Load playlist cards from stage camera prims
        cards = enum_playlist_cards()
        # Add cards to model
        for card in cards:
            model.insert_item(card)

        def _on_playing_model_changed(name):
            self.__playing_model = name

        def _on_playing_card(card):
            self.__playing_card = card

        sub_model = play_manager.subscribe_playing_playlist_changed(_on_playing_model_changed)
        sub = play_manager.subscribe_current_playlist_item_changed(_on_playing_card)
        play_manager.current_playlist = model
        self.assertIsNone(play_manager.current_item)

        # Play
        self.assertTrue(play_manager.play())

        await omni.kit.app.get_app().next_update_async()
        self.assertEqual(self.__playing_model, "TestPlayManager")

        while self.__playing_model != "":
            await omni.kit.app.get_app().next_update_async()
        play_manager.stop()

        play_manager.next()
        await omni.kit.app.get_app().next_update_async()
        while self.__playing_model != "":
            await omni.kit.app.get_app().next_update_async()

        play_manager.previous()
        await omni.kit.app.get_app().next_update_async()
        while self.__playing_model != "":
            await omni.kit.app.get_app().next_update_async()

        sub.unsubscribe()
