# Public API for module omni.simready.explorer:

## Classes

- class AssetFactory
  - registry: Dict[AssetType, SimreadyAsset]
  - class def register(cls, asset_type: AssetType) -> Callable
  - class def create_asset(cls, raw_asset_data: Dict) -> Optional[SimreadyAsset]
  - class def num_asset_types(cls) -> int
  - class def dump_asset_types(cls)

- class AssetType(Enum)
  - PROP: int
  - VEHICLE: int
  - CHARACTER: int
  - SCENE: int
  - SIGN: int
  - ROADMARK: int
  - GENERIC: int
  - UNKNOWN: int

- class SimreadyAsset(BrowserFile, abc.ABC)
  - def __init__(self, raw_asset_data: Dict)
  - class def is_asset_data(cls, raw_asset_data: Dict) -> bool
  - [property] def name(self) -> str
  - [property] def asset_type(self) -> AssetType
  - [property] def main_url(self) -> str
  - [property] def thumbnail_url(self) -> Optional[str]
  - [property] def tags(self) -> List[str]
  - [property] def labels(self) -> List[str]
  - [property] def labels_as_str(self) -> List[str]
  - [property] def tags_as_str(self) -> str
  - [property] def extent_as_str(self) -> str
  - [property] def qcode(self) -> str
  - [property] def hierarchy(self) -> str
  - [property] def hierarchy_as_str(self)
  - [property] def physics_variant(self) -> Optional[Dict]
  - [property] def behaviors(self) -> Dict[str, List[str]]

- class PropAsset(SimreadyAsset)
  - def __init__(self, raw_asset_data: Dict)
  - class def is_asset_data(cls, raw_asset_data: Dict) -> bool

- class SimReadyDetailDelegate(FolderDetailDelegate)
  - def __init__(self, model: SimReadyBrowserModel)
  - def destroy(self)
  - def get_thumbnail(self, item: AssetDetailItem) -> str
  - def get_tooltip(self, item: AssetDetailItem) -> Optional[str]
  - def on_drag(self, item: AssetDetailItem) -> str
  - def on_multiple_drag(self, item: AssetDetailItem) -> str
  - def on_right_click(self, item: AssetDetailItem)
  - def build_widget(self, model: ui.AbstractItemModel, item: AssetDetailItem, index: int = 0, level: int = 0, expand: bool = False)
  - def build_thumbnail(self, item: AssetDetailItem) -> Optional[ui.Image]

- class AssetFolder(FileSystemFolder)
  - def __init__(self, *args, **kwargs)
  - [property] def asset_by_tags(self) -> Dict[str, List[SimreadyAsset]]
  - [property] def asset_by_labels(self) -> Dict[str, List[SimreadyAsset]]

- class AssetDetailItem(DetailItem)
  - def __init__(self, asset: SimreadyAsset)
  - class def get_default_physics_value(cls) -> str
  - [property] def physics(self) -> str
  - [physics.setter] def physics(self, value: str)
  - def filter(self, filter_words: Optional[List[str]]) -> bool

- class SimReadyBrowserModel(TreeFolderBrowserModel)
  - def __init__(self, *args, **kwargs)
  - [property] def current_asset_folder(self) -> Optional[AssetFolder]
  - def refresh_current_asset_folder(self)
  - def start_traverse(self, folder: FileSystemFolder, force: bool = False)
  - def create_folder_object(self, *args, **kwargs)
  - def get_category_items(self, item: FolderCollectionItem) -> List[FolderCategoryItem]
  - def get_detail_items(self, item: CategoryItem) -> List[FileDetailItem]
  - def get_drag_mime_data(self, item: AssetDetailItem = None) -> str
  - def execute(self, item: DetailItem)
  - def create_detail_item(self, asset: SimreadyAsset) -> FileDetailItem

- class SimReadyBrowserWidget(BrowserWithPropertyWidget)
  - def __init__(self, *args, **kwargs)
  - [property] def search_field(self) -> SearchField
  - [property] def category_all(self) -> FolderCategoryItem

- class ComboBoxModel(ui.AbstractItemModel)
  - def __init__(self, texts: List[str], values: Optional[List[Any]] = None, current_value: Any = None)
  - def destroy(self)
  - [property] def current_value(self) -> str
  - [current_value.setter] def current_value(self, value: str)
  - def get_item_children(self, item) -> List[ComboBoxItem]
  - def get_item_value_model(self, item, column_id)
  - def on_current_changed(self)

