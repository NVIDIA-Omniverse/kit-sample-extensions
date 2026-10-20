# Public API for module omni.kit.browser.core:

## Classes

- class AbstractBrowserModel(ui.AbstractItemModel)
  - def __init__(self, overview_name: Optional[str] = None, always_realod_detail_items: bool = False)
  - def get_item_children(self, item: Optional[BaseItem] = None) -> List[ui.AbstractItem]
  - def sort_changed(self)
  - def get_item_value_model(self, item: Optional[BaseItem] = None, index: int = 0) -> Optional[ui.AbstractValueModel]
  - def get_item_value_model_count(self, item = None) -> int
  - def get_collection_items(self) -> List[CollectionItem]
  - def get_category_items(self, item: CollectionItem) -> List[CategoryItem]
  - def get_detail_items(self, item: CategoryItem) -> List[DetailItem]
  - def get_sort_args(self) -> Optional[Dict]
  - def execute(self, item: DetailItem)
  - def remove_collection(self, item: CollectionItem) -> bool

- class CategoryItem(BaseItem)
  - def __init__(self, name, count = 0, parent: Optional[BaseItem] = None, is_last_child: Optional[bool] = False)
  - def filter(self, filter_words: Optional[List[str]]) -> bool

- class CollectionItem(BaseItem)
  - def __init__(self, name: str, url: str)

- class DetailItem(BaseItem)
  - def __init__(self, name: str, url: str, thumbnail: str = None)
  - [property] def url(self) -> str
  - [property] def thumbnail(self) -> str
  - [url.setter] def url(self, value: str)
  - [thumbnail.setter] def thumbnail(self, value: str)
  - def filter(self, filter_words: Optional[List[str]]) -> bool

- class BrowserSearchBar
  - def __init__(self, enable_navigation_visibility: bool = True, options_menu: Optional[OptionsMenu] = OptionsMenu(), style = {}, subscribe_edit_changed = True)
  - [property] def width(self) -> ui.Length
  - [width.setter] def width(self, value: ui.Length)
  - [property] def navigation_button(self) -> ui.Button
  - def destroy(self)
  - def bind_browser_widget(self, browser_widget: BrowserWidget)
  - def set_navigation_clicked_fn(self, on_clicked_fn: Optional[callable])
  - def add_on_search_fn(self, on_search_fn: Callable[[Optional[List[str]]], None])
  - def remove_on_search_fn(self, on_search_fn: callable) -> bool
  - def clear_search(self)

- class BrowserWidget
  - def __init__(self, model: AbstractBrowserModel, style = {}, category_delegate = None, category_width: float = 120, detail_delegate = None, min_thumbnail_size: int = 32, max_thumbnail_size: int = 512, detail_thumbnail_size: int = 128, thumbnail_aspect: float = 1.0, extra_filter_fn: callable = None, category_tree_mode: bool = False, overview_delegate = None, overview_thumbnail_size: int = 192, overview_thumbnail_aspect: float = 1.0, overview_thumbnail_padding_width: int = 10, overview_thumbnail_padding_height: int = 1, always_select_category: bool = True, show_category_splitter: bool = False, splitter_extra_width: int = 4, show_collection: bool = True, on_category_selection_changed_fn: Callable[[CategoryItem], None] = None, extra_ui_style: Dict = {}, multiple_drag: bool = False)
  - def destroy(self)
  - [property] def visible(self) -> bool
  - [visible.setter] def visible(self, value)
  - [property] def model(self) -> ui.AbstractItemModel
  - [model.setter] def model(self, new_model: AbstractBrowserModel)
  - [property] def collection_index(self) -> int
  - [collection_index.setter] def collection_index(self, value)
  - [property] def collection_selection(self) -> Optional[CollectionItem]
  - [property] def category_selection(self) -> List[CategoryItem]
  - [category_selection.setter] def category_selection(self, items: List[CategoryItem])
  - [property] def detail_selection(self) -> List[DetailItem]
  - [detail_selection.setter] def detail_selection(self, selection: List[DetailItem])
  - def add_thumbnail_size_changed_fn(self, on_thumbnail_size_changed_fn: Callable[[int], None]) -> int
  - def remove_thumbnail_size_changed_fn(self, sub_id: int)
  - def filter_details(self, filter_words: Optional[List[str]])
  - def add_filter_changed_fn(self, on_filter_changed_fn: Callable[[Optional[List[str]]], None]) -> int
  - def remove_filter_changed_fn(self, sub_id: int)
  - def refresh_details(self)
  - def show_widgets(self, collection: Optional[bool] = None, category: Optional[bool] = None, detail: Optional[bool] = None)
  - def sort_changed(self)

