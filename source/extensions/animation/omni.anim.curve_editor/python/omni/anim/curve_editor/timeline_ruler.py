import enum
from typing import Tuple

from omni import ui


class Ruler(ui.Frame):
    class FaceDirection(enum.Enum):
        Down = "Down"
        Right = "Right"

    def __init__(self, face_dir=FaceDirection.Down, range=(0, 1), **kwargs):
        self._face_dir = face_dir

        self._range = (0, 1)
        self.range = range
        self._last_text_size = 0
        self.on_built = None

        is_horizontal = None
        if self._face_dir == self.FaceDirection.Down:
            is_horizontal = True
        elif self._face_dir == self.FaceDirection.Right:
            is_horizontal = False

        super().__init__(
            build_fn=self._build,
            computed_content_size_changed_fn=lambda: self.rebuild(),
            horizontal_clipping=is_horizontal,
            vertical_clipping=not is_horizontal,
            **kwargs,
        )

    @property
    def range(self):
        return self._range

    @range.setter
    def range(self, range: Tuple):
        if self._range == range:
            return

        self._range = range
        self.rebuild()

    def _build(self):
        # Get widget length
        is_horizontal = None
        if self._face_dir == self.FaceDirection.Down:
            is_horizontal = True
        elif self._face_dir == self.FaceDirection.Right:
            is_horizontal = False

        widget_length = None
        if is_horizontal:
            widget_length = self.computed_width
        else:
            widget_length = self.computed_height

        if widget_length == 0:
            return

        # Approximate text width
        range_begin, range_end = self.range
        if range_begin == range_end:
            return

        text_prefix = " "
        font_size = 14
        text_size = 4

        if is_horizontal:
            begin_text = str(int(range_begin))
            end_text = str(int(range_end))
            text_size = max(len(begin_text), len(end_text)) + len(text_prefix) + 1
            if abs(text_size - self._last_text_size) <= 1:
                text_size = self._last_text_size
            else:
                self._last_text_size = text_size

        text_width = text_size * font_size * 0.5

        # Find a stride
        max_step_count = widget_length / text_width
        range = abs(range_end - range_begin)
        min_stride = range / max_step_count

        stride_sign = 1 if range_end >= range_begin else -1
        stride = 1
        minor_stride = stride
        exp = 0
        stride_list = [1, 2, 5]
        stride_list.sort()
        while True:
            found = False
            for basic_stride in stride_list:
                stride = basic_stride * 10**exp
                if stride >= min_stride:
                    minor_stride = stride / basic_stride
                    found = True
                    break
            if found:
                break

            exp += 1

        is_range_float = isinstance(range_begin, float) or isinstance(range_end, float)

        if stride == 1 and is_range_float:
            stride_list.reverse()
            exp = -1
            while True:
                found = False
                for basic_stride in stride_list:
                    smaller_stride = basic_stride * 10**exp
                    if smaller_stride < min_stride:
                        found = True
                        break
                    else:
                        stride = smaller_stride
                if found:
                    break

                exp -= 1
            minor_stride = stride / 5
        else:
            if minor_stride > 5:
                minor_stride = stride / 5

        if is_range_float:
            minor_stride = stride

        # Draw steps
        unit_length = widget_length / range
        stride_length = unit_length * stride
        minor_stride_length = unit_length * minor_stride

        def length_arg(length):
            return {"width": length} if is_horizontal else {"height": length}

        with self:
            with ui.ZStack():
                # Lines
                begin_step = None
                begin_minor_step = None

                stack_type = ui.HStack if is_horizontal else ui.VStack
                with stack_type():
                    current_minor_step = range_begin
                    remain = range_begin % minor_stride
                    if remain * unit_length >= 0.0001:
                        if stride_sign >= 0:
                            current_minor_step = current_minor_step + (minor_stride - remain)
                        else:
                            current_minor_step = current_minor_step - remain

                    begin_minor_step = current_minor_step
                    ui.Spacer(**length_arg(abs(begin_minor_step - range_begin) * unit_length))

                    line_alignment = line_alignment = ui.Alignment.LEFT if is_horizontal else ui.Alignment.TOP

                    while abs(current_minor_step - range_begin) * unit_length <= widget_length:
                        remain = current_minor_step % stride
                        remain = min(remain, abs(remain - stride))
                        if remain * unit_length <= 0.00001:
                            # Main step line
                            ui.Line(alignment=line_alignment, **length_arg(minor_stride_length))
                            if begin_step is None:
                                begin_step = current_minor_step
                        else:
                            # Minor step line
                            minor_stack = None
                            if is_horizontal:
                                minor_stack = ui.VStack(width=minor_stride_length)
                            else:
                                minor_stack = ui.HStack(height=minor_stride_length)

                            with minor_stack:
                                if is_horizontal:
                                    ui.Spacer(height=20)
                                else:
                                    ui.Spacer(width=20)

                                ui.Line(alignment=line_alignment)

                        current_minor_step += minor_stride * stride_sign

                if begin_step is None:
                    begin_step = current_minor_step

                # Numbers
                with stack_type():
                    current_step = begin_step

                    ui.Spacer(**length_arg(abs(current_step - range_begin) * unit_length))
                    while abs(current_step - range_begin) * unit_length <= widget_length:
                        text = None
                        if is_range_float:
                            digits = None
                            if exp >= 0:
                                digits = 1
                            else:
                                digits = abs(exp)
                            text = ("{:." + str(digits) + "f}").format(current_step + 10 ** (exp - 3))
                        else:
                            text = str(int(current_step))
                        ui.Label(
                            text_prefix + text, **length_arg(stride_length), style={"alignment": ui.Alignment.LEFT_TOP}
                        )
                        current_step += stride * stride_sign

                if self.on_built is not None:
                    self.on_built(self.range, begin_minor_step, minor_stride, begin_step, stride)
