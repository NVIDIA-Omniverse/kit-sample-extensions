# Public API for module omni.kit.widget.zoombar:

## Classes

- class ZoomBar
  - def __init__(self, min: int = 0, max: int = 5, value: int = 2, width: int = 150, icon_mode: bool = False, on_view_mode_changed_fn: callable = None, on_value_changed_fn: callable = None, style: Dict = {})
  - def destroy(self)
  - [property] def model(self) -> ui.AbstractValueModel
  - def set_on_hovered_fn(self, on_hovered_fn: Callable[[bool], None])

- class FileZoomBar(ZoomBar)
  - def __init__(self, show_grid_view: bool = False, grid_view_scale: int = 2, on_toggle_grid_view_fn: callable = None, on_scale_grid_view_fn: callable = None)
