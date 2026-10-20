import math

import carb
import carb.input
import omni.ext
import omni.timeline
from omni import ui

from .timeline_view_component import (
    TimelineViewBottomDefault,
    TimelineViewElement,
    TimelineViewRoot,
    TimelineViewTopDefault,
    TimelineViewTopPlacerDefault,
)
from .timeline_view_range_width import RangeSlider
from .timeline_view_scrubber import Scrubber
from .ui_helpers import EditScope, Logger, WeakMethod, do_later, get_number_width

# Why is this so dramatically complicated?!?!
# Well, as it contains many layers of UI, and some of those layers depend on the sizes of other layers,
# sizes which are computed once drawn, we have to sometimes wait a frame to make sure that the widgets
# we depend on have drawn once!

# relam -- There are far too many conditionals in this code.  Conditionals are the main cause of bugs.
# As we revise and refactor this code, we should take care to remove conditionals in favor of
# encapsulated functionality.
# Also, more of this needs to be data-driven

# TODO relam - Ugly magic numbers...
TIMELINE_BORDER_WIDTH = 0
TIMELINE_RANGE_BAR_HEIGHT = 16
TIMELINE_HEIGHT = 28
PIXELS_PER_NUMBER = 50  # This is the size, in pixels, of the max number to render on the timeline
MAX_FRAME_COUNT = 999999

DEBUG_STYLE = {"background_color": 0xFF444400}


