import functools

import omni.ext
import omni.timeline
import omni.ui as ui

from .timeline_value_model import TimelineValueModel
from .ui_helpers import Logger, ResizeableWidget, do_later

RIGHT_HANDLE_WIDTH = 10


class RangeSliderPlacer(ResizeableWidget):
    """Generic Placer higher level helper which handles much of the overhead of setting up a Placer to drag around and resize"""

    """ When deriving a class from ResizeableWidget, you likely need most of these override functions below.  """

    def __init__(self, parent_frame, range_view, axis=ui.Axis.X):
        self._range_view = range_view
        self._axis = axis
        self._parent_frame = parent_frame
        self._begin_time_label = None
        self._end_time_label = None
        super().__init__(
            parent_frame, left_handle_width=RIGHT_HANDLE_WIDTH, right_handle_width=RIGHT_HANDLE_WIDTH, drag_axis=axis
        )
        # self._logger_debug = True

    def fill_body(self):
        super().fill_body()
        with ui.VStack():
            ui.Spacer()
            with ui.HStack(height=12):
                ui.Spacer(width=16)
                new_begin, new_end = self._get_transformed_begin_end()
                self._begin_time_label = ui.Label(f"{new_begin:0.0f}", width=0)
                ui.Spacer()
                self._end_time_label = ui.Label(f"{new_end:0.0f}", width=0)
                ui.Spacer(width=16)
            ui.Spacer()

    def build_ui(self):
        super().build_ui()

    def get_style_type_name_override(self):
        return "Timeline.RangeSlider"

    def get_left_handle_style(self):
        return "Timeline.RangeSlider.LeftHandle"

    def get_right_handle_style(self):
        return "Timeline.RangeSlider.RightHandle"

    def calculate_frame_values(self, width):
        # Called from the deferred build function in the base class
        # to calculate values which were not present until the "next frame"

        if not self._edit:
            # Something already edits it
            return

        with self._edit:
            tlv = self._range_view._timeline_view
            if tlv is not None:
                range_begin = tlv._range_begin
                range_end = tlv._range_end
                self.set_width(width)
                begin_pos = tlv.transform_timeline_to_position(range_begin, width)
                end_pos = tlv.transform_timeline_to_position(range_end, width)
                self.set_begin(begin_pos, update=False)
                self.set_end(end_pos, update=False)

                Logger.debug(
                    self,
                    f"calculate_frame_values -- range_begin={range_begin} range_end={range_end} width={width} begin_pos={begin_pos} end_pos={end_pos}",
                )
            super().calculate_frame_values()

    def _clamp(self, min_value, max_value, value):
        return max(min_value, min(value, max_value))

    def _get_transformed_begin_end(self):
        tlv = self._range_view._timeline_view
        if not tlv:
            return 0, 0
        new_begin = tlv.transform_position_to_timeline(self.begin, self.width)
        new_end = tlv.transform_position_to_timeline(self.end, self.width)
        return new_begin, new_end

    def _begin_moved(self, begin, body, end, rect):
        if not self._edit:
            # Something already edits it
            return

        with self._edit:
            begin_x = begin.offset_x.value

            if begin_x > end.offset_x.value:
                begin_x = end.offset_x.value
                begin.offset_x.value = begin_x

            if begin_x < 0:
                begin_x = 0
                begin.offset_x.value = begin_x

            self.begin = begin.offset_x.value
            new_begin, new_end = self._get_transformed_begin_end()
            self._begin_time_label.text = f"{new_begin:0.0f}"
            self.range = self.end - self.begin

            self.body.offset_x = begin_x
            self.body_frame.width = ui.Length(self.range)

            # relam - This should only happen if the user is doing it -- not if it's moving for some other reason
            new_begin, new_end = self._get_transformed_begin_end()
            tlv = self._range_view._timeline_view
            tlv.set_range_begin(new_begin)
            self._fill_body()
            Logger.debug(
                self, f"begin_moved -- beginloc={self.begin} range={self.range} new_begin={new_begin} new_end={new_end}"
            )

    def _body_moved(self, begin, body, end, rect):
        if not self._edit:
            # Something already edits it
            return

        # TODO relam - When the user hits the left or right side,
        # scroll the screen rather than just blocking it
        with self._edit:
            beginloc = body.offset_x.value
            if beginloc < 0:
                beginloc = 0
                body.offset_x = beginloc
            # TODO -- Max width needs to be stored for things like this, I think

            if beginloc + self.range > self.width:
                beginloc = self.width - self.range
                body.offset_x = beginloc

            if begin:
                begin.offset_x = body.offset_x.value

            begin_x = begin.offset_x.value
            end_x = begin_x + self.range

            if end:
                end.offset_x = end_x

            self.set_range(begin_x, end_x, False)
            tlv = self._range_view._timeline_view
            new_begin = tlv.transform_position_to_timeline(begin.offset_x.value, self.width)
            end_loc = self.end
            new_end = tlv.transform_position_to_timeline(end_loc, self.width)
            tlv.set_range(new_begin, new_end)
            self._begin_time_label.text = f"{new_begin:0.0f}"
            self._end_time_label.text = f"{new_end:0.0f}"

            Logger.debug(
                self, f"body_moved -- beginloc={beginloc} range={self.range} new_begin={new_begin} new_end={new_end}"
            )

    def _end_moved(self, begin, body, end, rect):
        if not self._edit:
            # Something already edits it
            return

        with self._edit:
            endpos = end.offset_x.value + self.right_handle_width
            maxend = self.width
            if endpos > maxend:
                end.offset_x.value = maxend - self.right_handle_width
                endpos = maxend

            if endpos < begin.offset_x.value:
                endpos = begin.offset_x.value
                end.offset_x.value = endpos - self.right_handle_width

            self.end = endpos
            self.range = endpos - begin.offset_x.value
            _, new_end = self._get_transformed_begin_end()
            self._end_time_label.text = f"{new_end:0.0f}"
            self.body_frame.width = ui.Length(self.range)
            # relam - This should only happen if the user is doing it -- not if it's moving for some other reason
            tlv = self._range_view._timeline_view
            tlv.set_range_end(new_end)
            Logger.debug(
                self,
                f"end_moved -- endpos={endpos} new_end={new_end} maxend={maxend} end_x={end.offset_x.value} range={self.range}",
            )
            self._fill_body()

    def _fill_body(self):
        screen_width = self.range
        if self._begin_time_label is not None:
            if screen_width < 100:
                self._begin_time_label.visible = False
                self._end_time_label.visible = False
            else:
                self._begin_time_label.visible = True
                self._end_time_label.visible = True

        super()._fill_body()

    def _update_ui(self):
        if not self._edit:
            return

        with self._edit:
            if self.begin == self.end:
                if self.left_handle is not None:
                    self.left_handle.visible = False
                if self.right_handle is not None:
                    self.right_handle.visible = False
                if self.body_frame is not None:
                    self.body_frame.visible = False
            else:
                if self.left_handle is not None:
                    self.left_handle.visible = True
                    self.left_handle.offset_x = self.begin
                if self.body is not None:
                    self.body.visible = True
                    self.body.offset_x = self.begin
                if self.body_frame is not None:
                    self.body_frame.visible = True
                    body_width = self.range
                    self.body_frame.width = ui.Length(body_width)

                if self.right_handle is not None:
                    self.right_handle.visible = True
                    cur = self.right_handle.offset_x
                    new = max(self.end - self.right_handle_width, 0)
                    if new != cur:
                        self.right_handle.offset_x = new

            tlv = self._range_view._timeline_view
            range_begin = tlv._range_begin
            range_end = tlv._range_end
            self._begin_time_label.text = f"{range_begin:0.0f}"
            self._end_time_label.text = f"{range_end:0.0f}"

            if self.body:
                Logger.debug(
                    self,
                    f"update_ui -- self.range={self.range} self.begin={self.begin} self.body.offset_x={self.body.offset_x} self.body_frame.width={self.body_frame.width}",
                )
            self._fill_body()
        return True

    def _mouse_released(self, x, y, b, rect):
        # TODO - We removed all the code in here to prioritize updates for each move
        # hopefully performance holds!
        tlv = self._range_view._timeline_view
        # tlv.update_ui()


