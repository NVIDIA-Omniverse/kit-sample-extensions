# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from omni import ui
from omni.kit.playlist.core import PlaylistModel, PlayMode, get_play_manager
from omni.kit.widgets.custom import CustomWidgetComboBox, FloatSpinner, LabelDelegate, SimpleImageButton

from ..constant import OPTIONS_PADDING_X
from ..utils import get_icon_path

CONTROLS_SPACING = 20
CONTROLS_ICON_SIZE = 24


class PlayControls:
    PLAY_ICON = get_icon_path("Play.svg")
    STOP_ICON = get_icon_path("Stop.svg")

    def __init__(self, playlist_model: PlaylistModel):
        self._transition_types = [PlayMode.TRANSITION_CUT, PlayMode.TRANSITION_SMOOTH]
        self.__play_manager = get_play_manager()
        self.__play_manager.current_playlist = playlist_model
        self.__sub_id = self.__play_manager.subscribe_playing_playlist_changed(self.__on_playing_status_changed)

        self._build_ui()

    def destroy(self):
        self.__sub_id = None

    def _build_ui(self):
        self._build_controls()
        ui.Spacer(height=10)
        self._build_options()

    def bind_playlist(self, playlist_model: PlaylistModel):
        self.__play_manager.current_playlist = playlist_model
        if playlist_model:
            self._item_time_spinner.value = playlist_model.item_time
            self._transition_time_spinner.value = playlist_model.transition_time
            self._transition_type_combobox.current_index = self._transition_types.index(playlist_model.transition_type)

    def _build_controls(self):
        with ui.HStack(spacing=CONTROLS_SPACING, height=0):
            ui.Spacer()
            self._previouse_button = SimpleImageButton(
                get_icon_path("StepBackward.svg"), CONTROLS_ICON_SIZE, self._on_previous
            )
            self._play_button = SimpleImageButton(self.PLAY_ICON, CONTROLS_ICON_SIZE, self._on_play)
            self._next_button = SimpleImageButton(get_icon_path("StepForward.svg"), CONTROLS_ICON_SIZE, self._on_next)
            ui.Spacer()

    def _build_options(self):
        widget_width = 100
        with ui.HStack(height=0):
            ui.Spacer(width=OPTIONS_PADDING_X)
            with ui.VStack(spacing=10):
                with ui.HStack(height=26):
                    ui.Label("Time Per Item")
                    ui.Spacer()
                    self._item_time_spinner = FloatSpinner(
                        self._on_item_time_changed,
                        value=5,
                        step=0.1,
                        vertical=True,
                        width=widget_width,
                        height=26,
                        min_value=0.1,
                        max_value=9999,
                    )
                    ui.Spacer(width=5)
                    ui.Label("sec", width=15)
                with ui.HStack(height=26):
                    ui.Label("Transition Type")
                    ui.Spacer()
                    self._transition_type_combobox = CustomWidgetComboBox(
                        0,
                        *self._transition_types,
                        width=widget_width,
                        item_delegate=LabelDelegate(),
                        alignment=ui.Alignment.CENTER,
                    )
                    ui.Spacer(width=24)
                self._transition_time_panel = ui.HStack(height=26)
                with self._transition_time_panel:
                    ui.Label("Transition Time")
                    ui.Spacer()
                    self._transition_time_spinner = FloatSpinner(
                        self._on_transition_time_changed,
                        value=5,
                        step=0.1,
                        vertical=True,
                        width=widget_width,
                        height=26,
                        min_value=0.1,
                        max_value=9999,
                    )
                    ui.Spacer(width=5)
                    ui.Label("sec", width=15)
            ui.Spacer(width=OPTIONS_PADDING_X)

        self._transition_type_combobox.model.add_item_changed_fn(self._on_transition_type_changed)
        self._on_transition_type_changed(None, None)

    def _on_previous(self):
        self.__play_manager.previous()

    def _on_next(self):
        self.__play_manager.next()

    def _on_play(self):
        if self.__play_manager.is_playing:
            # Stop playing
            self.__play_manager.stop()
        else:
            self.__play_manager.play()

    def _on_item_time_changed(self, value):
        model = self.__play_manager.current_playlist
        if model:
            model.item_time = value

    def _on_transition_time_changed(self, value):
        model = self.__play_manager.current_playlist
        if model:
            model.transition_time = value

    def _on_transition_type_changed(self, model, item):
        model = self.__play_manager.current_playlist
        if model:
            model.transition_type = self._transition_type_combobox.current_value

        if self._transition_type_combobox.current_value == PlayMode.TRANSITION_CUT:
            self._transition_time_spinner.enabled = False
        else:
            self._transition_time_spinner.enabled = True

    def __on_playing_status_changed(self, playing_name: str) -> None:
        if playing_name:
            # Disable transition options
            self._transition_type_combobox.enabled = False
            self._transition_time_spinner.enabled = False

            # Diable previous and next button
            self._previouse_button.enable(False)
            self._next_button.enable(False)
            # Use stop instead of play
            self._play_button.set_image(self.STOP_ICON)
        else:
            # Enable transition options
            self._transition_type_combobox.enabled = True
            self._transition_time_spinner.enabled = True

            # Enable previous and next button
            self._previouse_button.enable(True)
            self._next_button.enable(True)
            # Use play instead of stop
            self._play_button.set_image(self.PLAY_ICON)