- class CategoryDelegate(ui.AbstractItemDelegate)
  - def __init__(self, tree_mode: bool = False)
  - def build_widget(self, model: ui.AbstractItemModel, item: CategoryItem, index: int = 0, level: int = 0, expanded: bool = False)
  - def build_branch(self, model: ui.AbstractItemModel, item: CategoryItem, column_id: int = 0, level: int = 0, expanded: bool = False)
  - def get_label(self, item: CategoryItem) -> str
  - def get_count(self, item: CategoryItem) -> str

- class DetailDelegate(ui.AbstractItemDelegate)
  - def __init__(self, model: AbstractBrowserModel = None)
  - def destroy(self)
  - def set_drag_fn(self, drag_fn: Callable[[DetailItem], str])
  - def build_branch(self, model: ui.AbstractItemModel, item: DetailItem, column_id: int = 0, level: int = 0, expanded: bool = False)
  - def build_widget(self, model: ui.AbstractItemModel, item: DetailItem, index: int = 0, level: int = 0, expand: bool = False)
  - def item_changed(self, model: ui.AbstractItemModel, item: Optional[DetailItem])
  - def get_thumbnail(self, item: DetailItem) -> Optional[str]
  - def get_label(self, item: DetailItem) -> Optional[str]
  - def get_label_height(self) -> int
  - def get_tooltip(self, item: DetailItem) -> Optional[str]
  - def on_hover(self, item: DetailItem, hovered: bool)
  - def on_click(self, item: DetailItem)
  - def on_right_click(self, item: DetailItem)
  - def on_double_click(self, item: DetailItem)
  - def on_drag(self, item: DetailItem) -> str
  - def on_multiple_drag(self, item: DetailItem) -> str
  - def build_thumbnail(self, item: DetailItem) -> Optional[ui.Image]

- class OptionsMenu
  - def __init__(self)
  - def destroy(self)
  - def bind_browser_widget(self, browser_widget: BrowserWidget)
  - def set_add_collection_fn(self, on_add_collection_fn: Callable[[], None])
  - def append_menu_item(self, desc: OptionMenuDescription)
  - def show(self)

- class OptionMenuDescription
  - def __init__(self, name: str, clicked_fn: callable = None, enabled_fn: callable = None, visible_fn: callable = None, get_text_fn: callable = None)

- class TreeBrowserWidget(BrowserWidget)
  - def __init__(self, *args, **kwargs)

- class TreeCategoryDelegate(CategoryDelegate)
  - def __init__(self, hide_zero_count: bool = False, *args, **kwargs)
  - def destroy(self)
  - def build_widget(self, model: ui.AbstractItemModel, item: CategoryItem, index: int = 0, level: int = 0, expanded: bool = False)
  - def build_branch(self, model: ui.AbstractItemModel, item: CategoryItem, column_id: int = 0, level: int = 0, expanded: bool = False)
  - def draw_expanded_symbol(self, expanded: bool)
  - def get_label(self, item: CategoryItem) -> str
  - def build_loading_overlay(self, item: CategoryItem)

## Functions

- def create_drop_helper(pickable: bool = False, add_outline: bool = True, on_drop_accepted_fn: Callable = None, on_drop_fn: Callable = None, on_pick_fn: Callable = None, protocal: str = None)
