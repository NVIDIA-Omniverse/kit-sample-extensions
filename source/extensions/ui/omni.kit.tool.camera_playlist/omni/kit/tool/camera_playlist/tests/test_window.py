# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb
import omni.kit.ui_test as ui_test
import omni.ui as ui
import omni.usd
from omni.kit.test import AsyncTestCase
from omni.kit.viewport.utility import get_active_viewport
from omni.kit.widgets.custom import Dialog

from ..extension import get_instance
from ..playlist_manager import PlaylistManager
from ..playlist_usd import PlaylistUsd


class TestPlaylistWindow(AsyncTestCase):
    async def setUp(self):
        ui.Workspace.show_window("Playlist")

    # After running each test
    async def tearDown(self):
        pass

    @staticmethod
    def _find_button(icon_name):
        image_widgets = ui_test.find_all("Playlist//Frame/**/Image[*]")
        for wid in image_widgets:
            if wid.widget.source_url.endswith(icon_name):
                return wid
        return None

    @staticmethod
    def _find_input_dialog_button(dialog_name, accept=True):
        buttons = ui_test.find_all(f"[DIALOG#{Dialog._Dialog__dialog_counter-1} - {dialog_name}//Frame/**/Button[*]")
        if not buttons:
            return None
        return buttons[1 - int(accept)]

    async def _execute_playlist_command(self, command):
        options_button = self._find_button("Options.svg")
        self.assertIsNotNone(options_button)

        await options_button.click()
        await ui_test.select_context_menu(command)

    async def _add_default_playlist(self):
        await self._execute_playlist_command("Create New Playlist")
        button = self._find_input_dialog_button("New Playlist")
        self.assertIsNotNone(button)
        await button.click()

    async def test_add_playlist(self):
        manager = PlaylistManager.get_instance()

        usd_context = omni.usd.get_context()
        await usd_context.new_stage_async()

        self.assertNotIn("My Playlist", manager.playlists)

        await self._add_default_playlist()
        self.assertIn("My Playlist", manager.playlists)

        await self._add_default_playlist()
        self.assertIn("My Playlist_01", manager.playlists)

        await usd_context.close_stage_async()

    async def test_del_playlist(self):
        manager = PlaylistManager.get_instance()

        usd_context = omni.usd.get_context()
        await usd_context.new_stage_async()

        self.assertNotIn("My Playlist", manager.playlists)

        # test add
        await self._add_default_playlist()
        self.assertIn("My Playlist", manager.playlists)

        await self._execute_playlist_command("Delete Current Playlist")
        self.assertNotIn("My Playlist", manager.playlists)

        await usd_context.close_stage_async()

    async def test_clone_playlist(self):
        manager = PlaylistManager.get_instance()

        usd_context = omni.usd.get_context()
        await usd_context.new_stage_async()

        self.assertNotIn("My Playlist", manager.playlists)

        # test add
        await self._add_default_playlist()
        self.assertIn("My Playlist", manager.playlists)

        await self._execute_playlist_command("Duplicate Playlist")
        button = self._find_input_dialog_button("New Playlist")
        self.assertIsNotNone(button)
        await button.click()
        self.assertIn("My Playlist", manager.playlists)
        self.assertIn("My Playlist_01", manager.playlists)

        await usd_context.close_stage_async()

    async def test_rename_playlist(self):
        manager = PlaylistManager.get_instance()

        usd_context = omni.usd.get_context()
        await usd_context.new_stage_async()

        self.assertNotIn("My Playlist", manager.playlists)

        await self._add_default_playlist()
        self.assertIn("My Playlist", manager.playlists)

        await self._execute_playlist_command("Rename Playlist")
        str_field = ui_test.find(
            f"[DIALOG#{Dialog._Dialog__dialog_counter-1} - Rename Playlist//Frame/**/StringField[0]"
        )
        self.assertIsNotNone(str_field)
        str_field.model.set_value("a")
        button = self._find_input_dialog_button("Rename Playlist")
        self.assertIsNotNone(button)
        await button.click()

        self.assertNotIn("My Playlist", manager.playlists)
        self.assertIn("a", manager.playlists)

        await usd_context.close_stage_async()

    async def test_add_camera_to_creating_playlist(self):
        usd_context = omni.usd.get_context()
        await usd_context.new_stage_async()

        camera_path = "/camera"
        omni.kit.commands.execute("CreatePrimWithDefaultXform", prim_type="Camera", prim_path=camera_path)
        prim = usd_context.get_stage().GetPrimAtPath(camera_path)
        get_instance().add_to_playlist(prim, None)
        await ui_test.human_delay(10)
        button = self._find_input_dialog_button("New Playlist")
        self.assertIsNotNone(button)
        await button.click()
        self.assertIn("My Playlist", PlaylistManager.get_instance().playlists)

        await usd_context.close_stage_async()

    async def _click_menu_item(self, item, right_click=False):
        offset = ui_test.Vec2(5, 5)
        pos = ui_test.Vec2(item.screen_position_x, item.screen_position_y) + offset
        await ui_test.emulate_mouse_move(pos, 4)
        await ui_test.human_delay(4)
        await ui_test.emulate_mouse_click(right_click=right_click)
        await ui_test.human_delay(4)

    async def _execute_menu_path(self, path):
        curr = ui.Menu.get_current()
        for node in path.split("/"):
            self.assertIsNotNone(curr)
            menu_items = [i for i in ui.Inspector.get_children(curr) if isinstance(i, (ui.Menu, ui.MenuItem))]
            found = False
            for i in menu_items:
                if i.text == node:
                    curr = i
                    found = True
                    break
            self.assertTrue(found)
            await self._click_menu_item(curr)

    async def _add_camera_to_playlist(self, path):
        button = ui_test.find("Playlist//Frame/VStack[0]/**/Button[0]")
        await button.click()
        await ui_test.human_delay(4)
        await self._execute_menu_path(path)
        await ui_test.human_delay(4)

    def _get_current_name_string_list(self):
        return [item.name_model.as_string for item in get_instance()._playlist_window._playlist_view.items]

    async def test_add_camera_to_playlist(self):
        manager = PlaylistManager.get_instance()

        usd_context = omni.usd.get_context()
        await usd_context.new_stage_async()

        camera_path = "/camera"
        omni.kit.commands.execute("CreatePrimWithDefaultXform", prim_type="Camera", prim_path=camera_path)

        await self._add_default_playlist()
        self.assertIn("My Playlist", manager.playlists)

        await self._add_camera_to_playlist("Cameras/camera")

        names = self._get_current_name_string_list()
        self.assertIn("camera", names)

        await usd_context.close_stage_async()

    async def _setup_playlist_order_case(self):
        manager = PlaylistManager.get_instance()
        camera_path = "/camera"
        for i in range(3):
            path = camera_path + str(i)
            omni.kit.commands.execute("CreatePrimWithDefaultXform", prim_type="Camera", prim_path=path)
        await self._add_default_playlist()
        self.assertIn("My Playlist", manager.playlists)
        for i in range(3):
            await self._add_camera_to_playlist("Cameras/camera" + str(i))

        items = ui_test.find_all("Playlist//Frame/**/ScrollingFrame[0]/TreeView[0]/**/Label[0]")
        self.assertEqual(len(items), 3)

    async def _right_click_on_playlist_item(self, items, index, command):
        self.assertTrue(index < len(items))
        item = items[index]

        pos = ui_test.Vec2(item.center.x, item.center.y)
        await ui_test.emulate_mouse_move(pos, 4)
        await ui_test.human_delay(4)
        await ui_test.emulate_mouse_click(right_click=True)
        await ui_test.human_delay(4)

        root_menu = ui.Menu.get_current()
        menu_items = [i for i in ui.Inspector.get_children(root_menu) if isinstance(i, (ui.Menu, ui.MenuItem))]
        for menu_item in menu_items:
            if menu_item.text == command:
                await self._click_menu_item(menu_item)
                break

    async def test_playlist_send_item_to_start(self):
        usd_context = omni.usd.get_context()
        await usd_context.new_stage_async()
        await self._setup_playlist_order_case()

        items = ui_test.find_all("Playlist//Frame/**/ScrollingFrame[0]/TreeView[0]/**/Label[0]")
        expecting = ["camera" + str(i) for i in range(3)]
        self.assertEqual(self._get_current_name_string_list(), expecting)

        await self._right_click_on_playlist_item(items, 1, "Send to Start")
        await ui_test.human_delay(4)
        expecting[1], expecting[0] = expecting[0], expecting[1]
        self.assertEqual(self._get_current_name_string_list(), expecting)

        await usd_context.close_stage_async()

    async def test_playlist_send_item_to_end(self):
        usd_context = omni.usd.get_context()
        await usd_context.new_stage_async()
        await self._setup_playlist_order_case()

        items = ui_test.find_all("Playlist//Frame/**/ScrollingFrame[0]/TreeView[0]/**/Label[0]")
        expecting = ["camera" + str(i) for i in range(3)]
        self.assertEqual(self._get_current_name_string_list(), expecting)

        await self._right_click_on_playlist_item(items, 1, "Send to End")
        await ui_test.human_delay(4)
        expecting[-1], expecting[1] = expecting[1], expecting[-1]
        self.assertEqual(self._get_current_name_string_list(), expecting)

        await usd_context.close_stage_async()

    async def test_playlist_send_item_to_end(self):
        usd_context = omni.usd.get_context()
        await usd_context.new_stage_async()
        await self._setup_playlist_order_case()

        items = ui_test.find_all("Playlist//Frame/**/ScrollingFrame[0]/TreeView[0]/**/Label[0]")
        expecting = ["camera" + str(i) for i in range(3)]
        self.assertEqual(self._get_current_name_string_list(), expecting)

        await self._right_click_on_playlist_item(items, 1, "Remove Item")
        await ui_test.human_delay(4)
        expecting = [expecting[0], expecting[-1]]
        self.assertEqual(self._get_current_name_string_list(), expecting)

        await usd_context.close_stage_async()

    async def test_camera_item_updates_viewport_camera(self):
        ext_inst = get_instance()

        # create new stage
        usd_context = omni.usd.get_context()
        await usd_context.new_stage_async()
        playlist_name = "All Cameras"

        # create another camera
        camera_path = "/camera_01"
        omni.kit.commands.execute("CreatePrimWithDefaultXform", prim_type="Camera", prim_path=camera_path)
        prim = usd_context.get_stage().GetPrimAtPath(camera_path)
        ext_inst.add_to_playlist(prim, playlist_name)
        await ui_test.wait_n_updates(10)

        prev_button = self._find_button("StepBackward.svg")
        next_button = self._find_button("StepForward.svg")
        self.assertIsNotNone(prev_button)
        self.assertIsNotNone(next_button)

        # no default is selected, so when click next, should be the first item
        viewport_api = get_active_viewport()

        await next_button.click()
        persp_camera_path = viewport_api.camera_path.pathString
        self.assertTrue(persp_camera_path.endswith("Persp"))

        await next_button.click()
        self.assertEqual(viewport_api.camera_path.pathString, camera_path)

        await prev_button.click()
        self.assertTrue(persp_camera_path.endswith("Persp"))
        await usd_context.close_stage_async()
