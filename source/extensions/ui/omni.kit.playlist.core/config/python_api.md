# Public API for module omni.kit.playlist.core:

## Classes

- class PlayMode
  - TRANSITION_CUT: str
  - TRANSITION_SMOOTH: str

- class PlaylistPlayer
  - static def create(playlist: PlaylistModel, start: int = 0, on_started_fn: Callable = None, on_stopped_fn: Callable = None, on_playing_fn: Callable = None, on_transition_fn: Callable[[bool], None] = None) -> PlaylistPlayer
  - def __init__(self, playlist: PlaylistModel, start_position: int, on_started_fn: callable, on_stopped_fn: callable, on_playing_fn: callable = None)
  - def destroy(self)
  - def play(self, navigation_mode: bool = False)
  - def stop(self)
  - def set_time_per_item(self, time_per_item)
  - def set_transition_time(self, transition_time)
  - def set_playing_index(self, index: int)

- class PlaylistModel(SimpleListModel)
  - def __init__(self, name: str, on_changed_fn: callable = None, system = False, transition_type = PlayMode.TRANSITION_CUT, transition_time = 5, item_time = 5, on_dropped_fn: callable = None, path: Optional[str] = None, auto_active: bool = True)
  - [property] def name(self)
  - [name.setter] def name(self, value)
  - [property] def transition_type(self) -> PlayMode
  - [transition_type.setter] def transition_type(self, value: PlayMode)
  - [property] def transition_time(self) -> float
  - [transition_time.setter] def transition_time(self, value: float)
  - [property] def item_time(self) -> float
  - [item_time.setter] def item_time(self, value: float)
  - [property] def attributes(self)
  - [attributes.setter] def attributes(self, value)
  - [property] def system(self)
  - [property] def auto_save(self)
  - [property] def can_change(self)
  - [property] def selection(self) -> Optional[CardItem]
  - [selection.setter] def selection(self, item: Optional[CardItem])
  - def set_dropped_fn(self, on_dropped_fn: callable)
  - def check_update(self)
  - def save(self)
  - def insert_item(self, item: Union[CardItem, PlaylistCard], index = -1, notify = True)
  - def remove_item(self, item: Union[int, CardItem])
  - def remove_index(self, index: int)
  - [property] def previous_index(self) -> int
  - def previous(self) -> int
  - [property] def next_index(self) -> int
  - def next(self) -> int
  - def get_drag_mime_data(self, item)
  - def drop_accepted(self, target_item, source, drop_location = -1)
  - def drop(self, target_item, source, drop_location = -1)

- class SystemPlaylistModel(PlaylistModel)
  - def __init__(self, name, camera_type)
  - [property] def camera_type(self)
  - def check_update(self)

- class Column
  - NAME: int
  - TYPE: int
  - ID: int
  - COUNT: int

- class CardItem(SimpleListItem)
  - def __init__(self, card: PlaylistCard, index)
  - [property] def name_model(self)
  - [property] def type_model(self)
  - [property] def index_model(self)
  - def active(self)
  - def change_index(self, differ)
  - def set_index(self, index)
  - def subscribe_index_changed_fn(self, fn)
  - def get_value_model(self, index = 0)

- class PlaylistCard
  - CAMERA: str
  - PLAYLIST: str
  - WAYPOINT: str
  - static def register(type: str, cls) -> bool
  - static def deregister(type: str)
  - class def accept(camera_path: str) -> bool
  - static def create(type: Optional[str] = None, camera_prim: Optional[Usd.Prim] = None, name: Optional[str] = None, path: Optional[str] = None)
  - def __init__(self, type: str, path: str, name: Optional[str] = None)
  - [property] def camera_prim(self) -> Optional[Usd.Prim]
  - [property] def menu_text(self) -> str
  - [property] def icon(self) -> str
  - def active(self, without_camera = False)
  - def clean(self, without_camera = False)

- class PlayManager
  - def __init__(self, playlist: Optional[PlaylistModel] = None)
  - def destroy(self)
  - [property] def is_playing(self) -> bool
  - [property] def current_playlist(self) -> Optional[PlaylistModel]
  - [current_playlist.setter] def current_playlist(self, playlist: Optional[PlaylistModel])
  - [property] def current_item(self) -> Optional[CardItem]
  - [current_item.setter] def current_item(self, item: CardItem)
  - def subscribe_playing_playlist_changed(self, on_playing_changed_fn: Callable[[str], None])
  - def subscribe_current_playlist_item_changed(self, on_current_playlist_item_changed_fn: Callable)
  - def play(self, model: Optional[PlaylistModel] = None, navigation_mode: bool = False) -> bool
  - def stop(self)
  - def navigate(self, index: Optional[int] = None, item: Optional[CardItem] = None) -> bool
  - def next(self)
  - def previous(self)

## Functions

- def enum_playlist_cards() -> List[PlaylistCard]
- def get_play_manager() -> PlayManager

## Variables

- PLAYLISTS_ROOT: str
