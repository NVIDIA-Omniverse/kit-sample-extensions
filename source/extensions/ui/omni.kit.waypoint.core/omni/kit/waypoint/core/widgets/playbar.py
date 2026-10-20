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
from typing import TYPE_CHECKING, Optional
from weakref import ref

import carb
import carb.dictionary
import carb.events
import carb.settings
import omni.kit.app
import omni.ui as ui
from omni.kit.playlist.core import PlaylistCard, PlaylistModel, PlaylistPlayer, PlayMode

from ..playlist_card_waypoint import WaypointCard

if TYPE_CHECKING:  # pragma: no cover
    from .list_window import WaypointListWindow

from ..common import CURRENT_TOOL_PATH, EXTENSION_NAME, ICON_PATH

IMAGE_SIZE = 16

PLAYBAR_STYLE = {
    "Button": {
        "padding": 4,
        "marging": 0,
    },
    "Button.Image:disabled": {
        "color": 0xFF6E6E6E,
    },
    "Button.Image::previous": {
        "image_url": f"{ICON_PATH}/StepBackward.svg",
    },
    "Button.Image::play": {
        "image_url": f"{ICON_PATH}/Play.svg",
    },
    "Button.Image::pause": {
        "image_url": f"{ICON_PATH}/Pause.svg",
        "color": 0xFF9E9E9E,
    },
    "Button.Image::next": {
        "image_url": f"{ICON_PATH}/StepForward.svg",
    },
}

SETTINGS_WAYPOINT_ROOT = "/exts/omni.kit.waypoint.core/"
SETTINGS_WAYPOINT_ACTIVE = SETTINGS_WAYPOINT_ROOT + "active_waypoint"
SETTINGS_WAYPOINT_EDITING = SETTINGS_WAYPOINT_ROOT + "editing_waypoint"

WAYPOINT_PLAY_NEXT_EVENT = "waypoint.playlist.NEXT"
WAYPOINT_PLAY_PREVIOUS_EVENT = "waypoint.playlist.PREVIOUS"
WAYPOINT_PLAY_PLAY_EVENT = "waypoint.playlist.PLAY"
WAYPOINT_PLAY_STOP_EVENT = "waypoint.playlist.STOP"

SETTING_PLAY_NEXT_ENABLED = "/app/waypoint/playlist/next/enabled"
SETTING_PLAY_PREVIOUS_ENABLED = "/app/waypoint/playlist/previous/enabled"
SETTING_PLAY_PLAY_ENABLED = "/app/waypoint/playlist/play/enabled"
SETTING_PLAY_PLAYING = "/app/waypoint/playlist/playing"


class PlayBar:
    _window: "ref[WaypointListWindow]"

    def __init__(self):
        self._player: Optional[PlaylistPlayer] = None
        self._playlist_model: Optional[PlaylistModel] = None

        self._settings = carb.settings.get_settings()
        self._play_event_subs = [
            carb.eventdispatcher.get_eventdispatcher().observe_event(
                observer_name="omni.kit.waypoint.core.playbar",
                event_name=e,
                on_event=trigger_fn,
            )
            for e, trigger_fn in [
                (WAYPOINT_PLAY_NEXT_EVENT, lambda _: self.__on_next()),
                (WAYPOINT_PLAY_PREVIOUS_EVENT, lambda _: self.__on_previous()),
                (WAYPOINT_PLAY_PLAY_EVENT, lambda _: self.__on_play()),
                (WAYPOINT_PLAY_STOP_EVENT, lambda _: self.__on_play()),
            ]
        ]

        self._update_current_tool_sub = omni.kit.app.SettingChangeSubscription(
            CURRENT_TOOL_PATH, lambda *_: self._on_current_tool_changed()
        )

        self.__build_ui()

    def destroy(self):  # pragma: no cover
        self._play_event_subs.clear()
        self._play_event_subs = None
        self._update_current_tool_sub = None

    def __del__(self):  # pragma: no cover
        self.destroy()

    def bind_widget(self, widget: "WaypointListWindow"):
        self._window = ref(widget)

    def __build_ui(self):
        with ui.HStack(spacing=8, height=30, style=PLAYBAR_STYLE):
            ui.Spacer()
            self._previouse_button = ui.Button(
                "", image_width=IMAGE_SIZE, image_height=IMAGE_SIZE, name="previous", clicked_fn=self.__on_previous
            )
            self._play_button = ui.Button(
                "", image_width=IMAGE_SIZE, image_height=IMAGE_SIZE, name="play", clicked_fn=self.__on_play
            )
            self._next_button = ui.Button(
                "", image_width=IMAGE_SIZE, image_height=IMAGE_SIZE, name="next", clicked_fn=self.__on_next
            )
            ui.Spacer()

    def __on_previous(self):
        self.__step(-1)

    def __on_next(self):
        self.__step(1)

    def __step(self, step):
        if bool(self._settings.get(SETTINGS_WAYPOINT_EDITING)):
            return
        window = self._window()
        if not window or not window.widgets:
            return

        if window.selected_index is None:
            window.selected_index = 0

        val = (window.selected_index + step) % len(window.widgets)
        window.selected_index = val

    def __on_play(self):
        window = self._window()
        if not window or not window.widgets:
            return

        if window.selected_index is None:
            window.selected_index = 0

        if self._player:
            # Stop playing
            self._player.stop()
            self._player = None
        else:
            self._playlist_model = self.__create_playlist_model()
            if self._playlist_model:
                self._player = PlaylistPlayer.create(
                    self._playlist_model, window.selected_index, self._on_started, self._on_stopped, self._on_playing
                )
                if self._player:
                    if not self._player.play():
                        self._player.destroy()
                        self._player = None

    def _on_current_tool_changed(self):
        new_tool = self._settings.get_as_string(CURRENT_TOOL_PATH)
        if new_tool != EXTENSION_NAME and self._player:
            self._player.stop()
            self._player = None

    def _on_started(self):
        current_tool = self._settings.get_as_string(CURRENT_TOOL_PATH)
        if current_tool != EXTENSION_NAME:
            self._settings.set(CURRENT_TOOL_PATH, EXTENSION_NAME)

        # Diable previous and next button
        self._previouse_button.enabled = False
        self._next_button.enabled = False
        # Use stop instead of play
        self._play_button.name = "pause"

    def _on_stopped(self):
        if self._player:
            self._player.destroy()
            self._player = None
        self._in_playing = False

        # Enable previous and next button
        self._previouse_button.enabled = True
        self._next_button.enabled = True
        # Use play instead of stop
        self._play_button.name = "play"

        from ..extension import get_instance

        ext = get_instance()
        if ext:
            ext._reset_current_tool()

    def _on_playing(self, index: int):
        window = self._window()
        if not window or not window.widgets:
            return

        window.selected_index = index

    def __create_playlist_model(self):
        window = self._window()
        if not window or not window.widgets:
            carb.log_warn("No waypoints defined!")
            return None

        # Create playlist model
        self._playlist_model = PlaylistModel("_waypoints_menubar", system=True, transition_type=PlayMode.TRANSITION_CUT)

        for item in window.widgets:
            card = WaypointCard.create(PlaylistCard.WAYPOINT, path=item.waypoint.path)
            self._playlist_model.insert_item(card)

        return self._playlist_model
