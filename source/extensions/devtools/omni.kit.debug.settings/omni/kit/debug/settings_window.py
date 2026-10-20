import os

import carb.dictionary
import carb.settings
import omni.ext
import omni.kit.settings.model as model
import omni.kit.ui

WINDOW_NAME = "Debug Settings"
STARTUP_VIS = carb.settings.get_settings().get_as_bool("exts/omni/kit/debug/settings/visible_at_startup")
VIS_CHANGED_SETTINGS_PATH = "exts/omni/kit/debug/settings/visibility"


class Extension(omni.ext.IExt):
    def on_startup(self):
        self._main_window = omni.kit.ui.get_main_window()

        self._model = model.get_ui_model()

        self._window = None
        self._view_collapsing = None
        self._search_layout = None
        self._search_textbox = None
        self._btn_refresh = None

        self._window = omni.kit.ui.WindowStandalone(
            WINDOW_NAME, 800, 600, open=STARTUP_VIS, dock=omni.kit.ui.DockPreference.RIGHT_TOP, menu_path=""
        )
        self._main_window.add_child(self._window)
        self._build_ui()
        self._view_collapsing.set_filter("")

        self._settings = carb.settings.get_settings()
        self._change_id = self._settings.subscribe_to_node_change_events(
            VIS_CHANGED_SETTINGS_PATH, self._on_visibility_changed
        )
        self._window.set_visibility_changed_fn(self._debug_settings_visibility_changed)

    def _on_visibility_changed(self, item: carb.dictionary.Item, event_type: carb.settings.ChangeEventType):
        if event_type == carb.settings.ChangeEventType.CHANGED:
            self._window.show() if item.get_dict() == True else self._window.hide()
            from omni import ui

            win_handle = ui.Workspace.get_window(WINDOW_NAME)
            if win_handle:
                win_handle.visible = item.get_dict()

    def _debug_settings_visibility_changed(self, v):
        carb.settings.get_settings().set(VIS_CHANGED_SETTINGS_PATH, v)
        from omni import ui

        win_handle = ui.Workspace.get_window(WINDOW_NAME)
        if win_handle:
            win_handle.visible = v

    def on_shutdown(self):
        self._main_window.remove_child(self._window)
        del self._window
        self._settings.unsubscribe_to_change_events(self._change_id)
        del self._settings

    def on_list_suggestions(self, text_box, prefix):
        suggestions_list = []

        base_path = text_box.text

        if self._model.get_type(base_path, meta="") == omni.kit.ui.ModelNodeType.UNKNOWN:
            # Find the root path for the supplied path
            base_path = os.path.dirname(base_path)

        if base_path == "/":
            base_path = ""

        child_count = self._model.get_key_count(base_path, meta="")
        for idx in range(child_count):
            suggestions_list.append(base_path + "/" + self._model.get_key(base_path, meta="", index=idx))

        prefix_lower = prefix.lower()
        return [suggestion for suggestion in suggestions_list if suggestion.lower().startswith(prefix_lower)]

    def on_finalize(self, text_box):
        cmd = text_box.text
        if "=" not in cmd:
            return

        separator = cmd.find("=")
        path = cmd[:separator]
        value = cmd[separator + 1 :]

        change_info = omni.kit.ui.ModelChangeInfo()
        change_info.transient = False
        self._model.set_value(path, meta="", value=value, index=0, info=change_info, is_time_sampled=False, time=0.0)

    def _refresh(self, widget):
        self._window.layout.remove_child(self._view_collapsing)
        self._view_collapsing = None
        self._view_collapsing = omni.kit.ui.ViewCollapsing(False, True)
        self._view_collapsing.use_frame_background_color = False
        self._view_collapsing.set_model(self._model)
        self._window.layout.add_child(self._view_collapsing)
        self._search_textbox.text = ""
        self._view_collapsing.set_filter("")

    def _build_ui(self):
        layout = self._window.layout
        self._search_layout = layout.add_child(omni.kit.ui.RowLayout())

        def apply_filter(button):
            filter = self._search_textbox.text
            if "=" in filter:
                filter = filter[: filter.find("=")]
            self._view_collapsing.set_filter(filter)

        self._search_layout.add_child(omni.kit.ui.Label("Modify/search path:"))
        self._btn_refresh = self._search_layout.add_child(
            omni.kit.ui.Button(omni.kit.ui.get_custom_glyph_code("${glyphs}/menu_refresh.svg"))
        )
        self._btn_refresh.set_clicked_fn(self._refresh)
        self._search_textbox = self._search_layout.add_child(omni.kit.ui.TextBox(""))
        self._search_textbox.width = omni.kit.ui.Percent(75)
        self._search_textbox.set_text_changed_fn(apply_filter)
        self._search_textbox.set_list_suggestions_fn(self.on_list_suggestions)
        self._search_textbox.set_text_finalized_fn(self.on_finalize)

        self._view_collapsing = omni.kit.ui.ViewCollapsing(False, True)
        self._view_collapsing.use_frame_background_color = False
        self._view_collapsing.set_model(self._model)
        layout.add_child(self._view_collapsing)
