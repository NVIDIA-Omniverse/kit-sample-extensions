# Public API for module omni.kit.widgets.custom:

## Classes

- class FileBrowserSelectionType
  - FILE_ONLY: int
  - DIRECTORY_ONLY: int
  - ALL: int

- class FileBrowserMode
  - OPEN: int
  - SAVE: int

- class FilePicker
  - def __init__(self, title, mode, file_type, filter_options)
  - def set_file_selected_fn(self, file_open_handler)
  - def set_cancel_fn(self, cancel_handler)
  - def show(self, dir = None, filename = None, show_local = False)
  - def set_current_directory(self, dir)
  - def set_current_filename(self, filename)
  - def destroy(self)

- class ViewUsd
  - def __init__(self)
  - [property] def edit_context(self) -> Usd.EditContext
  - def update_stage(self, stage)
  - def get_prim(self, path, create = True, type_name = None)
  - def remove_prim(self, path)
  - def set_prim_attribute(self, prim, name, value, type_name = Sdf.ValueTypeNames.String, create = True)
  - def get_prim_attribute(self, prim, name, default)
  - def move_prim(self, path_from, path_to)

- class EditorCheck(object)
  - def __init__(self)
  - [property] def has_editor(self)
  - def capture_screenshot(self, capture_filename, wait_result = False)

- class DefaultWidgetStyle
  - LIGHT: Dict
  - DARK: Dict
  - static def get_style(ui_style = None)

- class InvisibleButton(ui.Button)
  - STYLE: Dict
  - def __init__(self, *arg, **kwargs)

- class DashButton
  - def __init__(self, height = 0, name = None, image_source = None, image_size = 16, image_padding = 7, dash_padding_x = 2, padding = 6, clicked_fn = None, alignment = ui.Alignment.LEFT)
  - [property] def enabled(self)
  - [enabled.setter] def enabled(self, value)

- class ImageButton
  - LIGHT_STYLE: Dict
  - DARK_STYLE: Dict
  - UI_STYLES: Dict
  - def __init__(self, name, width, height, image, clicked_fn, tooltip = None, visible = True, enabled = True, activated = False, tooltip_fn = None)
  - def create(self, style = None, padding_x = 2, padding_y = 2)
  - def destroy(self)
  - [property] def enabled(self)
  - [enabled.setter] def enabled(self, value)
  - def get_width(self)
  - def get_height(self)
  - def get_widget_pos(self)
  - def enable(self, enabled)
  - def set_tooltip(self, tooltip)
  - def set_tooltip_fn(self, tooltip_fn: callable)
  - def is_visible(self)
  - def set_visible(self, visible = True)
  - def identify(self, name)
  - def get_name(self)
  - def is_activated(self)
  - def activate(self, activated = True)
  - def set_image(self, image)

- class SimpleImageButton(ImageButton)
  - def __init__(self, image, size, clicked_fn = None, name = None, style = None, padding = 2)
  - [property] def clicked_fn(self)
  - [clicked_fn.setter] def clicked_fn(self, fn)

- class BoolImageButton(ImageButton)
  - def __init__(self, true_image, false_image, size, state = True, clicked_fn = None)
  - [property] def state(self)
  - [state.setter] def state(self, value)
  - def set_state(self, state, notify = False)

- class SimpleCollapsableFrame(ui.CollapsableFrame)
  - UI_STYLE: Dict
  - def __init__(self, title, style: Dict = None, **kwargs)

- class ExpandPanel
  - def __init__(self, title, title_width: float = 0, expand: bool = False, **kwargs)
  - def rebuild(self)
  - def show(self, visible = True)

- class InfoPanel(ExpandPanel)
  - LIGHT_STYLE: Dict
  - DARK_STYLE: Dict
  - UI_STYLES: Dict
  - def __init__(self, expand: bool = True)
  - def build_panel(self)
  - def update_data(self, attributes)

- class ComboBoxEx(ui.ComboBox, IndexModelManager)
  - def __init__(self, *args, **kwargs)

