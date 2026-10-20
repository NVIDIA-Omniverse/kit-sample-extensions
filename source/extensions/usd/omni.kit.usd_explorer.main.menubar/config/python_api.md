# Public API for module omni.kit.usd_explorer.main.menubar:

## Classes

- class MenuAlignment
  - DEFAULT: int
  - RIGHT: int

- class MenuItemDescription
  - MAX_DEPTH: int
  - def __init__(self, name: str = '', glyph: str = '', header: Optional[str] = None, appear_after: Union[list, str] = '', enabled: bool = True, ticked: bool = False, ticked_value: Optional[bool] = None, radio_group: Optional[str] = '', sub_menu = None, hotkey: Tuple[int, int] = None, name_fn: Callable = None, show_fn: Callable = None, enable_fn: Callable = None, ticked_fn: Callable = None, onclick_action: Tuple = None, unclick_action: Tuple = None, onclick_fn: Callable = None, unclick_fn: Callable = None, onclick_right_fn: Callable = None, original_svg_color: bool = False, original_menu_item = None, user = None, hotkey_window: Optional[str] = None)
  - def add_on_delete_func(self, on_delete_fn: callable)
  - def remove_on_delete_func(self, on_delete_fn: callable)
  - def add_on_hotkey_update_func(self, hotkey_update_fn: callable)
  - def remove_on_hotkey_update_func(self, hotkey_update_fn: callable)
  - def set_hotkey(self, hotkey)
  - def get_action_mapping_desc(self)
  - def has_action(self)
  - def destroy(self, recurse: bool = True)
  - def json_enc(self)
  - def get(self, key, default_value = None)
  - def can_be_merged(self, other)

- class ApplicationModeControl
  - class async def async_update_selection_state(cls, frame_delay: int = 1)
  - class def request_update_selection_state(cls)
  - class def shutdown(cls)
  - def __init__(self)
  - [property] def button_group(self) -> TabedGroup
  - def build_buttons(self)
  - def destroy(self)

- class RenderModeControl
  - def __init__(self)
  - [property] def button_group(self) -> TabedGroup
  - def build_buttons(self)
  - def set_render(self, render_type: str)
  - def get_render(self)

- class FileMenu
  - def __init__(self)

- class MenubarDelegate(ui.MenuDelegate)
  - STYLE: Dict
  - def __init__(self)
  - [property] def render_control(self) -> Optional[RenderModeControl]
  - [property] def application_control(self) -> Optional[ApplicationModeControl]
  - [property] def file_menu(self) -> Optional[FileMenu]
  - def build_item(self, menu: ui.MenuHelper)
  - def get_menu_alignment(self) -> int

- class usd_explorerUIMainMenuBarExtension(omni.ext.IExt)
  - def __init__(self)
  - def on_startup(self, _ext_id: str)
  - def on_shutdown(self)

## Functions

- def get_eventdispatcher() -> IEventDispatcher
- def get_main_window() -> MainWindow
- def add_menu_items(menu: list, name: str, menu_index: int = 0, can_rebuild_menus: bool = True, delegate = None)
- def rebuild_menus()
- def remove_menu_items(menu: list, name: str, can_rebuild_menus: bool = True)

## Variables

- EXTENSION_NAME: str
- EXTENSION_DESCRPITION: str
- APPLICAITON_MODE_WIDGET_NAME: str
- CENTER_WIDGET_OFFSET: int
- NO_RENDER_MODE_OFFSET: int
- NO_FILE_MENU_OFFSET: int
- SETTINGS_INCLUDE_RENDER_MODES_PATH: str
- SETTINGS_INCLUDE_APPLICATION_MODES_PATH: str
- SETTINGS_INCLUDE_FILE_MENU_PATH: str

## Other

- Optional: unknown
- carb.settings: public module
- omni.appwindow: public module
- omni.ext: public module
- omni.kit.app: public module
- ui: public module
