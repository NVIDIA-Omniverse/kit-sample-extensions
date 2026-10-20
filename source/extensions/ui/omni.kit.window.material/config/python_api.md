# Public API for module omni.kit.window.material:

## Classes

- class MaterialBrowserExtension(omni.ext.IExt)
  - def on_startup(self, ext_id)
  - def on_shutdown(self)
  - [property] def library_options_menu(self) -> Optional[OptionsMenu]
  - [property] def stage_options_menu(self) -> Optional[OptionsMenu]

- class MaterialBrowserWidget(TreeFolderBrowserWidget)
  - def __init__(self, **kwargs)
  - def destroy(self)
  - [property] def library_options_menu(self) -> Optional[OptionsMenu]
  - [property] def stage_options_menu(self) -> Optional[OptionsMenu]
  - def build_widgets(self)
  - def preview_material(self, item: MaterialPrimDetailItem, on: bool)

## Functions

- def get_instance()
