import carb
import carb.input
from omni import ui
from omni.kit.widgets.custom import DefaultWidgetStyle, WindowMenuHelper, get_ui_style


def merge_dicts(a, b):
    result = a.copy()
    result.update(b)
    return result


class WindowBase:
    LIGHT_STYLE = {}
    DARK_STYLE = {}
    UI_STYLES = {"NvidiaLight": LIGHT_STYLE, "NvidiaDark": DARK_STYLE}

    def __init__(
        self,
        title,
        dock_preference,
        width=0,
        height=0,
        resizable=False,
        menu_path=None,
        menu_hotkey=None,
        appear_after="",
        **kwargs,
    ):
        self._title = title
        self._resizable = resizable

        self._stage_sub = None
        self._ui_style = "undefined"

        self._window = ui.Window(
            title,
            dock_preference,
            width=width,
            height=height,
            padding_x=kwargs.pop("padding_x", 0),
            padding_y=kwargs.pop("padding_y", 0),
            flags=self._get_window_flags(),
            visible=False,
            **kwargs,
        )

        if menu_path is not None:
            use_editor_menu = kwargs.get("use_editor_menu", False)
            self._menu_helper = WindowMenuHelper(
                self._window, menu_path, hotkey=menu_hotkey, appear_after=appear_after, use_editor_menu=use_editor_menu
            )
        else:
            self._menu_helper = None

        self.set_visibility_changed_fn(self.on_show)

        self._build_ui()
        self.set_ui_style(get_ui_style())

    def __del__(self):
        self.destroy()

    def _build_ui(self):
        with self._window.frame:
            with ui.VStack(spacing=0):
                ui.Spacer(height=10)
                self._build_content()

    def set_ui_style(self, ui_style):
        if self._ui_style == ui_style:
            return

        self._ui_style = ui_style
        style = DefaultWidgetStyle.get_style(ui_style)
        style = merge_dicts(style, self._get_content_style(ui_style))
        self._window.frame.set_style(style)

    def get_window_handle(self):
        return self._window

    def show(self, visible=True, x=0, y=0):
        if self._window:
            self._window.visible = visible
            if visible and x > 0 and y > 0:
                self._window.position_x = x
                self._window.position_y = y

    def is_visible(self):
        if self._window:
            return self._window.visible
        else:
            return False

    def set_visibility_changed_fn(self, on_visibility_changed_fn: callable = None):
        if self._menu_helper is not None:
            self._menu_helper.set_visibility_changed_fn(on_visibility_changed_fn)
        else:
            self._window.set_visibility_changed_fn(on_visibility_changed_fn)

    def dock(self, window_name, ratio=0.311, position=ui.DockPosition.RIGHT):
        if not self._window.docked:
            viewport = ui.Workspace.get_window("Viewport")
            if viewport:
                self._window.dock_in(viewport, position, ratio)
        return self._window.docked

    def destroy(self):
        if self._stage_sub:
            self._stage_sub = None
        if self._menu_helper is not None:
            self._menu_helper.destroy()
        self._window.visible = False
        self._window = None

    def _get_content_style(self, ui_style):
        # This function should be overided.
        return {}

    def _get_window_flags(self):
        # This function can be overided.
        flags = ui.WINDOW_FLAGS_NO_SCROLLBAR
        if not self._resizable:
            flags |= ui.WINDOW_FLAGS_NO_RESIZE

        return flags

    def _build_content(self):
        # This function should be overided.
        carb.log_error("ViewWindow._build_content, derived class should override this function")

    def on_show(self, visible):
        # This function can be overided in case the derived need to deal with on_show.
        pass

    @property
    def title(self):
        return self._title
