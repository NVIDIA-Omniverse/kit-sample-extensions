import math

import carb.eventdispatcher
import carb.settings
import omni.ext
import omni.timeline
import omni.ui as ui
import omni.usd
from carb.input import KEYBOARD_MODIFIER_FLAG_SHIFT
from omni.anim.curve.core import get_curvekey_clipboard, set_curvekey_clipboard
from omni.kit.commands import execute
from pxr import Usd

from .keyframe_listener import KeyFrameListener
from .keyframe_slider import KeyframeSlider, KeyframeWidget
from .live_session import TimelineLiveSession
from .timeline_value_model import TimeCodeModel, TimelineValueModel
from .utils import TimeDisplay, add_xform_keys, get_display_str, get_time_display, remove_all_keys


class TimelineWidgetStyle:
    FONT_SIZE = 14

    @staticmethod
    def get_style():
        style = {
            "TimelineWidget.MainFrame": {"margin_width": 0},
            "TimelineWidget.BackgroundRectangle": {"background_color": 0xFF2A2A27, "margin_width": 0},
            "TimelineWidget.HorizontalRectangle": {"background_color": 0xFF31312F, "margin_width": 0},
            "TimelineWidget.Tick.Line": {"color": 0x44BCB9A5},
            "TimelineWidget.Tick.FrameNumberLabel": {"color": 0xAABCB9A5, "margin": 0},
            "TimelineWidget.FrameNumberLabel": {
                "color": 0xFF2A2825,
                "margin_width": 0,
                "margin_height": 0,
                "font_size": TimelineWidgetStyle.FONT_SIZE,
            },
            "TimelineWidget.Scrubber.FrameRectangle": {"background_color": 0xFFFF7E09},
            "TimelineWidget.Scrubber.FrameShadowRectangle": {"background_color": 0x44AA8820},
            "TimelineWidget.Scrubber.FrameLine": {"border_width": 2, "color": 0xFFFF7E09},
            "FrameRangeWidget.ViewFrameInput": {"background_color": 0xFF292929, "border_radius": 0},
            "FrameRangeWidget.RangeSliderBackground": {"background_color": 0x66292929, "border_radius": 2},
        }
        return style


