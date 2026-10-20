# Public API for module omni.kit.variant.presenter:

## Classes

- class VariantPresenterExtension(omni.ext.IExt, MenuHelperExtension)
  - WINDOW_NAME: str
  - MENU_GROUP: str
  - def on_startup(self)
  - def on_shutdown(self)
  - def show_window(self, value)

- class VariantPresenterWindow
  - def __init__(self)
  - def set_visible(self, value: bool)
  - def set_visibility_changed_listener(self, listener)
  - def update_dirty(self)
  - def destroy(self)
  - def toggle_tabs(self, is_groups)
  - def toggle_locked_variants(self, state)

## Functions

- def get_model()
- def get_window()

## Variables

- SETTING_SHOW_STARTUP: str
