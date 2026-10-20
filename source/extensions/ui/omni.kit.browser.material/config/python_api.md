# Public API for module omni.kit.browser.material:

## Classes

- class MaterialBrowserModel(TreeFolderBrowserModel)
  - def __init__(self, **kwargs)
  - def create_folder_object(self, *args, **kwargs)
  - def create_category_item(self, folder: MaterialFolder) -> FolderCategoryItem
  - def create_detail_item(self, file: MaterialFile) -> Union[MaterialDetailItem, List[MaterialDetailItem]]
  - def execute(self, item: MaterialDetailItem)
  - static def create_material_by_url(material_url: str, sub_material_id: Optional[str], context_name: str = '')
  - static def create_material_by_item(item: MaterialDetailItem, context_name: str = '') -> str
  - def create_material(self, item: MaterialDetailItem, context_name: str = '') -> str
  - def bind_material(self, material_prim_path: str, target_paths: List[str])

- class MaterialDetailItem(FileDetailItem)
  - def __init__(self, file: MaterialFile, donot_cast_shadows: Optional[bool], sub_material: UsdSubMaterial = None)
  - def get_default_thumbmail_url(self)

- class MaterialFile(FileSystemFile)
  - def __init__(self, url: str, sub_materials: Optional[List[UsdSubMaterial]] = None)
  - def equals(self, other: MaterialFile) -> bool
  - def set_thumbnail(self, thumbnail_url: str) -> bool

- class MaterialDetailDelegate(FolderDetailDelegate)
  - def __init__(self, model: MaterialBrowserModel)
  - def destroy(self)
  - def get_label(self, item: MaterialDetailItem) -> Optional[str]
  - def get_thumbnail(self, item: MaterialDetailItem) -> str
  - def get_tooltip(self, item: MaterialDetailItem) -> str
  - def on_right_click(self, item: MaterialDetailItem)
  - def on_drag(self, item: MaterialDetailItem) -> str
  - def can_generate_thumbnail(self) -> bool
  - def generate_thumbnail(self, item: MaterialDetailItem)
  - static def get_material_info_from_drop(url: str) -> Tuple[str]

- class MaterialOptionsMenu(FolderOptionsMenu)
  - def __init__(self, delegate: MaterialDetailDelegate)