class FrameRangeSlider:
    LABEL_WIDTH = 80
    BOX_WIDTH = 14
    HANDLE_WIDTH = LABEL_WIDTH + BOX_WIDTH
    SLIDER_HEIGHT = 18

    @staticmethod
    def get_style():
        style = {
            "FrameRangeSlider.Body": {"border_radius": 0, "background_color": 0xFF222222},
            "FrameRangeSlider.Body:hovered": {"border_radius": 0, "background_color": 0xFF626262},
            "FrameRangeSlider.LeftHandle": {"border_radius": 2, "background_color": 0xFF999999},
            "FrameRangeSlider.LeftHandle:hovered": {"border_radius": 2, "background_color": 0xFF666666},
            "FrameRangeSlider.RightHandle": {"border_radius": 2, "background_color": 0xFF999999},
            "FrameRangeSlider.RightHandle:hovered": {"border_radius": 2, "background_color": 0xFF666666},
            "FrameRangeSlider.Label": {"color": 0xFFC6C6C6},
            "FrameRangeSlider.Background": {"background_color": 0xFF2A2825},
            "FrameRangeSlider.stack": {"margin_height": 2},
        }
        return style

    def __init__(self):
        self._settings = carb.settings.get_settings()
        self._timeline = omni.timeline.get_timeline_interface()
        self._range_slider_frame = None
        self._style = self.get_style()
        self._body_placer = None
        self._body_rectangle = None
        self._start_handle = None
        self._start_label = None
        self._end_handle = None
        self._end_label = None
        self._handle_editing = False
        self._body_editing = False
        self._slider_editing = False
        self._slider_width = None
        self._body_width = None
        self._range_slider_frame = ui.Frame()
        self._range_slider_frame.set_build_fn(self._on_range_slider_frame_built)

    def __del__(self):
        self.destroy()

    def destroy(self):
        self.clear()
        if self._range_slider_frame:
            self._range_slider_frame.destroy()
            self._range_slider_frame = None
        self._timeline = None
        self._settings = None
        self._style = None

    def clear(self):
        if self._body_placer:
            self._body_placer.destroy()
            self._body_placer = None
        if self._start_handle:
            self._start_handle.destroy()
            self._start_handle = None
        if self._end_handle:
            self._end_handle.destroy()
            self._end_handle = None
        if self._body_rectangle:
            self._body_rectangle.destroy()
            self._body_rectangle = None

        self._end_label = None

    def rebuild(self):
        if self._slider_editing:
            return
        self._range_slider_frame.rebuild()

    def get_slider_width(self):
        return self._range_slider_frame.computed_width

    def _on_range_slider_frame_built(self):
        self.clear()
        self._slider_width = self.get_slider_width()
        if self._slider_width < 2 * self.HANDLE_WIDTH:
            return
        with ui.ZStack(height=self.SLIDER_HEIGHT, style=self._style, style_type_name_override="FrameRangeSlider.stack"):
            start_position = self.second_to_slider_pos(self._timeline.get_zoom_start_time())
            start_position = min(self._slider_width - 2 * self.HANDLE_WIDTH, start_position)
            self._body_placer = ui.Placer(draggable=True, drag_axis=ui.Axis.X)
            self._body_placer.offset_x = start_position + self.HANDLE_WIDTH
            self._body_placer.set_offset_x_changed_fn(self.on_body_offset_changed)
            self._body_placer.set_mouse_released_fn(self.on_mouse_released)

            self._body_width = max(1, self._slider_width * self.get_zoom() - 2 * self.HANDLE_WIDTH)
            with self._body_placer:
                self._body_rectangle = ui.Rectangle(
                    width=self._body_width, style=self._style, style_type_name_override="FrameRangeSlider.Body"
                )
            self._start_handle = ui.Placer(draggable=True, drag_axis=ui.Axis.X)

            self._start_handle.offset_x = start_position
            self._start_handle.set_offset_x_changed_fn(self.on_start_handle_offset_changed)
            self._start_handle.set_mouse_released_fn(self.on_mouse_released)
            with self._start_handle:
                with ui.HStack(width=self.HANDLE_WIDTH):
                    with ui.ZStack():
                        ui.Rectangle(style=self._style, style_type_override="FrameRangeSlider.Background")
                        with ui.HStack():
                            self._view_start_model = TimeCodeModel(self._timeline.get_zoom_start_time())
                            self._view_start_model.add_end_edit_fn(self._on_view_range_edited)
                            ui.StringField(
                                self._view_start_model,
                                alignment=ui.Alignment.RIGHT_CENTER,
                                style_type_override="FrameRangeSlider.Label",
                                style=self._style,
                            )
                            ui.Spacer(width=4)

                    ui.Rectangle(
                        width=self.BOX_WIDTH,
                        style=self._style,
                        style_type_name_override="FrameRangeSlider.LeftHandle",
                    )
            self._end_handle = ui.Placer(draggable=True, drag_axis=ui.Axis.X)
            self._end_handle.offset_x = self._body_placer.offset_x + self._body_width
            self._end_handle.set_offset_x_changed_fn(self.on_end_handle_offset_changed)
            self._end_handle.set_mouse_released_fn(self.on_mouse_released)
            with self._end_handle:
                with ui.HStack(width=self.HANDLE_WIDTH):
                    ui.Rectangle(
                        width=self.BOX_WIDTH,
                        style=self._style,
                        style_type_name_override="FrameRangeSlider.RightHandle",
                    )
                    with ui.ZStack():
                        ui.Rectangle(style=self._style, style_type_override="FrameRangeSlider.Background")
                        with ui.HStack():
                            ui.Spacer(width=4)
                            self._view_end_model = TimeCodeModel(self._timeline.get_zoom_end_time())
                            self._view_end_model.add_end_edit_fn(self._on_view_range_edited)
                            ui.StringField(
                                self._view_end_model,
                                alignment=ui.Alignment.RIGHT_CENTER,
                                style_type_override="FrameRangeSlider.Label",
                                style=self._style,
                            )

    def on_mouse_released(self, *args):
        if self._slider_editing:
            self._slider_editing = False
            fps = self._timeline.get_time_codes_per_seconds()
            start_sec = self._view_start_model.get_value_as_float() / fps
            end_sec = self._view_end_model.get_value_as_float() / fps
            self._timeline.set_zoom_range(start_sec, end_sec)

    def clamp_x(self, x, min_x, max_x, placer):
        clamped = False
        if x.value < min_x:
            placer.offset_x = ui.Pixel(min_x)
            clamped = True
        if x.value > max_x:
            placer.offset_x = ui.Pixel(max_x)
            clamped = True
        return clamped

    def on_body_offset_changed(self, x):
        if self._handle_editing:
            self._handle_editing = False
            return
        self._body_editing = True
        min_x = self.HANDLE_WIDTH
        max_x = self.get_slider_width() - self.HANDLE_WIDTH - self._body_width
        if self.clamp_x(x, min_x, max_x, self._body_placer):
            return
        self._start_handle.offset_x = self._body_placer.offset_x - self.HANDLE_WIDTH
        self._end_handle.offset_x = self._body_placer.offset_x + self._body_width
        self.update_frame_numbers()

    def on_start_handle_offset_changed(self, x):
        if self._body_editing:
            self._body_editing = False
            return
        self._handle_editing = True
        self._slider_width = self.get_slider_width()
        max_x = self._end_handle.offset_x - self.HANDLE_WIDTH
        if self.clamp_x(x, 0, max_x, self._start_handle):
            return
        self.update_frame_numbers()
        self.update_slider_body()

    def on_end_handle_offset_changed(self, x):
        if self._body_editing:
            self._body_editing = False
            return
        self._handle_editing = True
        self._slider_width = self.get_slider_width()
        min_x = self._start_handle.offset_x + self.HANDLE_WIDTH
        max_x = self._slider_width - self.HANDLE_WIDTH
        if self.clamp_x(x, min_x, max_x, self._end_handle):
            return
        self.update_frame_numbers()
        self.update_slider_body()

    def update_frame_numbers(self):
        self._slider_editing = True
        frame_range_length = self.get_scene_range_length()
        start_pos = self._start_handle.offset_x
        start_sec = frame_range_length * (start_pos / self._slider_width)
        fps = self._timeline.get_time_codes_per_seconds()
        start_frame = (start_sec + self._timeline.get_start_time()) * fps
        end_pos = self._end_handle.offset_x + self.HANDLE_WIDTH
        end_sec = frame_range_length * (end_pos / self._slider_width)
        end_frame = (end_sec + self._timeline.get_start_time()) * fps

        self._view_start_model.set_value(round(start_frame))
        self._view_end_model.set_value(round(end_frame))

    def _on_view_range_edited(self, value):
        fps = self._timeline.get_time_codes_per_seconds()
        new_start = self._view_start_model.get_value_as_float() / fps
        new_end = self._view_end_model.get_value_as_float() / fps
        if new_start > new_end:
            carb.log_warn("input zoom start value > zoom end value")
            return
        # OM-99524:  update scene start/end if need
        scene_end = self._timeline.get_end_time()
        scene_start = self._timeline.get_start_time()
        if scene_start > new_start:
            self._timeline.set_start_time(new_start)
        if scene_end < new_end:
            self._timeline.set_end_time(new_end)
        self._timeline.set_zoom_range(new_start, new_end)

    def second_to_slider_pos(self, second: float):
        frame_range_length = self.get_scene_range_length()
        return self.get_slider_width() * (second - self._timeline.get_start_time()) / frame_range_length

    def update_slider_body(self):
        self._body_width = ui.Pixel(self._end_handle.offset_x - self._start_handle.offset_x - self.HANDLE_WIDTH)
        self._body_rectangle.width = self._body_width
        self._body_placer.offset_x = self._start_handle.offset_x + self.HANDLE_WIDTH

    def get_scene_range_length(self):
        len = self._timeline.get_end_time() - self._timeline.get_start_time()
        return len if len > 0 else 1

    def get_zoom(self):
        scene_len = self.get_scene_range_length()
        zoom = self._timeline.get_zoom_end_time() - self._timeline.get_zoom_start_time()
        return zoom / scene_len if scene_len > 0 and zoom > 0 else 1


