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

import carb
import omni.kit.ui_test as ui_test
import omni.ui as ui
import omni.usd
from omni.kit.playlist.core import SystemPlaylistModel
from omni.kit.test import AsyncTestCase

from ..extension import get_instance
from ..playlist_manager import PlaylistManager
from ..playlist_usd import PlaylistUsd

CURRENT_PATH = Path(__file__).parent.joinpath("../../../../../data/tests").absolute().resolve()


class TestPlaylist(AsyncTestCase):
    async def setUp(self):
        ui.Workspace.show_window("Playlist")
        pass

    # After running each test
    async def tearDown(self):
        pass

    async def test_extension(self):
        ext_inst = get_instance()
        # playlist should start empty without a stage. Kit 111's viewport runtime opens a startup stage, which already
        # has the system "All Cameras" playlist.
        expected = 1 if omni.usd.get_context().get_stage() else 0
        self.assertEqual(expected, len(ext_inst.get_playlists(user_only=False)))

        # create new stage
        usd_context = omni.usd.get_context()
        await usd_context.new_stage_async()
        playlist_name = "All Cameras"
        self.assertEqual(ext_inst.get_playlists(user_only=False, active_first=True), [playlist_name])
        # should have a default Perspective camera now
        self.assertEqual(1, len(ext_inst.get_playlist(playlist_name).items))
        self.assertEqual("Perspective", ext_inst.get_playlist(playlist_name).items[0].data.name)

        # create another camera
        camera_path = "/camera_01"
        omni.kit.commands.execute("CreatePrimWithDefaultXform", prim_type="Camera", prim_path=camera_path)
        prim = usd_context.get_stage().GetPrimAtPath(camera_path)
        ext_inst.add_to_playlist(prim, playlist_name)
        await ui_test.wait_n_updates(10)
        # should have a default Perspective camera now
        self.assertEqual(2, len(ext_inst.get_playlist(playlist_name).items))
        camera_names = []
        for item in ext_inst.get_playlist(playlist_name).items:
            camera_names.append(item.data.name)

        # order should maintain the added order
        self.assertEqual(["Perspective", camera_path.lstrip("/")], camera_names)

    async def test_playlist_manager_load(self):
        source_file = CURRENT_PATH.joinpath("camera_playlist.usd")
        carb.log_warn(str(source_file))
        # add some randome data to make sure new file is different
        await omni.usd.get_context().open_stage_async(str(source_file))
        stage = omni.usd.get_context().get_stage()
        self.assertTrue(stage)
        self.assertIn("My Playlist", PlaylistManager.get_instance().playlists)
        await omni.usd.get_context().close_stage_async()

    async def test_playlist_manager_register(self):
        ext_inst = get_instance()
        manager = ext_inst._playlist_manager
        test_model = SystemPlaylistModel("foo", "bar")

        # test register
        manager.register(test_model)
        self.assertIn("foo", manager.playlists)
        # test register same model
        self.assertFalse(manager.register(test_model))
        # test deregister
        manager.deregister(test_model)
        self.assertNotIn("foo", manager.playlists)

    async def test_playlist_manager_actions(self):
        ext_inst = get_instance()
        manager = ext_inst._playlist_manager
        # test append
        index = manager.append("dummy")
        self.assertEqual("dummy", manager.get_playlists(user_only=True)[-1])

        # test rename
        manager.rename(manager.get_playlist(index), "foo")
        self.assertEqual("foo", manager.get_playlists(user_only=True)[-1])

        # test remove
        original_count = len(manager.playlists)
        manager.remove_playlist(original_count - 1)
        self.assertNotIn("foo", manager.playlists)
        self.assertEqual(original_count - 1, len(manager.playlists))

        # test clone
        manager.clone("cloned", 0)
        self.assertIn("cloned", manager.playlists)
        for item_orig, item_cloned in zip(manager.get_playlist(0).items, manager.get_playlist(None, "cloned").items):
            self.assertEqual(item_orig.data.name, item_cloned.data.name)
