# SPDX-FileCopyrightText: Copyright (c) 2023-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
from __future__ import annotations

from functools import partial

import omni.client
import omni.ui
from omni.asset_validator.core import ValidationEngine
from omni.kit.widget.searchfield import SearchField
from omni.kit.window.filepicker import FilePickerDialog
from omni.ui import AbstractValueModel
from pxr import Sdf

from ..models._asset import AssetMode, ModeItemModel, PrimsModel
from ..models._model import ApplicationModel
from ._icons import Icons

__all__ = ["AssetWidget", "PrimsWidget"]


class PrimsWidget(SearchField):
    def __init__(self, model: PrimsModel | None = None):
        super().__init__()
        self._model = model or ApplicationModel.get().prims_model
        self.search_words = list(map(str, self._model.prims))
        self.suggestions = list(map(str, self._model.suggestions))
        self._on_search_fn = self._search_fn
        self._subscription = self._model.subscribe_value_changed_fn(self._update_fn)

    def _show_suggest_window(self) -> None:
        new_suggestions: list[str] = list(map(str, self._model.suggestions))
        if new_suggestions != self.suggestions:
            self.suggestions = new_suggestions
        super()._show_suggest_window()

    def _search_fn(self, tokens: list[str] | None) -> None:
        if tokens is not None:
            self._model.prims = list(map(Sdf.Path, filter(bool, tokens)))
        else:
            self._model.prims = []

    def _update_fn(self, _: AbstractValueModel) -> None:
        curr_words: list[str] = list(filter(bool, self.search_words))
        new_words: list[str] = list(map(str, self._model.prims))
        if curr_words != new_words:
            self.search_words = new_words


class AssetWidget:
    def __init__(self, *, model: ApplicationModel | None = None, visible: bool = True):
        # Models
        self._model = model or ApplicationModel.get()
        self._subscription = self._model.mode_model.subscribe_value_changed_fn(self._refresh_asset_mode)

        self._visible = omni.ui.SimpleBoolModel(visible)
        self._visible.add_value_changed_fn(self._on_visible_change)

        # Widgets
        self._main_stack = omni.ui.HStack(height=30, visible=visible)
        with self._main_stack:
            self._asset_mode_combo_box = omni.ui.ComboBox(
                ModeItemModel(self._model.mode_model), width=100, tooltip="Select the type of Asset to validate"
            )
            omni.ui.Spacer(width=10)
            with omni.ui.ZStack():
                with omni.ui.HStack():
                    self._asset_uri_field = omni.ui.StringField(self._model.uri_model, height=0)
                    self._asset_uri_button = omni.ui.Button(
                        width=30,
                        height=27,
                        image_url=Icons.FOLDER,
                        tooltip="Browse for an Asset to Validate",
                        clicked_fn=self._show_asset_uri_picker,
                    )
                self._asset_stage_field = omni.ui.StringField(self._model.stage_model, height=0)
                self._asset_stage_field.read_only = True
                self._asset_prims_field = PrimsWidget(self._model.prims_model)

        # Stage is default
        self._refresh_asset_mode(AssetMode.Stage)

    def _on_visible_change(self, model) -> None:
        self._main_stack.visible = model.as_bool

    def _show_asset_uri_picker(self):
        self._dialog = FilePickerDialog(
            "Select Asset Or Folder To Validate",
            enable_file_bar=True,
            enable_filename_input=True,
            enable_checkpoints=False,
            show_detail_view=True,
            show_only_collections=False,
            apply_button_label="Import",
        )
        self._dialog.set_item_filter_fn(partial(self._asset_uri_filter, self._dialog))
        self._dialog.set_click_apply_handler(partial(self._asset_uri_selected, self._dialog))
        self._dialog._widget.file_bar.enable_apply_button(True)
        self._dialog.show()

    @classmethod
    def _asset_uri_filter(cls, dialog, item, *_) -> bool:
        return item.is_folder or ValidationEngine.is_asset_supported(item.path)

    def _asset_uri_selected(self, dialog, file_name: str, dir_name: str) -> None:
        file_url = omni.client.combine_urls(dir_name, file_name)
        selections = dialog.get_current_selections()
        if selections:
            if file_url.startswith(selections[-1]):
                # use file_name when it is aligned with selection as it may provide
                # extra information such as checkpoint version
                self._model.uri = file_url
            else:
                self._model.uri = selections[-1]
        else:
            # fallback when nothing is selected
            self._model.uri = file_url
        dialog.hide()

    @property
    def visible(self) -> bool:
        return self._visible.as_bool

    @visible.setter
    def visible(self, flag: bool) -> None:
        self._visible.as_bool = flag

    def _refresh_asset_mode(self, _) -> None:
        asset_mode: AssetMode = self._model.mode
        self._asset_uri_field.visible = asset_mode is AssetMode.Uri
        self._asset_uri_button.visible = asset_mode is AssetMode.Uri
        self._asset_stage_field.visible = asset_mode is AssetMode.Stage
        self._asset_prims_field.visible = asset_mode is AssetMode.Prims
