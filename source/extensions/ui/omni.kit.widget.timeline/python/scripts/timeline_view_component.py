import math

import carb
import omni.ext
import omni.timeline
from omni import ui

from .ui_helpers import EditScope, Logger, WeakMethod, do_later, get_number_width


class TimelineViewRoot:
    """This is to document the public functions used by TimelineView, and aid with autocomplete"""

    def enable_scrubber(self, on):
        pass

    @property
    def zoom(self):
        return 1.0

    @zoom.setter
    def zoom(self, new_zoom):
        pass

    @property
    def zoom_location(self):
        return (0, 0)

    @zoom_location.setter
    def zoom_location(self, loc):
        pass

    def get_current_mouse_coords(self):
        return 0, 0

    def transform_timeline_to_position(self, timeline_val, frame_width=-1, snap=False) -> float:
        return 0.0


class TimelineViewElement:
    def __init__(self, view: TimelineViewRoot):
        self._view = view
        self._frame = None
        self._top_frame = None
        self._draw_frame = None

    #        self._logger_debug = True

    # Public actions
    def build_ui(self):
        pass

    def update_ui(self):
        pass

    # -------------------------------------------------------------------------------------------------------------
    #  Public events
    def on_zoom(self, new_zoom):
        """Handle the timeline being zoomed"""
        pass

    def on_zoom_width(self, new_width):
        pass

    def on_zoom_height(self, new_height):
        pass

    # -------------------------------------------------------------------------------------------------------------
    #  Public accessors
    def get_frame(self):
        return self._frame

    def get_top_frame(self):
        return self._top_frame

    def get_draw_frame(self):
        return self._draw_frame

    def get_frame_offset(self):
        raise Exception("Derived class must expose this function")

    def enable_scrubber(self, on):
        self._view.enable_scrubber(on)

    @property
    def zoom(self):
        """Override this function to change the behavior of the zoom"""
        return self._view.zoom

    @zoom.setter
    def zoom(self, new_zoom):
        self._view.zoom = new_zoom

    @property
    def zoom_location(self):
        return self._view.zoom_location

    @zoom_location.setter
    def zoom_location(self, loc):
        self._view.zoom_location = loc

    # -------------------------------------------------------------------------------------------------------------
    # Public behaviors
    def zoom_step(self, step):
        """Override to change behavior of zooming 1 step (+1 = zoom in, -1 = zoom out)"""
        # Should this stay here, or require two operations?
        # Maybe a bool as a parameter to suggest same-time position setting?
        pos_x, pos_y = self._view.get_current_mouse_coords()
        self.zoom_location = (pos_x, pos_y)

        cur_zoom = self.zoom
        step_scale = 0.1
        new_zoom = max(cur_zoom + (step * step_scale), 1.0)
        self.zoom = new_zoom

    def set_x(self, x):
        """This function should move the draw frame window to the position corresponding with 'X' in pixels"""
        raise Exception(f"Derived class {self} must expose this function - set_x")
        return

    def set_y(self, y):
        raise Exception(f"Derived class {self} must expose this function - set_y")
        return

    def get_x(self):
        raise Exception(f"Derived class {self} must expose this function - get_x")
        return 0.0

    def get_y(self):
        raise Exception(f"Derived class {self} must expose this function - get_y")
        return 0.0


class TimelineViewTopDefault(TimelineViewElement):
    """
    You can create a derived version of this class and override appropriate functions within it.
    Once you have created your class, call TimelineView.set_timeline_top(YourTimelineViewTop) to override
    the default.
    """

    def __init__(self, view: TimelineViewRoot):
        super().__init__(view)
        self._timeline_bottom_frame: ui.Frame = None
        # self._logger_debug = True

    def build_ui(self):
        self._frame = ui.ScrollingFrame(
            horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
            vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
        )
        with self._frame:
            with ui.VStack():
                with ui.HStack(height=0, width=ui.Percent(100)):
                    self._top_frame = ui.Frame()
                self._timeline_bottom_frame = ui.Frame()
        self._build_timeline_top()
        self._frame.set_build_fn(self._on_top_container_built)

    def update_ui(self):
        """This is a good candidate for a function to override.  It is called to update the upper "meter" portion of the timeline frame"""

        ret = self._view._draw_timeline_top()
        if ret is False:
            return False
        return True

    def get_bottom_frame(self):
        return self._timeline_bottom_frame

    def get_x(self):
        frame = self.get_frame()
        if not frame:
            return 0
        return frame.scroll_x

    def get_draw_x(self):
        draw_frame = self.get_draw_frame()
        if not draw_frame:
            return 0
        return draw_frame.scroll_x

    def set_x(self, x):
        # For this kind of Top, the scrolling frame is not the draw frame but the parent frame.
        timeline_frame = self.get_frame()
        if timeline_frame is not None:
            timeline_frame.scroll_x = x

    def _on_top_container_built(self):
        self._view.update_ui()

    def _build_timeline_top(self):
        Logger.debug(self, "build_timeline_top called ---")
        top_frame = self.get_top_frame()
        top_frame.clear()
        top_frame.set_mouse_pressed_fn(lambda x, y, b, m, s=self: s._on_top_mouse_pressed(x, y, b, m))
        top_frame.set_mouse_released_fn(lambda x, y, b, m, s=self: s._on_top_mouse_released(x, y, b, m))
        with top_frame:
            # timeline
            with ui.ZStack(height=self._view.get_timeline_height(), width=ui.Percent(100)):
                # timeline background
                self._draw_frame = ui.Frame()

    def _on_top_mouse_pressed(self, x, y, button_index, mod):
        timeline_position = self._view.transform_window_to_timeline(x, snap=self._view.get_snap_to_frame())
        delta = abs(timeline_position - self._view.get_time())
        if delta > 1:
            self._view.set_time(timeline_position)
            Logger.debug(self, f"Pressed top {x}-{y}-{button_index} timeline_pos={timeline_position}")
        return

    def _on_top_mouse_released(self, x, y, button_index, mod):
        # carb.log_warn(f"Released top {x}-{y}-{button_index}")
        return


