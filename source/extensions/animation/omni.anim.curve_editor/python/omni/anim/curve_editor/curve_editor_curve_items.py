import weakref

from omni import ui

from .curve_editor_tangent_manager import *


class CurveItem:
    def __init__(self, owner_curve):
        self._curve_wp = weakref.ref(owner_curve)


# UI widget representing a key.
class CurveKeyRect(CurveItem):
    def __init__(self, owner_curve, is_tangent_broken: bool, is_tangent_weighted: bool):
        super().__init__(owner_curve)
        self._is_tangent_weighted = is_tangent_weighted
        self._is_tangent_broken = is_tangent_broken
        self._kmb_manager = self._curve_wp()._create_kmb_manager()

    def get_default_tangent_type(self):
        return self._curve_wp()._get_default_tangent_type()

    def get_pre_infinity_type(self):
        return self._curve_wp()._get_pre_infinity_type()

    def get_post_infinity_type(self):
        return self._curve_wp()._get_post_infinity_type()

    def get_tangent_weighted(self) -> bool:
        return self._is_tangent_weighted

    def get_tangent_broken(self) -> bool:
        return self._is_tangent_broken

    def get_in_tangent_type(self) -> int:
        return self._curve_wp()._get_in_tangent_type(self)

    def get_out_tangent_type(self) -> int:
        return self._curve_wp()._get_out_tangent_type(self)

    def _get_value_y(self):
        return self._curve_wp()._get_value_y(float(self._placer.offset_y))

    def _get_value_x(self):
        return self._curve_wp()._get_value_x(float(self._placer.offset_x))

    def _get_size(self):
        return self._curve_wp()._get_key_rect_size()

    def _get_kmb_manager(self):
        return self._kmb_manager

    def get_key_ui_x(self):
        return float(self._placer.offset_x)

    def get_key_ui_y(self):
        return float(self._placer.offset_y)

    def _set_key_ui_x(self, offset_x):
        self._placer.offset_x = offset_x
        self._end_placer.offset_x = offset_x

    def _set_key_ui_y(self, offset_y):
        self._placer.offset_y = offset_y
        self._end_placer.offset_y = offset_y

    def _get_drag_ui_x(self):
        return float(self._drag_placer.offset_x)

    def _get_drag_ui_y(self):
        return float(self._drag_placer.offset_y)

    def _set_drag_ui_x(self, offset_x):
        self._drag_placer.offset_x = offset_x

    def _set_drag_ui_y(self, offset_y):
        self._drag_placer.offset_y = offset_y

    def _on_y_moved(self, _):
        if self._curve_wp()._is_key_y_movable():
            # compare first to avoid harmful callback when press released.
            if self.get_key_ui_y() != self._get_drag_ui_y():
                self._set_key_ui_y(self._get_drag_ui_y())
                self._curve_wp()._on_key_y_moved(self)

    def _on_x_moved(self, _):
        if self._curve_wp()._is_key_x_movable():
            # compare first to avoid harmful callback when press released.
            if self.get_key_ui_x() != self._get_drag_ui_x():
                self._set_key_ui_x(self._get_drag_ui_x())
                self._curve_wp()._on_key_x_moved(self)

    def _on_pressed(self, x, y, b, m):
        if b == 0:  # only handle left button
            self._curve_wp()._on_key_pressed(self, m)

    def _on_released(self, x, y, b, m):
        if b == 0:  # only handle left button
            self._curve_wp()._on_key_released(self)

    # align drag to current key rect offset. It will not cause callback because the offset comparison in _on_*_moved().
    def _drag_align(self):
        self._set_drag_ui_x(self.get_key_ui_x())
        self._set_drag_ui_y(self.get_key_ui_y())

    def _command_set_tangent_broken(self, is_tangent_broken: bool):
        if is_tangent_broken != self._is_tangent_broken:
            self._curve_wp()._pre_tangent_broken_changed(self)
            self._is_tangent_broken = is_tangent_broken
            self._curve_wp()._command_set_tangent_broken(self, is_tangent_broken)
            self._curve_wp()._post_tangent_broken_changed(self)

    def _command_set_tangent_weighted(self, is_tangent_weighted: bool):
        if is_tangent_weighted != self._is_tangent_weighted:
            self._curve_wp()._pre_tangent_weighted_changed(self)
            self._is_tangent_weighted = is_tangent_weighted
            self._curve_wp()._command_set_tangent_weighted(self, is_tangent_weighted)
            self._curve_wp()._post_tangent_weighted_changed(self)

    def _command_set_in_tangent_type(self, type: int):
        if type == CurveInterpolation.TangentType.Step:
            # Just skip if type is Step for in_tangent.
            pass
        elif self.get_in_tangent_type() != type:
            self._curve_wp()._pre_tangent_type_changed(self)
            self._curve_wp()._command_set_in_tangent_type(self, type)
            self._curve_wp()._post_tangent_type_changed(self)

    def _command_set_out_tangent_type(self, type: int):
        if self.get_out_tangent_type() != type:
            self._curve_wp()._pre_tangent_type_changed(self)
            self._curve_wp()._command_set_out_tangent_type(self, type)
            self._curve_wp()._post_tangent_type_changed(self)

    def _command_set_key_ui_y(self, offset_y):
        self._curve_wp()._on_key_pressed(self, 0)
        self._drag_placer.offset_y = offset_y
        self._curve_wp()._on_key_released(self)

    def _command_set_key_ui_x(self, offset_x):
        self._curve_wp()._on_key_pressed(self, 0)
        self._drag_placer.offset_x = offset_x
        self._curve_wp()._on_key_released(self)

    def _command_set_selected(self, selected: bool):
        self._curve_wp()._on_key_selected(self, selected)

    def _set_active_color(self, active: bool):
        if active:
            self._rect.name = "CurveActiveKey"
        else:
            self._rect.name = "CurveKey"

    def _has_active_color(self) -> bool:
        return self._rect.name == "CurveActiveKey"

    def build_ui(self, x, y):
        keyCenterOffset = -self._get_size() / 2.0
        with ui.Placer(draggable=False, stable_size=True, offset_x=keyCenterOffset, offset_y=keyCenterOffset):
            self._placer = ui.Placer(draggable=False, stable_size=True, offset_x=x, offset_y=y)
            with self._placer:
                with ui.Frame():

                    def change_tool_tip(hovered: bool):  # A temporary value display method.
                        if hovered and (self._curve_wp() != None):
                            if self._curve_wp() != None:
                                self._rect.set_tooltip(
                                    self._curve_wp()._name + ":" + "{:.2f}".format(self._get_value_y())
                                )
                            else:
                                # this code path is possible in corner situation.
                                self._rect.set_tooltip("")

                    self._rect = ui.Rectangle(
                        name="CurveKey",
                        width=self._get_size(),
                        height=self._get_size(),
                        mouse_hovered_fn=change_tool_tip,
                    )

        with ui.Placer(draggable=False, stable_size=True, offset_x=keyCenterOffset, offset_y=keyCenterOffset):
            self._drag_placer = ui.Placer(draggable=True, stable_size=True, offset_x=x, offset_y=y)
            with self._drag_placer:
                with ui.Frame():
                    self._drag_rect = ui.Rectangle(name="CurveKeyDrag", width=self._get_size(), height=self._get_size())

        self._drag_placer.set_offset_y_changed_fn(self._on_y_moved)
        self._drag_placer.set_offset_x_changed_fn(self._on_x_moved)
        self._drag_rect.set_mouse_released_fn(self._on_released)
        self._drag_rect.set_mouse_pressed_fn(self._on_pressed)

    # helper UI.  Without this, using _rect and _placer will not satisfy the following 2 at the same time. 1. showing the curve without latency|separation from the rect , 2, showing the rect on top of curve.
    def build_end_ui(self, x, y):
        self._end_placer = ui.Placer(draggable=False, stable_size=True, offset_x=x, offset_y=y)
        with self._end_placer:
            with ui.Frame():
                # always invisible. By experiment, the curve takes invisible _end_rect as 0 size.
                self._end_rect = ui.Rectangle(visible=False)