- class SpaceStringModel(ui.SimpleStringModel)
  - def __init__(self, value, num_spaces = 2)
  - [property] def real_value(self)
  - def get_value_as_string(self)
  - def set_value(self, value)

- class SpaceModelDelegate(AbstractValueModeldelegate)
  - def __init__(self, num_spaces = 2)
  - def get_value_model(self, value, value_type = None)

- class SpaceComboBox(ComboBoxEx)
  - def __init__(self, *args, **kwargs)
  - [property] def values(self)

- class CustomWidgetComboBox(IndexModelManager)
  - LIGHT_STYLE: Dict
  - DARK_STYLE: Dict
  - UI_STYLES: Dict
  - def __init__(self, *args, **kwargs)
  - [property] def enabled(self)
  - [enabled.setter] def enabled(self, value)
  - def current_index(self, value)
  - def insert(self, value, value_type = None)
  - def remove(self, index = None)
  - def clear(self)

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

- class MouseKey(IntEnum)
  - NONE: Unknown
  - LEFT: int
  - RIGHT: int
  - MIDDLE: int

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

- class AbstractValueModeldelegate
  - def __init__(self)
  - def get_value_model(self, value, value_type = None)

- class AbstractWidgetDelegate
  - def __init__(self)
  - def create_widget(self, value, *args, **kwargs)
  - def set_value(self, value)
  - def get_value(self)

- class LabelDelegate(AbstractWidgetDelegate)
  - def __init__(self, alignment = ui.Alignment.LEFT)
  - def create_widget(self, value, *args, **kwargs)
  - def set_value(self, value)
  - def get_value(self)

- class ComboboxLabelDelegate(LabelDelegate)
  - def __init__(self)
  - def create_widget(self, value, *args, **kwargs)
  - def set_value(self, value)
  - def get_value(self)

- class Dialog
  - ICON_NONE: int
  - ICON_NOTIFICATION: int
  - ICON_QUESTION: int
  - ICON_WARN: int
  - ICON_ERROR: int
  - DEFAULT_WIDTH: int
  - DEFAULT_HEIGHT: int
  - CONTENT_RATIO: float
  - LIGHT_STYLE: Dict
  - DARK_STYLE: Dict
  - UI_STYLES: Dict
  - static def cleanup_instance(dialog)
  - def __init__(self, title, message, icon = ICON_NONE, width = DEFAULT_WIDTH, height = DEFAULT_HEIGHT)
  - def add_button(self, title, is_final, callback: callable = None, image = '')
  - def set_button_alignment(self, width = 0, spacing = 5)
  - def show(self, is_modal, ui_style = 'NvidiaLight')

- class MessageDialog(Dialog)
  - def __init__(self, title, message, show_after_create = True)

- class QuestionDialog(Dialog)
  - def __init__(self, title, message, on_yes_fn, show_after_create = True, width = Dialog.DEFAULT_WIDTH, on_no_fn = None)

- class InputDialog(Dialog)
  - INPUT_TYPE_NONE: Unknown
  - INPUT_TYPE_STRING: int
  - INPUT_TYPE_INT: int
  - INPUT_TYPE_FLOAT: int
  - LIGHT_STYLE: Dict
  - DARK_STYLE: Dict
  - UI_STYLES: Dict
  - def __init__(self, title, input_type, on_finished_fn, default_value = None, prompt = None, check_valid_fn = None, on_cancelled_fn = None, icon = Dialog.ICON_NONE, width = Dialog.DEFAULT_WIDTH, height = Dialog.DEFAULT_HEIGHT, modal = True, show_after_create = True)

- class SimpleGridView
  - def __init__(self, **kwargs)
  - [property] def model(self)
  - [model.setter] def model(self, value)
  - [property] def selections(self)
  - [selections.setter] def selections(self, items)
  - [property] def column_width(self)
  - [column_width.setter] def column_width(self, value)
  - [property] def row_height(self)
  - [row_height.setter] def row_height(self, value)
  - def insert_item(self, item, index = -1)
  - def clear(self)
  - def rebuild_grid(self)
  - def on_width_changed(self)

