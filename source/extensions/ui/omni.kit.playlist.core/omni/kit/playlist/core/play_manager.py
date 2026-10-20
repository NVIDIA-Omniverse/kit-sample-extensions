# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
"""This module defines a PlayManager class that manages playlist playback, navigation, and subscriber notifications, along with a PlaylistCardSubscriber helper for callback handling when playlist cards change."""

import asyncio
import weakref
from typing import Callable, List, Optional

import carb
import carb.settings
import omni.kit.app
import omni.ui as ui
from omni.kit.viewport.utility import get_active_viewport_camera_path

from .constant import PlayMode
from .player import PlaylistPlayer
from .playlist import CardItem, PlaylistModel
from .playlist_card import PlaylistCard


class PlaylistCardSubscriber:
    """Handler of subscription to a channel."""

    def __init__(self, on_changed_fn: Callable, play_manager: weakref) -> None:
        """
        Constructor. Internal only.

        Args:
            on_changed_fn (Callable[[PlaylistCard], None]): Callback when current playlist card changed.
            channel (weakref): Weak holder of channel.
        """

        self.__play_manager = play_manager
        self.__on_changed_fn = on_changed_fn

    def __del__(self):
        self.unsubscribe()

    def unsubscribe(self):
        """Stop subscribe."""

        self.__on_changed_fn = None
        if self.__play_manager and self.__play_manager():
            self.__play_manager()._remove_subscriber(self)

    def on_changed(self, card: PlaylistCard):
        if self.__on_changed_fn:
            self.__on_changed_fn(card)