# TODO relam -- Further break down frames, and get updates to only update relevant frames instead of the entire control


class RangeSlider:
    def __init__(self, timeline_view, frame):
        self._timeline_view = timeline_view
        self._frame = frame
        self._range_slider_placer = None
        self._enable_range_slider_width = True
        self._range_slider_width_stack = None
        self._begin_time_field = None
        self._end_time_field = None
        # self._logger_debug = True

    def destroy(self):
        self._timeline_view = None
        self._frame = None
        self._range_slider_placer = None

    # -- Public funcitons

    def set_visible(self, is_visible):
        self._frame.visible = is_visible
        return

    def is_visible(self):
        return self._frame.visible

    def build_ui(self):
        with self._frame:
            with ui.ZStack():
                # ui.Rectangle(style_type_name_override="Tooltip")
                timeline_range_slider = ui.HStack(
                    style_type_name_override="Timeline.RangeSlider",
                    height=self._timeline_view.get_range_bar_height(),
                    horizontal_clipping=True,
                )
                with timeline_range_slider:
                    self._begin_time_model = TimelineValueModel(omni.timeline.TimelineEventType.START_TIME_CHANGED)
                    self._begin_time_field = ui.StringField(
                        self._begin_time_model,
                        width=ui.Pixel(50),
                        height=self._timeline_view.get_range_bar_height(),
                        style_type_name_override="Timeline.RangeSlider",
                    )
                    # Range slider, if desired
                    ui.Spacer(width=4)
                    self._range_slider_middle = ui.Frame(horizontal_clipping=True, build_fn=self._on_slider_built)
                    with self._range_slider_middle:
                        self._range_slider_placer = RangeSliderPlacer(self._range_slider_middle, self)
                        self._range_slider_placer.set_mouse_fn(functools.partial(self._on_mouse_pressed_range))
                    ui.Spacer(width=4)
                    self._end_time_model = TimelineValueModel(omni.timeline.TimelineEventType.END_TIME_CHANGED)
                    self._end_time_field = ui.StringField(
                        self._end_time_model,
                        width=ui.Pixel(50),
                        height=self._timeline_view.get_range_bar_height(),
                        style_type_name_override="Timeline.RangeSlider",
                    )
        self._frame.set_build_fn(self._on_range_frame_built)

    def _on_range_frame_built(self):
        self.update_ui()

    def _on_slider_built(self):
        self._range_slider_placer.build_ui()
        return

    def update_ui(self):
        if self._range_slider_placer:
            new_width = self._frame.computed_width - 120
            new_width = self._range_slider_middle.computed_width
            self._range_slider_placer.calculate_frame_values(width=new_width)
            self._range_slider_placer.update_ui()
            Logger.debug(
                self,
                f"update_ui -- width={new_width} frame_width={self._frame.computed_width} self.begin={self._range_slider_placer.begin} self.end={self._range_slider_placer.end}",
            )
        return True

    # -- Private functions

    def _on_mouse_pressed_range(self, x, y, button, mod):
        if button == 0:
            # TODO relam - What do we do if someone left-clicks on the timeline?
            pass
        if button == 1:
            # TODO relam - Context menu?
            pass
