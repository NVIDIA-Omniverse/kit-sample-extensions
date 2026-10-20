# Public API for module omni.kit.browser.folder.core:

## Classes

- class BrowserFile
  - def __init__(self, url: str, thumbnail: Optional[str] = None)
  - def equals(self, other: BrowserFile) -> bool
  - [property] def url(self) -> str
  - [url.setter] def url(self, value: str)
  - [property] def thumbnail(self) -> str
  - [thumbnail.setter] def thumbnail(self, value: str)
  - def set_thumbnail(self, thumbnail_url: str) -> bool
  - def get_default_thumbnail_url(self) -> str

- class FileDetailItem(DetailItem)
  - def __init__(self, name: str, url: str, file: BrowserFile, thumbnail: Optional[str] = None)

- class FileSystemFile(BrowserFile)
  - def __init__(self, url: str, list_entry: Optional[omni.client.ListEntry] = None, thumbnail: Optional[str] = None, thumbnail_list_entry: Optional[omni.client.ListEntry] = None)

- class FileSystemFolder(AbstractBrowserFolder)
  - def __init__(self, *args, **kwargs)
  - def destroy(self)
  - async def start_traverse(self, try_connect_nucleus: bool = True, on_connected_fn: Callable[[AbstractBrowserFolder, bool], None] = None) -> bool
  - def create_file_object(self, url: str) -> FileSystemFile
  - def create_folder_object(self, name: str, url: str, **kwargs) -> AbstractBrowserFolder

- class FolderBrowserModel(AbstractBrowserModel)
  - SUMMARY_FOLDER_NAME: str
  - COUNT_LOADING: str
  - COUNT_TIMEOUT: str
  - def __init__(self, filter_file_suffixes: Optional[List[str]] = None, ignore_folder_names: Optional[List[str]] = None, show_empty_folders: bool = False, show_summary_folder: bool = True, setting_folders: Optional[str] = None, create_file_object_fn: callable = None, hide_file_without_thumbnails: bool = False, show_category_subfolders: bool = False, timeout: Optional[float] = 5.0, category_tree_mode: bool = False, local_cache_file: str = None, run_warmup: bool = False, ignore_sub_folder_with_files: bool = False, custom_folders_setting: Optional[str] = None)
  - def process_root_folder(self, root_folder: str, sync: bool = True) -> Optional[FileSystemFolder]
  - def destroy(self)
  - def register_folder(self, url: str, name: Optional[str] = None)
  - def unregister_folder(self, url: str)
  - def append_root_folder(self, url: str, name: Optional[str] = None, save: bool = True, sync: bool = True) -> Optional[FileSystemFolder]
  - def remove_root_folder(self, url: str) -> bool
  - def get_root_folder(self, url: str) -> Optional[AbstractBrowserFolder]
  - def folder_changed(self, item: Union[AbstractBrowserFolder, BrowserFile, None])
  - def start_traverse(self, folder: FileSystemFolder, force: bool = False)
  - def get_collection_items(self) -> List[FolderCollectionItem]
  - def get_category_items(self, item: FolderCollectionItem) -> List[FolderCategoryItem]
  - def get_detail_items(self, item: CategoryItem) -> List[FileDetailItem]
  - def remove_collection(self, item: FolderCollectionItem) -> bool
  - def get_folder_item(self, folder: FileSystemFolder) -> FolderCategoryItem
  - def filter_file(self, url: str) -> bool
  - def sort_items(self, items: List[Union[FolderCollectionItem, FolderCollectionItem, FileDetailItem]])
  - def create_collection_item(self, folder: AbstractBrowserFolder) -> FolderCollectionItem
  - def create_category_item(self, folder: AbstractBrowserFolder, parent: Optional[CategoryItem] = None) -> FolderCategoryItem
  - def create_detail_item(self, file: BrowserFile) -> Union[FileDetailItem, List[FileDetailItem]]
  - def create_folder_object(self, *args, **kwargs) -> AbstractBrowserFolder