class FrameRangeWidget:
    def __init__(self):
        self._timeline = omni.timeline.get_timeline_interface()

        self._scene_start_frame_widget = None
        self._scene_end_frame_widget = None
        self._frame_range_slider = None
        self._build_ui()

    def __del__(self):
        self.destroy()

    def destroy(self):
        self._timeline = None
        if self._scene_start_frame_widget:
            self._scene_start_frame_widget.destroy()
            self._scene_start_frame_widget = None
        if self._scene_end_frame_widget:
            self._scene_end_frame_widget.destroy()
            self._scene_end_frame_widget = None
        if self._frame_range_slider:
            self._frame_range_slider.destroy()
            self._frame_range_slider = None
        self._scene_start_model = None
        self._scene_end_model = None

    def _build_ui(self):
        with ui.HStack(height=24):
            self._scene_start_model = TimelineValueModel(omni.timeline.TimelineEventType.START_TIME_CHANGED)
            self._scene_start_frame_widget = ui.StringField(
                self._scene_start_model, height=20, width=80, style={"margin_height": 2}
            )
            ui.Spacer(width=4)
            self._frame_range_slider = FrameRangeSlider()
            ui.Spacer(width=4)
            self._scene_end_model = TimelineValueModel(omni.timeline.TimelineEventType.END_TIME_CHANGED)
            self._scene_end_frame_widget = ui.StringField(
                self._scene_end_model, height=20, width=80, style={"margin_height": 2}, identifier="scene_end"
            )