class PlayManager:
    """Plays a playlist.

    Args:

        playlist (PlaylistModel): Playlist to play; default is None
    """

    def __init__(self, playlist: Optional[PlaylistModel] = None):
        """Initializes the PlayManager instance."""
        self.__player: Optional[PlaylistPlayer] = None
        self.__model: Optional[PlaylistModel] = playlist
        self._saved_selection = -1
        self.__sub_item_time_id = None
        self.__sub_transition_time_id = None
        self.__sub_index_id = None
        self.__navigation_model: Optional[PlaylistModel] = None
        self.__navigation_item: Optional[CardItem] = None

        # Model for name of current playing playlist
        self.current_playlist_name_model = ui.SimpleStringModel("")

        self._settings = carb.settings.get_settings()

        self._subscribers: List[PlaylistCardSubscriber] = []

    def destroy(self):
        """Destroys the current player and clears all associated resources and subscriptions."""
        if self.__player:
            self.__player.destroy()
            self.__player = None

        self.__sub_item_time_id = None
        self.__sub_transition_time_id = None
        self.__sub_index_id = None

    @property
    def is_playing(self) -> bool:
        """Gets the status if the playlist is playing.

        Returns:
            bool: True if a playlist is playing, otherwise False.
        """
        return self.current_playlist_name_model.as_string != ""

    @property
    def current_playlist(self) -> Optional[PlaylistModel]:
        """Gets the current playlist.

        Returns:
            Optional[PlaylistModel]: The currently assigned playlist.
        """
        return self.__model

    @current_playlist.setter
    def current_playlist(self, playlist: Optional[PlaylistModel]) -> None:
        """Sets the current playlist.

        Args:
            playlist (Optional[PlaylistModel]): The playlist to assign.
        """
        if self.__player:
            # Already playing, cannot bind new playlist
            carb.log_warn(f"'{self.current_playlist_name_model.as_string}' already in playing. Cannot assign new one.")
            return

        self.__model = playlist

        self.__sub_item_time_id = None
        self.__sub_transition_time_id = None
        self.__sub_index_id = None

        if not self.__model:
            return

        def __on_item_time_changed(model: ui.SimpleFloatModel):
            if self.__player:
                self.__player.set_time_per_item(model.as_float)

        self.__sub_item_time_id = self.__model.item_time_model.subscribe_value_changed_fn(__on_item_time_changed)

        def __on_transition_time_changed(model: ui.SimpleFloatModel):
            if self.__player:
                self.__player.set_transition_time(model.as_float)

        self.__sub_transition_time_id = self.__model.item_time_model.subscribe_value_changed_fn(
            __on_transition_time_changed
        )

        def __on_index_changed(model: ui.SimpleIntModel):
            if self.__model:
                index = model.as_int
                if index < 0 or index >= len(self.__model.items):
                    card = None
                else:
                    card = self.__model.items[index].data
                for subscriber in self._subscribers:
                    if subscriber():
                        subscriber().on_changed(card)

        self.__sub_index_id = self.__model.index_model.subscribe_value_changed_fn(__on_index_changed)

    @property
    def current_item(self) -> Optional[CardItem]:
        """Gets the current selected item from the playlist.

        Returns:
            Optional[CardItem]: The currently selected playlist card.
        """
        if self.__model:
            return self.__model.selection
        return None

    @current_item.setter
    def current_item(self, item: CardItem) -> None:
        """Sets the current item in the playlist.

        Args:
            item (CardItem): The playlist card item to select.
        """
        if self.__model:
            self.__model.selection = item

    def subscribe_playing_playlist_changed(self, on_playing_changed_fn: Callable[[str], None]):
        """Subscribes a callback for when the playing playlist changes.

        Args:
            on_playing_changed_fn (Callable[[str], None]): Callback triggered on playing playlist change.

        Returns:
            Object: Subscription handle for the playing playlist change.
        """
        return self.current_playlist_name_model.subscribe_value_changed_fn(lambda m: on_playing_changed_fn(m.as_string))

    def subscribe_current_playlist_item_changed(self, on_current_playlist_item_changed_fn: Callable):
        """Subscribes a callback for when the current playlist item changes.

        Args:
            on_current_playlist_item_changed_fn (Callable): Callback invoked when the current playlist item is updated.

        Returns:
            PlaylistCardSubscriber: Subscriber instance for the current playlist item change.
        """

        subscriber = PlaylistCardSubscriber(on_current_playlist_item_changed_fn, weakref.ref(self))
        self._subscribers.append(weakref.ref(subscriber))

        return subscriber

    def _remove_subscriber(self, subscriber: PlaylistCardSubscriber):
        to_be_removed = []
        for item in self._subscribers:
            if not item() or item() == subscriber:
                to_be_removed.append(item)

        for item in to_be_removed:
            self._subscribers.remove(item)

    def play(self, model: Optional[PlaylistModel] = None, navigation_mode: bool = False) -> bool:
        """Starts playback of the assigned playlist.

        Args:
            model (Optional[PlaylistModel]): Playlist model to play; default is current playlist.
            navigation_mode (bool): Indicates if navigation mode is active.

        Returns:
            bool: True if playback starts successfully, False otherwise.
        """
        if model is None:
            model = self.__model
        if self.__player:
            # Already playing
            return False
        elif not model:
            carb.log_warn("No playlist assigned!")
            return False
        elif len(model.items) == 0:
            carb.log_warn(f"'{model.name} is empty, cannot play!")
            return False

        self.current_playlist_name_model.set_value(model.name)
        if model.index_model.as_int < 0:
            model.index_model.set_value(0)

        start_index = model.index_model.as_int

        self.__player = PlaylistPlayer.create(
            model,
            start_index,
            self._on_started,
            self._on_stopped,
            None,
        )
        if self.__player:
            if not self.__player.play(navigation_mode=navigation_mode):
                self.current_playlist_name_model.set_value("")
                self.__player.destroy()
                self.__player = None
                return False
        return True

    def stop(self):
        """Stops the playlist playback if active."""
        if self.__player:
            self.__player.stop()
            self.__player = None

    def navigate(self, index: Optional[int] = None, item: Optional[CardItem] = None) -> bool:
        """Navigates to a specific item in the playlist.

        Args:
            index (Optional[int]): Index of the navigation item.
            item (Optional[CardItem]): Specific item to navigate to.

        Returns:
            bool: True if navigation is initiated successfully, otherwise False.
        """
        if not self.__model:
            return False
        if index is None and item is None:
            return False

        items = self.__model.get_item_children()
        if index is None:
            index = items.index(item)

        if self.__model.transition_type == PlayMode.TRANSITION_CUT:
            self.__model.index_model.set_value(index)
        else:

            async def __navigate_async(index):
                # If in playing, force to stop
                if self.__player:
                    self.__player.destroy()
                    self.__player = None
                    # Wait for _on_stopped triggered
                    await omni.kit.app.get_app().next_update_async()

                # Selected item but only active when navigation done
                self.__model.auto_active = False
                self.__model.index_model.set_value(index)

                # Create new model for navigation only with two items
                # First for active camera
                # Next for item to navigate
                self.__navigation_model = PlaylistModel(
                    "##Navigation##",
                    system=True,
                    transition_type=self.__model.transition_type,
                    transition_time=self.__model.transition_time,
                    item_time=0,
                )
                items = self.__model.get_item_children()
                active_camera = get_active_viewport_camera_path()
                if not active_camera:
                    self.__model.index_model.set_value(index)
                    return False
                card = PlaylistCard.create(PlaylistCard.CAMERA, name="Active Camera", path=active_camera.pathString)
                self.__navigation_model.insert_item(card)
                self.__navigation_model.insert_item(items[index].data)
                self.__navigation_item = items[index]

                # Start navigation
                if self.play(model=self.__navigation_model, navigation_mode=True):
                    return True
                else:
                    self.__navigation_model = None
                    self.__model.index_model.set_value(index)
                    return False

            asyncio.ensure_future(__navigate_async(index))
            return True

        return False

    def next(self) -> None:
        """Navigates tothe next item in the playlist."""
        if self.current_playlist_name_model.as_string == "":
            if self.__model:
                self.navigate(index=self.__model.next_index)

    def previous(self) -> None:
        """Navigates to the previous item in the playlist."""
        if self.current_playlist_name_model.as_string == "":
            if self.__model:
                self.navigate(index=self.__model.previous_index)

    def _on_started(self):
        # Save current selection
        self._saved_selection = self.__model.index_model.as_int

    def _on_stopped(self):
        if self.__player:
            self.__player.destroy()
            self.__player = None
        self.current_playlist_name_model.set_value("")

        if self.__navigation_model:
            # Update current playlist model when navigation done
            self.__navigation_model = None
            # Force active current item
            if self.__navigation_item:
                self.__navigation_item.active()
                self.__navigation_item = None
            self.__model.auto_active = True
