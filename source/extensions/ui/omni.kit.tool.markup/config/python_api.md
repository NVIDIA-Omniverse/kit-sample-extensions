# Public API for module omni.kit.tool.markup:

## Classes

- class MarkupTool
  - def __init__(self, *_args, **_kwargs)
  - def on_startup(self, _ext_id)
  - def on_shutdown(self)
  - def get_element_at_path(self, element_path)
  - def get_element_at(self, x, y)
  - def set_selected_element(self, element)
  - def get_gesture_manager(self)
  - def get_markup_stack(self) -> ui.ZStack
  - def refresh_elements(self, refresh_all_elements = False, selected_element = None)

## Functions

- def get_instance() -> Optional[MarkupTool]
