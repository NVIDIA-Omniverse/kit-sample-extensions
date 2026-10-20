import omni.ext
from omni import ui

from .timeline_view_component import TimelineViewRoot
from .ui_helpers import EditScope, Logger, do_later

CLAMP_TO_VISIBLE_RANGE = True
CLAMP_TO_SCENE_RANGE = False


class Scrubber:
    def __init__(self, timeline_view: TimelineViewRoot, frame):
        self._scrubber_label = None
        self._scrubber_placer_pill = None
        self._scrubber_width = 24
        self._scrubber_line = None
        self._scrubber_delay = None
        self._edit_scrubber = None
        self._left_button_down = False
        self._timeline_view = timeline_view
        self._timeline = omni.timeline.get_timeline_interface()
        self._edit_scrubber = EditScope()
        self._frame = frame
        self._enabled = True
        self._last_time = -900000
        # self._logger_debug = True

    def destroy(self):
        self._scrubber_placer_pill = None
        self._timeline_view = None
        self._frame = None

    def __del__(self):
        self.destroy()

    # -- Public funcitons

    def build_ui(self):
        self._delayed_build_ui()

    def update_ui(self):
        self._update_label()

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, on):
        self._enabled = on
        self._scrubber_placer_pill.enabled = on

    def on_timeline_event(self, new_time):
        self.update_time(new_time)

    def update_time(self, new_time):
        # This can get called BEFORE the UI has been defined.  In that case, this call is ignored
        # -- Check and see if that causes a problem later
        Logger.debug(self, f"New_time={new_time}")
        self.update_scrubber_ui()

    def update_scrubber_ui(self):
        tlv = self._timeline_view
        time = tlv.get_time()
        pos = self.transform_timeline_to_scrubber_position(time, snap=tlv.get_snap_to_frame())

        if self._edit_scrubber:
            with self._edit_scrubber:
                if self._scrubber_placer_pill:
                    if tlv._zoom == 0:
                        self._scrubber_line.visible = False
                        self._scrubber_placer_pill.visible = False
                        return
                    self._scrubber_placer_pill.visible = True
                    self._scrubber_line.visible = True
                    self._scrubber_placer_pill.offset_x = pos
                    Logger.debug(self, f"update_scrubber_ui time={time} pos={pos}")
        self._update_label()

    def transform_timeline_to_scrubber_position(self, timeline_time, snap=True):
        tlv = self._timeline_view
        offset = tlv.get_timeline_parent_offset()
        pos = tlv.transform_timeline_to_position(timeline_time, snap=snap)
        pos -= offset
        pos -= self._scrubber_width / 2.0
        return pos

    def transform_scrubber_position_to_timeline(self, pos, snap=True):
        tlv = self._timeline_view
        pos += self._scrubber_width / 2.0
        offset = tlv.get_timeline_parent_offset()
        pos += offset
        timeline_time = tlv.transform_position_to_timeline(pos, snap=snap)
        return timeline_time

    # -- Private functions

    def _update_scrubber(self):
        self._update_label()

    def _update_label(self):
        if self._scrubber_label:
            time = self._timeline_view.get_time()
            self._scrubber_label.text = f"{time:.0f}"

    @do_later(wait_frames=1)
    def _delayed_build_ui(self):
        from .extension import TimelineExtension

        if self._frame is None:
            return False

        tlv = self._timeline_view
        if not tlv:
            return False

        stack_width = self._scrubber_width
        timeline_height = self._timeline_view.get_timeline_height()
        disable_line = self._timeline_view.get_scrubber_disable_line()

        # TODO relam - Maybe this should move somewhere else... really need
        # better coordination for creation and updates!
        self._current_second = self._timeline.get_current_time()
        with self._frame:
            self._scrubber_placer_pill = ui.Placer(draggable=True, frames_to_start_drag=3, drag_axis=ui.Axis.X)
            self._scrubber_placer_pill.set_offset_x_changed_fn(lambda d: self._on_pill_offset_x_changed(d))
            pill_icon_path = f"{TimelineExtension._icon_path}/Path.svg"
            with self._scrubber_placer_pill:
                with ui.VStack(width=stack_width):
                    with ui.ZStack(height=timeline_height):
                        self._scrubber_top = ui.Image(
                            pill_icon_path,
                            alignment=ui.Alignment.CENTER_BOTTOM,
                            fill_policy=ui.FillPolicy.STRETCH,
                            style_type_name_override="Timeline.ScrubberTop",
                        )
                        self._scrubber_label = ui.Label(
                            str("{:.0f}".format(tlv.get_time())), height=20, alignment=ui.Alignment.CENTER
                        )
                    Logger.debug(self, f"DisableLine={disable_line}")
                    style_override = "Timeline.ScrubberLine"
                    if disable_line is True:
                        with ui.HStack(content_clipping=True):
                            ui.Spacer()
                            self._scrubber_line = ui.Line(
                                width=1, alignment=ui.Alignment.H_CENTER, style_type_name_override=style_override
                            )
                            ui.Spacer()
                            self._scrubber_line.enabled = False
                            self._scrubber_placer_pill.opaque_for_mouse_events = False
                            self._scrubber_line.opaque_for_mouse_events = False
                    else:
                        with ui.HStack():
                            ui.Spacer()
                            self._scrubber_line = ui.Line(
                                width=4, alignment=ui.Alignment.H_CENTER, style_type_name_override=style_override
                            )
                            ui.Spacer()

        self._scrubber_top.set_mouse_pressed_fn(self._on_mouse_pressed)
        self._scrubber_top.set_mouse_moved_fn(self._on_mouse_moved)
        self._scrubber_top.set_mouse_released_fn(self._on_mouse_released)

        # Finally, call the function that will put everything where it really belongs
        self.update_time(tlv.get_time())

    def _on_pill_offset_x_changed(self, scrubber_pos):
        # Take the edit scope
        # TODO Rewrite this function -- it is needlessly overcomplicated!
        if self._edit_scrubber:
            with self._edit_scrubber:
                pos = scrubber_pos.value
                tlv = self._timeline_view

                tlv = self._timeline_view

                timeline_time = self.transform_scrubber_position_to_timeline(pos, snap=tlv.get_snap_to_frame())
                Logger.debug(self, f"on_pill_offset_x_changed - timeline_time={timeline_time}")

                if CLAMP_TO_VISIBLE_RANGE:
                    if timeline_time < tlv._range_begin:
                        pos = self.transform_timeline_to_scrubber_position(tlv._range_begin)
                        self._scrubber_placer_pill.offset_x = pos
                        timeline_time = tlv._range_begin
                    elif timeline_time > tlv._range_end:
                        pos = self.transform_timeline_to_scrubber_position(tlv._range_end)
                        self._scrubber_placer_pill.offset_x = pos
                        timeline_time = tlv._range_end

                if CLAMP_TO_SCENE_RANGE:
                    if timeline_time < tlv._timeline_begin:
                        pos = self.transform_timeline_to_scrubber_position(tlv._timeline_begin)
                        self._scrubber_placer_pill.offset_x = pos
                        timeline_time = tlv._timeline_begin
                    if timeline_time > tlv._timeline_end:
                        pos = self.transform_timeline_to_scrubber_position(tlv._timeline_end)
                        self._scrubber_placer_pill.offset_x = pos
                        timeline_time = tlv._timeline_end

                self._scrubber_label.text = f"{timeline_time:.0f}"

                # If we are dragging the scrubber, let's update the timeline.  But if we're updating the timeline, DON'T update the scrubber
                if timeline_time != self._last_time:
                    tlv.set_time(timeline_time)
                    self._last_time = timeline_time
                    if tlv._timeline.get_time_codes_per_seconds() > 0:
                        timeline_codes = timeline_time / tlv._timeline.get_time_codes_per_seconds()
                        tlv.update_timeline_codes(timeline_codes)

    def _on_mouse_pressed(self, x, y, button, modifier):
        # We're already in an edit.  Skip this for now.
        if not self._edit_scrubber:
            return
        with self._edit_scrubber:
            Logger.debug(self, f"pressed pos={x}, {y} button={button} mod={modifier}")
            if button == 0:
                self._left_button_down = True
                pass

    def _on_mouse_moved(self, x, y, modifier, c):
        return

    def _on_mouse_line_pressed(self, x, y, button, modifier):
        # We're already in an edit.  Skip this for now.
        if not self._edit_scrubber:
            return
        with self._edit_scrubber:
            if button == 0:
                self._left_button_down = True
                pass

    def _on_mouse_released(self, x, y, button, modifier):
        if button == 0:
            tlv = self._timeline_view
            timeline_position = tlv.transform_window_to_timeline(x, snap=tlv.get_snap_to_frame())
            Logger.debug(
                self,
                f"Released scrubber x={x} y={y} button={button} modifier={modifier} timeline_position={timeline_position} snap={tlv.get_snap_to_frame()}",
            )
            # Don't SET the time again, as we may end up putting the "final" time not where the user intended.  Leave it where it is, just "snap" to closest position
            tlv.set_time(timeline_position)
            self.update_time(timeline_position)
            self._left_button_down = False

    def _on_mouse_line_released(self, x, y, button, modifier):
        if button == 0:
            tlv = self._timeline_view
            timeline_position = tlv.transform_window_to_timeline(x, snap=tlv.get_snap_to_frame())
            Logger.debug(
                self,
                f"Released scrubber x={x} y={y} button={button} modifier={modifier} timeline_position={timeline_position} snap={tlv.get_snap_to_frame()}",
            )
            # Don't SET the time again, as we may end up putting the "final" time not where the user intended.  Leave it where it is, just "snap" to closest position
            tlv.set_time(timeline_position)
            self.update_time(timeline_position)
            self._left_button_down = False
