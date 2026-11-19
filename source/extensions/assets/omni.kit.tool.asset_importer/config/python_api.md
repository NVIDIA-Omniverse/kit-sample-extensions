# Public API for module omni.kit.tool.asset_importer:

## Classes

- class AssetImporterExtension(omni.ext.IExt)
  - IMPORT_FILE_MENU_NAME: str
  - UPLOAD_MENU_NAME: str
  - IMPORT_AND_CONVERT_MENU_NAME: str
  - CONVERT_TO_USD_MENU_NAME: str
  - IMPORT_ICON_MENU_NAME: str
  - PERSISTENT_APP_IMPORT_SETTINGS_PATH: str
  - def on_startup(self, ext_id)
  - def on_shutdown(self)
  - def is_supported_format(self, path: str)
  - def add_importer(self, importer_delegate: AbstractImporterDelegate)
  - def remove_importer(self, importer_delegate: AbstractImporterDelegate)
  - def add_import_complete_callback(self, callback)
  - def remove_import_complete_callback(self, callback)
  - def add_import_canceled_callback(self, callback)
  - def remove_import_canceled_callback(self, callback)
  - def get_filter_options(self)
  - def import_asset(self, add_reference = False, export_to_current_folder = True)
  - static def get_instance()

- class AbstractImporterDelegate
  - [property] def name(self) -> str
  - [property] def filter_regexes(self) -> List[str]
  - [property] def filter_descriptions(self) -> List[str]
  - [property] def priority(self) -> int
  - def build_options(self, paths: List[str])
  - async def convert_assets(self, paths: List[str], **kargs) -> Dict[str, Union[str, None]]
  - async def added_reference(self, assets: Dict[str, Tuple[str, Sdf.Path]])
  - def is_supported_format(self, path: str) -> bool
  - def supports_usd_stage_cache(self)
  - def show_destination_frame(self)
  - def show_scene_optimizer_config_frame(self)

## Functions

- def register_importer(importer_delegate: AbstractImporterDelegate)
- def remove_importer(importer_delegate: AbstractImporterDelegate)
- def is_supported_format(path: str)
