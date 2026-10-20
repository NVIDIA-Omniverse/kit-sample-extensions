# Public API for module omni.kit.widget.timeline:

## Classes

- class EditScope
  - def __init__(self)

- [deprecated] class WeakMethod(weakref.WeakMethod)

- class TimelineView(TimelineViewRoot)
  - def __init__(self, parent_window)
  - def destroy(self)
  - def get_current_mouse_coords(self)
  - def set_timeline_top(self, new_top: TimelineViewElement)
  - def set_timeline_bottom(self, new_bottom: TimelineViewElement)
  - def build_containers(self)
  - def build_ui(self)
  - def update_ui(self)
  - def enable_scrubber(self, on)
  - def get_scrubber(self)
  - def build_top_container(self)
  - def build_scrubber_container(self)
  - def build_bottom_container(self)
  - def get_style(self)
  - def get_parent_window(self)
  - def get_frame(self)
  - def get_draw_frame(self)
  - def get_timeline_frame(self)
  - def get_bottom_frame(self)
  - def get_timeline_bottom_frame(self)
  - def get_timeline_draw_top_frame(self)
  - def get_timeline_padding(self)
  - def get_timeline_begin(self) -> float
  - def get_timeline_end(self) -> float
  - def get_border_width(self)
  - def get_range_bar_height(self)
  - def get_timeline_height(self)
  - def get_range(self)
  - def get_frame_width(self)
  - def get_time(self) -> float
  - def get_timeline_range(self)
  - def get_view_bottom(self) -> TimelineViewElement
  - def get_view_top(self) -> TimelineViewElement
  - def get_timeline_zoomed_width(self)
  - def get_timeline_parent_offset(self)
  - def update_timeline_codes(self, timeline_codes: float)
  - def transform_timeline_to_position(self, timeline_val, frame_width = -1, snap = False) -> float
  - def transform_position_to_timeline(self, position, frame_width = -1, snap = True) -> float
  - def transform_window_to_timeline(self, window_x, snap = True) -> float
  - def set_snap_to_frame(self, snap_to_frame)
  - def set_scrubber_disable_line(self, onoff)
  - def get_scrubber_disable_line(self)
  - def get_snap_to_frame(self)
  - def set_timeline_extents(self, timeline_begin, timeline_end)
  - def set_range_begin(self, new_begin)
  - def set_range_end(self, new_end)
  - def get_range_begin(self)
  - def get_range_end(self)
  - def set_range(self, new_begin, new_end)
  - [property] def zoom(self)
  - [zoom.setter] def zoom(self, new_zoom)
  - [property] def zoom_location(self)
  - [zoom_location.setter] def zoom_location(self, loc)
  - def set_time(self, new_time)
  - def scroll_to_range(self, range_begin, range_end)
  - def set_range_slider_visible(self, is_visible)
  - def update_scrubber_ui(self)

- class Scrubber
  - def __init__(self, timeline_view: TimelineViewRoot, frame)
  - def destroy(self)
  - def build_ui(self)
  - def update_ui(self)
  - [property] def enabled(self)
  - [enabled.setter] def enabled(self, on)
  - def on_timeline_event(self, new_time)
  - def update_time(self, new_time)
  - def update_scrubber_ui(self)
  - def transform_timeline_to_scrubber_position(self, timeline_time, snap = True)
  - def transform_scrubber_position_to_timeline(self, pos, snap = True)

- [deprecated] class Logger
  - static def warn(caller, string)
  - static def debug(caller, string)

- class RangeSlider
  - def __init__(self, timeline_view, frame)
  - def destroy(self)
  - def set_visible(self, is_visible)
  - def is_visible(self)
  - def build_ui(self)
  - def update_ui(self)

- class TimelineViewElement
  - def __init__(self, view: TimelineViewRoot)
  - def build_ui(self)
  - def update_ui(self)
  - def on_zoom(self, new_zoom)
  - def on_zoom_width(self, new_width)
  - def on_zoom_height(self, new_height)
  - def get_frame(self)
  - def get_top_frame(self)
  - def get_draw_frame(self)
  - def get_frame_offset(self)
  - def enable_scrubber(self, on)
  - [property] def zoom(self)
  - [zoom.setter] def zoom(self, new_zoom)
  - [property] def zoom_location(self)
  - [zoom_location.setter] def zoom_location(self, loc)
  - def zoom_step(self, step)
  - def set_x(self, x)
  - def set_y(self, y)
  - def get_x(self)
  - def get_y(self)

- class TimelineViewTopPlacerDefault(TimelineViewElement)
  - def __init__(self, view: TimelineViewRoot)
  - def build_ui(self)
  - def update_ui(self)
  - def get_top_frame(self)
  - def get_bottom_frame(self)
  - def get_frame_x(self)
  - def set_x(self, x)
  - def set_y(self, y)
  - def get_x(self)

- class TimelineValueModel(ui.AbstractValueModel)
  - def __init__(self, event_type = omni.timeline.TimelineEventType.END_TIME_CHANGED)
  - def get_value_as_string(self)
  - def get_value_as_float(self)
  - def begin_edit(self)
  - def set_value(self, value)
  - def end_edit(self)

- class ProgressPopup
  - def __init__(self, title, cancel_button_text = 'Cancel', cancel_button_fn = None, status_text = '', modal = True)
  - def set_cancel_fn(self, on_cancel_button_clicked)
  - def set_progress(self, progress)
  - def get_progress(self)
  - progress: Unknown
  - def set_status_text(self, status_text)
  - def get_status_text(self)
  - status_text: Unknown
  - def show(self)
  - def hide(self)
  - def is_visible(self)

## Functions

