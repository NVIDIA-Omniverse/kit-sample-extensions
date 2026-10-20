import carb


# Key Move Behavior manager
class KmbManager:
    # stub to update 6 neighboring controls by some rule
    def move_manage(
        self,
        key_rect,
        in_control_rect,
        out_control_rect,
        prev_key_rect,
        prev_in_control_rect,
        prev_out_control_rect,
        next_key_rect,
        next_in_control_rect,
        next_out_control_rect,
        step_rect,
        prev_step_rect,
    ):
        ## helper code path for subclass to use
        #

        if prev_key_rect:
            prev_out_control_rect._set_drag_ui_offset()
            # meaningful for derived tangent types, like auto and smooth
            prev_in_control_rect._set_drag_ui_offset()
        else:
            # the first in_control are kept the same offset the the first key.
            in_control_rect._set_drag_ui_offset(key_rect.get_key_ui_x(), key_rect.get_key_ui_y())

        if next_key_rect:
            next_in_control_rect._set_drag_ui_offset()
            # meaningful for derived tangent types, like auto and smooth
            next_out_control_rect._set_drag_ui_offset()
        else:
            # the last out_control are kept the same offset the the first key.
            out_control_rect._set_drag_ui_offset(key_rect.get_key_ui_x(), key_rect.get_key_ui_y())

        # update prev step rect. Same x as this indexed key.
        if prev_step_rect:
            prev_step_rect._set_ui_x(key_rect.get_key_ui_x())

        # update this step rect. Same y as this indexed key.
        if step_rect:
            step_rect._set_ui_y(key_rect.get_key_ui_y())

    def _check_has_old_values(self, key_rect):
        if not hasattr(key_rect, "_kmb_values"):
            carb.log_warn("Unexpected code path in CurveOfAttribute._on_key_*_moved()")
            return False
        else:
            return True

    def _get_old_offset_x(self, key_rect):
        return key_rect._kmb_values[0]

    def _get_old_offset_y(self, key_rect):
        return key_rect._kmb_values[1]

    def _get_old_in_tan_x(self, key_rect):
        return key_rect._kmb_values[2]

    def _get_old_in_tan_y(self, key_rect):
        return key_rect._kmb_values[3]

    def _get_old_out_tan_x(self, key_rect):
        return key_rect._kmb_values[4]

    def _get_old_out_tan_y(self, key_rect):
        return key_rect._kmb_values[5]


class KmbWeighRelatively(KmbManager):
    def move_manage(
        self,
        key_rect,
        in_control_rect,
        out_control_rect,
        prev_key_rect,
        prev_in_control_rect,
        prev_out_control_rect,
        next_key_rect,
        next_in_control_rect,
        next_out_control_rect,
        step_rect,
        prev_step_rect,
    ):
        if not self._check_has_old_values(key_rect):
            return
        else:
            old_offset_x = self._get_old_offset_x(key_rect)
            old_offset_y = self._get_old_offset_y(key_rect)
            old_in_tan_x = self._get_old_in_tan_x(key_rect)
            old_in_tan_y = self._get_old_in_tan_y(key_rect)
            old_out_tan_x = self._get_old_out_tan_x(key_rect)
            old_out_tan_y = self._get_old_out_tan_y(key_rect)

        offset_x = key_rect.get_key_ui_x()
        offset_y = key_rect.get_key_ui_y()

        # get in_offset_x, in_offset_y
        if prev_key_rect:
            prev_ratio = (offset_x - prev_key_rect.get_key_ui_x()) / (old_offset_x - prev_key_rect.get_key_ui_x())
            in_offset_x = offset_x + old_in_tan_x * prev_ratio
            in_offset_y = old_offset_y + old_in_tan_y * prev_ratio
        else:
            in_offset_x = offset_x + old_in_tan_x
            in_offset_y = old_offset_y + old_in_tan_y

        # get out_offset_x, out_offset_y
        if next_key_rect:
            next_ratio = (offset_x - next_key_rect.get_key_ui_x()) / (old_offset_x - next_key_rect.get_key_ui_x())
            out_offset_x = offset_x + old_out_tan_x * next_ratio
            out_offset_y = old_offset_y + old_out_tan_y * next_ratio
        else:
            out_offset_x = offset_x + old_out_tan_x
            out_offset_y = old_offset_y + old_out_tan_y

        # update control ui (and consequently tangent attribute).
        in_control_rect._set_drag_ui_offset(in_offset_x, in_offset_y)
        out_control_rect._set_drag_ui_offset(out_offset_x, out_offset_y)

        super().move_manage(
            key_rect,
            in_control_rect,
            out_control_rect,
            prev_key_rect,
            prev_in_control_rect,
            prev_out_control_rect,
            next_key_rect,
            next_in_control_rect,
            next_out_control_rect,
            step_rect,
            prev_step_rect,
        )


class KmbWeighAbsolutely(KmbManager):  # pragma: no cover    Unused code
    def move_manage(
        self,
        key_rect,
        in_control_rect,
        out_control_rect,
        prev_key_rect,
        prev_in_control_rect,
        prev_out_control_rect,
        next_key_rect,
        next_in_control_rect,
        next_out_control_rect,
        step_rect,
        prev_step_rect,
    ):
        if not self._check_has_old_values(key_rect):
            return

        old_offset_x = self._get_old_offset_x(key_rect)
        old_offset_y = self._get_old_offset_y(key_rect)
        old_in_tan_x = self._get_old_in_tan_x(key_rect)
        old_in_tan_y = self._get_old_in_tan_y(key_rect)
        old_out_tan_x = self._get_old_out_tan_x(key_rect)
        old_out_tan_y = self._get_old_out_tan_y(key_rect)

        offset_x = key_rect.get_key_ui_x()
        offset_y = key_rect.get_key_ui_y()

        # get in_offset_x, in_offset_y.
        in_offset_x = offset_x + old_in_tan_x
        in_offset_y = offset_y + old_in_tan_y

        # get out_offset_x, out_offset_y.
        out_offset_x = offset_x + old_out_tan_x
        out_offset_y = offset_y + old_out_tan_y

        # update control ui (and consequently tangent attribute).
        in_control_rect._set_drag_ui_offset(in_offset_x, in_offset_y)
        out_control_rect._set_drag_ui_offset(out_offset_x, out_offset_y)

        super().move_manage(
            key_rect,
            in_control_rect,
            out_control_rect,
            prev_key_rect,
            prev_in_control_rect,
            prev_out_control_rect,
            next_key_rect,
            next_in_control_rect,
            next_out_control_rect,
            step_rect,
            prev_step_rect,
        )


def create_kmb_manager():
    if False:
        manager = KmbWeighRelatively()
    else:
        manager = KmbWeighAbsolutely()

    return manager
