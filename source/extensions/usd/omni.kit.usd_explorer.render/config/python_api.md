# Public API for module omni.kit.usd_explorer.render:

## Classes

- class FastNavigation
  - def __init__(self)
  - def destroy(self)

- class RenderModeHelper
  - def __init__(self)
  - def destroy(self)
  - async def set_render_to_draft(self, reset: bool = True)

- class usd_explorerRenderExtension(omni.ext.IExt)
  - def on_startup(self, _ext_id: str)
  - def on_shutdown(self)

- class RenderSetItemData
  - def __init__(self, path, value)
  - def set(self)

- class QueueManager
  - def __init__(self)
  - def destroy(self)
  - def put(self, obj)

- class RenderPreset(object)
  - def __init__(self)
  - def destroy(self)
  - def update_menu_bar(self, menu_bar)
  - def update_setting_panel(self, setting_panel)
  - def get_value(self, render_type, path)
  - def update_value(self, render_type, path, value)
  - def update_current_value(self, path, value)
  - def update_draft_value(self, path, value)
  - def update_preview_value(self, path, value)
  - def update_photo_value(self, path, value)
  - def update_custom_value(self, path, value)
  - def add_new_preset(self, render_type)
  - def disable_lights(self)
  - def restore_lights(self)
  - def get_lights_status(self)
  - def set_value(self, render_type, is_reset = False, wait_frame = 4)
  - async def async_set_value(self, render_type, is_reset = False, wait_frame = 4)
  - def set(self, render_type)
  - def get_current_render(self)
  - def reset(self)

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

- class COLORS
  - CLR_0: int
  - CLR_1: int
  - CLR_2: int
  - CLR_3: int
  - CLR_4: int
  - CLR_5: int
  - CLR_6: int
  - CLR_7: int
  - CLR_8: int
  - CLR_9: int
  - CLR_A: int
  - CLR_B: int
  - CLR_C: int
  - CLR_D: int
  - CLR_E: int
  - LIGHRT_GARY: int
  - GRAY: int
  - DARK_GRAY: int
  - DARK_DARK: int
  - TRANSPARENT: int
  - L_SELECTED: int
  - D_SELECTED: int
  - BLACK: int
  - WHITE: int
  - TEXT_LIGHT: CLR_D
  - TEXT_DISABLED_LIGHT: int
  - TEXT_DARK: CLR_C
  - TEXT_DISABLED_DARK: int
  - TEXT_SELECTED: int
  - WIDGET_BACKGROUND_LIGHT: int
  - WIDGET_BACKGROUND_DARK: int
  - BUTTON_BACKGROUND_LIGHT: int
  - LINE_SEPARATOR: int
  - LINE_SEPARATOR_THICK: int

- class DarkColors
  - Background: Unknown
  - BackgroundSelected: int
  - BackgroundHovered: int
  - Text: Unknown
  - TextDisabled: Unknown
  - TextSelected: Unknown
  - Button: Unknown
  - ButtonHovered: int
  - ButtonPressed: int
  - ButtonSelected: int
  - WindowBackground: int

- class EditEventIntModel(ui.SimpleIntModel)
  - def __init__(self, on_begin_edit_fn: callable, on_end_edit_fn: callable, init_value = 0)
  - def begin_edit(self)
  - def end_edit(self)

- class FloatSliderEx
  - LIGHT_STYLE: Dict
  - DARK_STYLE: Dict
  - UI_STYLES: Dict
  - DEFAULT_HEIGHT: int
  - def __init__(self, value, on_value_changed_fn: callable = None, min = 0, max = 1, step = 0.1, unit = None, enabled = True, **kwargs)
  - [property] def value(self)
  - [value.setter] def value(self, new_value)
  - [property] def min(self)
  - [min.setter] def min(self, value)
  - [property] def max(self)
  - [max.setter] def max(self, value)
  - [property] def enabled(self)
  - [enabled.setter] def enabled(self, status)
  - [property] def selected(self)
  - [selected.setter] def selected(self, status)

- class FloatSpinner(BaseSpinner)
  - def __init__(self, value_changed_fn, **kwargs)

- class FontSize
  - Normal: int
  - Large: int
  - XLarge: int
  - XXLarge: int
  - XXXLarge: int
  - Small: int
  - XSmall: int
  - XXSmall: int
  - XXXSmall: int

