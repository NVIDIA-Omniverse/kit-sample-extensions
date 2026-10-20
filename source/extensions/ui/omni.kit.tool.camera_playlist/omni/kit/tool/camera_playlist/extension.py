# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
from typing import Callable, List, Optional

import carb
import carb.input
import omni.ext
from omni import ui
from omni.kit.menu.utils import MenuItemDescription
from omni.kit.playlist.core import PLAYLISTS_ROOT, PlaylistModel
from pxr import Usd

from .playlist_manager import PlaylistManager
from .window import PlaylistWindow

EXTENSION_MENU_PATH = "Window/Playlist"
SETTING_ROOT = "/exts/omni.kit.tool.camera_playlist/"
SETTING_LOAD_AFTER_VISIBLE = SETTING_ROOT + "visible_after_startup"
g_singleton = None


# Any class derived from `omni.ext.IExt` in top level module (defined in `python.modules` of `extension.toml`) will be
# instantiated when extension gets enabled and `on_startup(ext_id)` will be called. Later when extension gets disabled
# on_shutdown() is called.
class PlaylistExtension(omni.ext.IExt):
    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    def on_startup(self, ext_id):
        self._play_list = Playlist()
        self._play_list.on_startup(ext_id)

    def on_shutdown(self):
        self._play_list.on_shutdown()


class Playlist:
    """A class for managing camera playlist UI and operations in omni.kit.tool.camera_playlist.

    This class provides methods to initialize and manage the playlist window and its associated menu items, toggle the visibility of the playlist interface, and handle user interactions within the camera playlist workflow. It also offers functions to retrieve the current list of playlists with the option to prioritize the active one, get a specific playlist model by name, add a camera prim to a designated playlist, and check if a given prim path corresponds to a playlist root.
    """

    def on_startup(self, ext_id):
        """Initializes playlist on extension startup; sets up playlist window, menu items, and playlist manager.

        Args:
            ext_id (str): Current extension id.
        """
        settings = carb.settings.get_settings()

        visible = settings.get_as_bool(SETTING_LOAD_AFTER_VISIBLE)
        self._playlist_window = PlaylistWindow(visible)
        self._playlist_window.set_visibility_changed_fn(self._on_visibility_changed)

        self._playlist_manager = PlaylistManager.get_instance()

        self._menu_list = [
            MenuItemDescription(
                name="Playlist",
                ticked=True,
                ticked_fn=self._on_tick,
                onclick_fn=self._on_click,
                hotkey=(carb.input.KEYBOARD_MODIFIER_FLAG_CONTROL, carb.input.KeyboardInput.P),
            )
        ]
        omni.kit.menu.utils.add_menu_items(self._menu_list, "Window", -1)

        global g_singleton
        g_singleton = self

    def on_shutdown(self):  # pragma: no cover
        """Cleans up playlist resources by removing menu items, destroying the playlist window, and releasing the playlist manager."""
        if self._menu_list is not None:
            omni.kit.menu.utils.remove_menu_items(self._menu_list, "Window")
            self._menu_list = None

        if self._playlist_window is not None:
            self._playlist_window.destroy()
            self._playlist_window = None
        self._playlist_manager.destroy()
        self._playlist_manager = None

        global g_singleton
        g_singleton = None

    def _on_tick(self):
        if self._playlist_window:
            return self._playlist_window.visible
        else:
            return False

    def _on_click(self, *args):
        self._playlist_window.visible = not self._playlist_window.visible

    def _on_visibility_changed(self, visible):

        async def _rebuild_menus():
            await omni.kit.app.get_app().next_update_async()
            omni.kit.menu.utils.rebuild_menus()

        asyncio.ensure_future(_rebuild_menus())

    def get_playlists(self, user_only: bool = True, active_first: bool = False) -> List[str]:
        """Retrieves a list of playlist names from the playlist manager, optionally placing the active playlist first.

        Args:
            user_only (bool): Retrieve user playlists only if True.
            active_first (bool): Place active playlist at the beginning if True.

        Returns:
            List[str]: List of playlist names.
        """
        playlist_names = self._playlist_manager.get_playlists(user_only=user_only)
        if active_first:
            active_playlist_name = self._playlist_window.currect_playlist_name
            if active_playlist_name in playlist_names:
                playlist_names.pop(playlist_names.index(active_playlist_name))
                playlist_names.insert(0, active_playlist_name)
        return playlist_names

    def get_playlist(self, name: str) -> Optional[PlaylistModel]:
        """Fetches a playlist model using the provided playlist name.

        Args:
            name (str): Name of the playlist to retrieve.

        Returns:
            Optional[PlaylistModel]: The playlist model corresponding to the name or None if not found.
        """
        return self._playlist_manager.get_playlist(None, name=name)

    def add_to_playlist(self, camera_prim: Optional[Usd.Prim], playlist_name: str):
        """Adds a camera prim to the specified playlist via the playlist window.

        Args:
            camera_prim (Optional[Usd.Prim]): Camera primitive to add to the playlist.
            playlist_name (str): Name of the playlist.
        """
        self._playlist_window.add_camera_to_playlist(camera_prim, playlist_name)

    def is_playlist_prim(self, prim_path):
        """Determines if the given prim path represents a playlist prim by checking its prefix.

        Args:
            prim_path (str): The prim path to evaluate.

        Returns:
            bool: True if the prim path starts with the playlist root; otherwise False.
        """
        return str(prim_path).startswith(PLAYLISTS_ROOT)


def get_instance():
    """Return the global Playlist instance for the extension omni.kit.tool.camera_playlist.

    Returns:
        Playlist: The active singleton Playlist instance if initialized, else None.
    """
    global g_singleton
    return g_singleton
