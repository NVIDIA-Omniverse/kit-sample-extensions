# Public API for module omni.wrapp.package_explorer:

## Classes

- class WrappAsset(BrowserFile)
  - def __init__(self, raw_asset_data: Dict)
  - def equals(self, other: BrowserFile) -> bool
  - class def is_asset_data(cls, raw_asset_data: Dict) -> bool
  - [property] def name(self) -> str
  - [property] def asset_type(self) -> AssetType
  - [property] def extent_as_str(self) -> str
  - [property] def qcode(self) -> str
  - [property] def url(self) -> str
  - [url.setter] def url(self, value: str)
  - [property] def thumbnail(self) -> str
  - [thumbnail.setter] def thumbnail(self, value: str)
  - [property] def hierarchy(self) -> str
  - [property] def hierarchy_as_str(self) -> str
  - [property] def versions(self) -> List[str]
  - [property] def version(self) -> str
  - [version.setter] def version(self, value)
  - [property] def tags(self) -> List[str]
  - [property] def tags_as_str(self) -> str
  - [property] def labels(self) -> List[str]
  - [property] def labels_as_str(self) -> str
  - [property] def relative_destination(self) -> str
  - [property] def destination_wrapp(self) -> str
  - [property] def wrapp_repo_url(self) -> str
  - [property] def installed(self) -> bool
  - def get_url(self, version: str = None, name: str = None, ext: str = 'usd') -> str
  - def set_interface_usd_url_found_fn(self, fn: callable)
  - def populate_interface_usd_url_future(self, url, version_url) -> asyncio.Future
  - def get_interface_usd_url(self, version: str = None) -> str
  - def set_thumbnail_not_found_fn(self, fn: callable)
  - def populate_thumbnail_url_future(self, url: str = None) -> asyncio.Future
  - def get_thumbnail_url(self, url: str = None) -> str

- class WrappAssetDetailItem(DetailItem)
  - def __init__(self, asset: WrappAsset)
  - [property] def url(self) -> str
  - [property] def url_to_update(self) -> str
  - [property] def thumbnail(self) -> str
  - [property] def thumbnail_to_update(self) -> str
  - [property] def version_to_update(self) -> str
  - [version_to_update.setter] def version_to_update(self, value: str)
  - [property] def version(self) -> str
  - [version.setter] def version(self, value: str)
  - [property] def installed(self) -> bool
  - [property] def wrapp_progress(self) -> float
  - [wrapp_progress.setter] def wrapp_progress(self, value: float)
  - [property] def progress_type(self) -> str
  - [progress_type.setter] def progress_type(self, value: str)
  - def progress_updated(self, progress: float)
  - def set_on_wrapp_progress_updated_fn(self, fn: Callable[[float], None])
  - def remove_on_wrapp_progress_updated_fn(self)
  - def filter(self, filter_words: Optional[List[str]]) -> bool
  - async def update(self, version: str = None, run_on_updated: bool = False)
  - async def uninstall(self)
  - def set_thumbnail_not_found_fn(self, fn: Callable[[], None])
  - def set_interface_usd_url_found_fn(self, fn: Callable[[], None])
  - def set_on_updated_fn(self, fn: Callable[[], None])
  - def on_updated(self)

- class WrappBrowserModel(TreeFolderBrowserModel)
  - def __init__(self, *args, **kwargs)
  - [property] def wrapp_dependencies_json(self) -> str
  - [wrapp_dependencies_json.setter] def wrapp_dependencies_json(self, value: str)
  - [property] def wrapp_repo_config(self) -> str
  - [wrapp_repo_config.setter] def wrapp_repo_config(self, value: str)
  - [property] def wrapp_dependencies_folder(self) -> FileSystemFolder
  - [property] def wrapp_repo_config_folder(self) -> FileSystemFolder
  - [property] def wrapp_project_config_uri(self) -> List[str]
  - [property] def wrapp_project_config_folder(self) -> FileSystemFolder
  - [property] def folders_to_traverse(self) -> List[FileSystemFolder]
  - async def setup_wrapp_data_folders(self, wrapp_dependencies_json = '', wrapp_repo_config = '')
  - def subscribe_to_stage(self)
  - def register_to_workspace(self, force: bool = False)
  - def refresh_asset_folders(self, wrapp_dependencies_json = '', wrapp_repo_config = '', use_cache: bool = True)
  - async def refresh_asset_folders_async(self, wrapp_dependencies_json = '', wrapp_repo_config = '')
  - def set_start_refreshing_callback_fn(self, fn: Callable[[], None], name: str)
  - def start_traverse(self, folder: FileSystemFolder, force: bool = False)
  - def is_in_traversing(self) -> bool
  - def get_drag_mime_data(self, item: WrappAssetDetailItem = None) -> str
  - def execute(self, item: WrappAssetDetailItem)
  - def create_folder_object(self, *args, **kwargs)
  - def create_detail_item(self, asset: WrappAsset) -> FileDetailItem
  - def destroy(self)
  - def sort_items(self, items: List[WrappAssetDetailItem])
  - def get_category_items(self, item: FolderCollectionItem) -> List[FolderCategoryItem]
  - def get_detail_items(self, item: CategoryItem) -> List[FileDetailItem]
  - def reload_installed_folder(self)

- class WrappBrowserExtension(omni.ext.IExt)
  - def __init__(self)
  - [property] def window(self) -> Optional[WrappBrowserWindow]
  - [property] def browser_widget(self) -> Optional[TreeBrowserWidget]
  - [property] def browser_model(self) -> Optional[WrappBrowserModel]
  - def on_startup(self, ext_id)
  - def on_shutdown(self)

- class WrappBrowserWindow(ui.Window)
  - def __init__(self, visible = True)
  - def refresh_asset_folders(self)
  - def destroy(self)

## Functions

- def add_asset_from_drag(drag_mime_data: str, context: str = '', prim_path: Optional[Sdf.Path] = None) -> bool
- async def add_wrapp_asset_to_stage(stage: Usd.Stage, asset: WrappAsset, parent_path: str, as_payload: bool = False) -> str
- def get_instance() -> Optional[WrappBrowserExtension]
- async def find_assets(search_words: Optional[List[str]] = None) -> List[WrappAsset]
- def refresh_browser()

## Variables

- WRAPP_EXPLORER_NAME: str
- WRAPP_EXPLORER_DRAG_PREFIX: str
