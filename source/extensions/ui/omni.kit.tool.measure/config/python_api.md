# Public API for module omni.kit.tool.measure:

## Classes

- class Extension(omni.ext.IExt)
  - [property] def panel(self) -> Optional[MeasurePanel]
  - [property] def viewport(self) -> Optional[MeasureScene]
  - [property] def measurements_visible(self) -> bool
  - def set_measurements_visible(self, visible: bool)
  - def on_startup(self, ext_id)
  - def on_shutdown(self)

## Functions

- def get_instance() -> Extension
