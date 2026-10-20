import types
import weakref

import carb
import omni.kit.widget.timeline.scripts.timeline_view_scrubber as scrubber_lib
import omni.timeline
from omni import ui
from omni.kit.widget.timeline import (
    Logger,
    RangeSlider,
    TimelineView,
    TimelineViewElement,
    TimelineViewTopPlacerDefault,
)

from . import curve_editor_globals as globals
from .curve_editor_curves import CurveListView
from .curve_editor_scrubber import CurveEditorScrubber
from .live_session import TimelineLiveSession
from .timeline_merge_core_settings import TimelineMergeCoreSettings
from .timeline_ruler import Ruler

scrubber_lib.CLAMP_TO_VISIBLE_RANGE = False
ZOOM_SCALE_PER_PIXEL = 1.01  # only for ALT zoom


class CurveEditorBottom(TimelineViewElement):

    def __init__(self, view: TimelineView):
        super().__init__(view)
        self._dragging = False
        self._alt_dragging = False
        self._unfinished_scale = 1.0
        self._scroll_x = 0.0
        self._scroll_y = 0.0
        self._curve_list_view = CurveListView(view)
        self._rebuild_trigger_frame = None
        self._logger_debug = True

    def build_ui(self):
        # Lower frame needs to be set as "self._frame" and set by this function BEFORE calling super().build_ui()
        bottom_frame = self._view.get_timeline_bottom_frame()
        bottom_frame.horizontal_clipping = True
        bottom_frame.vertical_clipping = True
        bottom_frame.name = "timeline_bottom_frame"
        with bottom_frame:
            self._frame = ui.Placer(
                width=ui.Percent(100),
                height=ui.Percent(100),
                mouse_pressed_fn=self._on_mouse_pressed,
                mouse_released_fn=self._on_mouse_released,
                mouse_moved_fn=self._on_mouse_moved,
                mouse_wheel_fn=self._on_mouse_wheel,
                scroll_x_changed_fn=self._on_scroll_x_changed,
                scroll_y_changed_fn=self._on_scroll_y_changed,
            )
            self._scroll_x = 0
            self._scroll_y = 100
            super().build_ui()

            with self.get_bottom_frame():
                self._rebuild_trigger_frame = ui.Frame(build_fn=self._on_frame_built)
                with self._rebuild_trigger_frame:
                    self._curve_list_view.build_ui()

    # Do not call self._curve_list_view.update_ui() directly. Pack the calls of it by _rebuild_trigger_frame's build_fn.
    # I am still not clear about the time order of the cooperation. Just use it before problem exposes.
    def _lazy_update_ui(self):
        if self._rebuild_trigger_frame:
            self._rebuild_trigger_frame.rebuild()

    def update_ui(self):
        super().update_ui()
        self._lazy_update_ui()

    def set_x(self, x):
        # relam - The x value for this frame is actually set by the PlacerTop
        # self._frame.offset_x = -x
        return

    def set_y(self, y):
        self._frame.offset_y = -y

    def get_x(self):
        return -self._frame.offset_x

    def get_y(self):
        return -self._frame.offset_y

    def scroll_frame(self, x, y):
        self.set_x(x)
        self.set_y(y)

    def get_bottom_frame(self):
        return self._frame

    def transform_timeline_to_position(self, pos, frame_width=-1, snap=False):
        return self._view.transform_timeline_to_position(pos, frame_width, snap)

    def _on_frame_built(self):
        self._curve_list_view.raise_update_flag()

    def _on_mouse_pressed(self, x, y, button, mod):
        self.enable_scrubber(False)
        if button == 2:
            self._dragging = True
            self._pressed_range_begin = self._view.range_begin()
            self._pressed_range_end = self._view.range_end()
            self._pressed_x = x
            self._drag_y = y
            pressed_pixel_begin = self._view.transform_timeline_to_position_morph(
                self._pressed_range_begin, snap=False
            )  # temptest. todo. try the native version function again.
            pressed_pixel_end = self._view.transform_timeline_to_position_morph(self._pressed_range_end, snap=False)
            self._delta_range_ratio = (self._pressed_range_end - self._pressed_range_begin) / (
                pressed_pixel_end - pressed_pixel_begin
            )
        elif button == 1:
            if mod == carb.input.KEYBOARD_MODIFIER_FLAG_ALT:
                self._alt_dragging = True
                self._alt_pressed_x = x
                self._alt_pressed_y = y
                self._alt_drag_x = x
                self._alt_drag_y = y
                self._alt_zoom_center_time = self._view.transform_window_to_timeline(x, snap=False)
                self._alt_delta_range_begin = self._view.range_begin() - self._alt_zoom_center_time
                self._alt_delta_range_end = self._view.range_end() - self._alt_zoom_center_time

    def _on_mouse_released(self, x, y, button, mod):
        self.enable_scrubber(True)
        if button == 2 and self._dragging is True:
            self._dragging = False
            window = ui.Workspace.get_window("Curve Editor")
            """
            def print_widget_tree(widget, tabs=0):
                def print_widget(widget):
                    text = ""
                    for i in range(0, tabs):
                        text += "  "

                    if widget.name == "":
                        text += "None"
                    else:
                        text += widget.name

                    text += "  " + str(widget.__class__)

                    print(text)

                print_widget(widget)

                for child in ui.Inspector.get_children(widget):
                    print_widget_tree(child, tabs + 1)

            print_widget_tree(window.frame)
            """
        elif button == 1 and self._alt_dragging == True:
            self._alt_dragging = False

    def _on_mouse_moved(self, x, y, button, mod):
        need_update_ui = False

        if self._dragging is True:
            if self._drag_y != y:
                one_frame_delta_y = y - self._drag_y
                self._drag_y = y
                self._curve_list_view._on_view_pan_y(one_frame_delta_y)
                need_update_ui = True

            if self._pressed_x != x:
                # get move magnitude in pixels.
                delta_x = x - self._pressed_x
                self._on_view_pan_x(delta_x)
                need_update_ui = True

        elif self._alt_dragging == True:
            if self._alt_drag_y != y:
                one_frame_delta_y = y - self._alt_drag_y
                self._alt_drag_y = y
                scale_y = pow(ZOOM_SCALE_PER_PIXEL, one_frame_delta_y)
                self._on_view_zoom_y(scale_y)
                need_update_ui = True

            if self._alt_drag_x != x:
                self._alt_drag_x = x
                delta_x = x - self._alt_pressed_x
                scale_x = pow(ZOOM_SCALE_PER_PIXEL, -delta_x)
                self._on_view_zoom_x(scale_x)
                need_update_ui = True

        if need_update_ui:
            self._lazy_update_ui()

    # Do x zooming. But it can only get integer time range.
    # scale is relative to drag center
    def _on_view_zoom_x(self, scale: float):
        delta_range_begin = scale * self._alt_delta_range_begin
        delta_range_end = scale * self._alt_delta_range_end
        rb = self._alt_zoom_center_time + delta_range_begin
        re = self._alt_zoom_center_time + delta_range_end
        self._view.set_range(rb, re)

    # Do y zooming.
    # scale is relative to current y.
    def _on_view_zoom_y(self, scale: float):
        local_zoom_center_y = self._alt_pressed_y - self._view.get_bottom_frame().screen_position_y
        self._curve_list_view._on_view_zoom(scale, local_zoom_center_y)

    def _on_view_pan_x(self, offset_x):
        # change timeline range according to mouse move pixels.
        delta_range = offset_x * self._delta_range_ratio
        rb = self._pressed_range_begin - delta_range
        re = self._pressed_range_end - delta_range
        # the result of set_range() is not always rb, re, because the result is currently integer only.
        self._view.set_range(rb, re)

        self._curve_list_view._on_view_pan_x(offset_x)

    def _on_scroll_x_changed(self, x):
        # self._frame.scroll_x = self._scroll_x
        return

    def _on_scroll_y_changed(self, y):
        # self._frame.scroll_y = self._scroll_y
        return

    def _on_mouse_wheel(self, x, y, mod):
        if mod == 0:
            zoom_scale = self._unfinished_scale
            # for touch pad, y may be float. Not just 1 or -1.
            zoom_scale *= pow(1.1, -y)

            self._on_view_zoom(zoom_scale)

            self._lazy_update_ui()

    # Do uniform zooming. But it can only get integer time range.
    def _on_view_zoom(self, scale: float):
        zoom_center = self._view.get_current_mouse_coords()
        local_zoom_center_y = zoom_center[1] - self._view.get_bottom_frame().screen_position_y

        # x zoom
        time = self._view.transform_window_to_timeline(zoom_center[0], snap=False)
        delta_range_begin = self._view.range_begin() - time
        delta_range_end = self._view.range_end() - time
        delta_range_begin *= scale
        delta_range_end *= scale
        rb = time + delta_range_begin
        re = time + delta_range_end
        self._view.set_range(rb, re)
        # self._unfinished_scale is a workaround of the problem that set_range() only produces integer range. It is not perfect because the center location can not be cached.
        real_range = self._view.range_end() - self._view.range_begin()
        expected_range = re - rb
        self._unfinished_scale = expected_range / real_range

        # y zoom. do after self._unfinished_scale is ready.
        self._curve_list_view._on_view_zoom(scale / self._unfinished_scale, local_zoom_center_y)