# pure virtual class
class CurveControlRect(CurveItem):
    def __init__(self, owner_curve, tangent_type: int, is_tangent_weighted: bool):
        super().__init__(owner_curve)
        self._tangent_type = tangent_type
        self._is_tangent_weighted = is_tangent_weighted
        self._ttc_manager = self._curve_wp()._create_ttc_manager(tangent_type, is_tangent_weighted)
        # defacto Edit Scope for _set_drag_ui_offset.
        self._is_setting_drag = False

    def _command_set_tangent_weighted(self, is_tangent_weighted: bool):
        if self._is_tangent_weighted != is_tangent_weighted:
            self._is_tangent_weighted = is_tangent_weighted
            self._reinit_ttc_manager()

    def _command_set_tangent_type(self, tangent_type: int):
        if self._tangent_type != tangent_type:
            self._tangent_type = tangent_type
            self._reinit_ttc_manager()

    def _reinit_ttc_manager(self):
        self._ttc_manager = self._curve_wp()._create_ttc_manager(self._tangent_type, self._is_tangent_weighted)
        self._on_ttc_manager_changed()

    # it might not be the same as the key for end controls.
    def get_tangent_type(self):
        return self._tangent_type

    def get_tangent_weighted(self):
        return self._is_tangent_weighted

    def _within_setting_drag_scope(self) -> bool:
        return self._is_setting_drag

    # it is overridden by subclass for end controls handling.
    def _get_ttc_manager(self):
        return self._ttc_manager

    def _get_size(self):
        return self._curve_wp()._get_control_rect_size()

    def get_control_ui_x(self):
        return float(self._placer.offset_x)

    def get_control_ui_y(self):
        return float(self._placer.offset_y)

    def _get_drag_ui_x(self):
        return float(self._drag_placer.offset_x)

    def _get_drag_ui_y(self):
        return float(self._drag_placer.offset_y)

    def _get_proxy_ui_x(self):
        return float(self._proxy_placer.offset_x)

    def _get_proxy_ui_y(self):
        return float(self._proxy_placer.offset_y)

    def _set_control_ui_x(self, offset_x):
        self._placer.offset_x = offset_x

    def _set_control_ui_y(self, offset_y):
        self._placer.offset_y = offset_y

    # this is intentionally the only API of _drag_placer offset change.
    # ensures offset change fn executed in one shot.
    # 1st reason is performance: python is slow, it saves one call to _on_moved.
    # 2nd reason is to avoid corner case bug of moving to key offset for unbroken control.
    def _set_drag_ui_offset(self, offset_x=None, offset_y=None):
        if not self._is_setting_drag:
            self._is_setting_drag = True

            # these offset changes will not _on_moved in callback
            if offset_x != None:
                self._drag_placer.offset_x = offset_x
            if offset_y != None:
                self._drag_placer.offset_y = offset_y
            # call _on_moved one time.
            self._on_moved()

            self._is_setting_drag = False

    def _set_proxy_ui_x(self, offset_x):
        self._proxy_placer.offset_x = offset_x
        self._end_placer.offset_x = offset_x

    def _set_proxy_ui_y(self, offset_y):
        self._proxy_placer.offset_y = offset_y
        self._end_placer.offset_y = offset_y

    def _set_visible(self, vis: bool):
        self._drag_placer.visible = vis
        self._proxy_placer.visible = vis
        # do not touch self._placer, it should always be invisible.

    def _set_active_color(self, active: bool):
        if active:
            # just borrow the style from key
            self._proxy_rect.name = "CurveActiveKey"
        else:
            self._proxy_rect.name = "CurveControlProxy"

    # do like manually mouse drag drag_ui to proxy_ui's location, but not trigger callback.
    def _drag_align(self):
        if not self._is_setting_drag:
            self._is_setting_drag = True
            self._drag_placer.offset_x = self._get_proxy_ui_x()
            self._drag_placer.offset_y = self._get_proxy_ui_y()
            self._is_setting_drag = False
        else:
            # only use _drag_align in a standalone way. like in press release.
            carb.log_warn("Unexpected code path in CurveControlRect._drag_align")

    def _align_debug(self, b):
        if b == 0:  # only for left mouse button
            # warn cases do exist.
            if self._get_proxy_ui_x() != self._get_drag_ui_x():
                if abs(self._get_proxy_ui_x() - self._get_drag_ui_x()) > 0.1:
                    carb.log_warn(
                        f"For developer debugging only: control_ui_x: {self._get_proxy_ui_x()} != drag_ui_x: {self._get_drag_ui_x()}"
                    )
                else:
                    carb.log_info(f"control_ui_x: {self._get_proxy_ui_x()} != drag_ui_y: {self._get_drag_ui_x()}")
            if self._get_proxy_ui_y() != self._get_drag_ui_y():
                if abs(self._get_proxy_ui_y() - self._get_drag_ui_y()) > 0.1:
                    carb.log_warn(
                        f"For developer debugging only: control_ui_y: {self._get_proxy_ui_y()} != drag_ui_y: {self._get_drag_ui_y()}"
                    )
                else:
                    carb.log_info(f"control_ui_y: {self._get_proxy_ui_y()} != drag_ui_y: {self._get_drag_ui_y()}")

    def _build_ui_rect(self, x, y, name, draggable=False, visible=True):
        with ui.Placer(
            draggable=False, stable_size=True, offset_x=-self._get_size() / 2.0, offset_y=-self._get_size() / 2.0
        ):
            placer = ui.Placer(draggable=draggable, stable_size=True, offset_x=x, offset_y=y, visible=visible)
            with placer:
                with ui.Frame():
                    rect = ui.Rectangle(name=name, width=self._get_size(), height=self._get_size())

        return placer, rect

    # a stub for subclass. Use _set_drag_ui_offset(None, None) to call it indirectly except _on_moved_internal().
    def _on_moved(self):
        pass

    # a stub for subclass
    def _lazy_set_fixed(self):
        pass

    # conditional UI callback. Do not call directly.
    def _on_moved_internal(self):
        if self._is_setting_drag == False:
            # this code path is taken as real user dragging handling.
            self._lazy_set_fixed()

            self._on_moved()

    def build_ui(self, x, y):
        self._placer, self._rect = self._build_ui_rect(x, y, "CurveControl", visible=False)
        self._drag_placer, self._drag_rect = self._build_ui_rect(x, y, "CurveControlDrag", draggable=True)
        self._proxy_placer, self._proxy_rect = self._build_ui_rect(x, y, "CurveControlProxy")

        self._drag_placer.set_offset_x_changed_fn(lambda _: self._on_moved_internal())
        self._drag_placer.set_offset_y_changed_fn(lambda _: self._on_moved_internal())
        self._drag_rect.set_mouse_released_fn(self._on_released)
        self._drag_rect.set_mouse_pressed_fn(self._on_pressed)

        # For detecting unexpected cases. Anyway make sure _ui_drag_rect overlaps _ui_proxy_rect before mouse operation.
        self._proxy_rect.set_mouse_pressed_fn(lambda x, y, b, m: self._align_debug(b))

    # like other build_end_ui. It is to workaround some UI limitation. It is just like _proxy_placer and _proxy_rect in another UI layer.
    def build_end_ui(self, x, y):
        self._end_placer = ui.Placer(draggable=False, stable_size=True, offset_x=x, offset_y=y)
        with self._end_placer:
            with ui.Frame():
                self._end_rect = ui.Rectangle(visible=False)


