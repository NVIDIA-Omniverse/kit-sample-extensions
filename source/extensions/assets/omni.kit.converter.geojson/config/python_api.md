# Public API for module omni.kit.converter.geojson:

## Classes

- class WindowExtension
  - def on_startup(self, menu_path = None, hotkey = None, appear_after = '', use_editor_menu = False, on_visibility_changed_fn: callable = None)
  - def on_shutdown(self)
  - def is_visible(self)
  - def show(self, visible = True)
  - def hide(self)
  - [property] def active(self)
  - [active.setter] def active(self, value)
  - def dock(self, target, position = ui.DockPosition.RIGHT)

- class GeoJSONWindow(TitleWindowBase)
  - def __init__(self)

- class Extension(omni.ext.IExt, WindowExtension)
  - TOOL_NAME: str
  - def on_startup(self, ext_id)
  - def on_shutdown(self)

## Functions

- def get_instance()

## Variables

- EXTENSION_NAME: str

## Other

- omni.ext: public module
