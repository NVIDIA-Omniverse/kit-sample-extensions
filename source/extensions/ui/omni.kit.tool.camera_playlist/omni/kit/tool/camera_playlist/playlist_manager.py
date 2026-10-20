# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Dict, List, Optional

import carb
import omni.ui as ui
from omni.kit.playlist.core import PlaylistCard, PlaylistModel, SystemPlaylistModel

from .playlist_usd import PlaylistUsd


class PlaylistManager(ui.AbstractItemModel):
    """A class for managing system and user playlists.

    This class provides methods to register, deregister, retrieve, append, clone, remove, and rename playlists. It supports both system and user playlists and integrates with the underlying USD mechanism to auto-save playlists when required. The class maintains a consistent order by sorting playlists based on their names, ensuring that the UI reflects the up-to-date state of playlists.

    The class offers a property to retrieve a list of playlist names and static access to a singleton instance, enabling centralized management of playlists throughout the session.
    """

    __INSTANCE__ = None

    __g_registered: List[SystemPlaylistModel] = []

    def __init__(self):
        self._playlist_usd = PlaylistUsd.get_instance()
        self._playlists: List[PlaylistModel] = []
        super().__init__()

        PlaylistManager.__INSTANCE__ = self

    @staticmethod
    def get_instance():
        """Returns the sole instance of PlaylistManager. If no instance exists, a new one is created.

        Returns:
            PlaylistManager: The current instance of PlaylistManager.
        """
        if PlaylistManager.__INSTANCE__ is None:
            PlaylistManager.__INSTANCE__ = PlaylistManager()
        return PlaylistManager.__INSTANCE__

    @property
    def playlists(self):
        """Gets the list of playlist names.

        Returns:
            List[str]: List of playlist names.
        """
        return [playlist.name for playlist in self._playlists]

    def destroy(self):
        """Destroys the PlaylistManager instance. Actual resource cleanup is not implemented."""
        pass

    def register(self, model: SystemPlaylistModel) -> bool:
        """Registers a system playlist model and appends it to playlists if successful.

        Args:
            model (SystemPlaylistModel): System playlist model to register.

        Returns:
            bool: False if the model is already registered; otherwise, registration result.
        """
        if model in PlaylistManager.__g_registered:
            return False

        PlaylistManager.__g_registered.append(model)
        self._playlists.append(model)
        self._sort_playlist()
        self._item_changed(None)
        carb.log_info(f"[Playlist] registered system playlist '{model.name}'")

    def deregister(self, model: SystemPlaylistModel):
        """Deregisters a system playlist model from registration and playlists.

        Args:
            model (SystemPlaylistModel): System playlist model to deregister.
        """
        if model in PlaylistManager.__g_registered:
            PlaylistManager.__g_registered.remove(model)
            if model in self._playlists:
                self._playlists.remove(model)
            self._item_changed(None)
            carb.log_info(f"[Playlist] deregistered system playlist '{model.name}'")

    def get_playlists(self, user_only: bool = False) -> List[str]:
        """Returns the list of playlist names, optionally filtering user-created playlists.

        Args:
            user_only (bool): When True, returns only non-system playlists.

        Returns:
            List[str]: List of playlist names, filtered by user_only if applicable.
        """
        if user_only:
            return [playlist.name for playlist in self._playlists if not playlist.system]
        else:
            return [playlist.name for playlist in self._playlists]

    def get_playlist(self, index, name=None) -> Optional[PlaylistModel]:
        """Returns a playlist model by index or by name if index is None.

        Args:
            index (Optional[int]): Playlist index; if None, lookup is based on name.
            name (Optional[str]): Playlist name used when index is None.

        Returns:
            Optional[PlaylistModel]: The playlist model if found, otherwise None.
        """
        if index is None:
            if name is None:
                return None
            if name not in self.playlists:
                return None
            index = self.playlists.index(name)
            return self._playlists[index]

        if index >= len(self._playlists):
            return None
        else:
            return self._playlists[index]

    def remove_playlist(self, index):
        """Removes a playlist at the given index, logging an error if index is out of range.

        Args:
            index (int): Index of the playlist to remove.
        """
        if index < 0 or index >= len(self._playlists):
            carb.log_error(f"[Playlist] Failed to remove playlist due to index {index} out of range")
        else:
            playlist = self._playlists[index]
            if playlist.auto_save:
                self._playlist_usd.remove_playlist(playlist)
            del self._playlists[index]

    def append(self, name):
        """Appends a new playlist with the given name if it does not exist.

        Args:
            name (str): Name of the playlist to append.

        Returns:
            int: Index of the new playlist, or -1 if the playlist already exists.
        """
        if name in self.playlists:
            carb.log_error(f"[Playlist] {name} already exists!")
            return -1

        playlist = self._create_playlist_model(name)
        self._add_playlist(playlist)

        if playlist.auto_save:
            self._playlist_usd.add_playlist(playlist)

        return self._playlists.index(playlist)

    def clone(self, name, index):
        """Clones an existing playlist to create a new playlist with a specified name.

        Args:
            name (str): Name for the new cloned playlist.
            index (int): Index of the playlist to clone.

        Returns:
            int: Index of the cloned playlist, or -1 if the name already exists.
        """
        if name in self.playlists:
            carb.log_error(f"[Playlist] {name} already exists!")
            return -1

        new_playlist = self._create_playlist_model(name)
        old_playlist = self._playlists[index]
        for item in old_playlist.get_item_children(None):
            new_playlist.insert_item(item.data, notify=False)

        self._add_playlist(new_playlist)

        if new_playlist.auto_save:
            self._playlist_usd.add_playlist(new_playlist)
        return len(self._playlists) - 1

    def rename(self, playlist: PlaylistModel, new_name: str):
        """Renames the specified playlist, updates its sort order, and saves the playlist if auto_save is enabled.

        Args:
            playlist (PlaylistModel): The playlist to rename.
            new_name (str): New name for the playlist.
        """
        playlist.name = new_name
        self._sort_playlist()
        if playlist.auto_save:
            self._playlist_usd.save_playlist(playlist)

    def load_from_usd(self, stage):
        """Loads playlists from USD stage data by clearing current playlists, loading playlists from PlaylistUsd paths, appending default system playlists, and sorting the list.

        Args:
            stage (object): Stage source for loading USD data.
        """
        self._playlists.clear()

        playlist_paths = self._playlist_usd.get_playlist_paths()
        for path in playlist_paths:
            name = path.split("/")[-1]
            if name == "__Navigation__":
                continue
            if name == "All Cameras" or name == "All Waypoints" or name == "All Markups":
                # When play system playlists, will create prim path. Here to filter since they will be append later.
                continue
            playlist = self._create_playlist_model(name, path=path)
            self._playlist_usd.load_playlist(playlist)
            self._playlists.append(playlist)

        # Append default playlists
        playlist_camera = SystemPlaylistModel("All Cameras", PlaylistCard.CAMERA)
        self._playlists.append(playlist_camera)

        self._playlists.extend(PlaylistManager.__g_registered)

        self._sort_playlist()
        carb.log_info(f"[Playlist]: Load playlists: {self.playlists}")

    def get_item_children(self, item=None):
        """Returns an empty list representing item children. Not used.

        Args:
            item (object): Input item parameter (unused).

        Returns:
            list: An empty list.
        """
        # Not used
        return []

    def get_item_value_model_count(self, item=None):
        """The number of columns.

        Args:
            item (object): Unused input parameter.

        Returns:
            int: Always 1, representing a single column.
        """
        return 1

    def get_item_value_model(self, item=None, column_id=0):
        """Retrieves the value model for the specified item and column. Always returns None.

        Args:
            item (object): The item for which the value model is requested (unused).
            column_id (int): Identifier for the target column.

        Returns:
            None: No value model available.
        """
        return None

    def _add_playlist(self, playlist: PlaylistModel):
        self._playlists.append(playlist)
        self._sort_playlist()

    def _sort_playlist(self):
        def sort_by_name(playlist):
            return playlist.name

        self._playlists.sort(key=sort_by_name)

    def _on_playlist_changed(self, playlist: PlaylistModel):
        if playlist.auto_save:
            self._playlist_usd.save_playlist(playlist)

    def _create_playlist_model(self, name: str, path: Optional[str] = None) -> PlaylistModel:
        return PlaylistModel(name, self._on_playlist_changed, path=path)