- def do_later(wait_frames = 1)

# Public API for module omni.kit.widget.timeline:

## Classes

- class EditScope
  - def __init__(self)

- [deprecated] class WeakMethod(weakref.WeakMethod)

- class TimelineView(TimelineViewRoot)
  - def __init__(self, parent_window)
  - def destroy(self)
  - def get_current_mouse_coords(self)
  - def set_timeline_top(self, new_top: TimelineViewElement)
  - def set_timeline_bottom(self, new_bottom: TimelineViewElement)
  - def build_containers(self)
  - def build_ui(self)
  - def update_ui(self)
  - def enable_scrubber(self, on)
  - def get_scrubber(self)
  - def build_top_container(self)
  - def build_scrubber_container(self)
  - def build_bottom_container(self)
  - def get_style(self)
  - def get_parent_window(self)
  - def get_frame(self)
  - def get_draw_frame(self)
  - def get_timeline_frame(self)
  - def get_bottom_frame(self)
  - def get_timeline_bottom_frame(self)
  - def get_timeline_draw_top_frame(self)
  - def get_timeline_padding(self)
  - def get_timeline_begin(self) -> float
  - def get_timeline_end(self) -> float
  - def get_border_width(self)
  - def get_range_bar_height(self)
  - def get_timeline_height(self)
  - def get_range(self)
  - def get_frame_width(self)
  - def get_time(self) -> float
  - def get_timeline_range(self)
  - def get_view_bottom(self) -> TimelineViewElement
  - def get_view_top(self) -> TimelineViewElement
  - def get_timeline_zoomed_width(self)
  - def get_timeline_parent_offset(self)
  - def update_timeline_codes(self, timeline_codes: float)
  - def transform_timeline_to_position(self, timeline_val, frame_width = -1, snap = False) -> float
  - def transform_position_to_timeline(self, position, frame_width = -1, snap = True) -> float
  - def transform_window_to_timeline(self, window_x, snap = True) -> float
  - def set_snap_to_frame(self, snap_to_frame)
  - def set_scrubber_disable_line(self, onoff)
  - def get_scrubber_disable_line(self)
  - def get_snap_to_frame(self)
  - def set_timeline_extents(self, timeline_begin, timeline_end)
  - def set_range_begin(self, new_begin)
  - def set_range_end(self, new_end)
  - def get_range_begin(self)
  - def get_range_end(self)
  - def set_range(self, new_begin, new_end)
  - [property] def zoom(self)
  - [zoom.setter] def zoom(self, new_zoom)
  - [property] def zoom_location(self)
  - [zoom_location.setter] def zoom_location(self, loc)
  - def set_time(self, new_time)
  - def scroll_to_range(self, range_begin, range_end)
  - def set_range_slider_visible(self, is_visible)
  - def update_scrubber_ui(self)

- class Scrubber
  - def __init__(self, timeline_view: TimelineViewRoot, frame)
  - def destroy(self)
  - def build_ui(self)
  - def update_ui(self)
  - [property] def enabled(self)
  - [enabled.setter] def enabled(self, on)
  - def on_timeline_event(self, new_time)
  - def update_time(self, new_time)
  - def update_scrubber_ui(self)
  - def transform_timeline_to_scrubber_position(self, timeline_time, snap = True)
  - def transform_scrubber_position_to_timeline(self, pos, snap = True)

- [deprecated] class Logger
  - static def warn(caller, string)
  - static def debug(caller, string)

- class RangeSlider
  - def __init__(self, timeline_view, frame)
  - def destroy(self)
  - def set_visible(self, is_visible)
  - def is_visible(self)
  - def build_ui(self)
  - def update_ui(self)

- class TimelineViewElement
  - def __init__(self, view: TimelineViewRoot)
  - def build_ui(self)
  - def update_ui(self)
  - def on_zoom(self, new_zoom)
  - def on_zoom_width(self, new_width)
  - def on_zoom_height(self, new_height)
  - def get_frame(self)
  - def get_top_frame(self)
  - def get_draw_frame(self)
  - def get_frame_offset(self)
  - def enable_scrubber(self, on)
  - [property] def zoom(self)
  - [zoom.setter] def zoom(self, new_zoom)
  - [property] def zoom_location(self)
  - [zoom_location.setter] def zoom_location(self, loc)
  - def zoom_step(self, step)
  - def set_x(self, x)
  - def set_y(self, y)
  - def get_x(self)
  - def get_y(self)

- class TimelineViewTopPlacerDefault(TimelineViewElement)
  - def __init__(self, view: TimelineViewRoot)
  - def build_ui(self)
  - def update_ui(self)
  - def get_top_frame(self)
  - def get_bottom_frame(self)
  - def get_frame_x(self)
  - def set_x(self, x)
  - def set_y(self, y)
  - def get_x(self)

- class TimelineValueModel(ui.AbstractValueModel)
  - def __init__(self, event_type = omni.timeline.TimelineEventType.END_TIME_CHANGED)
  - def get_value_as_string(self)
  - def get_value_as_float(self)
  - def begin_edit(self)
  - def set_value(self, value)
  - def end_edit(self)

- class ProgressPopup
  - def __init__(self, title, cancel_button_text = 'Cancel', cancel_button_fn = None, status_text = '', modal = True)
  - def set_cancel_fn(self, on_cancel_button_clicked)
  - def set_progress(self, progress)
  - def get_progress(self)
  - progress: Unknown
  - def set_status_text(self, status_text)
  - def get_status_text(self)
  - status_text: Unknown
  - def show(self)
  - def hide(self)
  - def is_visible(self)

## Functions

- def do_later(wait_frames = 1)
