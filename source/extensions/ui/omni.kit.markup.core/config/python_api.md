# Public API for module omni.kit.markup.core:

## Classes

- class MarkupBrowserWidget(BrowserWidget)
  - def __init__(self, model: Optional[MarkupModel] = None, delegate: Optional[MarkupDelegate] = None, max_thumbnail_size: int = 320, on_markup_selection_changed: Optional[Callable[[Any], Any]] = None)
  - def destroy(self)

- class MarkupDelegate(DetailDelegate)
  - def __init__(self, model: MarkupModel)
  - def destroy(self)
  - def get_label(self, item: MarkupItem) -> str
  - def on_right_click(self, item: MarkupItem)
  - def on_click(self, item: MarkupItem)
  - def on_hover(self, item: MarkupItem, hovered: bool)
  - def build_thumbnail(self, item: MarkupItem) -> Union[ui.Image, ui.ImageWithProvider]
  - def show_context_menu(self, item: MarkupItem)

- class MarkupExport
  - def __init__(self, markup_instance, export_format_map: Dict[str, bool], pdf_page_size_idx: int = 0, pdf_page_landscape: bool = False)
  - [property] def export_dir(self) -> Path
  - [property] def filename(self) -> str
  - [property] def title(self) -> str
  - [property] def timestamp(self) -> str
  - [property] def export_filepath(self) -> Path
  - async def export(self, finished_callback: Callable)

- class MarkupExportObject
  - def __init__(self, markup_name: str, markup_usd)
  - [property] def author(self) -> str
  - [property] def camera_name(self) -> str
  - [property] def comments(self) -> str
  - [property] def creation_date(self) -> str
  - [property] def frame(self) -> int
  - [property] def markup_name(self) -> str
  - [property] def notes(self) -> str
  - [property] def screenshot(self) -> Optional[PIL.Image.Image]
  - [screenshot.setter] def screenshot(self, img: Optional[PIL.Image.Image])
  - [property] def screenshot_buffer(self) -> io.BytesIO
  - [property] def thumbnail_image(self) -> Optional[PIL.Image.Image]
  - [property] def thumbnail_buffer(self) -> Tuple[io.BytesIO, int, int]
  - [property] def url(self) -> str

- class MarkupItem(DetailItem)
  - def __init__(self, markup: ViewportMarkup)
  - [property] def markup(self) -> ViewportMarkup|None

- class MarkupModel(AbstractBrowserModel)
  - def __init__(self, on_markup_changed_fn: Callable[..., None]|None = None)
  - def destroy(self)
  - def execute(self, item: MarkupItem)
  - def get_collection_items(self) -> List[CollectionItem]
  - def get_category_items(self, item: CollectionItem) -> List[CategoryItem]
  - def get_detail_items(self, item: CategoryItem) -> List[MarkupItem]
  - def on_markup_changed(self, *_)

- class ViewportMarkup
  - def __init__(self, name, parent_path = '')
  - [property] def edit_context(self) -> Usd.EditContext
  - [property] def name(self) -> str
  - [name.setter] def name(self, new_name)
  - [property] def path(self) -> str
  - [property] def thumbnail(self) -> Optional[str]
  - [property] def thumbnail_data(self) -> Optional[Tuple[bytes, int, int]]
  - [property] def create_time(self) -> Optional[str]
  - [property] def created_by(self) -> Optional[str]
  - [property] def comment(self) -> str
  - [comment.setter] def comment(self, comment: str)
  - [property] def frame(self) -> float
  - [frame.setter] def frame(self, frame: float)
  - [property] def approval_type(self) -> ApproveType
  - [property] def camera_prim(self) -> Optional[Usd.Prim]
  - [property] def usd_prim(self) -> Optional[Usd.Prim]
  - [property] def is_dirty(self) -> bool
  - [property] def info(self) -> Optional[List[List[str]]]
  - def recall(self, without_camera = False, enable_settings: Optional[List[str]] = None, disable_settings: Optional[List[str]] = None)
  - def rename(self, new_name)
  - def create(self, on_created_fn: Callable[..., None]|None = None)
  - def create_from_prim(self, prim: Usd.Prim) -> bool
  - def delete(self)
  - def get_usd_prim_path(self) -> str
  - def refresh_thumbnail(self, refresh_callback)
  - def approve(self)
  - def reject(self)
  - def reset_approval(self)
  - async def wait(self)

