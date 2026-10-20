# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
"""This module implements a movie capture window that integrates capture, rendering, output, and farm settings widgets while managing movie and sequence capture options and UI updates based on stage events using Omni UI."""

import typing

import carb
import omni.kit.capture.viewport
import omni.ui as ui
import omni.usd
from carb.eventdispatcher import get_eventdispatcher
from omni.kit.capture.viewport import CaptureOptions

from .base_widget import FRAME_SPACING, WINDOW_DARK_STYLE, WINDOW_HEIGHT, WINDOW_WIDTH
from .capture_settings_widget import CaptureSettingsWidget
from .farm_settings_widget import FarmSettingsWidget
from .output_settings_widget import OutputSettingsWidget
from .render_settings_widget import RenderSettingsWidget
from .ui_values_interface import UIValuesInterface


def read_kit_capture_options(
    options: CaptureOptions,
    to_capture_sequence: bool,
    capture_widget: CaptureSettingsWidget,
    render_widget: RenderSettingsWidget,
    output_widget: OutputSettingsWidget,
    farm_widget: FarmSettingsWidget,
    to_send_to_farm=False,
) -> bool:

    capture_widget.collect_settings(options)
    if not render_widget.collect_settings(options):
        return False
    output_widget.collect_settings(options)
    if to_send_to_farm:
        farm_widget.collect_settings(options)

    ## the following is demo code to use customized progress_update_fn and forward_one_frame_fn
    ## keep it here for reference in case someone needs to do a customized movie capture UI for their kit experience
    # self._capture_instance.show_default_progress_window = False
    # self._capture_instance.progress_update_fn = self._on_capture_progress
    #
    # self._frames_to_capture = self._capture_instance.options.end_frame - self._capture_instance.options.start_frame
    # self._start_time = float(self._capture_instance.options.start_frame) / self._capture_instance.options.fps
    # self._time = self._start_time
    # fps = self._capture_instance.options.fps
    # self._time_rate = 1.0 / (fps * (self._capture_instance.options.ptmb_fsc - self._capture_instance.options.ptmb_fso) * self._capture_instance.options.ptmb_subframes_per_frame)
    # self._capture_instance.forward_one_frame_fn = self._on_forward_one_frame

    if to_capture_sequence:
        if options.file_type == ".mp4":
            if options.capture_every_Nth_frames >= 1:
                carb.log_warn(
                    f"Capture every Nth frame value {options.capture_every_Nth_frames} will be ignored while file format is .mp4. Please choose image types to capture Nth frames."
                )
            options.capture_every_Nth_frames = -1
        else:
            # if Capture Nth frame checkbox is unchecked, then we want to capture all the frames and not to generate movie
            if options.capture_every_Nth_frames == -1:
                options.capture_every_Nth_frames = 1
    else:
        if options.file_type == ".mp4":
            carb.log_warn(
                "File format .mp4 is selected while capturing current frame. Will capture current frame in .png."
            )
            options.file_type = ".png"
        options.capture_every_Nth_frames = -1

    return True