class Scrubber:

    @staticmethod
    def get_style(is_presenter: bool):
        style = {
            "TimelineWidget.Scrubber.FrameRectangle": {"background_color": 0xFFFF7E09},
            "TimelineWidget.Scrubber.FrameShadowRectangle": {"background_color": 0x44AA8820},
            "TimelineWidget.Scrubber.FrameLine": {"border_width": 2, "color": 0xFFFF7E09},
        }
        style_presenter = {
            "TimelineWidget.Scrubber.FrameRectangle": {"background_color": 0xFF2784EB},
            "TimelineWidget.Scrubber.FrameShadowRectangle": {"background_color": 0x442080AB},
            "TimelineWidget.Scrubber.FrameLine": {"border_width": 2, "color": 0xFF2784EB},
        }
        return style_presenter if is_presenter else style

    def __init__(self, width, timeline_widget):
        self._settings = carb.settings.get_settings()
        self._timeline_widget = timeline_widget
        self._timeline = omni.timeline.get_timeline_interface()
        self._placer = None
        self._frame_number_label = None
        self._body = None
        self._width = width
        self._frame_number_placer = None
        self._frame_number_stack = None
        self._number_of_digits = None
        self._frame_number_rectangle = None
        self._frame_number_container = None
        self._frame_number = -1
        self._widget = ui.Frame()
        self._widget.set_build_fn(self._build_ui)
        self._widget.rebuild()

    def destroy(self):
        if self._placer:
            self._placer.destroy()
            self._placer = None
        if self._frame_number_placer:
            self._frame_number_placer.destroy()
            self._frame_number_placer = None

        self._frame_number_rectangle = None
        self._frame_number_container = None
        self._body = None
        self._timeline = None
        self._timeline_widget = None

    def __del__(self):
        self.destroy()

    def rebuild(self):
        self._widget.rebuild()

    def _build_ui(self):
        style = Scrubber.get_style(self._timeline_widget.am_i_presenter())
        self._placer = ui.Placer(draggable=False)
        with self._placer:
            with ui.ZStack():
                self._body = ui.Rectangle(
                    width=max(2, self._width),
                    style=style,
                    style_type_name_override="TimelineWidget.Scrubber.FrameShadowRectangle",
                )
                ui.Line(
                    style=style,
                    style_type_name_override="TimelineWidget.Scrubber.FrameLine",
                    alignment=ui.Alignment.LEFT,
                )
                self._frame_number_placer = ui.Placer(offset_x=ui.Pixel(-self.get_frame_number_width() * 0.5 + 0.5))
                with self._frame_number_placer:
                    self._frame_number_stack = ui.ZStack()
                    self._frame_number_stack.width = ui.Pixel(self.get_frame_number_width())
                    with self._frame_number_stack:
                        with ui.VStack():
                            self._frame_number_rectangle = ui.Rectangle(
                                height=14,
                                width=ui.Pixel(self.get_frame_number_width()),
                                style=style,
                                style_type_name_override="TimelineWidget.Scrubber.FrameRectangle",
                            )
                            self._frame_number_triangle = ui.Triangle(
                                height=6,
                                width=ui.Pixel(self.get_frame_number_width()),
                                style=style,
                                style_type_name_override="TimelineWidget.Scrubber.FrameRectangle",
                                alignment=ui.Alignment.CENTER_BOTTOM,
                            )
                        self._frame_number_label = ui.Label(
                            get_display_str(
                                self._timeline.get_time_codes_per_seconds(), self.get_timeline_frame_number()
                            ),
                            style=style,
                            style_type_name_override="TimelineWidget.FrameNumberLabel",
                            alignment=ui.Alignment.CENTER_TOP,
                        )
        self._placer.set_offset_x_changed_fn(self.on_offset_x_changed)
        self._sync_from_timeline()

    def get_frame_number_width(self):
        frame_number = self.get_number_of_digits() if get_time_display() == TimeDisplay.FRAMES else 10
        return frame_number * TimelineWidgetStyle.FONT_SIZE * 0.6

    def get_number_of_digits(self):
        frame_number = self.get_timeline_frame_number()
        number_of_digits = abs(self._timeline_widget.get_number_of_digits(frame_number))
        number_of_digits = max(3, number_of_digits + 1)
        return number_of_digits

    def on_offset_x_changed(self, x):
        number_of_digits = self.get_number_of_digits()
        if self._number_of_digits == number_of_digits:
            return
        self._number_of_digits = number_of_digits
        width = ui.Pixel(self.get_frame_number_width())
        self._frame_number_rectangle.width = width
        self._frame_number_triangle.width = width
        self._frame_number_placer.offset_x = ui.Pixel(-self.get_frame_number_width() * 0.5 + 0.5)

    def get_timeline_frame_number(self):
        frame_rate = self._timeline.get_time_codes_per_seconds()
        frame_number = round(self._timeline.get_tentative_time() * frame_rate)
        return frame_number

    def get_frame_number(self):
        return self._frame_number

    def set_frame_number(self, frame_number):
        # view range
        fps = self._timeline.get_time_codes_per_seconds()
        start_frame = self._timeline.get_zoom_start_time() * fps
        end_frame = self._timeline.get_zoom_end_time() * fps
        if end_frame <= start_frame:
            return
        self._frame_number = frame_number

        if self._frame_number_label:
            self._frame_number_label.text = get_display_str(
                self._timeline.get_time_codes_per_seconds(), self._frame_number
            )

        if self._placer:
            relative_frame_number = self._frame_number - round(start_frame)
            self._placer.offset_x = self._width * relative_frame_number

    def _sync_from_timeline(self):
        frame_number = self.get_timeline_frame_number()
        self.set_frame_number(frame_number)


