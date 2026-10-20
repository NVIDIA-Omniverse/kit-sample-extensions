# Public API for module omni.kit.viewport.menubar.bottom:

## Classes

- class Extension(omni.ext.IExt)
  - BOTTOMBAR_NAME: NoneType
  - def on_startup(self, ext_id)
  - def on_shutdown(self)

- class ViewportBottomBar(ViewportMenubar)
  - def __init__(self, name: str, spacing: int = 5)
  - def build_fn(self, menu_items, factory)

- class ViewportMenuBlank(ViewportMenuItem)
  - def __init__(self, order_setting_path: str)
  - def build_fn(self, factory)
  - [property] def computed_width(self) -> float

## Functions

- def get_bottombar_name()

## Variables

- BOTTOMBAR_STYLE: Dict
- BUTTON_SIZE: int
- BG_SIZE: int
- SPACER_SIZE: Unknown
- VIEWPORT_BOTTOM_MENU_STYLE: Dict
- BG_STYLE: Dict
