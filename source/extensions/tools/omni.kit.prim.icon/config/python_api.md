# Public API for module omni.kit.prim.icon:

## Classes

- class IconScene
  - def __init__(self, title: str = None, icon_scale: float = 1.0, **kwargs)
  - [property] def visible(self)
  - [visible.setter] def visible(self, value: bool)
  - def destroy(self)
  - def clear(self)

- class PrimIcon
  - def __init__(self, test = False)
  - static def get_instance()
  - def destroy(self)
  - def get_model(self)
  - def add_prim_icon(self, prim_path, icon_url)
  - def remove_prim_icon(self, prim_path)
  - def set_icon_click_fn(self, prim_path, call_back)
  - def show_prim_icon(self, prim_path)
  - def hide_prim_icon(self, prim_path)
  - def clear(self)

## Functions

- def get_prim_icon_interface()