class CurveEditorTimeline(TimelineView):
    def __init__(self, parent_view, parent_window):
        super().__init__(weakref.proxy(parent_window))
        self.set_timeline_top(TimelineViewTopPlacerDefault(self))
        self._curve_editor_bottom = CurveEditorBottom(self)
        self.set_timeline_bottom(self._curve_editor_bottom)
        self._curve_editor_view_wp = weakref.ref(parent_view)

        # RANGE is defined as the part of the entire TIMELINE that is visible to the user
        self._range_begin = TimelineMergeCoreSettings.get_instance().range_begin
        self._range_end = TimelineMergeCoreSettings.get_instance().range_end
        if self._range_end <= self._range_begin:
            self._range_end = self._range_begin + 1
        self._range_begin -= 5
        self._range_end += 5
        self._timeline_begin = self._range_begin
        self._timeline_end = self._range_end

        self._ruler = None

        self._live_session = None
        self._is_listener = False
        self._listener_stack = None
        self._user_circle = None
        self._short_user_name = None
        self._user_name = None

    def get_curve_editor_view(self):
        return self._curve_editor_view_wp()

    def _on_timeline_event(self, evt):
        if self._curve_editor_bottom._curve_list_view.is_timeline_node_mode():
            return

        if (
            evt.type == int(omni.timeline.TimelineEventType.CURRENT_TIME_CHANGED)
            or evt.type == int(omni.timeline.TimelineEventType.CURRENT_TIME_TICKED)
            or evt.type == int(omni.timeline.TimelineEventType.STOP)
        ):
            super()._on_timeline_event(evt)
        elif evt.type == int(omni.timeline.TimelineEventType.TENTATIVE_TIME_CHANGED):
            self._timeline_event_set_time(self.get_tentative_time())

    # try to give TimelineView some useful interface
    def range_begin(self):
        return self._range_begin

    # try to give TimelineView some useful interface
    def range_end(self):
        return self._range_end

    # Seems sometimes range is empty. So percentage calculation is not possible. Try to skip the situation when trouble comes.
    def is_range_valid(self):
        return self._range_begin < self._range_end

    def scroll_to_range(self, range_begin, range_end):
        begin = self.transform_timeline_to_position(range_begin)
        end = self.transform_timeline_to_position(range_end)
        width = end - begin
        return begin, width

    # learned from sequencer. a stub for TimelineView. override to make config setting possible.
    def set_range(self, new_begin, new_end):
        new_begin = int(new_begin)
        new_end = int(new_end)
        if new_end <= new_begin:
            new_end = new_begin + 1

        if new_begin == self._range_begin and new_end == self._range_end:
            return

        # Store the new values
        if new_begin != self._range_begin:
            TimelineMergeCoreSettings.get_instance().range_begin = new_begin
        if new_end != self._range_end:
            TimelineMergeCoreSettings.get_instance().range_end = new_end

        def set_range(new_begin, new_end):
            # TODO -- This function likely needs to get broken up more

            if new_begin == self._range_begin and new_end == self._range_end:
                # Redundant call
                return

            current_range = self.get_range()

            if new_begin != self._range_begin:
                self._range_begin = int(new_begin)
            if new_end != self._range_end:
                self._range_end = int(max(new_begin, new_end))

            self._timeline_begin = self._range_begin
            self._timeline_end = self._range_end

            range = self.get_range()
            if range > 0.0:
                self._zoom = self.get_timeline_range() / range
            else:
                self._zoom = 0

            self.update_ui()
            self.scroll_to_range(self._range_begin, self._range_end)
            self._delayed_update_scrubber_ui()

        set_range(new_begin, new_end)

    def _draw_timeline_top(self):
        draw_frame = self._timeline_view_top.get_draw_frame()
        if (
            draw_frame is None
        ):  # draw_frame is created in build callback of frame. And the callback hasn't been called yet when this function is called in some cases. And this function should not be explicitly called. It should be in frame build callback too.
            return

        if self._ruler is None:
            draw_frame.name = "timeline_view_top_draw_frame"
            with draw_frame:
                self._ruler = Ruler(style={"Line": {"color": globals.GUIDELINE_COLOR}})

        self._ruler.range = (int(self._range_begin), int(self._range_end))

    def set_live_session(self, live_session: TimelineLiveSession):
        self._live_session = live_session
        self._live_session.register_status_changed_fn(self._on_live_session)

    def _on_live_session(self, is_presenter: bool, is_sync: bool):
        self._is_listener = is_sync and not is_presenter
        is_presenter = not self._is_listener
        if self._scrubber:
            self._scrubber._set_draggable(is_presenter)
            self._scrubber._set_as_presenter_style(self._live_session.am_i_presenter())

        if self._listener_stack:
            self._update_listener_stack()

    def _update_listener_stack(self):
        if self._is_listener:
            self._user_circle.style = {"background_color": self._live_session.get_presenter_user_color()}
            self._short_user_name.text = self._live_session.get_presenter_user_short_name()
            self._user_name.text = self._live_session.get_presenter_user_name()

        self._listener_stack.visible = self._is_listener

    def build_containers(self):
        super().build_containers()
        self._build_listener_stack()
        self._update_listener_stack()

    def _build_listener_stack(self):
        self._listener_stack = ui.HStack()

        with self._listener_stack:
            ui.Spacer()
            with ui.VStack(width=1, alignment=ui.Alignment.RIGHT):
                ui.Spacer()
                with ui.ZStack(height=1, alignment=ui.Alignment.BOTTOM):
                    ui.Rectangle()
                    with ui.HStack(width=1):
                        # show presenter info
                        with ui.ZStack(height=24):
                            self._user_circle = ui.Circle(
                                radius=10,
                                size_policy=ui.CircleSizePolicy.FIXED,
                                style={"background_color": 0xFF000000},
                                alignment=ui.Alignment.CENTER,
                            )
                            self._short_user_name = ui.Label("", alignment=ui.Alignment.CENTER)
                        ui.Label(" Timeline is currently controlled by ")
                        self._user_name = ui.Label("unknown@nvidia.com")

    # learned from sequencer. a stub for TimelineView.
    def get_style(self):
        style = super().get_style()
        more_style = {
            "Timeline.ScrubberTop": {
                "color": 0xFF2784EB,
                "background_color": 0x00FF7E09,
                "border_width": 0,
                "border_radius": 0,
            },
            "Timeline.ScrubberTop:disabled": {
                "color": 0xFFFF7E09,
                "background_color": 0x00FF7E09,
                "border_width": 0,
                "border_radius": 0,
            },
            "Timeline.ScrubberLine": {
                "color": 0xFF2784EB,
                "background_color": 0xFF000000,
                "border_width": 1,
                "border_radius": 0,
            },
            "Timeline.ScrubberLine:disabled": {
                "color": 0xFFFF7E09,
                "background_color": 0xFF000000,
                "border_width": 1,
                "border_radius": 0,
            },
            "Timeline.ScrubberLine:hovered": {
                "color": 0xFF47A4FF,
                "background_color": 0xFF000000,
                "border_width": 2,
                "border_radius": 0,
            },
        }
        style.update(more_style)
        return style

    # learned from sequencer.
    def build_ui(self):
        super().build_ui()
        self._timeline_view_top.get_top_frame().set_mouse_pressed_fn(
            lambda x, y, b, m: self._on_top_mouse_pressed(x, y, b, m)
        )

        self.set_range_slider_visible(False)

    def _on_top_mouse_pressed(self, x, y, button_index, mod):
        if self._is_listener:
            return
        else:
            timeline_position = self.transform_window_to_timeline(x, snap=False)
            delta = abs(timeline_position - self.get_time())
            snap_flag = self.get_snap_to_frame()
            self.set_snap_to_frame(False)
            self._scrubber._scrubber_top.dragging = True
            self.set_time(timeline_position)
            self.set_snap_to_frame(snap_flag)

            Logger.debug(self, f"Pressed top {x}-{y}-{button_index} timeline_pos={timeline_position}")

    # learned from sequencer. a stub for TimelineView.
    def update_ui(self):
        super().update_ui()

    # learned from sequencer. a stub for TimelineView
    def _update_timeline_bottom(self):
        if super()._update_timeline_bottom() is False:
            return False

        if (
            super().get_timeline_frame().computed_width == 0
            or super().get_timeline_frame().computed_height == 0
            or super().get_timeline_zoomed_width() == 0
        ):
            # This is the abnormal situation that TimelineView does not handle gracefully. If you do not skip it here, things like transform_timeline_to_position() may cause further problem.
            return False

        return True

    def _get_curve_list_view(self):
        return self._curve_editor_bottom._curve_list_view

    def _retained_update(self, stage):
        self._get_curve_list_view()._retained_update(stage)

    def _ui_update_track_visibility(self, track, is_visible: bool):
        self._get_curve_list_view()._ui_update_track_visibility(track, is_visible)

    def _ui_raise_refit_and_update_flag(self):
        self._get_curve_list_view().raise_refit_flag()
        self._get_curve_list_view().raise_update_flag()

    def _ui_add_track(self, stage, track):
        self._get_curve_list_view()._ui_add_track(stage, track)

    def _ui_remove_track(self, track):
        self._get_curve_list_view()._ui_remove_track(track)

    def _on_fit_all(self):
        self._get_curve_list_view()._on_fit_all()
        self.update_ui()

    def _on_fit_selection(self):
        self._get_curve_list_view()._on_fit_selection()
        self.update_ui()

    def _on_fit_conditionally(self):
        self._get_curve_list_view()._on_fit_conditionally()
        self.update_ui()

    # this is modified version of TimelineView.transform_timeline_to_position(). Later it might need to expose by Ryan.
    def transform_timeline_to_position_morph(self, timeline_val, frame_width=-1, snap=False) -> float:
        timeline_range = self._timeline_end - self._timeline_begin
        if timeline_range == 0:
            return 0.0
        if frame_width <= 0:
            frame_width = self.get_timeline_zoomed_width()
        scale = float(frame_width / timeline_range)
        offset = self._timeline_begin
        if snap is True:
            position = int(timeline_val - offset) * scale
        else:
            position = (timeline_val - offset) * scale

        # do not max(position, 0). just position. This is the difference from TimelineView.transform_timeline_to_position().
        return position

    # A dummy function to counter the super class's _zoom_extents since we have our own zoom logic
    def _zoom_extents(self):
        pass

    def _on_built(self):
        if True:
            # this codepath is almost the same as super()._on_build(). The only difference is _scrubber is another type.
            if self._scrubber_frame is not None:
                self._scrubber = CurveEditorScrubber(self, self._scrubber_frame)
                self._scrubber.build_ui()

            if self._range_slider_frame is not None:
                self._range_slider = RangeSlider(self, self._range_slider_frame)
                self._range_slider.build_ui()
                self._range_slider_frame.visible = self._range_slider_visible

            self._delayed_build_ui_fn()
            self._zoom_extents()  # for now, zoom all the way out when time changes
            self._range_slider.update_ui()

        def transform_scrubber_position_to_timeline(self, pos, snap=True):
            tlv = self._timeline_view
            pos += self._scrubber_width / 2.0
            offset = tlv.get_timeline_parent_offset()
            pos += offset
            # Always make snap to False so that we set to continuous timeline's time
            timeline_time = tlv.transform_position_to_timeline(pos, snap=False)
            return timeline_time

        def transform_timeline_to_scrubber_position(self, timeline_time, snap=True):
            tlv = self._timeline_view
            offset = tlv.get_timeline_parent_offset()
            pos = tlv.transform_timeline_to_position(timeline_time, snap=False)
            pos -= offset
            pos -= self._scrubber_width / 2.0
            return pos

        self._scrubber.transform_scrubber_position_to_timeline = types.MethodType(
            transform_scrubber_position_to_timeline, self._scrubber
        )
        self._scrubber.transform_timeline_to_scrubber_position = types.MethodType(
            transform_timeline_to_scrubber_position, self._scrubber
        )

    def update_timeline_codes(self, timeline_codes: float):
        if self._curve_editor_bottom._curve_list_view.is_timeline_node_mode():
            return

        super().update_timeline_codes(timeline_codes)

    def get_tentative_time(self):
        return self._timeline.get_tentative_time() * self._timeline.get_time_codes_per_seconds()
