import math

import AnimationSchema
import carb
from pxr import Gf

from .curve_editor_globals import *


# Tangent Type Control manager
class TtcManager:
    def __init__(self, is_weight_explicit, schema_strategy):
        self._is_weight_explicit = is_weight_explicit
        self._schema_strategy = schema_strategy

    def update_segment(self, segment, key_rect, next_key_rect, out_control_rect, next_in_control_rect):
        segment.show_as_bezier()
        segment.update_control(key_rect, next_key_rect, out_control_rect, next_in_control_rect)

    @staticmethod
    def _set_control_visible(rect, line, vis: bool):
        rect._set_visible(vis)
        line._set_visible(vis)

    def update_in_control_visibility(self, active: bool, prev_out_manager, in_control_rect, in_control_line):
        # update self.in_control visibility
        in_visible = (
            False
            if ((prev_out_manager is None) or prev_out_manager.hide_next_in_visible())
            else self.is_control_visible()
        )
        if active == False:
            in_visible = False
        self._set_control_visible(in_control_rect, in_control_line, in_visible)

    def update_out_control_visibility(self, active: bool, next_in_manager, out_control_rect, out_control_line):
        # update self.in_control visibility
        out_visible = False if (next_in_manager is None) else self.is_control_visible()
        if active == False:
            out_visible = False
        self._set_control_visible(out_control_rect, out_control_line, out_visible)

    def on_in_control_moved(
        self, key_rect, prev_key_rect, next_key_rect, in_control_rect, prev_out_control_rect, prev_segment
    ):
        if prev_key_rect:
            self._in_control_moved(key_rect, prev_key_rect, next_key_rect, in_control_rect)
            # update curve UI according to control
            prev_segment.update_control(prev_key_rect, key_rect, prev_out_control_rect, in_control_rect)
            # update proxy according to control
            self.update_control_proxy(key_rect, in_control_rect)
        else:
            # first in_control, do nothing but alignment with the key.
            offset_x = key_rect.get_key_ui_x()
            offset_y = key_rect.get_key_ui_y()
            in_control_rect._set_control_ui_x(offset_x)
            in_control_rect._set_control_ui_y(offset_y)
            in_control_rect._set_proxy_ui_x(offset_x)
            in_control_rect._set_proxy_ui_y(offset_y)

    # for in_control_rect to _set_control_ui. This UI is not draggable so no concern of recursive callback
    def _in_control_moved(self, key_rect, prev_key_rect, next_key_rect, in_control_rect):
        coord = Gf.Vec2d(key_rect.get_key_ui_x(), key_rect.get_key_ui_y())
        prev_coord = Gf.Vec2d(prev_key_rect.get_key_ui_x(), prev_key_rect.get_key_ui_y()) if prev_key_rect else None
        next_coord = Gf.Vec2d(next_key_rect.get_key_ui_x(), next_key_rect.get_key_ui_y()) if next_key_rect else None
        control_coord = Gf.Vec2d(in_control_rect._get_drag_ui_x(), in_control_rect._get_drag_ui_y())
        self._schema_strategy.ValidateInControl(coord, prev_coord, next_coord, control_coord)

        # update control offset.
        in_control_rect._set_control_ui_x(control_coord[0])
        in_control_rect._set_control_ui_y(control_coord[1])

    def on_out_control_moved(
        self, key_rect, prev_key_rect, next_key_rect, out_control_rect, next_in_control_rect, segment
    ):
        if next_key_rect:
            self._out_control_moved(key_rect, prev_key_rect, next_key_rect, out_control_rect)
            # update curve UI according to control
            segment.update_control(key_rect, next_key_rect, out_control_rect, next_in_control_rect)
            # update proxy according to control
            self.update_control_proxy(key_rect, out_control_rect)
        else:
            # last out_control, do nothing but alignment with the key.
            offset_x = key_rect.get_key_ui_x()
            offset_y = key_rect.get_key_ui_y()
            out_control_rect._set_control_ui_x(offset_x)
            out_control_rect._set_control_ui_y(offset_y)
            out_control_rect._set_proxy_ui_x(offset_x)
            out_control_rect._set_proxy_ui_y(offset_y)

    # a stub to for out_control_rect to _set_control_ui. This UI is not draggable so no concern of recursive callback
    def _out_control_moved(self, key_rect, prev_key_rect, next_key_rect, out_control_rect):
        coord = Gf.Vec2d(key_rect.get_key_ui_x(), key_rect.get_key_ui_y())
        prev_coord = Gf.Vec2d(prev_key_rect.get_key_ui_x(), prev_key_rect.get_key_ui_y()) if prev_key_rect else None
        next_coord = Gf.Vec2d(next_key_rect.get_key_ui_x(), next_key_rect.get_key_ui_y()) if next_key_rect else None
        control_coord = Gf.Vec2d(out_control_rect._get_drag_ui_x(), out_control_rect._get_drag_ui_y())
        self._schema_strategy.ValidateOutControl(coord, prev_coord, next_coord, control_coord)

        # update control offset.
        out_control_rect._set_control_ui_x(control_coord[0])
        out_control_rect._set_control_ui_y(control_coord[1])

    def hide_next_in_visible(self) -> bool:
        return False

    def is_control_visible(self) -> bool:
        return True

    # update control proxy according to the current control offset. Based on weighted or not.
    def update_control_proxy(self, key_rect, control_rect):
        control_offset_x = control_rect.get_control_ui_x()
        control_offset_y = control_rect.get_control_ui_y()

        # update visible proxy offset.
        if self._is_weight_explicit:
            control_rect._set_proxy_ui_x(control_offset_x)
            control_rect._set_proxy_ui_y(control_offset_y)
        else:
            offset_x = key_rect.get_key_ui_x()
            offset_y = key_rect.get_key_ui_y()
            delta_x = control_offset_x - offset_x
            delta_y = control_offset_y - offset_y
            in_length = math.sqrt(delta_x * delta_x + delta_y * delta_y)
            if in_length < EDITOR_CONTROL_HANDLE_SMALL_LENGTH:
                if SHOW_MORE_LOG_WARN:
                    carb.log_warn("Defective Usd data when initializing or key moving may also trigger this warning.")
            else:
                # ajust length while keep the direction.
                line_ratio = EDITOR_CONTROL_HANDLE_FIXED_LENGTH / in_length
                control_rect._set_proxy_ui_x(offset_x + delta_x * line_ratio)
                control_rect._set_proxy_ui_y(offset_y + delta_y * line_ratio)


