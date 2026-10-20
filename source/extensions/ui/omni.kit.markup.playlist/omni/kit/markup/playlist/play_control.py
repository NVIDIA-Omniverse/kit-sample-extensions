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

import carb.settings
import omni.kit.app
import omni.ui as ui
from carb.eventdispatcher import get_eventdispatcher
from omni.kit.playlist.core import PlaylistModel, get_play_manager

MARKUP_PLAY_NEXT_EVENT = "markup.playlist.NEXT"
MARKUP_PLAY_PREVIOUS_EVENT = "markup.playlist.PREVIOUS"
MARKUP_PLAY_PLAY_EVENT = "markup.playlist.PLAY"
MARKUP_PLAY_STOP_EVENT = "markup.playlist.STOP"

SETTING_PLAY_NEXT_ENABLED = "/app/markup/playlist/next/enabled"
SETTING_PLAY_PREVIOUS_ENABLED = "/app/markup/playlist/previous/enabled"
SETTING_PLAY_PLAY_ENABLED = "/app/markup/playlist/play/enabled"
SETTING_PLAY_PLAYING = "/app/markup/playlist/playing"
SETTING_PLAYLIST_ACTIVE = "/exts/omni.kit.tool.camera_playlist/active"


class PlayControl:
    def __init__(self, playlist_model: PlaylistModel):
        self._playlist_model = playlist_model
        self.__play_manager = get_play_manager()

        self._settings = carb.settings.get_settings()
        self._active_playlist_sub = self.__play_manager.subscribe_playing_playlist_changed(
            self.__on_playing_status_changed
        )

        self._event_subs = [
            get_eventdispatcher().observe_event(
                observer_name="omni.kit.markup.core:extension",
                event_name=event,
                on_event=func,
            )
            for event, func in [
                (MARKUP_PLAY_NEXT_EVENT, lambda e: self.__on_next()),
                (MARKUP_PLAY_PREVIOUS_EVENT, lambda e: self.__on_previous()),
                (MARKUP_PLAY_PLAY_EVENT, lambda e: self.__start_play()),
                (MARKUP_PLAY_STOP_EVENT, lambda e: self.__stop_play()),
            ]
        ]

    def destroy(self):
        self._active_playlist_sub = None

        self._play_next_event_sub = None
        self._play_previous_event_sub = None
        self._play_play_event_sub = None
        self._play_stop_event_sub = None

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

        playing_markup = name == self._playlist_model.name
        self._settings.set(SETTING_PLAY_PLAY_ENABLED, not playing or playing_markup)
        self._settings.set(SETTING_PLAY_PLAYING, playing_markup)