- class CustomMenuItem
  - LIGHT_STYLE: Dict
  - DARK_STYLE: Dict
  - UI_STYLES: Dict
  - def __init__(self, value, create_widget_fn: callable, width, height, on_clicked_fn = None, selected = False)
  - [property] def selected(self)
  - [selected.setter] def selected(self, value)

- class CustomMenu(PopupWindow)
  - LIGHT_STYLE: Dict
  - DARK_STYLE: Dict
  - UI_STYLES: Dict
  - def __init__(self, values, create_widget_fns, menuitem_width, menuitem_height, selection = None, on_selection_changed_fn: callable = None, *args, **kwargs)
  - [property] def selection(self)
  - [selection.setter] def selection(self, value)
  - def show_at(self, widget, alignment = ui.Alignment.RIGHT, visible = True)

- class CustomWidgetMenuItem
  - LIGHT_STYLE: Dict
  - DARK_STYLE: Dict
  - UI_STYLES: Dict
  - def __init__(self, value, padding_x = 4, padding_y = 0, clicked_fn = None, on_value_changed_fn = None, selected = False, **kwargs)
  - [property] def selected(self)
  - [selected.setter] def selected(self, value)
  - [property] def value(self)
  - [value.setter] def value(self, _value)

- class CustomWidgetMenu(PopupWindow)
  - LIGHT_STYLE: Dict
  - DARK_STYLE: Dict
  - UI_STYLES: Dict
  - def __init__(self, values, delegate = None, selection = None, on_selection_changed_fn: callable = None, *args, **kwargs)
  - [property] def selection(self)
  - [selection.setter] def selection(self, value)
  - def show_at(self, widget, alignment = ui.Alignment.RIGHT, visible = True, offset_x = 0, offset_y = 0)

- class CustomComboBoxDroplist(CustomWidgetMenu)

- class EditEventIntModel(ui.SimpleIntModel)
  - def __init__(self, on_begin_edit_fn: callable, on_end_edit_fn: callable, init_value = 0)
  - def begin_edit(self)
  - def end_edit(self)

- class EditEventFloatModel(ui.SimpleFloatModel)
  - def __init__(self, on_begin_edit_fn: callable, on_end_edit_fn: callable, init_value = 0.0)
  - def begin_edit(self)
  - def end_edit(self)

- class EditEventStringModel(ui.SimpleStringModel)
  - def __init__(self, on_begin_edit_fn: callable, on_end_edit_fn: callable, init_value = '')
  - def begin_edit(self)
  - def end_edit(self)

- class SimpleListItem(ui.AbstractItem)
  - def __init__(self, values, delegate = None)
  - def get_value_model(self, index = 0)

- class SimpleItemModel(ui.AbstractItemModel)
  - def __init__(self, columns_count = 1)
  - [property] def items(self)
  - def insert_item(self, item, index = -1)
  - def remove_item(self, item)
  - def remove_index(self, index)
  - def clear(self)
  - def on_item_updated(self, item = None)
  - def get_item_children(self, item = None)
  - def get_item_value_model_count(self, item = None)
  - def get_item_value_model(self, item = None, column_id = 0)

- class SimpleListModel(SimpleItemModel)
  - def __init__(self, columns_count = 1, enable_drag_drop = True)
  - def get_drag_mime_data(self, item)
  - def drop_accepted(self, target_item, source, drop_location = -1)
  - def drop(self, target_item, source, drop_location = -1)

- class SimpleComboboxItem(ui.AbstractItem)
  - def __init__(self, text)

- class SimpleComboboxModel(SimpleItemModel)
  - def __init__(self, *args, **kwargs)
  - def insert_value(self, value, value_type = None)
  - def get_item_value_model(self, item = None, column_id = 0)
  - [property] def current_index(self)
  - [current_index.setter] def current_index(self, index)
  - [property] def current_model(self)
  - [property] def string_values(self)

- class ModelManager
  - def __init__(self, model)
  - [property] def values(self)
  - [property] def values_count(self)
  - def reset(self, *args)
  - def clear(self)
  - def remove(self, index = None)
  - def remove_selected(self)
  - def insert(self, value, value_type = None)
  - def append(self, *args)