- class FolderCategoryDelegate(TreeCategoryDelegate)
  - def __init__(self, **kwargs)
  - def build_loading_overlay(self, item)
  - def get_count(self, item: FolderCategoryItem) -> str
  - def bind_model(self, model: TreeFolderBrowserModel)

- class FolderCategoryItem(CategoryItem)
  - def __init__(self, name: str, count: int, folder: AbstractBrowserFolder, parent: Optional[CategoryItem] = None, is_last_child: Optional[bool] = False)

- class FolderCollectionItem(CollectionItem)
  - def __init__(self, name: str, url: str, folder: AbstractBrowserFolder)

- class TreeFolderBrowserModel(FolderBrowserModel)
  - def __init__(self, *args, **kwargs)
  - def process_root_folder(self, root_folder: str, sync: bool = True) -> Optional[FileSystemFolder]
  - def remove_collection(self, item: FolderCollectionItem) -> bool
  - def get_collection_items(self) -> List[FolderCollectionItem]
  - def get_category_items(self, item: FolderCollectionItem) -> List[FolderCategoryItem]
  - def destroy(self)
  - def get_detail_items(self, item: CategoryItem) -> List[FileDetailItem]
  - def folder_changed(self, item: Union[AbstractBrowserFolder, BrowserFile, None])

- class BrowserPropertyDelegate(abc.ABC)
  - def __init__(self)
  - def destroy(self)
  - def accepted(self, detail_items: List[FileDetailItem]) -> bool
  - def build_widgets(self, detail_items: List[FileDetailItem])

- class BrowserPropertyView
  - def __init__(self, property_delegates: List[BrowserPropertyDelegate] = [], style: Optional[dict] = None)
  - def destroy(self)
  - [property] def visible(self) -> bool
  - [visible.setter] def visible(self, value)
  - def show(self, detail_items: List[FileDetailItem])

- class TreeFolderBrowserWidgetEx(TreeFolderBrowserWidget)
  - def __init__(self, *args, **kwargs)
  - def build_widgets(self)
  - def build_property_view(self) -> BrowserPropertyView

- class FolderBrowserWidget
  - def __init__(self, browser_model: FolderBrowserModel, category_delegate: Optional[CategoryDelegate] = None, detail_delegate: Optional[FolderDetailDelegate] = None, options_menu: Optional[OptionsMenu] = None, min_thumbnail_size: int = 32, max_thumbnail_size: int = 512, detail_thumbnail_size: int = 128, thumbnail_aspect: float = 1.0, predownload_folder: Optional[str] = None, style: Dict = {}, extra_filter_fn: callable = None, category_tree_mode = False, show_category_splitter = False, category_width: float = 120, splitter_extra_width: int = 4, always_select_category: bool = True, multiple_drag: bool = False, show_scan_progress: bool = False)
  - def destroy(self)
  - [property] def category_selection(self) -> List[FolderCategoryItem]
  - [category_selection.setter] def category_selection(self, selection: List[FolderCategoryItem])
  - [property] def detail_selection(self) -> List[DetailItem]
  - [detail_selection.setter] def detail_selection(self, selection: List[DetailItem])
  - def build_widgets(self)
  - def select_folder(self, folder: FileSystemFolder, expand: bool = False)

- class FolderDetailDelegate(DetailDelegate)
  - def __init__(self, model: FolderBrowserModel = None)
  - def destroy(self)
  - def get_tooltip(self, item: FileDetailItem) -> str
  - def get_label(self, item: FileDetailItem) -> Optional[str]
  - def get_label_height(self) -> int

- class FolderOptionsMenu(OptionsMenu)
  - def __init__(self, predownload_folder: Optional[str] = None)
  - def destroy(self)

- class TreeFolderBrowserWidget(FolderBrowserWidget)
  - def __init__(self, *args, **kwargs)

## Variables

- CONTEXT_MENU_STYLE: Dict
