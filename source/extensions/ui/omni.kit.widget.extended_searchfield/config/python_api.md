# Public API for module omni.search_grammar:

## Functions

- def create_filters(query_dict: dict, path: str)
- def flatten_list_of_lists(input_list: list)
- def parse_description(query_dict: dict)
- def parse_query(query: str)
- def get_max_results(query_dict: dict) -> int
- def get_similarity_threshold(query_dict: dict) -> float

# Public API for module omni.kit.widget.extended_searchfield:

## Classes

- class ExtendedSearchField(SearchDelegate)
  - def __init__(self, width: Optional[ui.Length] = None, height: Optional[ui.Length] = ui.Pixel(26), on_search_fn: Callable[[List[str], str, callable], None] = None, engine_delegate: EngineSelection = EngineSelection(), browser_delegate: BrowserDelegate = None, subscribe_edit_changed: bool = False, show_tokens: bool = True, show_image_menu: bool = True, style: Dict = None, auto_close_popups: bool = True, auto_search_delay: Optional[float] = None, parent_window: Optional[ui.Window] = None, show_search_button: bool = True, max_tokens: int = 5, max_search_word_length: Optional[int] = 30)
  - [property] def visible(self) -> bool
  - [visible.setter] def visible(self, value: bool)
  - [property] def enabled(self) -> bool
  - [enabled.setter] def enabled(self, value: bool)
  - def valid_drag_drop_location(self, pos_x: float, pos_y: float) -> bool
  - def handle_drag_drop(self, payload: List[str]) -> bool
  - [property] def search_dir(self)
  - [search_dir.setter] def search_dir(self, search_dir: str)
  - static def is_supported_url(scheme: str) -> bool
  - def build_ui(self)
  - def search(self, search_query: str = None, image_path: str = None)
  - def verify_query(self, search_query: Optional[str], path: str = '/', logger: Callable[[str], None] = carb.log_warn) -> bool
  - def parsing_succeeded(self) -> Optional[bool]
  - def destroy(self)

- class EngineSelection
  - def __init__(self, engines: List[str] = [])
  - [property] def current_engine(self) -> str
  - [current_engine.setter] def current_engine(self, engine: str)
  - [property] def engines(self) -> List[str]
  - async def prefixes_for_dir(self, search_dir: str) -> List[str]

- class PersistentEngineSelection(EngineSelection)
  - def __init__(self)
  - [property] def current_engine(self) -> str
  - [current_engine.setter] def current_engine(self, engine: str)
  - [property] def search_dir(self) -> str
  - [search_dir.setter] def search_dir(self, dir: str)
  - [property] def engines(self) -> List[str]
