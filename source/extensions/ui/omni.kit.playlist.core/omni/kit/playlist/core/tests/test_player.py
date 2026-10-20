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
from omni.kit.playlist.core import (
    PlaylistCard,
    PlaylistModel,
    PlaylistPlayer,
    PlayMode,
    SystemPlaylistModel,
    enum_playlist_cards,
)
from omni.kit.test_suite.helpers import wait_stage_loading
from omni.kit.viewport.utility import get_active_viewport

EXTENSION_FOLDER_PATH = Path(omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__))
TEST_DATA_PATH = EXTENSION_FOLDER_PATH.joinpath("data/tests/stage")


class TestPlayer(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._context = omni.usd.get_context()

        await self._context.open_stage_async(f"{TEST_DATA_PATH}/playlist.usd")
        await wait_stage_loading()

    # After running each test
    async def tearDown(self):
        pass

    async def test_system_playlist_model_with_cut_play(self):
        model = SystemPlaylistModel("All Cameras", PlaylistCard.CAMERA)
        self.assertEqual(model.name, "All Cameras")
        self.assertEqual(model.camera_type, PlaylistCard.CAMERA)
        self.assertEqual(model.transition_type, PlayMode.TRANSITION_CUT)
        self.assertEqual(model.transition_time, 5)
        model.transition_time = 1
        self.assertEqual(model.item_time, 5)
        model.item_time = 0.5
        self.assertTrue(model.system)
        self.assertFalse(model.can_change)
        self.assertFalse(model.auto_save)
        attrs = model.attributes
        self.assertEqual(attrs[0], ["Author", "System"])
        items = model.get_item_children(None)
        self.assertEqual(len(items), 0)

        model.check_update()
        items = model.get_item_children(None)
        self.assertEqual(len(items), 4)

        self.assertIsNone(model.selection)

        # Play
        player = PlaylistPlayer.create(model, 0, self._on_started, self._on_stopped, self._on_playing)
        self.assertIsNotNone(player)
        succ = player.play()
        self.assertTrue(succ)

        while not self.__stopped:
            await omni.kit.app.get_app().next_update_async()

        player.destroy()
        player = None

        # Selection and previous/next
        model.selection = items[0]
        self.assertEqual(model.selection, items[0])

        model.selection = None
        self.assertEqual(model.index_model.as_int, -1)

        index = model.previous()
        self.assertEqual(index, 3)

        for _ in range(4):
            saved_index = model.index_model.as_int
            index = model.previous()
            self.assertEqual(index, (saved_index + 3) % 4)

        model.selection = None
        index = model.next()
        self.assertEqual(index, 0)
        for _ in range(4):
            saved_index = model.index_model.as_int
            index = model.next()
            self.assertEqual(index, (saved_index + 1) % 4)

        # Drag and drop
        self.assertEqual(model.get_drag_mime_data(items[0]), "Camera")
        self.assertTrue(model.drop_accepted(None, items[0], drop_location=0))
        self.assertFalse(model.drop_accepted(None, "/World/Camera1", drop_location=0))
        self.assertFalse(model.drop_accepted(None, 1))

        dropped_item = items[0]
        next_item = items[1]
        model.drop(None, dropped_item, drop_location=3)
        new_items = model.get_item_children(None)
        self.assertEqual(new_items[0], next_item)
        self.assertEqual(new_items[2], dropped_item)

        # remove item
        model.remove_item(items[-1])
        items = model.get_item_children(None)
        self.assertEqual(len(items), 3)
        model.remove_item(0)
        items = model.get_item_children(None)
        self.assertEqual(len(items), 2)

    async def test_general_playlist_with_smooth(self):
        # Create playlist model
        model = PlaylistModel("Test")
        model.name = "New"
        self.assertEqual(model.name, "New")

        model.transition_type = PlayMode.TRANSITION_SMOOTH
        model.transition_time = 1
        model.item_time = 0.5
        self.assertFalse(model.system)
        self.assertTrue(model.can_change)
        items = model.get_item_children(None)
        self.assertEqual(len(items), 0)

        # Load playlist cards from stage camera prims
        cards = enum_playlist_cards()
        self.assertEqual(len(cards), 4)
        self.assertEqual(cards[0].camera_prim.GetPath().pathString, "/World/Camera")
        self.assertEqual(cards[0].menu_text, "Cameras")
        self.assertIsNotNone(cards[0].icon)

        vp = get_active_viewport()
        cards[0].active()
        self.assertEqual(vp.camera_path, cards[0].path)

        # Add cards to model
        for card in cards:
            model.insert_item(card)

        items = model.get_item_children(None)
        self.assertEqual(len(items), 4)

        items[1].active()
        self.assertEqual(vp.camera_path, cards[1].path)

        # Play
        player = PlaylistPlayer.create(model, 0, self._on_started, self._on_stopped, self._on_playing)
        self.assertIsNotNone(player)
        succ = player.play()
        self.assertTrue(succ)
        while not self.__stopped:
            await omni.kit.app.get_app().next_update_async()

        player.destroy()
        player = None

    async def test_playlist_card_register_type(self):

        class TestCard(PlaylistCard):
            @classmethod
            def accept(cls, camera_path: str) -> bool:
                return "Cone" in camera_path

        stage = self._context.get_stage()
        prim = stage.GetPrimAtPath("/World/Cone")
        card = PlaylistCard.create(camera_prim=prim)

        # Register new type
        self.assertIsNone(card)
        succ = PlaylistCard.register("TestType", TestCard)
        self.assertTrue(succ)
        succ = PlaylistCard.register("TestType", TestCard)
        self.assertFalse(succ)

        # Create card with new type
        card = PlaylistCard.create(camera_prim=prim)
        self.assertIsNotNone(card)
        self.assertTrue(isinstance(card, TestCard))

        # Deregister and create again
        PlaylistCard.deregister("TestType")
        card = PlaylistCard.create(camera_prim=prim)
        self.assertIsNone(card)

    def _on_started(self):
        self.__started = True
        self.__stopped = False

    def _on_stopped(self):
        self.__stopped = True
        self.__started = False

    def _on_playing(self, index):
        self.__playing_index = index
