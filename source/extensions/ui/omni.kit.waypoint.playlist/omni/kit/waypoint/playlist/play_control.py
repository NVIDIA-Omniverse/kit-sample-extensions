# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Optional

import carb.eventdispatcher
import carb.events
import carb.settings
import omni.kit.app
import omni.ui as ui
from omni.kit.playlist.core import PlaylistModel, get_play_manager

WAYPOIONT_PLAY_NEXT_EVENT = "waypoint.playlist.NEXT"
WAYPOIONT_PLAY_PREVIOUS_EVENT = "waypoint.playlist.PREVIOUS"
WAYPOIONT_PLAY_PLAY_EVENT = "waypoint.playlist.PLAY"
WAYPOIONT_PLAY_STOP_EVENT = "waypoint.playlist.STOP"

SETTING_PLAY_NEXT_ENABLED = "/app/waypoint/playlist/next/enabled"
SETTING_PLAY_PREVIOUS_ENABLED = "/app/waypoint/playlist/previous/enabled"
SETTING_PLAY_PLAY_ENABLED = "/app/waypoint/playlist/play/enabled"
SETTING_PLAY_PLAYING = "/app/waypoint/playlist/playing"
SETTING_PLAYLIST_ACTIVE = "/exts/omni.kit.tool.camera_playlist/active"


class PlayControl:
    def __init__(self, playlist_model: PlaylistModel):
        self._playlist_model = playlist_model
        self.__play_manager = get_play_manager()

        self._settings = carb.settings.get_settings()
        self._active_playlist_sub = self.__play_manager.subscribe_playing_playlist_changed(
            self.__on_playing_status_changed
        )

        self._play_event_subs = [
            carb.eventdispatcher.get_eventdispatcher().observe_event(
                observer_name="omni.kit.waypoint.playlist.play_control",
                event_name=e,
                on_event=trigger_fn,
            )
            for e, trigger_fn in [
                (WAYPOIONT_PLAY_NEXT_EVENT, lambda _: self.__on_next()),
                (WAYPOIONT_PLAY_PREVIOUS_EVENT, lambda _: self.__on_previous()),
                (WAYPOIONT_PLAY_PLAY_EVENT, lambda _: self.__start_play()),
                (WAYPOIONT_PLAY_STOP_EVENT, lambda _: self.__stop_play()),
            ]
        ]

    def destroy(self):
        self._active_playlist_sub = None
        self._play_event_subs.clear()
        self._play_event_subs = None

    def __on_next(self):
        if self.__play_manager.is_playing:
            carb.log_warn(f"Alreay playing '{self.__play_manager.current_playlist.name}'")
            return
        self.__play_manager.current_playlist = self._playlist_model
        self.__play_manager.next()

    def __on_previous(self):
        if self.__play_manager.is_playing:
            carb.log_warn(f"Alreay playing '{self.__play_manager.current_playlist.name}'")
            return
        self.__play_manager.current_playlist = self._playlist_model
        self.__play_manager.previous()

    def __start_play(self):
        if self.__play_manager.is_playing:
            carb.log_warn(f"Alreay playing '{self.__play_manager.current_playlist.name}'")
            return
        self.__play_manager.current_playlist = self._playlist_model
        self.__play_manager.play()

    def __stop_play(self):
        self.__play_manager.stop()

    def __on_playing_status_changed(self, name: str):
        playing = name != ""
        self._settings.set(SETTING_PLAY_NEXT_ENABLED, not playing)
        self._settings.set(SETTING_PLAY_PREVIOUS_ENABLED, not playing)

        playing_waypoint = name == self._playlist_model.name
        self._settings.set(SETTING_PLAY_PLAY_ENABLED, not playing or playing_waypoint)
        self._settings.set(SETTING_PLAY_PLAYING, playing_waypoint)