class MovieCaptureWindow:

    WINDOW_NAME = "Movie Capture"

    def __init__(self):
        self._init()

    def _init(self):
        self._capture_instance = omni.kit.capture.viewport.CaptureExtension.get_instance()
        self._visiblity_changed_listener = None

        self._capture_settings_widget = None
        self._render_settings_widget = None
        self._output_settings_widget = None
        self._farm_settings_widget = None

        self._window = self._build_ui()
        self._window.set_visibility_changed_fn(self._visibility_changed_fn)
        self._stage_opened = ""
        UIValuesInterface().try_update_ui_for_current_stage(
            self._capture_settings_widget,
            self._render_settings_widget,
            self._output_settings_widget,
            self._farm_settings_widget,
        )
        self._stage_event_sub = get_eventdispatcher().observe_event(
            observer_name="omni.kit.window.movie_capture.load_settings",
            event_name=omni.usd.get_context().stage_event_name(omni.usd.StageEventType.SETTINGS_LOADED),
            on_event=self._on_stage_settings_loaded,
        )

    def _on_stage_settings_loaded(self, _):
        UIValuesInterface().try_update_ui_for_current_stage(
            self._capture_settings_widget,
            self._render_settings_widget,
            self._output_settings_widget,
            self._farm_settings_widget,
        )

    def _visibility_changed_fn(self, visible):
        if self._visiblity_changed_listener:
            self._visiblity_changed_listener(visible)
        if visible:
            cur_stage = omni.usd.get_context().get_stage_url()
            if cur_stage != self._stage_opened:
                self._stage_opened = cur_stage
                UIValuesInterface().try_update_ui_for_current_stage(
                    self._capture_settings_widget,
                    self._render_settings_widget,
                    self._output_settings_widget,
                    self._farm_settings_widget,
                )

            # also update movie types in case new movie types are available
            self._capture_settings_widget.refresh_movie_types()
            self._render_settings_widget.refresh_ui()

    def set_visibility_changed_listener(self, listener):
        self._visiblity_changed_listener = listener

    def destroy(self):
        self._visiblity_changed_listener = None
        self._window.visible = False
        self._window.set_visibility_changed_fn(None)
        self._window.destroy()
        self._window = None
        self._capture_instance = None

        if self._capture_settings_widget:
            self._capture_settings_widget.destroy()
        if self._render_settings_widget:
            self._render_settings_widget.destroy()
        if self._output_settings_widget:
            self._output_settings_widget.destroy()
        if self._farm_settings_widget:
            self._farm_settings_widget.destroy()

        self._capture_settings_widget = None
        self._render_settings_widget = None
        self._output_settings_widget = None
        self._farm_settings_widget = None

        self._stage_event_sub = None

    def _build_ui(self) -> ui.Window:
        window_flags = ui.WINDOW_FLAGS_NO_SCROLLBAR
        window = ui.Window(
            self.WINDOW_NAME,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            style=WINDOW_DARK_STYLE,
            flags=window_flags,
            dockPreference=ui.DockPreference.RIGHT_TOP,
        )
        with window.frame:
            with ui.ScrollingFrame():
                with ui.VStack(spacing=FRAME_SPACING):
                    self._build_ui_widgets()
                    ui.Spacer()

        window.set_width_changed_fn(self._output_settings_widget.on_window_width_changed)
        return window

    def _rebuild_ui(self):
        self.destroy()
        self._init()

    def show(self):
        self._window.visible = True
        self._visibility_changed_fn(True)

    def hide(self):
        self._window.visible = False
        self._visibility_changed_fn(False)

    def _build_ui_widgets(self):
        self._build_ui_capture_settings()
        self._build_ui_rendering_settings()
        self._build_ui_farm_settings()
        self._build_ui_output_settings()

    def _on_update(self, dt):
        pass

    def _build_ui_capture_settings(self):
        self._capture_settings_widget = CaptureSettingsWidget()
        self._capture_settings_widget.build_ui()

    def _build_ui_rendering_settings(self):
        self._render_settings_widget = RenderSettingsWidget(self._capture_instance)
        self._render_settings_widget.build_ui()

    def _build_ui_output_settings(self):
        self._output_settings_widget = OutputSettingsWidget(self._read_kit_capture_options, self._capture_instance)
        self._output_settings_widget.build_ui()

    def _build_ui_farm_settings(self):
        self._farm_settings_widget = FarmSettingsWidget()
        self._farm_settings_widget.build_ui()

    def _is_default_scene(self):
        # default scene's stage url starts with "anon:"
        stage_url = omni.usd.get_context().get_stage_url()
        return stage_url.startswith("anon:")

    def _read_kit_capture_options(
        self, to_capture_sequence, to_send_to_farm=False
    ) -> typing.Tuple[CaptureOptions, typing.Dict]:
        # refresh the options as we don't want to keep options from last run, like the early quit time limit for Farm option
        self._capture_instance.options = CaptureOptions()
        if not read_kit_capture_options(
            self._capture_instance.options,
            to_capture_sequence,
            self._capture_settings_widget,
            self._render_settings_widget,
            self._output_settings_widget,
            self._farm_settings_widget,
            to_send_to_farm,
        ):
            return None, None

        metadata = {}
        # Handle optional advanced rendering features for metadata:
        task_extensions = self._farm_settings_widget.get_task_extensions()
        if task_extensions is not None:
            metadata["extensions"] = task_extensions
        task_registries = self._farm_settings_widget.get_task_registries()
        if task_registries is not None:
            metadata["registries"] = self._farm_settings_widget.get_task_registries()

        farm_data = {
            "farm_url": self._farm_settings_widget.get_selected_farm(),
            "task_type": self._farm_settings_widget.get_task_type(),
            "start_delay": self._farm_settings_widget.get_start_delay(),
            "batch_count": self._farm_settings_widget.get_batch_count(),
            "task_comment": self._farm_settings_widget.get_task_comment(),
            "priority": self._farm_settings_widget.get_task_priority(),
            "metadata": metadata,
            "bad_frame_size_threshold": self._farm_settings_widget.get_task_valid_frame_size(),
            "max_bad_frame_threshold": self._farm_settings_widget.get_task_frame_size_threshold(),
            "texture_streaming_memory_budget": self._farm_settings_widget.get_texture_streaming_memory_budget(),
        }

        # Handle optional advanced rendering features for farm data:
        upload_to_s3 = self._farm_settings_widget.get_upload_to_s3()
        if upload_to_s3 is not None:
            farm_data["upload_to_s3"] = upload_to_s3
        skip_upload = self._farm_settings_widget.get_skip_upload_to_s3()
        if skip_upload is not None:
            farm_data["skip_upload"] = skip_upload

        if not self._is_default_scene():
            UIValuesInterface().save_ui_values(
                self._capture_settings_widget,
                self._render_settings_widget,
                self._output_settings_widget,
                self._farm_settings_widget,
            )
        return self._capture_instance.options, farm_data
