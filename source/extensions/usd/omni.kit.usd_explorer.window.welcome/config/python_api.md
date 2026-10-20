# Public API for module omni.kit.usd_explorer.window.welcome:

## Classes

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

- class WelcomeWindowFakeModal(ui.Window)
  - def __init__(self, title: str)
  - def destroy(self)
  - def show(self)
  - def hide(self)

- class WindowWelcomeExtension(omni.ext.IExt)
  - WINDOW_NAME: str
  - MENU_PATH: Unknown
  - def on_startup(self, ext_id)
  - def on_shutdown(self)
  - def show_window(self, show)

## Functions

- def get_active_viewport_window(window_name: str = None, usd_context_name: str = '', **kwargs)
- def deregister_actions(extension_id)
- def register_actions(extension_id, cls)
- def get_instance()

## Variables

- CURRENT_TOOL_PATH: str
- MUTE_VIEWPORT_LAYERS: Tuple
- g_extension: NoneType

## Other

- asyncio: builtin module
- carb: public module
- carb.settings: public module
- omni.ext: public module
- omni.kit.app: public module
- omni.kit.menu.utils: public module
- omni.usd: public module
- ui: public module
