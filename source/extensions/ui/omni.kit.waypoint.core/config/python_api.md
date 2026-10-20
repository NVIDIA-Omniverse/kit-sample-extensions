# Public API for module omni.kit.waypoint.core:

## Classes

- class WaypointCard(PlaylistCard)
  - PLAYLIST_CARD_TYPE_WAYPOINT: str
  - WAYPOINT_EXTENSION_INSTANCE: NoneType
  - def __init__(self, type: str, path: str, name: str = None)
  - class def accept(cls, camera_path: str) -> bool
  - [property] def menu_text(self) -> str
  - [property] def camera_prim(self)
  - [property] def icon(self)
  - def active(self, without_camera = False)
  - def clean(self, without_camera = False)

- class ViewportWaypoint
  - def __init__(self, name, parent_path = '', icon_url: str = WAYPOINT_ICON_URL, icon_click: callable = None, sidecar_data: Optional[Usd.EditContext] = None, edit_context: Usd.EditContext = None, edit_target_exists: bool = False, hide_in_stage_window_disabled: bool = False, viewport_widget = None)
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
  - [property] def camera_prim(self) -> Optional[Usd.Prim]
  - [property] def is_dirty(self) -> bool
  - [property] def info(self) -> str
  - [property] def edit_context(self) -> Usd.EditContext
  - [property] def usd_prim(self) -> Optional[Usd.Prim]
  - def recall(self, without_camera = False, enable_settings: Optional[List[str]] = None, disable_settings: Optional[List[str]] = None)
  - def stop_recalling(self)
  - def rename(self, new_name)
  - async def create_async(self, on_created_fn: callable = None)
  - def create(self, on_created_fn: callable = None)
  - def create_from_prim(self, prim: Usd.Prim) -> bool
  - def delete(self)
  - def get_usd_prim_path(self) -> str
  - def subscribe_changes(self, enable: bool)

- class WaypointModel(AbstractBrowserModel)
  - def __init__(self, on_waypoint_changed_fn: callable = None)
  - def destroy(self)
  - def execute(self, item: WaypointItem)
  - def get_collection_items(self) -> List[CollectionItem]
  - def get_category_items(self, item: CollectionItem) -> List[CategoryItem]
  - def get_detail_items(self, item: CategoryItem) -> List[WaypointItem]
  - def on_waypoint_changed(self, *_)

- class WaypointItem(DetailItem)
  - def __init__(self, waypoint: ViewportWaypoint)

- class WaypointDelegate(DetailDelegate)
  - def __init__(self, model: WaypointModel)
  - def destroy(self)
  - def get_label(self, item: WaypointItem) -> str
  - def on_right_click(self, item: WaypointItem)
  - def on_click(self, item: WaypointItem)
  - def on_hover(self, item: WaypointItem, hovered: bool)
  - def build_thumbnail(self, item: WaypointItem) -> Optional[ui.Image]
  - def show_context_menu(self, item: WaypointItem)

- class WaypointBrowserWidget(BrowserWidget)
  - def __init__(self, model: Optional[WaypointModel] = None, delegate: Optional[WaypointDelegate] = None, max_thumbnail_size: int = 320, on_waypoint_selection_changed: callable = None)
  - def destroy(self)

- class WaypointItemEditWidget
  - def __init__(self, item: WaypointItem, on_edit_end_fn: callable = None)
  - def destroy(self)
  - [property] def visible(self) -> bool
  - [visible.setter] def visible(self, value: bool)

- class WaypointChangeCallbacks
  - def __init__(self, on_waypoint_created: callable = __dummy, on_waypoint_deleted: callable = __dummy, on_waypoint_changed: callable = __dummy, on_reset: callable = __dummy)

- class Waypoint
  - def on_startup(self, ext_id)
  - def on_shutdown(self)
  - [property] def viewport_widget(self)
  - def set_viewport_widget(self, viewport_widget)
  - [property] def main_window_name(self)
  - def set_main_window_name(self, main_window_name)
  - [property] def hide_in_stage_window_disabled(self)
  - [hide_in_stage_window_disabled.setter] def hide_in_stage_window_disabled(self, is_disabled: bool)
  - [property] def current_waypoint(self) -> Optional[ViewportWaypoint]
  - [current_waypoint.setter] def current_waypoint(self, waypoint: Optional[ViewportWaypoint])
  - [property] def editing_waypoint(self) -> Optional[ViewportWaypoint]
  - [editing_waypoint.setter] def editing_waypoint(self, waypoint: Optional[ViewportWaypoint])
  - [property] def edit_target(self) -> Sdf.Layer
  - [edit_target.setter] def edit_target(self, layer: Sdf.Layer)
  - [property] def edit_context(self) -> Usd.EditContext
  - def register_callback(self, notification: WaypointChangeCallbacks)
  - def deregister_callback(self, notification: WaypointChangeCallbacks)
  - def is_waypoint_prim(self, prim_path: str, exact: bool = False) -> bool
  - def create_waypoint(self, new_waypoint_path: str = '', icon_url: str = WAYPOINT_ICON_URL, icon_click: callable = None)
  - async def create_waypoint_async(self, new_waypoint_path: str = '', icon_url: str = WAYPOINT_ICON_URL, icon_click: callable = None)
  - def begin_edit_waypoint(self, waypoint: ViewportWaypoint) -> bool
  - def end_edit_waypoint(self, waypoint: ViewportWaypoint, save: bool, create: bool = False)
  - def delete_waypoint(self, waypoint: Optional[ViewportWaypoint])
  - def recall_waypoint(self, waypoint: Optional[ViewportWaypoint], without_camera = False, enable_settings: Optional[List[str]] = None, disable_settings: Optional[List[str]] = None, force: bool = False, recall_timeline: bool = True)
  - def rename_waypoint(self, waypoint: ViewportWaypoint, new_name: str) -> bool
  - def get_waypoints(self) -> List[ViewportWaypoint]
  - def get_waypoint(self, name) -> Optional[ViewportWaypoint]
  - def get_waypoint_from_prim_path(self, path: str) -> Optional[ViewportWaypoint]
  - def show_preference(self, x: float, y: float)
  - def can_edit_waypoint(self, waypoint: ViewportWaypoint, show_messages = True) -> bool
  - def update_dirty(self)

- class WaypointListWindow(ui.Window)
  - WINDOW_WIDTH: int
  - VIEWPORT_MAIN_MENUBAR_HEIGHT: int
  - SPACING: int
  - def __init__(self, on_edit_waypoint_fn: Callable[[WaypointItem, float, float], None] = lambda *x: None)
  - [property] def selected_index(self) -> int|None
  - [selected_index.setter] def selected_index(self, value: int|None)
  - [property] def widgets(self) -> list[WaypointEntryWidget]
  - def destroy(self)

## Functions

- def get_instance()

## Variables

- WAYPOINT_BROWSER_WIDGET_STYLES: Dict
