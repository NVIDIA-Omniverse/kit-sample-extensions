# SPDX-FileCopyrightText: Copyright (c) 2022-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
__all__ = ["TimelineMinibar"]

import omni.timeline
import omni.ui as ui

from .live_session import TimelineLiveSession
from .style import BUTTON_IMAGE_SIZE, CORSOR_WIDTH, MINIBAR_HEIGHT, RANGE_HANDLE_WIDTH, minibar_style
from .timeline_model import *


class TimelineMinibar:
    """The class that represents the timeline minibar"""

    def __init__(self, live_session: TimelineLiveSession):
        self.__root = None

        self._timeline = omni.timeline.get_timeline_interface()
        self._loop_model = TimelineLoopModel()
        self._play_model = TimelinePlayModel()
        self._start_model = TimelineStartModel()
        self._end_model = TimelineEndModel()
        self._cur_model = TimelineCurrentModel()

        self._live_session = live_session
        self._presenter_widget = None
        self._cursor = None
        self._cursor_frame = None

        self._build_fn()
        self.__root.visible = False

        if self._live_session is not None:
            self._live_session.register_status_changed_fn(self._on_live_session)

    def destroy(self):  # pragma: no cover
        self._timeline = None
        if self._live_session:
            self._live_session.deregister_status_changed_fn(self._on_live_session)
            self._live_session = None

        self._presenter_widget = None

        self._start_widget = None
        self._end_widget = None
        self._slider = None
        self._cursor = None
        self._cursor_frame = None

        if self.__root:
            self.__root.clear()
            self.__root = None
        if self._loop_model:
            self._loop_model.destroy()
            self._loop_model = None
        if self._play_model:
            self._play_model.destroy()
            self._play_model = None
        if self._start_model:
            self._start_model.destroy()
            self._start_model = None
        if self._end_model:
            self._end_model.destroy()
            self._end_model = None
        if self._cur_model:
            self._cur_model.destroy()
            self._cur_model = None

    def _build_fn(self):
        self.__root = ui.HStack(height=MINIBAR_HEIGHT, style=minibar_style, identifier="TimelineMiniBar")
        with self.__root:
            with ui.ZStack(content_clipping=True):
                ui.Rectangle()
                with ui.HStack(spacing=0):
                    ui.Spacer(width=8)
                    self._start_widget = ui.IntField(
                        model=self._start_model, width=RANGE_HANDLE_WIDTH, identifier="startwidget"
                    )
                    ui.Spacer(width=4)
                    with ui.ZStack():
                        self._slider = ui.IntSlider(
                            name="timeline",
                            model=self._cur_model,
                            min=self._start_model.get_value_as_int(),
                            max=self._end_model.get_value_as_int(),
                        )
                        # use a custom cursor instead of the default rect in ui.IntSlider
                        self._cursor_frame = ui.Frame(build_fn=self._build_cursor)
                    ui.Spacer(width=4)
                    self._end_widget = ui.IntField(
                        model=self._end_model, width=RANGE_HANDLE_WIDTH, identifier="endwidget"
                    )

                    self._start_model.add_value_changed_fn(self._on_range_changed)
                    self._end_model.add_value_changed_fn(self._on_range_changed)
                    self._cur_model.add_value_changed_fn(self._on_current_changed)

                    ui.ToolButton(
                        image_width=BUTTON_IMAGE_SIZE,
                        iamge_height=BUTTON_IMAGE_SIZE,
                        width=20,
                        model=self._play_model,
                        name="play",
                    )
                    ui.ToolButton(
                        image_width=BUTTON_IMAGE_SIZE,
                        iamge_height=BUTTON_IMAGE_SIZE,
                        width=20,
                        model=self._loop_model,
                        name="loop",
                    )

                    # presenter info
                    self._presenter_widget = ui.HStack(width=24, identifier="presenter_widget")
                    with self._presenter_widget:
                        ui.Spacer(width=4)
                        with ui.ZStack():
                            self._user_circle = ui.Circle(
                                radius=10,
                                size_policy=ui.CircleSizePolicy.FIXED,
                                style={"Circle": {"background_color": 0xFFFF0000}},
                                tooltip="presenter",
                                alignment=ui.Alignment.CENTER,
                            )
                            self._short_user_name = ui.Label(
                                "",
                                name="short_name",
                                alignment=ui.Alignment.CENTER,
                            )

                    ui.Spacer(width=8)

                    if self._live_session:
                        is_sync = self._live_session.is_sync_enabled()
                        is_presenter = self._live_session.am_i_presenter()
                        self._on_live_session(is_presenter, is_sync)
                    else:
                        self._presenter_widget.visible = False

    def _on_live_session(self, is_presenter: bool, is_sync: bool):
        is_listener = is_sync and not is_presenter
        self._presenter_widget.visible = is_listener
        self.__root.enabled = not is_listener

        if is_listener:
            self._user_circle.style = {"Circle": {"background_color": self._live_session.get_presenter_user_color()}}
            self._short_user_name.text = self._live_session.get_presenter_user_short_name()

    def _on_range_changed(self, model):
        if not self._start_model:
            return
        start = self._start_model.get_value_as_int()
        end = self._end_model.get_value_as_int()
        self._slider.min = start
        self._slider.max = end
        cur = self._cur_model.get_value_as_int()
        cur_clamp = max(start, min(end, cur))
        if cur_clamp == cur:
            self._on_current_changed(None)
        else:
            self._cur_model.set_value(cur_clamp)

    def _on_current_changed(self, model):
        if self.__root and self.__root.visible and self._cursor:
            self._update_cursor_offset()

    @property
    def visible(self) -> bool:
        return self.__root and self.__root.visible

    @visible.setter
    def visible(self, value: bool):
        if not self.__root:
            return
        if self.__root.visible == value:
            return
        self.__root.visible = value
        if value and self._cursor_frame:
            self._cursor_frame.rebuild()

    def _update_cursor_offset(self):
        if not self._start_model or not self._end_model or not self._slider or not self._cursor:
            return
        start = self._start_model.get_value_as_int()
        end = self._end_model.get_value_as_int()
        width = self._slider.computed_content_width
        if end <= start or width <= 0:
            offset = 0
        else:
            cur = self._cur_model.get_value_as_int()
            offset = width * (cur - start) / (end - start)
            offset = max(0, min(width - CORSOR_WIDTH, offset))
        self._cursor.offset_x = ui.Length(offset)

    def _build_cursor(self):
        self._cursor = ui.Placer(
            draggable=False,
            width=0,
            drag_axis=ui.Axis.X,
            offset_y=0,
        )
        self._update_cursor_offset()
        with self._cursor:
            ui.Rectangle(width=CORSOR_WIDTH, name="cursor", alignment=ui.Alignment.CENTER)
