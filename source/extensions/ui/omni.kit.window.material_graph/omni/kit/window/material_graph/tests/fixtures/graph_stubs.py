class DummyGraphView:
    """Graph view stub with default geometry and identity mapping."""

    def __init__(
        self,
        *,
        visible: bool = True,
        zoom: float = 1.0,
        computed_width: int = 100,
        computed_height: int = 100,
    ) -> None:
        self.model = object()
        self.visible = visible
        self.zoom = zoom
        self.screen_position_x = 0
        self.screen_position_y = 0
        self.computed_width = computed_width
        self.computed_height = computed_height

    def screen_to_canvas(self, x: int, y: int) -> tuple[int, int]:
        return (x, y)