- class MarkupCore
  - def on_startup(self, _ext_id)
  - async def deferred_startup(self)
  - [property] def edit_state_change_fn(self) -> Optional[Callable]
  - [edit_state_change_fn.setter] def edit_state_change_fn(self, val: Optional[Callable])
  - [property] def edit_end_fn(self) -> Optional[Callable]
  - [edit_end_fn.setter] def edit_end_fn(self, val: Optional[Callable])
  - [property] def export_fn(self) -> Optional[Callable]
  - [export_fn.setter] def export_fn(self, val: Optional[Callable])
  - def on_shutdown(self)
  - [property] def edit_context(self) -> Usd.EditContext
  - [property] def current_markup(self) -> Optional[ViewportMarkup]
  - [current_markup.setter] def current_markup(self, markup: Optional[ViewportMarkup])
  - [property] def editing_markup(self) -> Optional[ViewportMarkup]
  - [editing_markup.setter] def editing_markup(self, markup: Optional[ViewportMarkup])
  - [property] def opened_markup_name(self) -> str
  - [opened_markup_name.setter] def opened_markup_name(self, name: str)
  - def register_callback(self, notification: MarkupChangeCallbacks)
  - def deregister_callback(self, notification: MarkupChangeCallbacks)
  - def is_markup_prim(self, prim_path: str) -> bool
  - def load_markups(self)
  - def create_markup(self, new_markup_path: str = '', icon_url: str = MARKUP_ICON_URL, icon_click: Optional[Callable[[str], None]] = None)
  - def begin_edit_markup(self, markup: ViewportMarkup, set_editing_markup = True) -> bool
  - def end_edit_markup(self, markup: ViewportMarkup)
  - def delete_markup(self, markup: Optional[ViewportMarkup])
  - def export_markups(self)
  - def recall_markup(self, markup: Optional[ViewportMarkup], without_camera = False, enable_settings: Optional[List[str]] = None, disable_settings: Optional[List[str]] = None, force: bool = False)
  - def rename_markup(self, markup: ViewportMarkup, new_name: str) -> bool
  - def get_markups(self)
  - def get_markup(self, name) -> Optional[ViewportMarkup]
  - def get_markup_from_prim_path(self, path: str) -> Optional[ViewportMarkup]
  - def take_screenshot(self)
  - def can_edit_markup(self, markup: ViewportMarkup) -> bool
  - def set_open_callback(self, cb)
  - def get_markup_prim_path(self, name)
  - def refresh_stage(self)
  - def get_all_markup_names(self)
  - def get_markup_name(self, prim_path: str)
  - def open_markup(self, name)
  - def add_element(self, start_x, start_y, end_x, end_y, element_type, element_style, text = None, points = None, shape_type = None, color = None, pixel_size = None)
  - def remove_element(self, name: str)
  - def update_element_pos(self, element_name, start_x, start_y, end_x, end_y)
  - def update_element_attrs(self, element_name, element_style = None, text = None, points = None, ele_type = None, shape_type = None, color = None)
  - def get_element_attr(self, element_name, attr, default_value)
  - def get_markup_elements(self)
  - def lock_camera(self, camera_path: str)
  - def unlock_camera(self)
  - def show_preference(self, x: float, y: float)
  - def set_selection_command(self, fn)
  - def select_markup_in_list_window(self, markup)

- class MarkupChangeCallbacks
  - def __init__(self, on_markup_created: Callable = __dummy, on_markup_deleted: Callable = __dummy, on_markup_changed: Callable = __dummy, on_reset: Callable = __dummy)

- class MarkupListWindow(ui.Window)
  - WINDOW_WIDTH: int
  - VIEWPORT_MAIN_MENUBAR_HEIGHT: int
  - SPACING: int
  - def __init__(self)
  - [property] def selected_index(self) -> int|None
  - [selected_index.setter] def selected_index(self, value: int|None)
  - [property] def widgets(self) -> list[MarkupEntryWidget]
  - def destroy(self)
  - def select_markup_widget(self, mk)

- class ApproveType(Enum)
  - NONE: Unknown
  - REJECTED: int
  - APPROVED: int

- class MarkupCard(PlaylistCard)
  - PLAYLIST_CARD_TYPE_MARKUP: str
  - def __init__(self, type: str, path: str, name: str = None)
  - class def accept(cls, camera_path: str) -> bool
  - [property] def menu_text(self) -> str
  - [property] def icon(self)
  - def active(self, without_camera = False)
  - def clean(self, without_camera = False)

## Functions

- def get_instance() -> Optional[MarkupCore]

## Variables

- FORMAT_EXTS: Tuple
- SETTING_MARKUP_EXPORT_LOCAL_FOLDER: str
- MARKUP_BROWSER_WIDGET_STYLES: Dict
- APPLICATION_MODE: str
- MARKUP_ROOT_PRIM_PATH: str
- SETTINGS_MARKUP_ACTIVE: Unknown
- SETTINGS_MARKUP_EDITING: Unknown
- SETTINGS_MARKUP_ROOT: str