- class IndexModelManager(ModelManager)
  - [property] def current(self)
  - [current.setter] def current(self, value)
  - [property] def current_index(self)
  - [current_index.setter] def current_index(self, value)
  - [property] def current_value(self)
  - [current_value.setter] def current_value(self, value)

- class OpaqueRectangle(ui.Rectangle)
  - def __init__(self, **kwargs)

- class ShortSeparator
  - def __init__(self, height)

- class DashRectangle
  - def __init__(self, width, height, padding_x = 2, padding_y = 2, w_step = 10, h_step = 10)

- class TriangleCursorIntSlider
  - LIGHT_STYLE: Dict
  - DARK_STYLE: Dict
  - UI_STYLES: Dict
  - def __init__(self, min, max, value, width, height, **kwargs)
  - def set_value_changed_fn(self, value_changed_fn)
  - def set_value(self, value)

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

- class BaseSpinner
  - LIGHT_STYLE: Dict
  - DARK_STYLE: Dict
  - UI_STYLES: Dict
  - def __init__(self, value_changed_fn, value = 0.0, step = 0.1, width = None, height = SPINNER_MIN_HEIGHT, vertical = True, min_value = None, max_value = None, auto_subscribe = True, **kwargs)
  - [property] def max(self)
  - [max.setter] def max(self, value)
  - [property] def min(self)
  - [min.setter] def min(self, value)
  - [property] def enabled(self)
  - [enabled.setter] def enabled(self, value)
  - [property] def value(self)
  - [value.setter] def value(self, _value)
  - def lock(self, locked)
  - def get_value(self)
  - def set_value(self, value)
  - def on_update(self, dt)

- class FloatSpinner(BaseSpinner)
  - def __init__(self, value_changed_fn, **kwargs)

- class IntSpinner(BaseSpinner)
  - def __init__(self, value_changed_fn, **kwargs)

- class OpaqueZStack(ui.ZStack)
  - def __init__(self, **kwargs)

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

- class SimpleListView
  - LIGHT_STYLE: Dict
  - DARK_STYLE: Dict
  - UI_STYLES: Dict
  - def __init__(self, model = SimpleListModel(columns_count=1), column_widths = [], on_item_selected_fn = None, multi_selection = False, root_visible = False, header_visible = False, **kwargs)
  - def destroy(self)
  - [property] def treeview(self)
  - [property] def model(self)
  - [model.setter] def model(self, value)
  - [property] def items(self)
  - [property] def selection(self)
  - [selection.setter] def selection(self, indexes)
  - [property] def selection_items(self)
  - def update_data(self, model)
  - def insert(self, item, index = -1)
  - def clear(self)
  - def remove_selected(self)

- class Rect
  - def __init__(self, left, width, top, height)
  - def is_inside(self, x, y)
  - [property] def left(self)
  - [property] def top(self)
  - [property] def right(self)
  - [property] def bottom(self)
  - [property] def width(self)
  - [property] def height(self)

- class WindowRect(Rect)
  - def __init__(self, window: ui.Window)

- class WidgetRect(Rect)
  - def __init__(self, widget: ui.Widget)

- class WindowExtension
  - def on_startup(self, menu_path = None, hotkey = None, appear_after = '', use_editor_menu = False, on_visibility_changed_fn: callable = None)
  - def on_shutdown(self)
  - def is_visible(self)
  - def show(self, visible = True)
  - def hide(self)
  - [property] def active(self)
  - [active.setter] def active(self, value)
  - def dock(self, target, position = ui.DockPosition.RIGHT)

- class PopupWindow(ui.Window)
  - def __init__(self, title: str, *args, **kwargs)
  - def add_valid_window(self, window: ui.Window)
  - def remove_valid_window(self, window: ui.Window)
  - def set_pre_close_fn(self, pre_close_fn: callable)
  - def set_visibility_changed_fn(self, on_visibility_changed_fn: callable)