class TimelineViewTopPlacerDefault(TimelineViewElement):
    """
    You can create a derived version of this class and override appropriate functions within it.
    Once you have created your class, call TimelineView.set_timeline_top(YourTimelineViewTop) to override
    the default.
    """

    def __init__(self, view: TimelineViewRoot):
        super().__init__(view)
        self._timeline_bottom_frame: ui.Frame = None
        # self._logger_debug = True

    def build_ui(self):
        with ui.Frame(horizontal_clipping=True):
            self._frame = ui.Placer()
            with self._frame:
                with ui.VStack():
                    with ui.HStack(height=0, width=ui.Percent(100)):
                        self._top_frame = ui.Frame()
                    self._timeline_bottom_frame = ui.Frame()
            self._build_timeline_top()
            Logger.debug(self, "build_ui finished ---")

        self._top_frame.set_build_fn(self._on_top_container_built)

    def update_ui(self):
        """This is a good candidate for a function to override.  It is called to update the upper "meter" portion of the timeline frame"""
        ret = self._view._draw_timeline_top()
        if ret is False:
            return False
        return True

    def get_top_frame(self):
        return self._top_frame

    def get_bottom_frame(self):
        return self._timeline_bottom_frame

    def get_frame_x(self):
        frame = self.get_frame()
        if not frame:
            return 0
        return frame.offset_x

    def set_x(self, x):
        timeline_frame = self.get_frame()
        if timeline_frame is not None:
            timeline_frame.offset_x = -x
        return 0.0

    def set_y(self, y):
        return

    def get_x(self):
        timeline_frame = self.get_frame()
        if timeline_frame is not None:
            offset = timeline_frame.offset_x.value
            return -offset
        return 0.0

    def _on_top_container_built(self):
        self._view.update_ui()

    def _build_timeline_top(self):
        Logger.debug(self, "build_timeline_top called ---")
        top_frame = self.get_top_frame()
        top_frame.clear()
        top_frame.set_mouse_pressed_fn(lambda x, y, b, m, s=self: s._on_top_mouse_pressed(x, y, b, m))
        top_frame.set_mouse_released_fn(lambda x, y, b, m, s=self: s._on_top_mouse_released(x, y, b, m))
        with top_frame:
            # timeline
            with ui.ZStack(height=self._view.get_timeline_height(), width=ui.Percent(100)):
                # timeline background
                ui.Rectangle(style_type_name_override="Timeline.TimelineBackground")
                self._draw_frame = ui.Frame()

    def _on_top_mouse_pressed(self, x, y, button_index, mod):
        timeline_position = self._view.transform_window_to_timeline(x, snap=self._view.get_snap_to_frame())
        delta = abs(timeline_position - self._view.get_time())
        if delta > 1:
            self._view.set_time(timeline_position)
            Logger.debug(self, f"Pressed top {x}-{y}-{button_index} timeline_pos={timeline_position}")
        return

    def _on_top_mouse_released(self, x, y, button_index, mod):
        # carb.log_warn(f"Released top {x}-{y}-{button_index}")
        return


class TimelineViewBottomDefault(TimelineViewElement):
    """See the Timeline Demo Window example that comes with this extension for an example of using this as a Canvas style frame"""

    def __init__(self, view: TimelineViewRoot):
        super().__init__(view)

    def build_ui(self):
        # Lower frame
        # Initial bottom frame is created by the top frame container, to make the UI work out
        bottom_frame = self._view.get_timeline_bottom_frame()
        with bottom_frame:
            self._frame = ui.ScrollingFrame(
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
            )
            self._view.get_timeline_bottom_frame().set_drop_fn(lambda event: self._on_drop(event))
            self._view.get_timeline_bottom_frame().set_accept_drop_fn(lambda event: self._on_accept_drop(event))
            super().build_ui()

    def set_x(self, x):
        timeline_frame = self.get_frame()
        if timeline_frame is not None:
            timeline_frame.scroll_x = x

    def set_y(self, y):
        timeline_frame = self.get_frame()
        if timeline_frame is not None:
            timeline_frame.scroll_y = y

    def _on_drop(self, event):
        Logger.debug(self, f"Dropped {event}")
        self._view._on_drop(event)

    def _on_accept_drop(self, event):
        Logger.debug(self, f"Dropping {event} onto bottom frame  ")
        return True
