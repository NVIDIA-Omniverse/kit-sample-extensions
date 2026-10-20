# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import TYPE_CHECKING, Optional
from weakref import ref

import carb
import carb.dictionary
import carb.settings
import omni.kit.app
import omni.ui as ui
from carb.eventdispatcher import get_eventdispatcher
from omni.kit.playlist.core import PlaylistModel, PlaylistPlayer, PlayMode

from ..playlist_card_markup import MarkupCard

if TYPE_CHECKING:  # pragma: no cover
    from .list_window import MarkupListWindow

from ..common import CURRENT_TOOL_PATH

IMAGE_SIZE = 16

SETTINGS_MARKUP_ROOT = "/exts/omni.kit.markup.core/"
SETTINGS_MARKUP_ACTIVE = SETTINGS_MARKUP_ROOT + "active_markup"
SETTINGS_MARKUP_EDITING = SETTINGS_MARKUP_ROOT + "editing_markup"

MARKUP_PLAY_NEXT_EVENT = "markup.playlist.NEXT"
MARKUP_PLAY_PREVIOUS_EVENT = "markup.playlist.PREVIOUS"
MARKUP_PLAY_PLAY_EVENT = "markup.playlist.PLAY"
MARKUP_PLAY_STOP_EVENT = "markup.playlist.STOP"

SETTING_PLAY_NEXT_ENABLED = "/app/markup/playlist/next/enabled"
SETTING_PLAY_PREVIOUS_ENABLED = "/app/markup/playlist/previous/enabled"
SETTING_PLAY_PLAY_ENABLED = "/app/markup/playlist/play/enabled"
SETTING_PLAY_PLAYING = "/app/markup/playlist/playing"

EXTENSION_NAME = "markup"


class PlayBar:
    _window: "ref[MarkupListWindow]"

    def __init__(self):
        self._player: Optional[PlaylistPlayer] = None
        self._playlist_model: Optional[PlaylistModel] = None

        self._settings = carb.settings.get_settings()
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

        self._update_current_tool_sub = omni.kit.app.SettingChangeSubscription(
            CURRENT_TOOL_PATH, lambda *_: self._on_current_tool_changed()
        )

        self.__build_ui()

    def destroy(self):
        self._update_current_tool_sub = None

    def __del__(self):  # pragma: no cover
        self.destroy()

    def bind_widget(self, widget: "MarkupListWindow"):
        self._window = ref(widget)

    def __build_ui(self):
        with ui.HStack(spacing=8, height=30):
            ui.Spacer()
            self._previous_button = ui.Button(
                "",
                image_width=IMAGE_SIZE,
                image_height=IMAGE_SIZE,
                name="previous",
                clicked_fn=self.__on_previous,
                identifier="PlayBarPrevious",
            )
            self._play_button = ui.Button(
                "",
                image_width=IMAGE_SIZE,
                image_height=IMAGE_SIZE,
                name="play",
                clicked_fn=self.__on_play,
                identifier="PlayBarPlay",
            )
            self._next_button = ui.Button(
                "",
                image_width=IMAGE_SIZE,
                image_height=IMAGE_SIZE,
                name="next",
                clicked_fn=self.__on_next,
                identifier="PlayBarNext",
            )
            ui.Spacer()

    def __on_previous(self):
        self.__step(-1)

    def __on_next(self):
        self.__step(1)

    def __step(self, step):
        if bool(self._settings.get(SETTINGS_MARKUP_EDITING)):
            return
        window = self._window()
        if not window or not window.widgets:  # pragma: no cover
            return

        if window.selected_index is None:
            window.selected_index = 0

        val = (window.selected_index + step) % len(window.widgets)
        window.selected_index = val

    def __on_play(self):
        window = self._window()
        if not window or not window.widgets:  # pragma: no cover
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
                    if not self._player.play():  # pragma: no cover
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

        # Disable previous and next button
        self._previous_button.enabled = False
        self._next_button.enabled = False
        # Use stop instead of play
        self._play_button.name = "pause"

        # Hide the MarkupToolbar

    def _on_stopped(self):
        if self._player:
            self._player.destroy()
            self._player = None
        self._in_playing = False

        # Enable previous and next button
        self._previous_button.enabled = True
        self._next_button.enabled = True
        # Use play instead of stop
        self._play_button.name = "play"

        # upon completion of playthrough, return to navigation
        self._settings.set(CURRENT_TOOL_PATH, "navigation")

    def _on_playing(self, index: int):
        window = self._window()
        if not window or not window.widgets:  # pragma: no cover
            return

        window.selected_index = index

    def __create_playlist_model(self):
        window = self._window()
        if not window or not window.widgets:  # pragma: no cover
            carb.log_warn("No markups defined!")
            return None

        # Create playlist model
        if self._playlist_model is not None:  # pragma: no cover
            self._playlist_model = None
        self._playlist_model = PlaylistModel("_markups_menubar", system=True, transition_type=PlayMode.TRANSITION_CUT)

        for item in window.widgets:
            card = MarkupCard.create(MarkupCard.PLAYLIST_CARD_TYPE_MARKUP, path=item.markup.path)
            self._playlist_model.insert_item(card)

        return self._playlist_model
