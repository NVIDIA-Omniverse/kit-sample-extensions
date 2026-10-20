from math import ceil

import omni.anim.curve.core
import omni.kit.commands
import omni.timeline
import omni.ui as ui
import omni.usd

from .keyframe_listener import KeyFrameListener
from .utils import get_snap_to_frame, snap_to_frame


class keyframeNode:
    def __init__(self, timeline_widget, key_tick):
        self._timeline_widget = timeline_widget
        self._key_tick = key_tick
        curve_core = omni.anim.curve.core.acquire_interface()
        tps = curve_core.get_ticks_per_second()
        timeline = omni.timeline.get_timeline_interface()
        fps = timeline.get_time_codes_per_seconds()
        start_offset = timeline.get_zoom_start_time()
        self._origin_offset_value = fps * (key_tick / tps - start_offset) * self._timeline_widget.get_frame_width()
        self._moving = False
        self._highlight = False
        self._rect = None
        self._build_ui()

    def __del__(self):
        self._timeline_widget = None
        self._rect = None

    def _build_ui(self):
        self._placer = ui.Placer(
            width=0,
            draggable=False,
            drag_axis=ui.Axis.X,
            offset_x=self._origin_offset_value,
        )
        with self._placer:
            self._rect = ui.Rectangle(
                width=self.get_node_width(), style={"background_color": 0xFF2233A0, "margin_width": 0}
            )

        # om-44869: use rangeslider, not support drag key node
        # self._placer.set_offset_x_changed_fn(self._on_keyframe_moving)
        # self._placer.set_mouse_released_fn(self._on_keyframe_released)
        # self._placer.set_mouse_pressed_fn(self._on_mouse_pressed)

    def get_origin_offset(self):
        return self._origin_offset_value

    def get_node_width(self):
        return max(self._timeline_widget.get_frame_width() * 0.5, 1)

    @property
    def offset(self):
        return self._placer.offset_x.value

    @offset.setter
    def offset(self, value):
        self._placer.offset_x = value

    @property
    def highlight(self):
        return self._highlight

    @highlight.setter
    def highlight(self, value):
        self._highlight = value
        color = 0xFF5566C0 if value else 0xFF2233A0
        self._rect.style = {"background_color": color}
        self._placer.draggable = value

    # def _on_mouse_pressed(self, x, y, key, m):
    #     if key == 0 and m == KEYBOARD_MODIFIER_FLAG_SHIFT:
    #         offset = self._timeline_widget.screen_to_timeline(x) - self._placer.offset_x
    #         if offset > 0 and offset < self.get_node_width():
    #             self.highlight = not self.highlight

    # def _on_keyframe_moving(self, x):
    #     self._moving = True

    # def _on_keyframe_released(self, x, y, key, m):
    #     if key == 0 and self._moving and self.highlight:
    #         self._moving = False
    #         self.update_to_timeline()

    def update_to_timeline(self):
        if self._origin_offset_value != self._placer.offset_x.value:
            selection = omni.anim.curve.core.KeySelectionState()

            cmd = omni.anim.curve.core.commands.SelectAnimCurveKeys(
                times=omni.anim.curve.core.key_time_to_time_code(self._key_tick), selection_state=selection
            )
            cmd.do()

            frame = self._timeline_widget.offset_to_frame(self._placer.offset_x.value)
            frame = snap_to_frame(frame)
            omni.kit.commands.execute("EditAnimCurveKeys", selection_state=selection, time=frame)
        else:
            self._placer.offset_x = ui.Pixel(self._origin_offset_value)


class KeyframeWidget:
    def __init__(self, timeline_widget):
        self._timeline = omni.timeline.get_timeline_interface()
        self._timeline_widget = timeline_widget
        self._keyframe_listener = KeyFrameListener.get_instance()
        self._keyframe_listener.add_curve_update_fn(self._on_keyframe_evt)
        self._selection = omni.usd.get_context().get_selection()
        self._animcurve = omni.anim.curve.core.acquire_interface()
        self._keyframe_nodes = []
        self._keyframes_container = None

    def __del__(self):
        self.destroy()

    def destroy(self):
        self._timeline = None
        self._keyframes_container = None
        self._timeline_widget = None
        self._keyframe_listener = None
        self._selection = None
        self._animcurve = None
        if self._keyframe_nodes:
            self._keyframe_nodes.clear()
            self._keyframe_nodes = None

    def build_ui(self):
        self._keyframes_container = ui.Frame()
        self._keyframes_container.set_build_fn(self.on_keyframes_container_built)

    def rebuild(self):
        self._keyframes_container.rebuild()

    def on_keyframes_container_built(self):
        listen_prims = self._selection.get_selected_prim_paths()
        # save highlight
        highlights = []
        for node in self._keyframe_nodes:
            if node.highlight:
                highlights.append(node.offset)

        self._keyframe_nodes.clear()
        start_sec = self._timeline.get_zoom_start_time()
        end_sec = self._timeline.get_zoom_end_time()
        self._sorted_keyframes = self._keyframe_listener.get_keyframes(listen_prims, start_sec, end_sec)
        if len(self._sorted_keyframes) == 0:
            ui.Spacer()
            return

        with ui.ZStack():
            for key_tick in self._sorted_keyframes:
                kf_node = keyframeNode(self._timeline_widget, key_tick)
                self._keyframe_nodes.append(kf_node)

        # set highlight
        for offset in highlights:
            for node in self._keyframe_nodes:
                if abs(node.offset - offset) < (0.5 * self._timeline_widget.get_frame_width()):
                    node.highlight = True

    def get_nodes(self, min_pos, max_pos):
        nodes = []
        e = 0.01
        for node in self._keyframe_nodes:
            pos = node.get_origin_offset() + e
            if pos > min_pos and pos < max_pos:
                nodes.append(node)
        return nodes

    def _on_keyframe_evt(self, path, **kwargs):
        self._keyframes_container.rebuild()

    def get_next_key_time(self, cur_time):
        tps = self._animcurve.get_ticks_per_second()
        cur_tick = cur_time * tps
        next_key_time = None
        for key_tick in self._sorted_keyframes:
            if key_tick > cur_tick:
                next_key_time = key_tick / tps
                break
        return next_key_time

    def get_pre_key_time(self, cur_time):
        tps = self._animcurve.get_ticks_per_second()
        cur_tick = cur_time * tps
        pre_time = None
        for key_tick in self._sorted_keyframes:
            if key_tick < cur_tick:
                pre_time = key_tick / tps
            else:
                break

        return pre_time