class SmoothManager(TtcManager):
    pass


class FlatManager(TtcManager):
    pass


class FixedManager(TtcManager):
    pass


# using adsk autotangent.
class AutomaticManager(TtcManager):
    pass


class LinearManager(TtcManager):
    pass


class StepManager(TtcManager):
    def is_control_visible(self) -> bool:
        return False

    def hide_next_in_visible(self):
        return True

    def update_segment(self, segment, key_rect, next_key_rect, out_control_rect, next_in_control_rect):
        segment.show_as_step()


# special case for end controls
class DummyTtcManager(TtcManager):
    def __init__(self):
        super().__init__(True, None)

    def update_in_control_visibility(self, active: bool, prev_out_manager, in_control_rect, in_control_line):
        # always invisible
        in_visible = False
        self._set_control_visible(in_control_rect, in_control_line, in_visible)

    def update_out_control_visibility(self, active: bool, next_in_manager, out_control_rect, out_control_line):
        # always invisible
        out_visible = False
        self._set_control_visible(out_control_rect, out_control_line, out_visible)

    def _in_control_moved(self, key_rect, prev_key_rect, next_key_rect, in_control_rect):
        carb.log_error("Unexpected code path in DummyTtcManager._in_control_moved()")

    def _out_control_moved(self, key_rect, prev_key_rect, next_key_rect, out_control_rect):
        carb.log_error("Unexpected code path in DummyTtcManager._out_control_moved()")


gSingletonDummyTtcManager = DummyTtcManager()


def get_dummy_ttc_manager():
    global gSingletonDummyTtcManager
    return gSingletonDummyTtcManager


def create_ttc_manager(tangent_type, is_weight_explicit):
    schema_strategy = AnimationSchema.GetTangentControlStrategy(
        CurveInterpolation.TangentType.to_tangent_type_token(tangent_type), is_weight_explicit
    )

    if tangent_type == CurveInterpolation.TangentType.Automatic:
        manager = AutomaticManager(is_weight_explicit, schema_strategy)
    elif tangent_type == CurveInterpolation.TangentType.Smooth:
        manager = SmoothManager(is_weight_explicit, schema_strategy)
    elif tangent_type == CurveInterpolation.TangentType.Flat:
        manager = FlatManager(is_weight_explicit, schema_strategy)
    elif tangent_type == CurveInterpolation.TangentType.Fixed:
        manager = FixedManager(is_weight_explicit, schema_strategy)
    elif tangent_type == CurveInterpolation.TangentType.Linear:
        manager = LinearManager(is_weight_explicit, schema_strategy)
    elif tangent_type == CurveInterpolation.TangentType.Step:
        manager = StepManager(is_weight_explicit, schema_strategy)
    else:
        manager = None

    return manager