# UI widgets for the user to drag when visible.
class CurveInControlRect(CurveControlRect):
    def __init__(self, owner_curve, tangent_type: int, is_tangent_weighted: bool):
        super().__init__(owner_curve, tangent_type, is_tangent_weighted)

    def _on_ttc_manager_changed(self):
        self._curve_wp()._on_in_ttc_manager_changed(self)

    def _get_ttc_manager(self):
        # if the first in control
        if self._curve_wp()._get_in_control_index(self) == 0:
            # omit the data specified manager.
            return get_dummy_ttc_manager()
        else:
            return self._ttc_manager

    def _lazy_set_fixed(self):
        self._curve_wp()._lazy_in_control_set_fixed(self)

    def _on_moved(self):
        self._curve_wp()._on_in_control_moved(self)

    def _on_released(self, x, y, b, m):
        if b == 0:  # only handle left button
            self._curve_wp()._on_in_control_released(self)

    def _on_pressed(self, x, y, b, m):
        if b == 0:  # only handle left button
            self._curve_wp()._on_in_control_pressed(self)


# UI widgets for the user to drag when visible.
class CurveOutControlRect(CurveControlRect):
    def __init__(self, owner_curve, tangent_type: int, is_tangent_weighted: bool):
        super().__init__(owner_curve, tangent_type, is_tangent_weighted)

    def _on_ttc_manager_changed(self):
        self._curve_wp()._on_out_ttc_manager_changed(self)

    def _get_ttc_manager(self):
        # if the last out control
        if self._curve_wp()._get_out_control_index(self) == self._curve_wp()._get_segment_quantity():
            # omit the data specified manager.
            return get_dummy_ttc_manager()
        else:
            return self._ttc_manager

    def _lazy_set_fixed(self):
        self._curve_wp()._lazy_out_control_set_fixed(self)

    def _on_moved(self):
        self._curve_wp()._on_out_control_moved(self)

    def _on_released(self, x, y, b, m):
        if b == 0:  # only handle left button
            self._curve_wp()._on_out_control_released(self)

    def _on_pressed(self, x, y, b, m):
        if b == 0:  # only handle left button
            self._curve_wp()._on_out_control_pressed(self)


