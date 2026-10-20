# Public API for module omni.kit.window.section:

## Classes

- class SectionToolExtension(omni.ext.IExt, MenuHelperExtension)
  - SETTING_MENU_PATH: str
  - VIEW_TOOLBAR_ID: str
  - def on_startup(self, ext_id)
  - def on_shutdown(self)
  - def show_window(self, menu, value)
  - def get_section_widget_prim(self, create_if_not_exist=False)
  - def set_widget_position(self, position)

## Functions

- def get_instance() -> SectionToolExtension
