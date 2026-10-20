from omni import ui


class Guidelines(ui.Frame):
    def __init__(self, **kwargs):
        self.offset = None
        self.stride = None

        super().__init__(
            build_fn=self._build,
            computed_content_size_changed_fn=lambda: self.rebuild(),
            horizontal_clipping=True,
            vertical_clipping=True,
            **kwargs,
        )

    def _build(self):
        if self.offset is None or self.stride is None or self.computed_width == 0:
            return

        with self:
            with ui.HStack():
                current_offset = self.offset
                ui.Spacer(width=current_offset * self.computed_width)
                while current_offset < 1:
                    ui.Line(alignment=ui.Alignment.LEFT, width=self.stride * self.computed_width)
                    current_offset += self.stride