class TimelineWidget:
    UNIT_WIDTH_MIN = 20
    UNIT_STEP_SIZES = [1, 2, 4, 5, 10]
    SCRUBBER_HEIGHT = 18

    def __init__(self, parent_window):
        self._timeline = omni.timeline.get_timeline_interface()
        self._style = TimelineWidgetStyle.get_style()
        self._scrubber = None
        self._top_container = None
        self._bottom_container = None
        self._frame_range_widget = None
        self._unit_width = None
        self._unit_width_min = self.UNIT_WIDTH_MIN
        self._unit_step = 1
        self._timeline_time_changed_sub = None
        self._timeline_time_ticked_sub = None
        self._timeline_time_stop_sub = None
        self._timeline_start_time_changed_sub = None
        self._timeline_end_time_changed_sub = None
        self._timeline_fps_sub = None
        self._timeline_zoom_sub = None
        self._subscribed = False
        self._parent_window = parent_window
        self._drag_frame_start = False
        # Subscribe to specific USD stage events via Events 2.0
        ed = carb.eventdispatcher.get_eventdispatcher()
        self._usd_ctx = omni.usd.get_context()
        self._stage_subs = [
            ed.observe_event(
                observer_name="timeline_widget:stage_selection_changed",
                event_name=self._usd_ctx.stage_event_name(omni.usd.StageEventType.SELECTION_CHANGED),
                on_event=lambda e: self._on_selection_changed(),
            ),
            ed.observe_event(
                observer_name="timeline_widget:stage_opened",
                event_name=self._usd_ctx.stage_event_name(omni.usd.StageEventType.OPENED),
                on_event=lambda e: self._on_stage_opened(),
            ),
        ]
        self._settings = carb.settings.get_settings()
        self._line_y = 0
        self._line_moving = False
        self._modifier = KEYBOARD_MODIFIER_FLAG_SHIFT
        self._keyframe_widget = KeyframeWidget(self)
        self._keyframe_slider = KeyframeSlider(self._keyframe_widget)
        self._keyframe_listener = KeyFrameListener.get_instance()
        self._end_frame = 0
        self._begin_frame = 0
        self._begin_group = False
        self._popup_menu = None
        self._press_on_slider = False
        self._is_listener = False
        self._live_session = None

        self._build_ui()

    def __del__(self):
        self.destroy()

    def destroy(self):  # pragma: no cover
        self._settings = None
        self._timeline = None
        self._parent_window = None
        self._keyframe_listener = None

        self._stage_subs = None
        self._time_setting_sub = None
        self._timeline_time_changed_sub = None
        self._timeline_time_ticked_sub = None
        self._timeline_time_stop_sub = None
        self._timeline_start_time_changed_sub = None
        self._timeline_end_time_changed_sub = None
        self._timeline_tentative_sub = None
        self._timeline_fps_sub = None
        self._timeline_zoom_sub = None
        self._subscribed = False
        self._keyframe_slider = None
        self._popup_menu = None

        if self._live_session:
            self._live_session.deregister_status_changed_fn(self._on_live_session)
            self._live_session = None

        if self._scrubber:
            self._scrubber.destroy()
            self._scrubber = None
        if self._top_container:
            self._top_container.destroy()
            self._top_container = None

        if self._bottom_container:
            self._bottom_container.destroy()
            self._bottom_container = None

        if self._frame_range_widget:
            self._frame_range_widget.destroy()
            self._frame_range_widget = None

        if self._keyframe_widget:
            self._keyframe_widget.destroy()
            self._keyframe_widget = None

    def get_style(self):
        return self._style

    def rebuild_top_container(self):
        self._top_container.rebuild()

    def resize_width(self):
        self._bottom_container.rebuild()
        # OM-45784: top container ui should rebuild after width changed

    def resize_height(self, delta):
        new_height = max(30, self._top_container.height + delta)
        self._top_container.height = ui.Length(new_height)
        self._top_container.rebuild()

    def rebuild(self):
        self._bottom_container.rebuild()
        self._top_container.rebuild()

    def subscribe_to_timeline_events(self):
        if self._subscribed:
            return

        # Note: CURRENT_TIME_CHANGED is not dispatched in Events 2.0 adapter; rely on CURRENT_TIME_TICKED/STOP
        self._timeline_time_ticked_sub = self._timeline.get_timeline_event_stream().create_subscription_to_pop_by_type(
            event_type=omni.timeline.TimelineEventType.CURRENT_TIME_TICKED,
            fn=self._on_timeline_time_changed,
            name="Timeline Widget Time Ticked",
        )
        self._timeline_time_stop_sub = self._timeline.get_timeline_event_stream().create_subscription_to_pop_by_type(
            event_type=omni.timeline.TimelineEventType.STOP,
            fn=self._on_timeline_time_changed,
            name="Timeline Widget Time Stop",
        )
        self._timeline_tentative_sub = self._timeline.get_timeline_event_stream().create_subscription_to_pop_by_type(
            event_type=omni.timeline.TimelineEventType.TENTATIVE_TIME_CHANGED,
            fn=self._on_timeline_time_changed,
            name="Timeline Widget Tentative Time Changed",
        )
        self._timeline_start_time_changed_sub = (
            self._timeline.get_timeline_event_stream().create_subscription_to_pop_by_type(
                event_type=omni.timeline.TimelineEventType.START_TIME_CHANGED,
                fn=self._on_timeline_start_time_changed,
                name="Timeline Widget Start Time Changed",
            )
        )
        self._timeline_end_time_changed_sub = (
            self._timeline.get_timeline_event_stream().create_subscription_to_pop_by_type(
                event_type=omni.timeline.TimelineEventType.END_TIME_CHANGED,
                fn=self._on_timeline_end_time_changed,
                name="Timeline Widget End Time Changed",
            )
        )
        self._timeline_fps_sub = self._timeline.get_timeline_event_stream().create_subscription_to_pop_by_type(
            event_type=omni.timeline.TimelineEventType.TIME_CODE_PER_SECOND_CHANGED,
            fn=self._on_timeline_fps_changed,
            name="Timeline Widget TimeCode per Second Changed",
        )
        self._timeline_zoom_sub = self._timeline.get_timeline_event_stream().create_subscription_to_pop_by_type(
            omni.timeline.TimelineEventType.ZOOM_CHANGED,
            fn=self._on_timeline_zoom_changed,
            name="Timeline Widget Zoom Changed",
        )
        self._subscribed = True

    def get_zoom_range_length(self):
        len = self._timeline.get_zoom_end_time() - self._timeline.get_zoom_start_time()
        return len if len > 0 else 1

    def offset_to_frame(self, offset) -> float:
        fps = self._timeline.get_time_codes_per_seconds()
        frame_number = offset / self._frame_width
        frame_number = min(frame_number, self.get_zoom_range_length() * fps)
        frame_number = max(frame_number, 0)
        return frame_number + self._timeline.get_zoom_start_time() * fps

    def _build_ui(self):
        cover_style = {
            "Rectangle": {"background_color": 0x33FFFFFF, "margin": 0, "padding": 0},
        }
        with ui.HStack():
            ui.Spacer(width=2)
            with ui.ZStack():
                with ui.Stack(ui.Direction.BOTTOM_TO_TOP):
                    self.build_ui_bottom_container()
                    self.build_ui_top_container()
                # cover stack for timeline live session
                self._cover_stack = ui.ZStack(content_clipping=True)
                with self._cover_stack:
                    ui.Rectangle(style=cover_style)

        if self._live_session:
            is_sync = self._live_session.is_sync_enabled()
            is_presenter = self._live_session.am_i_presenter()
            self._on_live_session(is_presenter, is_sync)
        else:
            self._cover_stack.visible = False

    def _on_timeline_time_changed(self, event):
        if self._scrubber:
            actual_frame_number = round(
                self._timeline.get_time_codes_per_seconds() * self._timeline.get_tentative_time()
            )
            if self._scrubber.get_frame_number() != actual_frame_number:
                self.set_ui_frame_number(actual_frame_number)

    def build_ui_top_container(self):
        self._top_container = ui.CanvasFrame(
            style=self._style, style_type_name_override="TimelineWidget.MainFrame", draggable=False
        )
        self._top_container.set_build_fn(self.on_top_container_built)
        self._top_container.set_computed_content_size_changed_fn(self.rebuild_top_container)

    def build_ui_bottom_container(self):
        self._bottom_container = ui.Frame()
        self._bottom_container.set_build_fn(self.on_bottom_container_built)

    def on_bottom_container_built(self):
        if self._frame_range_widget:
            self._frame_range_widget.destroy()
        self._frame_range_widget = FrameRangeWidget()

    def _on_timeline_start_time_changed(self, *args):
        self.rebuild()

    def _on_timeline_end_time_changed(self, *args):
        self.rebuild()

    def _on_timeline_fps_changed(self, *args):
        self.rebuild()

    def _on_timeline_zoom_changed(self, *args):
        self.rebuild()

    def on_top_container_built(self):
        self.build_timeline_ui_components()
        self.subscribe_to_timeline_events()

    def get_number_of_digits(self, number):
        if number == 0:
            return 1
        return int(math.log10(abs(number)))

    def build_timeline_ui_components(self):
        fps = self._timeline.get_time_codes_per_seconds()
        end_display_str = get_display_str(fps, self._timeline.get_zoom_end_time() * fps)
        number_of_digits = len(end_display_str)
        frame_numbers_label_size = number_of_digits * TimelineWidgetStyle.FONT_SIZE * 0.6
        self._unit_width_min = frame_numbers_label_size + 10
        view_range_length = self.get_zoom_range_length() * fps
        if view_range_length > 0:
            self._unit_width = self._top_container.computed_width / (view_range_length + 1)
        else:
            self._unit_width = self._top_container.computed_width
        self._unit_step = 1
        if self._unit_width < self._unit_width_min:
            self.find_fitting_unit_width(self._top_container.computed_width)
        if self._unit_step == 0:
            return

        self._frame_width = self._unit_width / self._unit_step

        with ui.ZStack():
            ui.Rectangle(style=self._style, style_type_name_override="TimelineWidget.BackgroundRectangle")
            with ui.VStack():
                ui.Spacer(height=self.SCRUBBER_HEIGHT)
                with ui.ZStack():
                    ui.Rectangle(
                        style=self._style,
                        style_type_name_override="TimelineWidget.HorizontalRectangle",
                    )
                    self._keyframe_widget.build_ui()
                    self._keyframe_slider.build_ui()
                    self._keyframe_slider.visible = False

            with ui.HStack():
                small_tick_width = max(4, self._frame_width)
                small_ticks_number = int(self._unit_width / small_tick_width)
                small_tick_width = ui.Pixel(self._unit_width / small_ticks_number)
                start_frame = int(self._timeline.get_zoom_start_time() * fps)
                end_frame = round(self._timeline.get_zoom_end_time() * fps) + 1
                for i in range(start_frame, end_frame, self._unit_step):
                    display_str = get_display_str(fps, i)
                    with ui.VStack(width=self._unit_width):
                        with ui.HStack():
                            ui.Line(
                                style=self._style,
                                width=2,
                                style_type_name_override="TimelineWidget.Tick.Line",
                                alignment=ui.Alignment.LEFT,
                            )
                            ui.Label(
                                display_str,
                                height=0,
                                style=self._style,
                                style_type_name_override="TimelineWidget.Tick.FrameNumberLabel",
                                alignment=ui.Alignment.LEFT_TOP,
                            )
                        ui.Spacer(height=ui.Percent(15))
                        if small_ticks_number > 1:
                            with ui.HStack():
                                for i in range(0, small_ticks_number):
                                    ui.Line(
                                        style={"color": 0x44BCB9A5},
                                        width=small_tick_width,
                                        alignment=ui.Alignment.LEFT,
                                    )

            self._scrubber = Scrubber(self._frame_width, self)

        self._top_container.set_mouse_pressed_fn(self._on_mouse_pressed)
        self._top_container.set_mouse_moved_fn(self._on_mouse_moved)
        self._top_container.set_mouse_released_fn(self._on_mouse_released)

    def _on_mouse_pressed(self, x, y, button_index, mod):
        if self._is_listener:
            return
        if y < (self._top_container.screen_position_y + self.SCRUBBER_HEIGHT):
            # if pressed on the top part of timeline, set frame num
            self.set_time_from_mouse_pos(x, button_index == 2)
            self._drag_frame_start = True
        else:
            # if pressed on the bottom part of timeline, process keyframe
            self._drag_frame_start = False
            if self._timeline.is_playing():
                self._timeline.pause()

            self._press_on_slider = False
            if self._keyframe_slider.visible:
                if self._keyframe_slider.inside(self.screen_to_timeline(x)):
                    self._press_on_slider = True
                else:
                    # if not press on key slider, hide it
                    execute("ShowKeyframeSlider", slider=self._keyframe_slider, visible=False)

            if button_index == 0:
                if mod & self._modifier:
                    self._begin_group = True
                    omni.kit.undo.begin_group()
                    self._begin_frame = int(self.screen_to_timeline(x) / self._frame_width)
                    self._end_frame = self._begin_frame
                    execute(
                        "SetKeyframeSlider", slider=self._keyframe_slider, start=self._begin_frame, end=self._end_frame
                    )
            elif button_index == 1:
                self._show_popup_menu()

    def _on_live_session(self, is_presenter: bool, is_sync: bool):
        self._is_listener = is_sync and not is_presenter
        self._cover_stack.visible = self._is_listener
        if self._scrubber:
            self._scrubber.rebuild()

    def set_live_session(self, live_session: TimelineLiveSession):
        self._live_session = live_session
        self._live_session.register_status_changed_fn(self._on_live_session)

    def am_i_presenter(self) -> bool:
        return self._live_session.am_i_presenter() if self._live_session else False

    def _on_mouse_moved(self, x, y, m, pressed):
        if self._is_listener:
            return
        if self._drag_frame_start:
            self.set_time_from_mouse_pos(x)
        elif pressed and m & self._modifier:
            self._end_frame = int(self.screen_to_timeline(x) / self._frame_width)
            self._keyframe_slider.set_unit_range(self._begin_frame, self._end_frame)

    def _on_mouse_released(self, x, y, button_index, mod):
        if self._is_listener:
            return
        if self._begin_group:
            self._begin_group = False
            if self._end_frame != self._begin_frame:
                # mouse draged
                omni.kit.commands.execute(
                    "SetKeyframeSlider", slider=self._keyframe_slider, start=self._begin_frame, end=self._end_frame
                )
            omni.kit.undo.end_group()
        self._drag_frame_start = False
        self._scrubber.rebuild()

    def screen_to_timeline(self, screen_x):
        return self._top_container.screen_to_canvas_x(screen_x)

    def get_frame_width(self):
        return self._frame_width

    def get_content_width(self):
        return self._top_container.computed_content_width

    def find_closest_step_size(self, n):
        for step_size in self.UNIT_STEP_SIZES:
            if n <= step_size:
                return step_size

    def get_next_step_size(self, n):
        index = self.UNIT_STEP_SIZES.index(n)
        index += 1
        if index == len(self.UNIT_STEP_SIZES):
            index = 0
        return self.UNIT_STEP_SIZES[index]

    def compute_unit_step(self, size):
        number_of_digits_minus_one = int(math.log10(size))
        ten_power = pow(10, number_of_digits_minus_one)
        first_digit = size // ten_power
        step_size = self.find_closest_step_size(first_digit)
        if step_size * ten_power < size:
            step_size = self.get_next_step_size(step_size)
        return step_size * ten_power

    def find_fitting_unit_width(self, top_container_width):
        fitting_units_number = top_container_width / self._unit_width_min
        if fitting_units_number < 1:
            self._unit_step = 0
            return

        frames = self.get_zoom_range_length() * self._timeline.get_time_codes_per_seconds() + 1
        unit_step = math.ceil(frames / fitting_units_number)
        if unit_step == 0:
            return

        self._unit_step = self.compute_unit_step(unit_step)
        drawn_units_number = frames / self._unit_step
        self._unit_width = top_container_width / drawn_units_number

    def set_time_from_mouse_pos(self, x, tentative: bool = False):
        frame_number = round(self.offset_to_frame(self.screen_to_timeline(x)))
        if self._scrubber.get_frame_number() != frame_number:
            self.set_ui_frame_number(frame_number)
            self.set_time(frame_number, tentative)
            if self._timeline.is_playing():
                self._timeline.pause()

    def set_ui_frame_number(self, actual_frame_number):
        self._scrubber.set_frame_number(actual_frame_number)

    def set_time(self, actual_frame_number, tentative: bool = False):
        frames_per_second = self._timeline.get_time_codes_per_seconds()
        if tentative:
            self._timeline.set_tentative_time(actual_frame_number / frames_per_second)
        else:
            self._timeline.set_current_time(actual_frame_number / frames_per_second)

    def get_next_key_time(self):
        cur_time = self._timeline.get_current_time()
        return self._keyframe_widget.get_next_key_time(cur_time)

    def get_previous_key_time(self):
        cur_time = self._timeline.get_current_time()
        return self._keyframe_widget.get_pre_key_time(cur_time)

    def _on_selection_changed(self):
        if self._parent_window.visible and self._keyframe_widget:
            self._keyframe_widget.rebuild()
            self._keyframe_slider.visible = False

    def _on_stage_opened(self):
        if self._timeline.is_playing():
            self._timeline.pause()
        self.rebuild()

    @property
    def modifier(self):
        return self._modifier

    @modifier.setter
    def modifier(self, value):
        self._modifier = value

    def _show_popup_menu(self):
        if self._press_on_slider:
            has_key = len(self._keyframe_slider.get_nodes()) > 0
        else:
            target_frame = self._timeline.get_tentative_time() * self._timeline.get_time_codes_per_seconds()
            start_pos = target_frame * self._frame_width
            has_key = len(self._keyframe_widget.get_nodes(start_pos, start_pos + self._frame_width)) > 0
        has_clip = get_curvekey_clipboard().get_prim_count() > 0
        if not self._popup_menu:
            self._popup_menu = omni.ui.Menu("Timeline popup")
            with self._popup_menu:
                ui.MenuItem("Add key", triggered_fn=self._on_add_key)
                self._delete_menu = ui.MenuItem("Delete key", triggered_fn=self._on_delete_key, enabled=has_key)
                self._copy_menu = ui.MenuItem("Copy key", triggered_fn=self._on_copy_key, enabled=has_key)
                self._paste_menu = ui.MenuItem("Paste key", triggered_fn=self._on_paste_key, enabled=has_clip)
        else:
            self._delete_menu.enabled = has_key
            self._copy_menu.enabled = has_key
            self._paste_menu.enabled = has_clip
        self._popup_menu.show()

    def _on_add_key(self):
        usd_context = omni.usd.get_context()
        stage = usd_context.get_stage()
        if not stage:
            carb.log_info("Try to add animation keys while the scene stage is invalid.")
            return
        selection = usd_context.get_selection()
        prim_paths = selection.get_selected_prim_paths()
        target_time = self._timeline.get_tentative_time() * self._timeline.get_time_codes_per_seconds()
        add_xform_keys(prim_paths, stage, time=Usd.TimeCode(target_time))

    def _on_delete_key(self):
        usd_context = omni.usd.get_context()
        stage = usd_context.get_stage()
        if not stage:
            carb.log_info("Try to remove animation keys while the scene stage is invalid.")
            return

        fps = self._timeline.get_time_codes_per_seconds()
        prim_paths = self._keyframe_listener.get_listen_prims()
        if self._press_on_slider:
            start_unit, end_unit = self._keyframe_slider.get_unit_range()
            start_frame = start_unit + self._timeline.get_zoom_start_time() * fps
            end_frame = end_unit + self._timeline.get_zoom_start_time() * fps
        else:
            start_frame = self._timeline.get_tentative_time() * fps
            end_frame = start_frame + 1
        remove_all_keys(prim_paths, stage, Usd.TimeCode(start_frame), Usd.TimeCode(end_frame))

    def _on_copy_key(self):
        stage = omni.usd.get_context().get_stage()
        fps = self._timeline.get_time_codes_per_seconds()
        if self._press_on_slider:
            start_unit, end_unit = self._keyframe_slider.get_unit_range()
            start_frame = Usd.TimeCode(start_unit + self._timeline.get_zoom_start_time() * fps)
            set_curvekey_clipboard(stage, None, Usd.TimeCode(start_frame), end_unit - start_unit)
        else:
            cur_frame = self._timeline.get_current_time() * fps
            set_curvekey_clipboard(stage, None, Usd.TimeCode(cur_frame))

    def _on_paste_key(self):
        usd_context = omni.usd.get_context()
        paste_time = self._timeline.get_tentative_time() * self._timeline.get_time_codes_per_seconds()
        execute("PasteAnimCurveKeys", stage=usd_context.get_stage(), paths=None, time=Usd.TimeCode(paste_time))
