import asyncio
import copy
from typing import List

import omni.kit.app
import omni.ui as ui
from omni.kit.widget.searchfield import SearchField
from omni.kit.widget.settings import get_style

from .model import SettingsModel
from .style import UI_STYLE
from .view import SettingsView


class SettingSearchFiled(SearchField):
    def __init__(self, on_end_edit_fn: callable, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__on_edit_edit_fn = on_end_edit_fn

    def _on_end_edit(self, model: ui.AbstractValueModel) -> None:
        super()._on_end_edit(model)
        self.__on_edit_edit_fn(model)


class SettingsWindow(ui.Window):

    WINDOW_TITLE = "Debug Settings"

    def __init__(self):
        super().__init__(self.WINDOW_TITLE, width=800, height=600)

        self.frame.set_build_fn(self._build_ui)
        style = copy.deepcopy(UI_STYLE)
        style.update(get_style())
        self.frame.set_style(style)

    def _build_ui(self):
        self._model = SettingsModel()
        with ui.VStack(spacing=8):
            with ui.HStack(height=0):
                ui.Spacer(width=8)
                ui.Label("Modify/search path:", width=0, style_type_name_override="TreeView.Item.Name")
                ui.Spacer(width=10)
                with ui.VStack(width=0):
                    ui.Spacer()
                    ui.Button(width=20, height=20, name="refresh", clicked_fn=self._on_refresh)
                    ui.Spacer()
                ui.Spacer(width=5)
                self._search_field = SettingSearchFiled(
                    self._on_end_edit_search,
                    on_search_fn=self._on_search,
                    subscribe_edit_changed=True,
                    show_tokens=False,
                    suggestions=[],
                )

            self._view = SettingsView(self._model)

    def _on_refresh(self):
        # Clear search field and refresh all items
        self._search_field.clear()

    def _on_search(self, search_words: List[str]):
        if search_words:
            filter_string = " ".join(search_words)
            path = filter_string.split("=")[0]
        else:
            path = None
        self._model.filter_settings(path)

        # Wait a frame for model items/suggestions updated
        async def _update_suggestions():
            await omni.kit.app.get_app().next_update_async()
            self._search_field.suggestions = self._model.filter_suggestions

        asyncio.ensure_future(_update_suggestions())

    def _on_end_edit_search(self, model: ui.AbstractValueModel):
        filter_string = model.as_string
        if filter_string:
            results = filter_string.split("=")
            if len(results) > 1:
                self._model.update_setting(results[0], results[1])
