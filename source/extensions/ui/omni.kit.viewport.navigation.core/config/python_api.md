# Public API for module omni.kit.viewport.navigation.core:

## Classes

- class ViewportNavigationButton(AbstractViewportMenuItem)
  - def __init__(self, name, size, visible_setting_path: Optional[str] = None, order_setting_path: Optional[str] = None, state = True, clicked_fn = None, auto_spin = True, build_tooltip_fn = lambda: (0, 0), show_label = True, has_triangle = False, build_menu_fn = None, build_window_fn = None, style = {}, alignment = ui.Alignment.LEFT_BOTTOM)
  - def build_fn(self, factory: Dict)
  - def invalidate(self)
  - def destroy(self)
  - [property] def hotkey(self) -> Optional[str]
  - [property] def tooltip(self) -> Optional[str]
  - [property] def visible(self) -> bool
  - [visible.setter] def visible(self, value: bool)
  - [property] def state(self)
  - [state.setter] def state(self, value)
  - [property] def screen_position_x(self)
  - [property] def screen_position_y(self)
  - [property] def width(self)
  - [property] def height(self)
  - [property] def auto_spin(self)
  - [auto_spin.setter] def auto_spin(self, value)
  - [property] def enabled(self)
  - [enabled.setter] def enabled(self, value: bool)
  - [property] def menu_item(self) -> ui.Menu
  - [property] def window(self) -> ui.Window
  - [property] def label(self) -> str
  - [label.setter] def label(self, value: str)
  - [property] def name(self) -> str
  - [name.setter] def name(self, value: str)
  - [property] def checked(self) -> bool
  - [checked.setter] def checked(self, value: bool)
  - [property] def style(self)
  - [style.setter] def style(self, value)
  - def on_right_clicked_fn(self)
  - def set_state(self, state)
  - def set_highlight(self, state)

- class ViewportNavigationSeparator(ViewportMenuItem)
  - def build_fn(self, factory)
  - [property] def width(self)

- class ViewportNavigationOptionMenuButton(ViewportNavigationButton)
  - def __init__(self, name, image, size, visible_setting_path: Optional[str] = None, order_setting_path: Optional[str] = None, state = True, show_tip_fn = None, size_change_fn = None, direction_change_fn = None, auto_spin = True, build_tooltip_fn = lambda: (0, 0), show_label = True, direction = ui.Direction.LEFT_TO_RIGHT)
  - def get_style(self)
  - def build_fn(self, factory: Dict)

- class NavigationIconMenuDelegate(ToolBarIconMenuDelegate)
  - def __init__(self, *args, **kwargs)
  - def build_item(self, item: ui.MenuItem)

- class ToolBarIconMenuDelegate(ui.MenuDelegate)
  - def __init__(self, name: str, text: bool = False, width: ui.Length = 38, height: ui.Length = 38, has_triangle: bool = False, triangle_size: float = 6, checked: bool = False, enabled: bool = True, triggered_fn: Callable[[None], None] = None, right_clicked_fn: Callable[[None], None] = None, tooltip: Optional[str] = None)
  - def build_title(self, item: ui.MenuItem)
  - def build_item(self, item: ui.MenuItem)
  - [property] def text_size(self) -> float
  - [property] def has_title(self) -> bool
  - [has_title.setter] def has_title(self, value: bool)
  - [property] def text_visible(self) -> bool
  - [text_visible.setter] def text_visible(self, value: bool)
  - [property] def checked(self) -> bool
  - [checked.setter] def checked(self, value)
  - [property] def enabled(self) -> bool
  - [enabled.setter] def enabled(self, value)
  - [property] def text(self)
  - [text.setter] def text(self, txt: str)
  - def destroy(self)

- class ViewportMenuDelegate(ui.MenuDelegate)
  - def __init__(self, icon_name: str = '', icon_width: int = 16, reserve_status: bool = True, force_checked: bool = False, icon_clicked_fn: Callable[[None], None] = None, build_custom_widgets: Callable[[ui.MenuDelegate, Union[ui.MenuItem, ui.Menu]], None] = None, show_hotkey_placeholder: bool = False)
  - def build_item(self, item: Union[ui.MenuItem, ui.Menu])
  - def get_selected(self) -> bool
  - def set_selected(self, value: bool) -> bool
  - def get_checked(self) -> bool
  - def set_checked(self, value: bool) -> bool
  - [property] def selected(self) -> bool
  - [selected.setter] def selected(self, value: bool)
  - [property] def checked(self) -> bool
  - [checked.setter] def checked(self, value: bool)

- class ViewportNavigationTooltip
  - POINTER_WIDTH: int
  - POINTER_HEIGHT: int
  - TOOLTIP_SIDE_SPACE: int
  - BOUNDARY: int
  - def __init__(self, upper_offset, lower_offset, limited_rect)
  - static def build_space(self)
  - static def build_shortcut(key, size)
  - static def build_label(text)
  - static def set_visible(visible)
  - static def create(upper_offset, lower_offset, limited_rect)
  - static def destroy()
  - static def show(widget, func_name, build_tooltip_fn)
  - static def show_tooltip()
  - static def hide(func_name)

## Functions

- def get_navigation_bar()
- def get_navigation_bar_name()

## Variables

- IMAGE_SIZE: int
- SETTINGS_ROOT: str
- NAVIGATION_TOOL_BOTTOM_OFFSET: Unknown
- NAVIGATION_TOOL_BOTTOM_SPACING: Unknown
- NAVIGATION_IS_LARGE: Unknown
- NAVIGATION_LARGE_SIZE: Unknown
- NAVIGATION_SMALL_SIZE: Unknown
- NAVIGATION_COMPUTED_WIDTH: Unknown
- CURRENT_PATH: Unknown
- ICON_PATH: Unknown
- VIEWPORT_DISPLAY_OPTIONS_PATH: str
- SETTING_NAVIGATION_ROOT: str
- NAVIGATION_TOOL_OPERATION_ACTIVE: Unknown
- NAVIGATION_IS_VISIBLE: Unknown
- SETTINGS_PATH_MODAL_TOOL_ACTIVE: str
- VIEWPORT_TOOLS_BOTTOM_OFFSET_PATH: str
- NAVIGATION_HOTKEYS_ENABLED: Unknown
- NAVIGATION_NEXT_OPERATION: Unknown
- NAVIGATION_NEXT_OPERATION_HOTKEY: Unknown
- BUTTON_RECT_STYLE: Dict
