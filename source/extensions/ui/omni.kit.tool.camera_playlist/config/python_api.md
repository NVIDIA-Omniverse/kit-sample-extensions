# Public API for module omni.kit.tool.camera_playlist:

## Classes

- class PlaylistManager(ui.AbstractItemModel)
  - def __init__(self)
  - static def get_instance()
  - [property] def playlists(self)
  - def destroy(self)
  - def register(self, model: SystemPlaylistModel) -> bool
  - def deregister(self, model: SystemPlaylistModel)
  - def get_playlists(self, user_only: bool = False) -> List[str]
  - def get_playlist(self, index, name = None) -> Optional[PlaylistModel]
  - def remove_playlist(self, index)
  - def append(self, name)
  - def clone(self, name, index)
  - def rename(self, playlist: PlaylistModel, new_name: str)
  - def load_from_usd(self, stage)
  - def get_item_children(self, item = None)
  - def get_item_value_model_count(self, item = None)
  - def get_item_value_model(self, item = None, column_id = 0)

- class Playlist
  - def on_startup(self, ext_id)
  - def on_shutdown(self)
  - def get_playlists(self, user_only: bool = True, active_first: bool = False) -> List[str]
  - def get_playlist(self, name: str) -> Optional[PlaylistModel]
  - def add_to_playlist(self, camera_prim: Optional[Usd.Prim], playlist_name: str)
  - def is_playlist_prim(self, prim_path)

## Functions

- def get_instance()