class KeyframeSlider:
    HANDLE_WIDTH = 10
    START_LOCKED = 0
    END_LOCKED = 1
    BODY_LOCKED = 2
    NOT_LOCKED = 3

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

    def __init__(self, keyframe_widget: KeyframeWidget):
        self._edit = KeyframeSlider.EditScope()
        self._keyframe_widget = keyframe_widget
        self._timeline_widget = keyframe_widget._timeline_widget
        self._selected_nodes = []
        self._start_unit = 0
        self._end_unit = 0
        self._units = 0
        self._locked = self.NOT_LOCKED

    def __del__(self):
        self._keyframe_widget = None
        self._timeline_widget = None

    def build_ui(self):
        self._ui_frame = ui.Frame()
        self._ui_frame.set_build_fn(self._on_sliders_built)

    @property
    def visible(self):
        return self._ui_frame.visible

    @visible.setter
    def visible(self, value):
        self._ui_frame.visible = value

    def _on_sliders_built(self):
        with self._ui_frame:
            with ui.ZStack():
                # Body
                self._body = ui.Placer(draggable=True, drag_axis=ui.Axis.X)
                with self._body:
                    self._rect = ui.Rectangle(style={"margin_height": 0, "background_color": 0x55119999})
                    self._rect.set_mouse_released_fn(self._on_mouse_released)
                # Left handle
                self._start = ui.Placer(draggable=True, drag_axis=ui.Axis.X)
                with self._start:
                    ui.Rectangle(width=self.HANDLE_WIDTH, style={"margin_height": 0, "background_color": 0x99999999})
                # Right handle
                self._end = ui.Placer(draggable=True, drag_axis=ui.Axis.X)
                with self._end:
                    ui.Rectangle(width=self.HANDLE_WIDTH, style={"margin_height": 0, "background_color": 0x99999999})

        self._update_slider()

        # Connect them together
        self._start.set_offset_x_changed_fn(lambda _: self._start_moved())
        self._body.set_offset_x_changed_fn(lambda _: self._body_moved())
        self._end.set_offset_x_changed_fn(lambda _: self._end_moved())

    def _on_mouse_released(self, x, y, button_id, modifier):
        if not self._edit:
            # Something already edits it
            return

        with self._edit:
            start_unit, end_unit, need = self._align_frame()
            if not need:
                return
            omni.kit.undo.begin_group()
            if len(self._selected_nodes) > 0:
                direct = self._body.offset_x.value > self._select_start
                # to avoid a->b, b->c, the b will overlaped
                nodes = reversed(self._selected_nodes) if direct else self._selected_nodes
                for node in nodes:
                    node.update_to_timeline()
                end_unit = max(
                    end_unit, round(self._selected_nodes[-1].offset / self._timeline_widget.get_frame_width() + 1)
                )
                self._selected_nodes.clear()

            omni.kit.commands.execute("SetKeyframeSlider", slider=self, start=start_unit, end=end_unit)
            if get_snap_to_frame():
                self._keyframe_widget._keyframes_container.rebuild()
            omni.kit.undo.end_group()

    # get nodes in the range of slider
    def get_nodes(self):
        w = self._timeline_widget.get_frame_width()
        self._select_start = self._start_unit * w
        self._select_end = self._select_start + self._rect.width.value - self.HANDLE_WIDTH
        return self._keyframe_widget.get_nodes(self._select_start, self._select_end)

    def _move_keyframe_node(self):
        if len(self._selected_nodes) > 0:
            # # don't support scale nodes now
            # to_start = self._body.offset_x.value + self.HANDLE_WIDTH
            # to_end = self._body.offset_x.value + self._rect.width.value - self.HANDLE_WIDTH
            # for node in self._selected_nodes:
            #     t = (node.get_origin_offset() - self._select_start) / (self._select_end - self._select_start)
            #     t = max(min(t, 1), 0)
            #     node.offset = to_start + (to_end - to_start) * t

            cur_start = self._body.offset_x.value + self.HANDLE_WIDTH
            moved = cur_start - self._select_start
            for node in self._selected_nodes:
                node.offset = node.get_origin_offset() + moved
        else:
            self._selected_nodes = self.get_nodes()

    def _start_moved(self):
        if not self._edit:
            # Something already edits it
            return

        with self._edit:
            self._locked = self.END_LOCKED
            max_value = min(self._timeline_widget.get_content_width(), self._end.offset_x.value)
            self._start.offset_x = min(max(0, self._start.offset_x.value), max_value - self.HANDLE_WIDTH)
            self._body.offset_x = self._start.offset_x
            self._rect.width = ui.Pixel(self._end.offset_x - self._start.offset_x + self.HANDLE_WIDTH)
            # self._move_keyframe_node()

    def _body_moved(self):
        if not self._edit:
            # Something already edits it
            return

        with self._edit:
            self._locked = self.BODY_LOCKED
            max_width = self._timeline_widget.get_content_width() - self.HANDLE_WIDTH
            self._body.offset_x = min(
                max(self.HANDLE_WIDTH - self._rect.width.value, self._body.offset_x.value), max_width
            )
            self._start.offset_x = self._body.offset_x
            self._end.offset_x = self._body.offset_x + self._rect.width.value - self.HANDLE_WIDTH
            self._move_keyframe_node()

    def _end_moved(self):
        if not self._edit:
            # Something already edits it
            return

        with self._edit:
            self._locked = self.START_LOCKED
            max_x = self._timeline_widget.get_content_width() - self.HANDLE_WIDTH
            min_x = max(self._start.offset_x + self.HANDLE_WIDTH, 0)
            self._end.offset_x = min(max(min_x, self._end.offset_x.value), max_x)
            self._rect.width = ui.Pixel(self._end.offset_x - self._start.offset_x + self.HANDLE_WIDTH)
            # self._move_keyframe_node()

    def inside(self, x):
        return x > self._start.offset_x.value and x < self._end.offset_x.value + self.HANDLE_WIDTH

    def get_unit_range(self):
        return (self._start_unit, self._end_unit)

    def set_unit_range(self, start, end):
        if start < end:
            self._start_unit = start
            self._end_unit = end
        else:
            self._start_unit = end
        if get_snap_to_frame():
            self._start_unit = round(self._start_unit)
            self._end_unit = round(self._end_unit)
        self._units = self._end_unit - self._start_unit
        self._ui_frame.rebuild()

    def _align_frame(self):
        w = self._timeline_widget.get_frame_width()
        if self._locked == self.NOT_LOCKED:
            return 0, 0, False
        elif self._locked == self.BODY_LOCKED:
            start_x = self._start.offset_x.value + self.HANDLE_WIDTH
            start_unit = start_x / w
            end_unit = start_unit + self._units
        elif self._locked == self.START_LOCKED:
            end_x = self._end.offset_x.value - self.HANDLE_WIDTH
            end_unit = end_x / w
            start_unit = self._start_unit
        elif self._locked == self.END_LOCKED:
            start_x = self._start.offset_x.value + self.HANDLE_WIDTH
            start_unit = start_x / w
            end_unit = self._end_unit

        self._locked = self.NOT_LOCKED
        return start_unit, end_unit, True

    def _update_slider(self):
        with self._edit:
            w = self._timeline_widget.get_frame_width()
            align_start = self._start_unit * w - self.HANDLE_WIDTH
            self._start.offset_x = align_start
            self._body.offset_x = align_start
            align_end = self._end_unit * w
            self._end.offset_x = align_end
            self._rect.width = ui.Pixel(align_end - align_start + self.HANDLE_WIDTH)


"""
Move slider
"""


class SetKeyframeSliderCommand(omni.kit.commands.Command):
    def __init__(self, slider: KeyframeSlider, start: float, end: float):
        self._slider = slider
        self._start_unit = start
        self._end_unit = end
        self._origin_visible = self._slider.visible
        self._origin_start, self._origin_end = self._slider.get_unit_range()

    def do(self):
        self._slider.visible = True
        self._slider.set_unit_range(self._start_unit, self._end_unit)

    def undo(self):
        self._slider.visible = self._origin_visible
        self._slider.set_unit_range(self._origin_start, self._origin_end)


class ShowKeyframeSliderCommand(omni.kit.commands.Command):
    def __init__(self, slider: KeyframeSlider, visible: bool):
        self._slider = slider
        self._visible = visible
        self._origin_visible = self._slider.visible

    def do(self):
        self._slider.visible = self._visible

    def undo(self):
        self._slider.visible = self._origin_visible


omni.kit.commands.register(SetKeyframeSliderCommand)
omni.kit.commands.register(ShowKeyframeSliderCommand)
