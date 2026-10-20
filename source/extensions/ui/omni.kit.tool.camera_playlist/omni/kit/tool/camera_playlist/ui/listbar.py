# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import re

import carb
from omni import ui
from omni.kit.playlist.core import get_play_manager
from omni.kit.widgets.custom import CustomWidgetComboBox, InputDialog, LabelDelegate, SimpleImageButton
from pxr import Sdf

from ..playlist_manager import PlaylistManager
from ..utils import get_icon_path

NAME_PADDING_X = 60


class PlaylistInputDialog(InputDialog):
    def __init__(self, title, on_ok_fn: callable, default_value, **kwargs):
        super().__init__(
            title,
            InputDialog.INPUT_TYPE_STRING,
            on_ok_fn,
            default_value=default_value,
            show_after_create=True,
            height=0,
            check_valid_fn=self._on_check_name,
            **kwargs,
        )

    def _on_check_name(self, name):
        name = name.replace(" ", "_")
        if Sdf.Path.IsValidPathString(name):
            return True
        else:
            carb.log_error(f"Invalid playlist name: {name}")
            return False


class ListBar:
    def __init__(self, on_playlist_changed_fn: callable):
        self._playlists_combobox = None

        self._build_ui()

        self._on_playlist_changed_fn = on_playlist_changed_fn
        self._playlist_manager = PlaylistManager.get_instance()
        self._sub_id = self._playlist_manager.subscribe_item_changed_fn(lambda m, i: self.reset())
        self._option_menu = None

        self._active_playlist_sub = get_play_manager().subscribe_playing_playlist_changed(
            self._on_active_playlist_changed
        )

    def destroy(self):  # pragma: no cover
        self._active_playlist_sub = None
        self._option_menu = None
        self._sub_id = None

    def reset(self, index=None):
        if not self._playlists_combobox:
            return
        self._playlists_combobox.reset(self._playlist_manager.playlists)
        if index is None:
            if self._playlists_combobox.values_count > 0:
                self._playlists_combobox.current_index = 0
            else:
                self._playlists_combobox.current_index = -1
        else:
            self._playlists_combobox.current_index = index

    def _build_ui(self):
        with ui.HStack(height=24):
            ui.Spacer(width=NAME_PADDING_X)
            self._playlists_combobox = CustomWidgetComboBox(
                -1,
                # height=26,
                item_delegate=LabelDelegate(),
                alignment=ui.Alignment.CENTER,
            )
            ui.Spacer(width=5)
            SimpleImageButton(get_icon_path("Options.svg"), 24, self._on_option)
            ui.Spacer(width=NAME_PADDING_X)

        self._playlists_combobox.model.add_item_changed_fn(self._on_current_playlist_changed)

    def _on_option(self):
        if self._option_menu is None:
            self._option_menu = ui.Menu(
                "Camera Playlist Option menu", name="this", menu_compatibility=False, tearable=False
            )
        self._option_menu.clear()

        def _menu_enabled():
            current_playlist = self._get_current_playlist()
            if current_playlist is None:
                return False
            else:
                return current_playlist.can_change

        with self._option_menu:
            ui.MenuItem("Rename Playlist", triggered_fn=self._on_rename_playlist, enabled=_menu_enabled())
            ui.MenuItem("Create New Playlist", triggered_fn=self.new_playlist)
            ui.MenuItem(
                "Duplicate Playlist",
                triggered_fn=self._on_clone_playlist,
                enabled=(self._get_current_playlist() is not None),
            )
            ui.MenuItem("Delete Current Playlist", triggered_fn=self._on_remove_playlist, enabled=_menu_enabled())

        self._option_menu.show()

    def new_playlist(self, on_playlist_created_fn=None):
        PlaylistInputDialog(
            "New Playlist",
            lambda new_name, fn=on_playlist_created_fn: self._on_new_playlist(new_name, on_created_fn=fn),
            self._get_default_playlist_name(),
        )

    def _get_current_playlist(self):
        if self._playlists_combobox.current_index < 0:
            return None
        else:
            return self._playlist_manager.get_playlist(self._playlists_combobox.current_index)

    def _get_default_playlist_name(self):
        return "My Playlist"

    def _on_new_playlist(self, name, on_created_fn=None):
        name = self._get_next_available_name(name)
        index = self._playlist_manager.append(name)
        if index >= 0:
            self.reset(index=index)

        if on_created_fn is not None:
            on_created_fn(index)

    def _get_next_available_name(self, name):
        # name = name.replace(" ", "_")

        def _increment_name(name):
            match = re.search(r"_(\d+)$", name)
            if match:
                new_num = int(match.group(1)) + 1
                ret = re.sub(r"_(\d+)$", str.format("_{:02d}", new_num), name)
            else:
                ret = name + "_01"
            return ret

        while name in self._playlist_manager.playlists:
            name = _increment_name(name)

        return name

    def _on_rename_playlist(self):
        playlist_name = self._get_current_playlist_name()
        if playlist_name is None:
            return
        else:
            PlaylistInputDialog(
                "Rename Playlist",
                lambda new_name, old_name=playlist_name: self._rename_playlist(new_name, old_name),
                playlist_name,
            )

    def _on_clone_playlist(self):
        playlist_name = self._get_current_playlist_name()

        PlaylistInputDialog(
            "New Playlist",
            lambda new_name: self._clone_playlist(new_name),
            self._get_next_available_name(playlist_name),
        )

    def _clone_playlist(self, name):
        name = self._get_next_available_name(name)
        index = self._playlist_manager.clone(name, self._playlists_combobox.current_index)
        if index >= 0:
            self.reset(index=index)

    def _on_remove_playlist(self):
        index = self._playlists_combobox.remove()
        self._playlist_manager.remove_playlist(index)

    def _get_current_playlist_name(self):
        current_playlist = self._get_current_playlist()
        return current_playlist.name if current_playlist is not None else None

    def _rename_playlist(self, new_name, old_name):
        playlist = self._get_current_playlist()
        self._playlist_manager.rename(playlist, new_name)
        self.reset(index=self._playlists_combobox.current_index)

    def _on_current_playlist_changed(self, model, item):
        playlist = self._get_current_playlist()
        if self._on_playlist_changed_fn:
            self._on_playlist_changed_fn(playlist)

    def _on_active_playlist_changed(self, active_playlist_name):
        if active_playlist_name:
            if active_playlist_name in self._playlists_combobox.values:
                index = self._playlists_combobox.values.index(active_playlist_name)
                if index != self._playlists_combobox.current_index:
                    self._playlists_combobox.current_index = index