# UI widget representing a line segment.
class CurveControlLine(CurveItem):
    def __init__(self, owner_curve):
        super().__init__(owner_curve)
        self._ui_line = None

    def build_ui(self, control_rect, key_rect):
        self._ui_line = ui.FreeLine(
            control_rect._end_rect, key_rect._end_rect, alignment=ui.Alignment.UNDEFINED, name="ControlLine"
        )

    def _set_visible(self, vis: bool):
        self._ui_line.visible = vis


# UI widget representing a key.
class CurveInvisibleRect(CurveItem):
    def __init__(self, owner_curve):
        super().__init__(owner_curve)

    def _get_value_y(self):
        return self._curve_wp()._get_value_y(float(self._placer.offset_y))

    def _get_value_x(self):
        return self._curve_wp()._get_value_x(float(self._placer.offset_x))

    def get_ui_x(self):
        return float(self._placer.offset_x)

    def get_ui_y(self):
        return float(self._placer.offset_y)

    def _set_ui_x(self, offset_x):
        self._placer.offset_x = offset_x

    def _set_ui_y(self, offset_y):
        self._placer.offset_y = offset_y

    def build_ui(self, x, y):
        self._placer = ui.Placer(draggable=False, stable_size=True, offset_x=x, offset_y=y)
        with self._placer:
            with ui.Frame():
                # always invisible. By experiment, the curve takes invisible _end_rect as 0 size.
                self._rect = ui.Rectangle(visible=False)


