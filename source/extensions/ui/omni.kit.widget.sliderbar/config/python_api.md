# Public API for module omni.kit.widget.sliderbar:

## Classes

- class SliderBar
  - OBJ_CURSOR: int
  - OBJ_START: int
  - OBJ_END: int
  - def __init__(self, width: ui.Length = ui.Fraction(1), start: float = 0.0, end: float = 24.0, current: float = 0.0, value_format_fn: Callable[[float], str] = None, min_value: float = 0.0, min_value_inclusive: bool = True, max_value: float = 24.0, max_value_inclusive: bool = False, style: Dict = {}, padding_width: ui.Length = ui.Pixel(60), slider_padding_width: ui.Length = ui.Pixel(30), slider_height: ui.Length = ui.Pixel(16), arrow_height: ui.Length = ui.Pixel(8), start_arrow_alignment: ArrowAlignment = ArrowAlignment.RIGHT, end_arrow_alignment: ArrowAlignment = ArrowAlignment.LEFT)
  - def destroy(self)
  - def set_current(self, current)
  - def get_current(self)
  - def set_start(self, start)
  - def get_start(self)
  - def set_end(self, end)
  - def get_end(self)
  - def add_callback_fns(self, on_start_changed: callable, on_end_changed: callable, on_current_changed: callable)

- class TimeSliderBar(SliderBar)

- class ImageAlignment
  - LEFT: str
  - RIGHT: str

- class ArrowAlignment
  - CENTER: str
  - LEFT: str
  - RIGHT: str

- class DragButton
  - def __init__(self, image_alignment: ImageAlignment = ImageAlignment.LEFT, arrow_alignment: ArrowAlignment = ArrowAlignment.LEFT, height: ui.Length = ui.Pixel(25), arrow_width: ui.Length = ui.Pixel(8), arrow_height: ui.Length = ui.Pixel(8), image_width: ui.Length = ui.Pixel(8))
  - def set_mouse_event_fn(self, dbclicked_fn, pressed_fn, moved_fn, released_fn, on_reset_position)
  - [property] def width(self)
  - [property] def offset_arrow(self)
  - [property] def text(self) -> str
  - [text.setter] def text(self, value)
  - def set_text(self, text)