- class LightColors
  - Background: Unknown
  - BackgroundSelected: Unknown
  - BackgroundHovered: Unknown
  - Text: Unknown
  - TextDisabled: Unknown
  - TextSelected: Unknown
  - Button: Unknown
  - ButtonHovered: Unknown
  - ButtonPressed: Unknown
  - ButtonSelected: int
  - WindowBackground: Unknown

- class MouseKey(IntEnum)
  - NONE: Unknown
  - LEFT: int
  - RIGHT: int
  - MIDDLE: int

- class SpaceComboBox(ComboBoxEx)
  - def __init__(self, *args, **kwargs)
  - [property] def values(self)

- class Switch
  - def __init__(self, on = False, switch_fn = None, images = None, **kwargs)
  - [property] def status(self)
  - [status.setter] def status(self, value)
  - [property] def enabled(self)
  - [enabled.setter] def enabled(self, value)
  - def set_tooltip(self, tooltip)

- class SwitchOrCheckbox
  - def __init__(self, status = False, changed_fn = None, **kwargs)
  - [property] def status(self)
  - [status.setter] def status(self, value)
  - [property] def enabled(self)
  - [enabled.setter] def enabled(self, value)

- class UpdateEventHelper
  - def __init__(self)
  - static def create()
  - static def get_instance()
  - def release(self)
  - def register_update(self, applicant)
  - def deregister_update(self, applicant)

- class WindowBase
  - LIGHT_STYLE: Dict
  - DARK_STYLE: Dict
  - UI_STYLES: Dict
  - def __init__(self, title, dock_preference, width = 0, height = 0, resizable = False, menu_path = None, menu_hotkey = None, appear_after = '', **kwargs)
  - def set_ui_style(self, ui_style)
  - def get_window_handle(self)
  - def show(self, visible = True, x = 0, y = 0)
  - def is_visible(self)
  - def set_visibility_changed_fn(self, on_visibility_changed_fn: callable = None)
  - def dock(self, window_name, ratio = 0.311, position = ui.DockPosition.RIGHT)
  - def destroy(self)
  - def on_show(self, visible)
  - [property] def title(self)

- class RenderItemType
  - COMBO: int
  - SWITCH: int
  - SWITCH_COMBO: int
  - SWITCH_DRAG: int
  - SPIN: int
  - FIELD: int
  - SWITCH_FIELD: int

- class RenderItemInfo
  - def __init__(self, name: str, item_type: RenderItemType, switch_path: str, value_path: Union[str, list], drag_step: float, drag_min: float, drag_max: float, combo_list: list = [], readonly: bool = False)

- class RenderItem
  - FONT_SIZE: int
  - BORDER_RADIUS: int
  - PADDING: int
  - STYLE: Dict
  - def __init__(self, info: RenderItemInfo, pick_combo = None, switch_change = None, slider_change = None)
  - def update_setting_value(self, path, value)
  - def on_update(self, dt)
  - def change_switch_status(self, status)

- class RenderSettingWindow(WindowBase)
  - MENU_PATH: Unknown
  - WINDOW_WIDTH: int
  - WINDOW_HEIGHT: int
  - def __init__(self)
  - def destroy(self)
  - def hide(self, *_)
  - def dock(self, position)
  - def on_update(self, dt)
  - def rebuild(self)

## Functions

- def get_render_preset_instance() -> RenderPreset
- def get_render_settings_instance() -> RenderSettingWindow
- def get_active_viewport(usd_context_name: str = '')
- def singleton(cls)
- def get_instance()
- def delay_execute_by_frame(frame_count, callback: callable, description, max_retry_count = 1)
- def get_ui_style()

## Variables

- g_singleton: NoneType
- SETTING_RESOLUTION_WIDTH: str
- SETTING_RESOLUTION_HEIGHT: str
- SETTING_SKIP_MOST_LIGHTS: str
- color: Unknown
- ICON_PATH: Path
- EXTENSION_NAME: str
- WIDGET_WIDTH: int
- WIDGET_HEIGHT: int
- COLLAPSED_FRAMES: bool

## Other

- Any: unknown
- omni.ext: public module
- asyncio: builtin module
- copy: builtin module
- functools: builtin module
- math: builtin module
- queue: builtin module
- carb: public module
- omni.usd: public module
- webbrowser: builtin module
- OrderedDict: unknown
- Union: unknown
- omni.kit: unknown module
- omni.kit.menu.utils: public module
- omni.kit.ui: internal module
- omni.ui: public module