# UI represent of a curve segment between 2 keys.
class CurveSegment(CurveItem):
    def __init__(self, owner_curve):
        super().__init__(owner_curve)
        self._rect = None
        self._next_rect = None
        self._ui_bezier_segment = None
        self._ui_step_first = None
        self._ui_step_second = None

    def _get_color(self):
        return self._curve_wp()._get_curve_segment_color()

    # all anchor_rect, next_anchor_rect, should not be None
    def build_ui(
        self,
        anchor_rect,
        next_anchor_rect,
        step_rect,
        start_tangent_width,
        start_tangent_height,
        end_tangent_width,
        end_tangent_height,
    ):
        self._ui_bezier_segment = ui.FreeBezierCurve(
            anchor_rect._rect, next_anchor_rect._rect, style={"color": self._get_color()}
        )
        self.update_ui_tangent(start_tangent_width, start_tangent_height, end_tangent_width, end_tangent_height)

        if step_rect != None:
            self._ui_step_first = ui.FreeLine(
                anchor_rect._rect, step_rect._rect, alignment=ui.Alignment.UNDEFINED, style={"color": self._get_color()}
            )
            self._ui_step_second = ui.FreeLine(
                step_rect._rect,
                next_anchor_rect._rect,
                alignment=ui.Alignment.UNDEFINED,
                style={"color": self._get_color()},
            )

        self.show_as_bezier(True)

    def update_ui_tangent(self, start_tangent_width, start_tangent_height, end_tangent_width, end_tangent_height):
        self._ui_bezier_segment.start_tangent_width = ui.Pixel(start_tangent_width)
        self._ui_bezier_segment.start_tangent_height = ui.Pixel(start_tangent_height)

        self._ui_bezier_segment.end_tangent_width = ui.Pixel(end_tangent_width)
        self._ui_bezier_segment.end_tangent_height = ui.Pixel(end_tangent_height)

    def show_as_bezier(self, do_show: bool):
        self._ui_bezier_segment.visible = do_show
        if self._ui_step_first != None:
            self._ui_step_first.visible = not do_show
            self._ui_step_second.visible = not do_show