- class TitleWindowBase
  - LIGHT_STYLE: Dict
  - DARK_STYLE: Dict
  - UI_STYLES: Dict
  - TITLEBAR_HEIGHT: int
  - def __init__(self, title, dock_preference, title_icon, width = 0, height = 0, resizable = False, has_option = False, has_help = False, has_close = True, popup = False, title_internal = None, build_custom_titlebar_fn = False, menu_path = None, menu_hotkey = None, appear_after = '', **kwargs)
  - def set_ui_style(self, ui_style)
  - def get_window_handle(self)
  - def set_title_icon(self, icon_path)
  - [deprecated] def listen_ui_style(self, listen_or_not)
  - def show(self, visible = True, x = 0, y = 0)
  - def is_visible(self)
  - def set_visibility_changed_fn(self, on_visibility_changed_fn: callable = None)
  - def dock(self, window_name, ratio = 0.311, position = ui.DockPosition.RIGHT)
  - def destroy(self)
  - def on_closed(self)
  - def on_show(self, visible)
  - [property] def title(self)

- class NoTitleWindowBase
  - LIGHT_STYLE: Dict
  - DARK_STYLE: Dict
  - UI_STYLES: Dict
  - def __init__(self, title = None, dock_preference = ui.DockPreference.DISABLED, title_icon = None, width = 0, height = 0, title_internal = None, build_custom_titlebar_fn = False, padding = 0)
  - def set_ui_style(self, ui_style)
  - def get_window_handle(self)
  - [deprecated] def listen_ui_style(self, listen_or_not)
  - def show(self, show = True, x = 0, y = 0)
  - def is_visible(self)
  - def dock(self, window_name, ratio = 0.311, position = ui.DockPosition.RIGHT)
  - def destroy(self)
  - def on_show(self, visible)

- class WindowMenuHelper
  - def __init__(self, window, menu_path, hotkey: Tuple[int, int] = None, appear_after: Union[list, str] = '', on_visibility_changed_fn: callable = None, use_editor_menu = False)
  - def destroy(self)
  - def set_visibility_changed_fn(self, on_visibility_changed_fn: callable = None)

- class HotkeyHelper
  - def __init__(self)
  - static def acquire_reference()
  - def release(self)
  - def register_hotkey(self, key, modifier: int, fn: callable) -> bool
  - def deregister_hotkey(self, key, modifier)

- class Hotkey
  - def __init__(self, hotkey, on_action_fn: callable, modifier = 0, hotkey_enabled_fn: callable = None)
  - def clean(self)

- class PreferencesHelper
  - static def add_page(page)
  - static def remove_page(page)
  - static def find_page(title)
  - static def get_page(index)
  - static def show_page(title)

- class UpdateEventHelper
  - def __init__(self)
  - static def create()
  - static def get_instance()
  - def release(self)
  - def register_update(self, applicant)
  - def deregister_update(self, applicant)

- class DelayExecutor
  - def __init__(self, callback: callable, description, max_retry_count = 1)
  - def deregister(self)
  - def on_update(self, dt)

- class DelayTimeExecutor(DelayExecutor)
  - def __init__(self, milliseconds, callback: callable, description, max_retry_count = 1)

- class DelayFrameExecutor(DelayExecutor)
  - def __init__(self, frame_count, callback: callable, description, max_retry_count = 1)

- class Timer
  - def __init__(self, interval: float, on_timer_fn: Callable[[None], bool], start = False)
  - [property] def running(self)
  - [property] def interval(self)
  - [interval.setter] def interval(self, value)
  - def on_update(self, dt)
  - def start(self)
  - def stop(self)
  - def pause(self)
  - def resume(self)

## Functions

- def get_ext_instance(ext_name)
- def has_extension(ext_name)
- def merge_dicts(a, b)
- def uniform_absolute_path(path)
- def Singleton(class_)
- def get_ui_style()
- def get_page_titles()
- def delay_execute_by_frame(frame_count, callback: callable, description, max_retry_count = 1)
- def delay_execute_by_milliseconds(milliseconds, callback: callable, description, max_retry_count = 1)
