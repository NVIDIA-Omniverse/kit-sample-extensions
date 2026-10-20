import asyncio
import functools
import math
import traceback
import weakref
from functools import partial, wraps

import carb
import omni.kit.app
import omni.ui as ui


def handle_exception(func):
    """
    Decorator to print exception in async functions

    TODO: The alternative way would be better, but we want to use traceback.format_exc for better error message.
        result = await asyncio.gather(*[func(*args)], return_exceptions=True)
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except asyncio.CancelledError:
            # We always cacncel the task. It's not a problem.
            pass
        except Exception as e:
            carb.log_error(f"Exception when async '{func}'")
            carb.log_error(f"{e}")
            carb.log_error(f"{traceback.format_exc()}")

    return wrapper


# With shout-out to @Victor Yuden


class EditScope:
    """The class to avoid circular event calling"""

    def __init__(self):
        self.active = False

    def __enter__(self):
        self.active = True

    def __exit__(self, type, value, traceback):
        self.active = False

    def __bool__(self):
        return not self.active


class DoLater:
    """A simplified DoLater - please use partials, not lambda!"""

    def __init__(self, func: partial, *args, **kwargs):
        self._task: asyncio.Task = None
        self._do_func = func
        self._args = args
        self._kwargs = kwargs
        self._wait_frames = kwargs.pop("wait_frames", 1)

    def do(self):
        if self._task is None or self._task.done():
            self._task = asyncio.ensure_future(self._delayed_do())

    @handle_exception
    async def _delayed_do(self):
        # wait one frame
        while self._wait_frames > 0:
            await omni.kit.app.get_app().next_update_async()
            self._wait_frames = self._wait_frames - 1

        self._do_func(*self._args, **self._kwargs)


def do_later(wait_frames=1):
    # TODO: do_once=False
    def actual_decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            kwargs["wait_frames"] = wait_frames
            _do_later = DoLater(func, *args, **kwargs)
            return _do_later.do()

        return wrapper

    return actual_decorator


class ResizeableWidget:
    def __init__(self, parent_frame, left_handle_width=10, right_handle_width=10, drag_axis=ui.Axis.X):
        """the parent_frame here needs to be a ZStack for all this to work"""
        self.parent_frame = parent_frame  # the frame this widget is drawn in, must be created as a ui.ZStack
        self.left_handle: ui.Placer = None  # represents the widget for the left handle
        self.right_handle: ui.Placer = None  # the widget for the right handle
        self.body = None  # the body widget
        self.body_frame = None
        self.body_rectangle = None
        self._mouse_dolater_fn = None
        self.begin = 0  # the beginning position of the widget in the frame
        self.end = 0  # the end position of the widget in the frame
        self.width = 0  # the width of the frame
        self.range = 0  # the width of the widget
        self._edit = EditScope()
        self.left_handle_width = left_handle_width
        self.right_handle_width = right_handle_width
        self.drag_axis = drag_axis
        self.is_selected = False

    @do_later(wait_frames=1)
    def _dolater_build_fn(self):
        return self._build_ui()

    @do_later(wait_frames=1)
    def _dolater_update_fn(self):
        return self._update_ui()

    def __del__(self):
        self._parent_frame = None
        self._edit = None
        self._mouse_dolater_fn = None

    def set_mouse_fn(self, mouse_fn):
        self._mouse_dolater_fn = mouse_fn

    # This is needed for deferring the caller's computation of frame elements which aren't yet built at the time
    # of creation
    def calculate_frame_values(self, width=0):
        return

    def set_begin(self, begin: int, update=True):
        if self.begin != begin:
            self.begin = begin
            self.range = max(self.end - self.begin, 0)
            if update:
                self.update_ui()
            return True
        return False

    def set_end(self, end: int, update=True):
        if self.end != end:
            self.end = end
            self.range = max(self.end - self.begin, 0)
            if update:
                self.update_ui()
            return True
        return False

    def set_width(self, width: int, update=True):
        if self.width != width:
            self.width = width
            if update:
                self.update_ui()

    def get_width(self):
        return self.width

    def get_begin(self):
        return self.begin

    def get_end(self):
        return self.end

    def set_range(self, begin, end, update=True):
        changed = False
        if begin != self.begin:
            changed = True
            self.begin = begin
        if end != self.end:
            changed = True
            self.end = end

        if changed:
            self.range = max(self.end - self.begin, 0)
            if update:
                self.update_ui()

        return changed

    # Build functions should setup the frames and permanent structures.  Update functions should
    # then be used to make any changes.  Build once, update many times.
    def build_ui(self):
        mouse_fn = self._mouse_dolater_fn
        self.calculate_frame_values(self.parent_frame.computed_width)

        with self.parent_frame:
            with ui.ZStack():
                style_override = self.get_style_type_name_override()
                self.body = ui.Placer(
                    draggable=True,
                    drag_axis=self.drag_axis,
                    offset_x=self.begin,
                    horizontal_clipping=True,
                    identifier="body",
                )
                with self.body:
                    if mouse_fn:
                        self.body.set_mouse_pressed_fn(mouse_fn)
                    self.body_frame = ui.ZStack(width=self.range)
                    with self.body_frame:
                        self.body_rectangle = ui.Rectangle(
                            style_type_name_override=style_override, selected=self.is_selected
                        )
                        self.body_rectangle.set_mouse_pressed_fn(functools.partial(self._mouse_dolater_fn))
                        self.fill_body()

                if self.left_handle_width > 0:
                    # Left handle
                    left_handle_style = self.get_left_handle_style()
                    self.left_handle = ui.Placer(
                        draggable=True, drag_axis=self.drag_axis, offset_x=self.begin, identifier="left_handle"
                    )
                    with self.left_handle:
                        self.fill_left_handle(left_handle_style)

                if self.right_handle_width > 0:
                    # Right handle
                    right_handle_style = self.get_right_handle_style()
                    self.right_handle = ui.Placer(
                        draggable=True,
                        drag_axis=self.drag_axis,
                        offset_x=self.begin + self.range - self.right_handle_width,
                        identifier="right_handle",
                    )
                    with self.right_handle:
                        self.fill_right_handle(right_handle_style)

                # Connect them together
                rect = self.body_rectangle
                if self.left_handle:
                    self.left_handle.set_offset_x_changed_fn(
                        lambda _, s=self.left_handle, b=self.body, e=self.right_handle, r=rect: self._begin_moved(
                            s, b, e, r
                        )
                    )
                if self.body:
                    self.body.set_offset_x_changed_fn(
                        lambda _, s=self.left_handle, b=self.body, e=self.right_handle, r=rect: self._body_moved(
                            s, b, e, r
                        )
                    )
                    self.body.set_mouse_released_fn(lambda _, x, y, b, r=rect: self._mouse_released(x, y, b, r))
                if self.right_handle:
                    self.right_handle.set_offset_x_changed_fn(
                        lambda _, s=self.left_handle, b=self.body, e=self.right_handle, r=rect: self._end_moved(
                            s, b, e, r
                        )
                    )
        self.update_ui()

    def set_selected(self, selected):
        self.is_selected = selected

    def get_style_type_name_override(self):
        return ""

    def get_left_handle_style(self):
        return self.get_style_type_name_override()

    def get_right_handle_style(self):
        return self.get_style_type_name_override()

    def update_ui(self):
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
                # self.left_handle.offset_x = self.begin
            if self.body is not None:
                self.body.visible = True
                # self.body.offset_x = self.begin
            if self.body_frame is not None:
                self.body_frame.visible = True
                # self.body_frame.width = ui.Length(self.range)

            if self.right_handle is not None:
                self.right_handle.visible = True
                # cur = self.right_handle.offset_x
                # new = max(self.end - self.right_handle_width, 0)
                # if new != cur:
                # self.right_handle.offset_x = self.end

        Logger.debug(self, f"update_ui -- range={self.range}")
        self._fill_body()
        return True

    def _build_ui(self):
        raise Exception("This function is deprecated!  Please update your code to use .build.ui() instead")
        return

    def _update_ui(self):
        raise Exception("This function is deprecated!  Please update your code to use .update_ui() instead")
        return

    def fill_body(self):
        return

    def _fill_body(self):
        return

    def update(self):
        return

    def get_selected(self):
        return self.is_selected

    def fill_left_handle(self, clip_style):
        with ui.HStack(width=self.left_handle_width - 1):
            ui.Spacer(width=1)
            with ui.VStack():
                ui.Spacer(height=1)
                ui.Rectangle(style_type_name_override=clip_style, style={"border_width": 0})
                ui.Spacer(height=1)

    def fill_right_handle(self, clip_style):
        with ui.HStack(width=self.right_handle_width - 1):
            with ui.VStack():
                ui.Spacer(height=1)
                ui.Rectangle(style_type_name_override=clip_style, style={"border_width": 0})
                ui.Spacer(height=1)
            ui.Spacer(width=1)

    # -- Private functions
    def _mouse_released(self, x, y, b, rect):
        return

    def _begin_moved(self, begin, body, end, rect):
        if not self._edit:
            # Something already edits it
            return

        with self._edit:
            # Set the default begin_x, but if a begin handle exists, it will override it
            begin_x = body.offset_x.value
            end_x = end.offset_x.value + self.right_handle_width
            if begin:
                # TODO relam -- Bug here, this should just be a simple clamp, whether or not begin handle exists
                begin_x = begin.offset_x.value
                if begin_x < 0:
                    begin_x = 0
                if begin_x > end_x:
                    begin_x = end_x

            self.range = int(end_x - begin_x)
            self.body.offset_x = begin_x
            self.body_frame.width = ui.Length(self.range)

    def _body_moved(self, begin, body, end, rect):
        if not self._edit:
            # Something already edits it
            return

        with self._edit:
            if begin:
                begin.offset_x = body.offset_x.value
            begin_x = begin.offset_x.value
            end_x = begin_x + self.range
            self.range = max(end_x - begin_x, 0)
            self.right_handle.offset_x = end_x
            # if self.set_range(begin_x, end_x, False):
            #     # carb.log_warn(f"BODY MOVED - Begin: {begin_x} End: {end_x} Range: {self.range}")
            #     self._update_ui()  # This is normally deferred, but must be done in-ine here

    def _end_moved(self, begin, body, end, rect):
        """Derived classes are responsible for "rules" about movement.... no rules, chaos ensues! =)"""
        if not self._edit:
            # Something already edits it
            return

        with self._edit:
            end_x = self.range
            if end:
                end_x = end.offset_x.value + self.right_handle_width
                begin_x = begin.offset_x.value
                if end_x > self.width:
                    end_x = self.width
                if end_x < begin_x:
                    end_x = begin_x

            self.range = end_x - begin_x
            self.body_frame.width = ui.Length(self.range)

            self.end = end_x


# relam - This should probably be a more global thing, really --- taken from Xu Nie's code
@omni.kit.app.deprecated("Use your own WeakMethod class instead")
class WeakMethod(weakref.WeakMethod):
    def __call__(self, *args, **kwargs):
        obj = weakref.ref.__call__(self)
        func = self._func_ref()
        if obj is None or func is None:
            return None
        return func(obj, *args, **kwargs)


class ClickEvent:
    def __init__(self, callback_fn, always_call):
        self._callback_fn = callback_fn
        self._always_call = always_call


class MouseClickSorter:
    """
    A class which allows for multiple events to be triggered in the same frame, but only one of those events to
    actually fire off based on "sorting".
    This allows for UI "layers" to only get called for the "top" layer when a mouse event happens, for example.
    Even though the class is called "MouseClickSorter", it could have a more generic name since it really
    just calls a callback function on a sorted list.
    """

    _instance = None

    def __init__(self):
        raise RuntimeError("Call instance() instead")

    def initialize(self):
        self._click_events_dict = {}
        self._wait_frames = 0
        return

    @do_later(wait_frames=3)
    def _delayed_do_click(self):
        # We're counting on this list already being sorted, so just return the LAST entry! Last entry is highest Z-order.
        # everything else gets ignored
        # TODO -- To improve this, call ALL the functions that were added, but notify each of them that someone else already handled it
        # functions need to be aware of this
        # NOTE: I don't see any actual use of _always_call being true.
        first = True
        for key in sorted(self._click_events_dict.keys()):
            click_events = self._click_events_dict[key]
            for click_event in reversed(click_events):
                if first or click_event._always_call:
                    click_event._callback_fn()
                    first = False

        self._click_events_dict.clear()
        return

    @classmethod
    def instance(self):
        if not self._instance:
            self._instance = self.__new__(self)
            self._instance.initialize()
        return self._instance

    def add_click_event(self, callback_fn, z_order=0, always_call=False):
        click_event = ClickEvent(callback_fn, always_call)
        zorder_events = self._click_events_dict.get(z_order)
        if zorder_events:
            zorder_events.append(click_event)
        else:
            self._click_events_dict[z_order] = [click_event]
        self._delayed_do_click()


class CustomProgressModel(ui.AbstractValueModel):
    def __init__(self):
        super().__init__()
        self._value = 0.0

    def set_value(self, value):
        """Reimplemented set"""
        try:
            value = float(value)
        except ValueError:
            value = None
        if value != self._value:
            # Tell the widget that the model is changed
            self._value = value
            self._value_changed()

    def get_value_as_float(self):
        return self._value

    def get_value_as_string(self):
        return str(int(self._value * 100)) + "%"


class ProgressPopup:
    """Creates a modal window with a status label and a progress bar inside.

    Args:
        title (str): Title of this window.
        cancel_button_text (str): It will have a cancel button by default. This is the title of it.
        cancel_button_fn (function): The callback after cancel button is clicked.
        status_text (str): The status text.
        min_value: The min value of the progress bar. It's 0 by default.
        max_value: The max value of the progress bar. It's 100 by default.
        dark_style: If it's to use dark style or light style. It's dark stye by default.
    """

    def __init__(self, title, cancel_button_text="Cancel", cancel_button_fn=None, status_text="", modal=True):
        self._status_text = status_text
        self._title = title
        self._cancel_button_text = cancel_button_text
        self._cancel_button_fn = cancel_button_fn
        self._modal = False
        self._build_ui()

    def __del__(self):
        self._cancel_button_fn = None

    def __enter__(self):
        self._popup.visible = True
        return self

    def __exit__(self, type, value, trace):
        self._popup.visible = False

    def set_cancel_fn(self, on_cancel_button_clicked):
        self._cancel_button_fn = on_cancel_button_clicked

    def set_progress(self, progress):
        self._progress_bar.model.set_value(progress)

    def get_progress(self):
        return self._progress_bar.model.get_value_as_float()

    progress = property(get_progress, set_progress)

    def set_status_text(self, status_text):
        self._status_label.text = status_text

    def get_status_text(self):
        return self._status_label.text

    status_text = property(get_status_text, set_status_text)

    def show(self):
        self._popup.visible = True

    def hide(self):
        self._popup.visible = False

    def is_visible(self):
        return self._popup.visible

    def _on_cancel_button_fn(self):
        self.hide()
        if self._cancel_button_fn:
            self._cancel_button_fn()

    def _build_ui(self):
        self._popup = ui.Window(self._title, visible=False, height=0, dockPreference=ui.DockPreference.DISABLED)
        self._popup.flags = (
            ui.WINDOW_FLAGS_NO_COLLAPSE
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_SCROLLBAR
            | ui.WINDOW_FLAGS_NO_RESIZE
            | ui.WINDOW_FLAGS_NO_MOVE
        )

        if self._modal:
            self._popup.flags = self._popup.flags | ui.WINDOW_FLAGS_MODAL

        with self._popup.frame:
            with ui.VStack(height=0):
                ui.Spacer(height=10)
                with ui.HStack(height=0):
                    ui.Spacer()
                    self._status_label = ui.Label(self._status_text, width=0, height=0)
                    ui.Spacer()
                ui.Spacer(height=10)
                with ui.HStack(height=0):
                    ui.Spacer()
                    self._progress_bar_model = CustomProgressModel()
                    self._progress_bar = ui.ProgressBar(
                        self._progress_bar_model, width=300, style={"color": 0xFFFF9E3D}
                    )
                    ui.Spacer()
                ui.Spacer(height=5)
                with ui.HStack(height=0):
                    ui.Spacer(height=0)
                    cancel_button = ui.Button(self._cancel_button_text, width=0, height=0)
                    cancel_button.set_clicked_fn(self._on_cancel_button_fn)
                    ui.Spacer(height=0)
                ui.Spacer(width=0, height=10)


@omni.kit.app.deprecated("Use your own Logger class instead")
class Logger:
    @staticmethod
    def warn(caller, string):
        if caller and hasattr(caller, "_logger_warn") and caller._logger_warn is True:
            carb.log_warn(f"[{type(caller).__name__}] {string}")

    @staticmethod
    def debug(caller, string):
        if caller and hasattr(caller, "_logger_debug") and caller._logger_debug is True:
            carb.log_warn(f"[{type(caller).__name__}] {string}")


def get_number_of_digits(number):
    if number > 0:
        return int(math.log10(number)) + 1
    elif number == 0:
        return 1
    return int(math.log10(-number)) + 2  # to account for the sign


def get_number_width(number, font_size=14):
    num = get_number_of_digits(number)
    return num * font_size