- class ContextMenu(ui.Menu)
  - def __init__(self)
  - def show_item(self, item: AssetDetailItem)

- class EmptyPropertyDelegate(BrowserPropertyDelegate)
  - def accepted(self, asset: Optional[AssetDetailItem]) -> bool
  - def show(self, asset: Optional[AssetDetailItem], frame: ui.Frame)
  - def accepted_multiple(self, detail_items: List[AssetDetailItem]) -> bool
  - def show_multiple(self, detail_items: List[AssetDetailItem], frame: ui.Frame)

- class SimReadyBrowserExtension(omni.ext.IExt)
  - [property] def window(self) -> Optional[SimReadyBrowserWindow]
  - [property] def browser_widget(self) -> Optional[TreeBrowserWidget]
  - [property] def browser_model(self) -> Optional[SimReadyBrowserModel]
  - def on_startup(self, ext_id)
  - def on_shutdown(self)

- class MultiPropertyDelegate(BrowserPropertyDelegate)
  - def accepted(self, asset: Optional[AssetDetailItem]) -> bool
  - def show(self, asset: Optional[AssetDetailItem], frame: ui.Frame)
  - def accepted_multiple(self, detail_items: List[AssetDetailItem]) -> bool
  - def show_multiple(self, detail_items: List[AssetDetailItem], frame: ui.Frame)

- class SimReadyFolderOptionsMenu(OptionsMenu)
  - def __init__(self, *args, **kwargs)
  - def destroy(self)
  - def set_add_collection_fn(self, on_add_collection_fn: callable)

- class PropAssetPropertyDelegate(BrowserPropertyDelegate)
  - def accepted(self, item: Optional[AssetDetailItem]) -> bool
  - def show(self, item: Optional[AssetDetailItem], frame: ui.Frame)
  - def accepted_multiple(self, detail_items: List[AssetDetailItem]) -> bool
  - def show_multiple(self, detail_items: List[AssetDetailItem], frame: ui.Frame)
  - def clear_buttons(self, buttons)

- class PropAssetTagsWidget
  - def __init__(self, tags, browser_widget)
  - [property] def tags(self)
  - [tags.setter] def tags(self, tags)
  - def clear_tags(self)
  - def append_tag(self, tag)
  - def remove_chip(self, chip)
  - def build_tag_chips(self)

- class SimReadyDragDropObject(UsdFileDropDelegate)
  - def __init__(self)
  - def drop_should_disable_preview(self)
  - def get_raw_data(self, drop_data: dict) -> dict
  - def get_url(self, drop_data: dict)
  - def add_reference_to_stage(self, usd_context, stage: Usd.Stage, url: str) -> Tuple[str, Usd.EditContext, str]
  - def accepted(self, drop_data: dict)
  - def dropped(self, drop_data: dict)

## Functions

- async def find_assets(search_words: Optional[List[str]] = None) -> List[SimreadyAsset]
- def add_asset_to_stage(url: str, parent_path: Sdf.Path = Sdf.Path.emptyPath, position: Gf.Vec3d = Gf.Vec3d(0, 0, 0), variants: Optional[Dict[str, str]] = None, payload: bool = False, instanceable: bool = False) -> Tuple[bool, Sdf.Path]
- def add_asset_to_stage_using_prims(usd_context: omni.usd.UsdContext, stage: Usd.Stage, url: str, variants: Optional[Dict[str, str]] = None, replace_prims: bool = False, prim_paths: List[Sdf.Path] = []) -> Tuple[bool, Sdf.Path]
- def get_average_position_of_prims(prims: List[Usd.Prim]) -> Gf.Vec3d
- def get_selected_xformable_prim_paths(usd_context: omni.usd.UsdContext, stage: Usd.Stage) -> List[Sdf.Path]
- def refresh_browser()
- def add_asset_from_drag(drag_mime_data: str, context: str = '', prim_path: Optional[Sdf.Path] = None) -> bool
- def add_asset_with_variant_to_stage(raw_data: dict, context: str = '', prim_path: Optional[Sdf.Path] = None) -> Tuple[bool, str]
- def configure_prim(stage: Usd.Stage, prim_path: Sdf.Path, variants: Dict[str, str])
- def deregister_actions(extension_id: str)
- def get_instance() -> Optional[SimReadyBrowserExtension]

## Variables

- ICON_PATH: Unknown
- PROPERTY_STYLES: Dict
- UI_STYLES: Dict
- CONTEXT_MENU_STYLE: Dict