class TimelineView(TimelineViewRoot):
    # We are working on deprecating the passing of the parent window.
    def __init__(self, parent_window):
        self._parent_window = parent_window  # This needs to be deprecated asap
        self._timeline = None
        self._current_second = None
        self._scrubber = None
        self._scrubber_frame = None
        self._scrubber_disable_line = False
        self._range_slider_frame = None
        self._range_slider = None
        self._range_slider_visible = True
        self._range_begin = 0
        self._range_end = 100
        self._zoom = 1.0
        self._zoom_location = (0, 0)
        self._current_time = 0.0
        self._left_padding = 0
        self._timeline = omni.timeline.get_timeline_interface()
        self._edit_timeline = EditScope()
        self._snap_to_frame = True
        self._timeline_view_top = TimelineViewTopPlacerDefault(self)
        self._timeline_view_bottom = TimelineViewBottomDefault(self)
        self._timeline_bottom_frame = None  # TODO this needs to be deprecated and only function calls used to access
        self._timeline_zoomed_width = 0

        self._timeline_event_sub = self._timeline.get_timeline_event_stream().create_subscription_to_pop(
            WeakMethod(self._on_timeline_event)
        )
        self._timeline_begin = self._timeline.get_start_time() * self._timeline.get_time_codes_per_seconds()
        self._timeline_end = self._timeline.get_end_time() * self._timeline.get_time_codes_per_seconds()
        self._frame = None  # This is the frame we "parent" to, our "window" if you will
        self._draw_frame = None  # This is the frame we actually paint inside
        # self._logger_debug = True

    def __del__(self):
        self.destroy()

    def destroy(self):
        self._timeline_event_sub = None
        self._timeline_view_top = None
        self._timeline_view_bottom = None
        self._edit_timeline = None
        self._timeline = None
        self._scrubber = None
        return

    # -- Public funcitons

    def get_current_mouse_coords(self):
        app_window = omni.appwindow.get_default_app_window()
        input = carb.input.acquire_input_interface()
        dpi_scale = ui.Workspace.get_dpi_scale()
        pos_x, pos_y = input.get_mouse_coords_pixel(app_window.get_mouse())
        return pos_x / dpi_scale, pos_y / dpi_scale

    def set_timeline_top(self, new_top: TimelineViewElement):
        self._timeline_view_top = new_top

    def set_timeline_bottom(self, new_bottom: TimelineViewElement):
        self._timeline_view_bottom = new_bottom

    def _on_mouse_wheel(self, x, y, button):
        carb.log_warn("WHEEEL!!!")

    def _build_ui(self, show_warn=True):
        if show_warn:
            carb.log_warn(
                f"(Called from {type(self).__name__}) -- timeline_view._build_ui is deprecated.  Please use .build_ui() instead"
            )

    def _update_ui(self, show_warn=True):
        if show_warn:
            carb.log_warn("timeline_view._update_ui is deprecated.  Please use .update_ui() instead")

    def _delayed_update_ui(self, show_warn=True):
        if show_warn:
            carb.log_warn("timeline_view._delayed_update_ui is deprecated.  Please use .update_ui() instead")

    def build_containers(self):
        """This function exists to allow child class to rearrange the build order of these containers."""
        self.build_scrubber_container()
        self.build_top_container()
        self.build_bottom_container()

    def build_ui(self):
        self._build_ui(False)  # Depreated -- show msg till all is cleaned up

        # This is funky, but basically we're reserving a frame here, knowing that we're going to fill it later (after hopefully dependencies have resolved)
        Logger.debug(self, "Building UI")
        self._frame = ui.Frame(style=self.get_style(), build_fn=self._on_built, horizontal_clipping=True)
        with self._frame:
            # Okay.... the Stacks are a bit nuts here.  BE CAREFUL moving things around, it breaks like for no reason...
            with ui.HStack():
                ui.Spacer(width=self.get_border_width())
                self._draw_frame = ui.Frame(horizontal_clipping=True)
                with self._draw_frame:
                    with ui.VStack():
                        with ui.ZStack():
                            self.build_containers()
                        ui.Spacer(height=4)
                        self._range_slider_frame = ui.Frame(
                            height=self.get_range_bar_height(), horizontal_clipping=True, width=ui.Percent(100)
                        )
                ui.Spacer(width=self.get_border_width())

        # TODO -- this should be depracated in favor of using function calls!!
        self._timeline_bottom_frame = self._timeline_view_bottom.get_frame()

    def update_ui(self):
        self._update_ui(False)
        top = self._timeline_view_top.update_ui()
        if top is None:
            return False

        self.scroll_to_range(self._range_begin, self._range_end)

        if self._range_slider_frame is not None:
            if self._range_slider is not None:
                range_slider = self._range_slider.update_ui()

        bottom = self._timeline_view_bottom.update_ui()
        if bottom is False:
            return False

        # This function call should be deprecated soon, in favor of using the timeline_view_bottom
        if self._update_timeline_bottom() is False:
            return False

        if self._update_scrubber() is False:
            return False

        self._delayed_update_ui(show_warn=False)
        # carb.log_warn("timeline_view._update_ui finished")
        return True

    def _on_built(self):
        # The rest of the UI depends on results coming back from omni.ui on the window frames...
        if self._scrubber_frame is not None:
            self._scrubber = Scrubber(self, self._scrubber_frame)
            self._scrubber.build_ui()

        if self._range_slider_frame is not None:
            self._range_slider = RangeSlider(self, self._range_slider_frame)
            self._range_slider.build_ui()
            self._range_slider_frame.visible = self._range_slider_visible

        self._delayed_build_ui_fn()
        self._zoom_extents()  # for now, zoom all the way out when time changes
        self._range_slider.update_ui()

    def enable_scrubber(self, on):
        self._scrubber.enabled = on

    def get_scrubber(self):
        return self._scrubber

    # @do_later(wait_frames=1)
    def _delayed_build_ui_fn(self):
        return self._delayed_build_ui()

    def _delayed_build_ui(self):
        return

    def build_top_container(self):
        self._timeline_view_top.build_ui()

    def build_scrubber_container(self):
        # time scrubber
        self._scrubber_frame = ui.Frame(horizontal_clipping=True)

    def build_bottom_container(self):
        self._timeline_view_bottom.build_ui()

    # ------ Public accessors ------------
    def get_style(self):
        """Derived class should expose this function"""
        carb.log_verbose("TODO: Override the get_style function in timeline_view")
        style = {
            "Window": {"background_color": 0xFF444444},
            "Label::search": {"color": 0xFFACACAC},
            "ScrollingFrame": {
                "background_color": 0xFF444444,
                "secondary_color": 0xFFFFFFFF,
                "scrollbar_size": 10,
                "margin": 0,
                "border": 0,
            },
            "Tooltip": {
                "background_color": 0xFFC7F5FC,
                "color": 0xFF4B493B,
                "border_width": 1,
                "margin_width": 2,
                "margin_height": 1,
                "padding": 1,
            },
            "Timeline.TimelineBackground": {
                "background_color": 0xFF343232,
                "border_color": 0xFF646464,
                "border_width": 0,
            },
            "Timeline.ScrubberSplitter": {"background_color": 0xFFFF7E09, "border_width": 1, "border_radius": 8},
            "Timeline.ScrubberTop": {
                "color": 0xFFFF7E09,
                "background_color": 0x00FF7E09,
                "border_width": 0,
                "border_radius": 0,
            },
            "Timeline.ScrubberRectangle": {
                "color": 0x00FF0000,
                "background_color": 0x00FF7E09,
                "border_width": 0,
                "border_radius": 0,
            },
            "Timeline.ScrubberSplitter:hovered": {
                "background_color": 0xFFFF9E29,
                "border_width": 0,
                "border_radius": 0,
            },
            "Timeline.ScrubberLine": {
                "background_color": 0xFF000000,
                "color": 0xFFFF7E09,
                "border_width": 1,
                "border_radius": 0,
            },
            "Timeline.ScrubberLine:hovered": {
                "background_color": 0xFF000000,
                "color": 0xFFFF9E29,
                "border_width": 2,
                "border_radius": 0,
            },
            "Timeline.RangeSlider.LeftHandle": {
                "background_color": 0xFF11A011,
                "border_color": 0xFF000000,
                "border_width": 1,
                "color": 0xFFC0C0C0,
            },
            "Timeline.RangeSlider.LeftHandle:hovered": {
                "background_color": 0xFF44FF44,
                "border_color": 0xFF000000,
                "border_width": 1,
                "color": 0xFFC0C0C0,
            },
            "Timeline.RangeSlider.RightHandle": {
                "background_color": 0xFF1111A0,
                "border_color": 0xFF000000,
                "border_width": 1,
                "color": 0xFFC0C0C0,
            },
            "Timeline.RangeSlider.RightHandle:hovered": {
                "background_color": 0xFF4444FF,
                "border_color": 0xFF000000,
                "border_width": 1,
                "color": 0xFFC0C0C0,
            },
            "Timeline.Ticks": {"background_color": 0xFF000000, "color": 0xFF707070, "border_width": 1},
        }
        return style

    def get_parent_window(self):
        return self._parent_window

    def get_frame(self):
        return self._frame

    def get_draw_frame(self):
        return self._draw_frame

    def get_timeline_frame(self):
        if self._timeline_view_top is None:
            return False
        return self._timeline_view_top.get_frame()

    def get_bottom_frame(self):
        return self._timeline_view_bottom.get_frame()

    def get_timeline_bottom_frame(self):
        return self._timeline_view_top.get_bottom_frame()

    def get_timeline_draw_top_frame(self):
        return self._timeline_view_top.get_top_frame()

    # def get_draw_width(self):
    #    return self.get_draw_frame().computed_width

    def get_timeline_padding(self):
        return self._left_padding

    def get_timeline_begin(self) -> float:
        # TODO RELAM -- This function needs to use a model
        return self._timeline_begin

    def get_timeline_end(self) -> float:
        return self._timeline_end

    def get_border_width(self):
        return TIMELINE_BORDER_WIDTH

    def get_range_bar_height(self):
        return TIMELINE_RANGE_BAR_HEIGHT

    def get_timeline_height(self):
        """Another function you can override to customize"""
        return TIMELINE_HEIGHT

    def get_range(self):
        return self._range_end - self._range_begin

    def get_frame_width(self):
        return self.get_frame().computed_width

    def get_time(self) -> float:
        return self._current_time

    def get_timeline_range(self):
        return self._timeline_end - self._timeline_begin

    def get_view_bottom(self) -> TimelineViewElement:
        return self._timeline_view_bottom

    def get_view_top(self) -> TimelineViewElement:
        return self._timeline_view_top

    def get_timeline_zoomed_width(self):
        frame = self.get_draw_frame()
        if frame is None:
            return 0
        return frame.computed_width * self._zoom

    def get_timeline_parent_offset(self):
        if self._timeline_view_top is None:
            return 0
        return self._timeline_view_top.get_x()

    def update_timeline_codes(self, timeline_codes: float):
        if not self._edit_timeline:
            return

        with self._edit_timeline:
            self._timeline.set_current_time(timeline_codes)

    # For this function, we default to NOT snapping to frame
    def transform_timeline_to_position(self, timeline_val, frame_width=-1, snap=False) -> float:
        timeline_range = self._timeline_end - self._timeline_begin
        if timeline_range == 0:
            return 0.0
        if frame_width <= 0:
            frame_width = self.get_timeline_zoomed_width()
        scale = float(frame_width / timeline_range)
        offset = self._timeline_begin
        if snap is True:
            position = round(timeline_val - offset) * scale
        else:
            position = (timeline_val - offset) * scale

        # Logger.debug(self,f"timeline_view.transform_timeline_to_position: frame_width={frame_width} from={timeline_val} pos={position}")
        return position

    def transform_position_to_timeline(self, position, frame_width=-1, snap=True) -> float:
        timeline_range = self._timeline_end - self._timeline_begin
        if frame_width <= 0:
            frame_width = self.get_timeline_zoomed_width()

        if timeline_range == 0 or frame_width == 0:
            return 0.0
        scale = frame_width / timeline_range
        offset = self._timeline_begin
        timeline_pos = offset + (position * (1.0 / scale))
        if snap is True:
            timeline_pos = round(timeline_pos)
        return timeline_pos

    def transform_window_to_timeline(self, window_x, snap=True) -> float:
        zoom_width = self.get_timeline_zoomed_width()
        if zoom_width <= 0:
            return self._range_begin
        timeline_frame = self._timeline_view_top.get_frame()
        window_pos = timeline_frame.screen_position_x
        position = window_x - window_pos
        scale = self.get_timeline_range() / zoom_width
        offset = self._range_begin  # This is in timeline-space
        timeline_draw_width = self.get_frame_width()
        if timeline_draw_width == 0:
            offset_scale = 1.0
        else:
            offset_scale = self.get_range() / self.get_frame_width()
        timeline_pos = (offset) + (position * scale)
        Logger.debug(
            self,
            f"Transform window_x={window_x} window_pos={window_pos} snap={snap} position={position} zoom={self._zoom} zwidth={zoom_width} scale={scale} offset={offset} offset_scale={offset_scale} tldrwidth={timeline_draw_width} timeline_pos={timeline_pos}",
        )
        if snap:
            return round(timeline_pos)
        return timeline_pos

    def set_snap_to_frame(self, snap_to_frame):
        self._snap_to_frame = snap_to_frame

    def set_scrubber_disable_line(self, onoff):
        self._scrubber_disable_line = onoff
        scrubber = self.get_scrubber()
        if scrubber is None:
            return
        scrubber.build_ui()

    def get_scrubber_disable_line(self):
        return self._scrubber_disable_line

    def get_snap_to_frame(self):
        return self._snap_to_frame

    def set_timeline_extents(self, timeline_begin, timeline_end):
        update = False
        if timeline_begin != self._timeline_begin:
            self._timeline_begin = timeline_begin
            update = True

        if timeline_end != self._timeline_end:
            self._timeline_end = timeline_end
            update = True

        if update:
            # carb.log_warn("Calling update on timeline because extents changed")
            self.update_ui()

    def set_range_begin(self, new_begin):
        self.set_range(new_begin, self._range_end)

    def set_range_end(self, new_end):
        self.set_range(self._range_begin, new_end)

    def get_range_begin(self):
        return self._range_begin

    def get_range_end(self):
        return self._range_end

    def set_range(self, new_begin, new_end):
        # TODO -- This function likely needs to get broken up more

        if new_begin == self._range_begin and new_end == self._range_end:
            # Redundant call
            return

        current_range = self.get_range()

        if new_begin != self._range_begin:
            self._range_begin = int(min(new_begin, MAX_FRAME_COUNT - 1))
        if new_end != self._range_end:
            self._range_end = int(max(new_begin, min(new_end, MAX_FRAME_COUNT)))

        range = self.get_range()
        if range > 0.0:
            self._zoom = self.get_timeline_range() / range
        else:
            self._zoom = 0
        #        tick_size, big_tick_size = self._calculate_timeline_ticks()
        # TODO timeline start is set when the range in the timeline is adjusted
        if range != current_range:
            self.update_ui()
            if range < 2:
                pass
        else:
            # TODO relam -- Need to just scroll the content
            new_position, new_width = self.scroll_to_range(self._range_begin, self._range_end)
        self._delayed_update_scrubber_ui()
        Logger.debug(
            self,
            f"set_range -- range begin/end={self._range_begin}, {self._range_end} range={range} current_range={current_range} timeline begin/end={self._timeline_begin}, {self._timeline_end}",
        )

    @property
    def zoom(self):
        return self._zoom

    @zoom.setter
    def zoom(self, new_zoom):
        if self._zoom == new_zoom:
            return
        loc = self.zoom_location
        timeline_x = self.transform_window_to_timeline(loc[0])
        old_zoom = self._zoom
        self._zoom = new_zoom
        begin = self.get_range_begin()
        end = self.get_range_end()
        range = end - begin
        new_range = range
        # For now, we're doing a uniform zoom.  Nobody has requested a non-uniform zoom
        if new_zoom > old_zoom:
            new_range = range - int(range * (new_zoom - old_zoom))
        elif new_zoom < old_zoom:
            new_range = range + int(range * (old_zoom - new_zoom))

        timeline_begin = self.get_timeline_begin()
        timeline_end = self.get_timeline_end()
        new_begin = min(timeline_end - new_range, max(timeline_x - int(new_range / 2.0), timeline_begin))
        new_end = new_begin + new_range

        Logger.debug(
            self,
            f"Loc {loc} Begin {begin} end {end} range {range} timeline_begin {timeline_begin} timeline_end {timeline_end} ||  timeline_x {timeline_x} new_begin {new_begin} new_end {new_end} new_range {new_range}",
        )
        self.set_range(new_begin, new_end)

    @property
    def zoom_location(self):
        return self._zoom_location

    @zoom_location.setter
    def zoom_location(self, loc):
        self._zoom_location = loc
        Logger.debug(self, f"Loc {loc}")

    def set_time(self, new_time):
        self._timeline_event_set_time(new_time)

        # if there is no stage open, get_time_codes_per_seconds should return 0
        if self._timeline.get_time_codes_per_seconds() > 0:
            timeline_codes = new_time / self._timeline.get_time_codes_per_seconds()
            self.update_timeline_codes(timeline_codes)

    def scroll_to_range(self, range_begin, range_end):
        begin = self.transform_timeline_to_position(range_begin)
        end = self.transform_timeline_to_position(range_end)
        width = end - begin
        self._timeline_view_top.set_x(begin)
        self._timeline_view_bottom.set_x(begin)
        return begin, width

    def set_range_slider_visible(self, is_visible):
        self._range_slider_visible = is_visible
        if self._range_slider is not None:
            self._range_slider.set_visible(is_visible)

    def _draw_timeline_top(self):

        # This is a case where we need to just abort the timeline -- likely an async issue
        # and we just need to wait till things "chill"
        draw_frame = self._timeline_view_top.get_draw_frame()

        timeline_width = self.get_timeline_range()
        if timeline_width < 1:
            timeline_width = 1

        visible_range = max(1, min(timeline_width, self.get_range()))
        # Next, calculate the visible pixels by taking the width
        # and dividing it by the range -- that's how big each "tick"
        # needs to be

        zoomed_width = self.get_timeline_zoomed_width()

        draw_frame.clear()
        draw_frame.width = ui.Pixel(zoomed_width)
        tick_size, big_tick_size = self._calculate_timeline_ticks()
        if big_tick_size == 0:
            carb.log_warn("Zero tick size in timeline_view")
        num_ticks = timeline_width / big_tick_size
        if num_ticks == 0:
            carb.log_warn(f"Zero num_ticks in timeline_view {visible_range} {big_tick_size}")
            big_tick_frame_size = 0
        else:
            big_tick_frame_size = zoomed_width / num_ticks

        Logger.debug(
            self,
            f"zoomed_width={zoomed_width} zoom={self.zoom} big_tick_frame_size={big_tick_frame_size} num_ticks={num_ticks}",
        )

        tick_per_big = big_tick_size / tick_size
        small_tick_frame_size = big_tick_frame_size / tick_per_big

        view_timeline_begin = self.get_timeline_begin()
        view_timeline_end = self.get_timeline_end()
        timeline_begin = math.ceil(view_timeline_begin / big_tick_size) * big_tick_size

        frac_big_tick_size = 0
        begin_mod_big_tick = view_timeline_begin % big_tick_size
        if begin_mod_big_tick:
            frac_big_tick_size = big_tick_frame_size * (1.0 - begin_mod_big_tick / big_tick_size)

        frac_small_tick_size = max(small_tick_frame_size * (1.0 - (view_timeline_begin % tick_size) / tick_size), 1)

        with draw_frame:
            # timeline ticks
            with ui.HStack():
                with ui.VStack(height=self.get_timeline_height()):
                    if view_timeline_begin % big_tick_size == 0:
                        timeline_begin = view_timeline_begin
                    else:
                        timeline_begin = math.floor((int(view_timeline_begin) / big_tick_size) + 1) * big_tick_size
                    if view_timeline_begin % tick_size == 0:
                        small_timeline_begin = view_timeline_begin
                    else:
                        small_timeline_begin = (
                            math.floor((int(view_timeline_begin) / frac_small_tick_size) + 1) * tick_size
                        )

                    # ------------- ticks(major) --------------------
                    if view_timeline_begin == 0:
                        frac_big_tick_size = 0
                        frac_small_tick_size = 0

                    num_width = get_number_width(view_timeline_end)

                    Logger.debug(
                        self,
                        f"Timeline top rendering big_tick_frame_size={big_tick_frame_size} zoomed_width={zoomed_width} draw_frame_width={draw_frame.computed_width} frame={self._frame.computed_width} zoom={self.zoom} tick_size={tick_size} big_tick={big_tick_size} frac_big_tick_size={frac_big_tick_size}",
                    )
                    with ui.ZStack(width=0):
                        with ui.HStack(height=ui.Fraction(0.5)):
                            # This is to put a "fudge" space in front of the timeline when there is an offset
                            ui.Spacer(width=frac_big_tick_size)
                            x = timeline_begin
                            drawn_big = 0
                            while x < view_timeline_end:
                                stack_width = big_tick_frame_size
                                if x + big_tick_size > view_timeline_end:
                                    stack_width = (
                                        big_tick_frame_size * (view_timeline_end % big_tick_size) / big_tick_size
                                    )

                                with ui.ZStack(width=stack_width, horizontal_clipping=True):
                                    ui.Line(alignment=ui.Alignment.LEFT, style_type_name_override="Timeline.Ticks")
                                    if stack_width > num_width:
                                        with ui.HStack(width=0):
                                            ui.Spacer(width=3)
                                            ui.Label(f"{int(x)}", alignment=ui.Alignment.LEFT_TOP)
                                x += big_tick_size
                                drawn_big += 1
                        ui.Spacer()

                    # ----------- ticks(gap) --------------------
                    ui.Spacer(height=ui.Fraction(0.1))

                    # ----------- ticks(minor) ------------------
                    with ui.HStack(height=ui.Fraction(0.2)):
                        ui.Spacer(width=frac_small_tick_size)
                        y = small_timeline_begin
                        while y < view_timeline_end:
                            stack_width = small_tick_frame_size
                            if y + tick_size > view_timeline_end:
                                stack_width = small_tick_frame_size * (view_timeline_end % tick_per_big) / tick_per_big
                            with ui.ZStack(width=stack_width):
                                ui.Line(alignment=ui.Alignment.LEFT, style_type_name_override="Timeline.Ticks")
                            y += tick_size
        return True

    def _update_timeline_top(self):
        self._timeline_view_top.update_ui()

    def _update_timeline_bottom(self):
        return True

    def _timeline_event_set_time(self, new_time: float):
        if self._edit_timeline:
            with self._edit_timeline:
                self._current_time = new_time
                if self._scrubber:
                    self._scrubber.on_timeline_event(self.get_time())

    def _zoom_extents(self):
        self._timeline_begin = self._timeline.get_start_time() * self._timeline.get_time_codes_per_seconds()
        self._timeline_end = self._timeline.get_end_time() * self._timeline.get_time_codes_per_seconds()
        self.set_timeline_extents(self._timeline_begin, self._timeline_end)
        self.set_range(self._timeline_begin, self._timeline_end)
        self.update_ui()
        Logger.debug(self, f"_zoom_extents begin={self._timeline_begin} end={self._timeline_end}")

    def _update_scrubber(self):
        if not self._scrubber:
            return False
        Logger.debug(self, "_update_scrubber")
        self._scrubber.update_time(self.get_time())
        return True

    # @do_later(wait_frames=1)
    def _delayed_update_scrubber_ui(self):
        Logger.debug(self, "_delayed_update_scrubber")
        self.update_scrubber_ui()

    def update_scrubber_ui(self):
        if not self._scrubber:
            return False
        self._scrubber.update_scrubber_ui()
        return True

    # TODO relam -- Totally brute-forcing this for the initial iteration
    # let's make this smarter when there's time and brainpower!
    # Needs to take into account the entire screen-space size of the timeline
    def _calculate_timeline_ticks(self):
        # start_range = self._range_end - self._range_begin
        start_range = self._timeline_end - self._timeline_begin
        range = max(start_range, 1)
        zoomed_window_size = self.get_timeline_zoomed_width()
        num_width = get_number_width(range) + 14
        max_big_ticks = max(int(zoomed_window_size / num_width), 1)

        tick_sizes = [
            1,
            5,
            10,
            20,
            30,
            50,
            60,
            100,
            200,
            300,
            500,
            600,
            1000,
            3000,
            5000,
            6000,
            10000,
            20000,
            30000,
            50000,
            60000,
            100000,
        ]

        if range > 0:
            x = 0
            big_ticksize = tick_sizes[x]
            while (range / big_ticksize) > max_big_ticks and big_ticksize < 100000:
                x += 1
                big_ticksize = tick_sizes[x]
        else:
            ticksize = 0
            big_ticksize = 0

        if big_ticksize < 30:
            ticksize = max(1, int(big_ticksize / 5))
        else:
            ticksize = int(big_ticksize / 10)

        Logger.debug(
            self,
            f"Range={range} ticksize={ticksize} big_ticksize={big_ticksize} max_big_ticks={max_big_ticks} num_width={num_width} window={zoomed_window_size}",
        )
        return ticksize, big_ticksize

    def _on_timeline_event(self, evt):
        if (
            (evt.type == int(omni.timeline.TimelineEventType.START_TIME_CHANGED))
            or (evt.type == int(omni.timeline.TimelineEventType.END_TIME_CHANGED))
            or (evt.type == int(omni.timeline.TimelineEventType.TIME_CODE_PER_SECOND_CHANGED))
        ):
            # TODO relam --- Let's not update everything and instead update what NEEDS to be updated!
            self._zoom_extents()  # for now, zoom all the way out when time changes
            self.update_ui()
        elif (
            (evt.type == int(omni.timeline.TimelineEventType.CURRENT_TIME_CHANGED))
            or (evt.type == int(omni.timeline.TimelineEventType.CURRENT_TIME_TICKED))
            or (evt.type == int(omni.timeline.TimelineEventType.STOP))
        ):
            new_current_second = self._timeline.get_current_time()
            if new_current_second != self._current_second:
                self._current_second = new_current_second
                self._timeline_event_set_time(self._current_second * self._timeline.get_time_codes_per_seconds())

    # this is still called by default behaviors, but should be deprecated as soon as possible
    def _on_drop(self, event):
        pass