# UI represent of a curve segment between 2 keys, with controls.
class CurveControlSegment(CurveSegment):
    def __init__(self, owner_curve):
        super().__init__(owner_curve)
        self._control_rect = None
        self._next_control_rect = None
        self._step_rect = None
        self._ui_flat = None
        self._ui_vertical = None

    def _on_double_clicked(self, x, y, b, m):
        if b == 0:  # only handle left button
            self._curve_wp()._on_curve_double_clicked(self)

    def _update_active_color(self):
        # active color is the same as "Rectangle::CurveActiveKey"'s border_color
        color = (
            0xFFCCCCCC
            if self._rect()._has_active_color() and self._next_rect()._has_active_color()
            else self._get_color()
        )
        self._ui_bezier_segment.style = {"color": color}
        self._ui_flat.style = {"color": color}
        self._ui_vertical.style = {"color": color}

    def update_ui(self, key_rect, next_key_rect, control_rect, next_control_rect, step_rect):
        if self._ui_Frame == None:
            carb.log_warn("Unexpected code path in CurveControlSegment.update_ui()")
            return

        self._rect = weakref.ref(key_rect)
        self._next_rect = weakref.ref(next_key_rect)
        self._control_rect = weakref.ref(control_rect)
        self._next_control_rect = weakref.ref(next_control_rect)
        self._step_rect = weakref.ref(step_rect)

        with self._ui_Frame:
            with ui.ZStack():
                self._ui_bezier_segment = ui.FreeBezierCurve(
                    key_rect._end_rect, next_key_rect._end_rect, style={"color": self._get_color()}
                )
                self._ui_flat = ui.FreeLine(
                    key_rect._end_rect,
                    step_rect._rect,
                    alignment=ui.Alignment.UNDEFINED,
                    style={"color": self._get_color()},
                )
                self._ui_vertical = ui.FreeLine(
                    next_key_rect._end_rect,
                    step_rect._rect,
                    alignment=ui.Alignment.UNDEFINED,
                    style={"color": self._get_color()},
                )

                # shortcut multi_selection of all keys by double clicking the curve
                self._ui_bezier_segment.set_mouse_double_clicked_fn(self._on_double_clicked)
                self._ui_flat.set_mouse_double_clicked_fn(self._on_double_clicked)
                self._ui_vertical.set_mouse_double_clicked_fn(self._on_double_clicked)

        # default to show as bezier curve
        self.show_as_bezier()
        self.update_control(key_rect, next_key_rect, control_rect, next_control_rect)

    # all key_rect, next_key_rect, control_rect, next_control_rect, step_rect should not be None
    def build_ui(self, key_rect, next_key_rect, control_rect, next_control_rect, step_rect):
        self._ui_Frame = ui.Frame()
        self.update_ui(key_rect, next_key_rect, control_rect, next_control_rect, step_rect)

    def _make_curve_tangent(self, ui_curve, key_rect, next_key_rect, control_rect, next_control_rect):
        ui_curve.start_tangent_width = ui.Pixel(control_rect.get_control_ui_x() - key_rect.get_key_ui_x())
        ui_curve.start_tangent_height = ui.Pixel(control_rect.get_control_ui_y() - key_rect.get_key_ui_y())

        ui_curve.end_tangent_width = ui.Pixel(next_control_rect.get_control_ui_x() - next_key_rect.get_key_ui_x())
        ui_curve.end_tangent_height = ui.Pixel(next_control_rect.get_control_ui_y() - next_key_rect.get_key_ui_y())

    # Handle control offset update. It may not change ui according to show state.
    def update_control(self, key_rect, next_key_rect, control_rect, next_control_rect):
        if self._rect and self._next_rect:
            if key_rect == self._rect() and next_key_rect == self._next_rect():
                # Here, data integrity about key_rect and next_key_rect are ensured. Then we change the curve apperance.
                if self._ui_bezier_segment.visible is False:
                    # no need to update ui.FreeBezierCurve
                    return
                if control_rect == self._control_rect() and next_control_rect == self._next_control_rect():
                    # Here, data integrity is satistified
                    self._make_curve_tangent(
                        self._ui_bezier_segment, key_rect, next_key_rect, control_rect, next_control_rect
                    )
                    # Notify the curve observer, which is only infinity curve currently
                    self._curve_wp()._notify_infinity_curve_segment_change(self)

    def show_as_bezier(self):
        self._ui_flat.visible = False
        self._ui_vertical.visible = False
        self._ui_bezier_segment.visible = True
        self._make_curve_tangent(
            self._ui_bezier_segment, self._rect(), self._next_rect(), self._control_rect(), self._next_control_rect()
        )
        self._curve_wp()._notify_infinity_curve_segment_visibility_change(self)

    def show_as_step(self):
        self._ui_flat.visible = True
        self._ui_vertical.visible = True
        self._ui_bezier_segment.visible = False
        self._curve_wp()._notify_infinity_curve_segment_visibility_change(self)
