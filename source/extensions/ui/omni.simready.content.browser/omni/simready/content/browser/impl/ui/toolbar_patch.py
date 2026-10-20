# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

from typing import Callable

import carb
import omni.ui as ui

from ..search import SearchBackend

_MODE_OPTIONS: tuple[tuple[str, SearchBackend | None], ...] = (
    ("Disabled", None),
    ("Natural Language", SearchBackend.USD_SEARCH),
    ("Tags", SearchBackend.WORKSPACE_CACHE),
    ("File Index", SearchBackend.FILE_INDEX),
)
_MODE_LABELS = tuple(label for label, _backend in _MODE_OPTIONS)

_SEARCH_SLOT_WIDTH_PX = 300


def _toggle_default_search_slot(toolbar_self: object, show_slot: bool) -> None:
    """Show or hide filepicker toolbar search chrome and reclaim horizontal space."""

    px = ui.Pixel(_SEARCH_SLOT_WIDTH_PX if show_slot else 0)
    slot = getattr(toolbar_self, "_simready_search_slot", None)
    if slot is not None:
        slot.visible = show_slot
        slot.width = px

    frame = getattr(toolbar_self, "_search_frame", None)
    if frame is not None:
        if show_slot:
            frame.visible = getattr(toolbar_self, "_search_delegate", None) is not None
        else:
            frame.visible = False


def _ensure_filepicker_toolbar_build_ui_patched(filepicker_toolbar_cls: type) -> None:
    """Capture the search-area HStack; keep body in sync with omni.kit.window.filepicker.ToolBar._build_ui."""
    from omni.kit.widget.browser_bar import BrowserBar
    from omni.kit.window.filepicker.config_button import ConfigButton as FilePickerConfigButton
    from omni.kit.window.filepicker.style import ICON_PATH as fp_ICON_PATH
    from omni.kit.window.filepicker.style import get_style as fp_get_style

    if getattr(filepicker_toolbar_cls._build_ui, "_simready_fp_patched", False):
        return

    if getattr(filepicker_toolbar_cls, "_simready_original_fp_toolbar_build_ui", None) is None:
        filepicker_toolbar_cls._simready_original_fp_toolbar_build_ui = filepicker_toolbar_cls._build_ui  # noqa: SLF001

    def _patched_fp_build_ui(self):
        """Same as upstream filepicker ToolBar._build_ui, plus _simready_search_slot for layout control."""

        # Body mirrored from filepicker tool_bar ToolBar._build_ui (Kit 2.15.x).
        with ui.HStack(height=0, style=fp_get_style(), style_type_name_override="ToolBar"):
            with ui.ZStack():
                with ui.HStack():
                    ui.Spacer(width=48)
                    ui.Rectangle(style_type_name_override="ToolBar.Field")
                with ui.HStack():
                    with ui.VStack():
                        ui.Spacer()
                        self._browser_bar = BrowserBar(  # noqa: SLF001
                            visited_history_size=20,
                            branching_options_handler=self._branching_options_handler,  # noqa: SLF001
                            apply_path_handler=self._apply_path_handler,  # noqa: SLF001
                            prefix_separator=self._prefix_separator,  # noqa: SLF001
                            modal=self._modal,  # noqa: SLF001
                            begin_edit_handler=self._begin_edit_handler,  # noqa: SLF001
                        )
                        ui.Spacer()
                    with ui.VStack(width=20):
                        ui.Spacer()
                        self._bookmark_button = ui.Button(  # noqa: SLF001
                            image_url=f"{fp_ICON_PATH}/bookmark_grey.svg",
                            image_width=18,
                            image_height=18,
                            height=18,
                            style_type_name_override="ToolBar.Button",
                            clicked_fn=lambda: self._on_toggle_bookmark(
                                self._current_directory_provider()
                            ),  # noqa: SLF001
                        )
                        ui.Spacer()

            ui.Spacer(width=2)
            with ui.HStack(width=ui.Pixel(_SEARCH_SLOT_WIDTH_PX)) as self._simready_search_slot:  # noqa: SLF001
                self._search_frame = ui.Frame()  # noqa: SLF001
                if self._search_delegate:  # noqa: SLF001
                    with self._search_frame:  # noqa: SLF001
                        self._search_delegate.build_ui()  # noqa: SLF001
                else:
                    self._search_frame.visible = False  # noqa: SLF001

            self._build_widgets()

            with ui.VStack(width=0):
                ui.Spacer()
                self._config_button = FilePickerConfigButton(  # noqa: SLF001
                    self._enable_soft_delete,  # noqa: SLF001
                    on_value_changed_fn=self._config_values_changed_handler,  # noqa: SLF001
                )
                ui.Spacer()

    _patched_fp_build_ui._simready_fp_patched = True
    filepicker_toolbar_cls._build_ui = _patched_fp_build_ui


def _restore_filepicker_toolbar_build_ui(filepicker_toolbar_cls: type) -> None:
    original = getattr(filepicker_toolbar_cls, "_simready_original_fp_toolbar_build_ui", None)
    if original is not None:
        filepicker_toolbar_cls._build_ui = original  # noqa: SLF001
        del filepicker_toolbar_cls._simready_original_fp_toolbar_build_ui  # noqa: SLF001


class ContentBrowserToolbarPatch:
    def __init__(
        self,
        get_content_browser: Callable[[], object | None],
        on_mode_selected: Callable[[SearchBackend | None], None] | None = None,
    ):
        self._get_content_browser = get_content_browser
        self._on_mode_selected = on_mode_selected
        self._original_build_ui = None

    def install(self) -> None:
        try:
            from omni.kit.window.content_browser import tool_bar as cb_tool_bar
            from omni.kit.window.content_browser.style import ICON_PATH, get_style
            from omni.kit.window.filepicker import ToolBar as FilePickerToolBar
        except Exception as e:  # noqa: BLE001
            carb.log_warn(f"[SimReady] Failed to import content browser toolbar module: {e}")
            return

        _ensure_filepicker_toolbar_build_ui_patched(FilePickerToolBar)

        toolbar_cls = cb_tool_bar.ToolBar
        if getattr(toolbar_cls._build_ui, "_simready_patched", False):
            return

        original_build_ui = getattr(toolbar_cls, "_simready_original_build_ui", None)
        if original_build_ui is None:
            original_build_ui = toolbar_cls._build_ui
            toolbar_cls._simready_original_build_ui = original_build_ui
        self._original_build_ui = original_build_ui

        patch_self = self

        def _patched_build_ui(toolbar_self):
            # Replicate the content_browser ToolBar's outer HStack so we can
            # inject the SimReady combo between the Import button and the rest.
            with ui.HStack(height=0, style=get_style(), style_type_name_override="ToolBar"):
                # Import button — identical to the original _build_ui.
                with ui.VStack(width=0):
                    ui.Spacer()
                    toolbar_self._import_button = ui.Button(  # noqa: SLF001
                        "Import  ",
                        image_url=f"{ICON_PATH}/plus.svg",
                        image_width=12,
                        height=24,
                        spacing=4,
                        style_type_name_override="ToolBar.Button",
                        name="import",
                    )
                    toolbar_self._import_button.set_clicked_fn(  # noqa: SLF001
                        lambda: toolbar_self._import_menu  # noqa: SLF001
                        and toolbar_self._import_menu.show_relative(  # noqa: SLF001
                            toolbar_self._import_button,  # noqa: SLF001
                            toolbar_self._current_directory_provider(),  # noqa: SLF001
                        )
                    )
                    ui.Spacer()

                # SimReady Search combo — immediately to the right of Import.
                ui.Spacer(width=8)
                with ui.VStack(width=0):
                    ui.Spacer()
                    with ui.HStack(height=24, spacing=6, alignment=ui.Alignment.LEFT_CENTER):
                        tooltip = "Enable SimReady search mode"
                        ui.Label(
                            "Search Filters", width=0, height=24, alignment=ui.Alignment.LEFT_CENTER, tooltip=tooltip
                        )
                        toolbar_self._simready_mode_combo = ui.ComboBox(  # noqa: SLF001
                            0,
                            *_MODE_LABELS,
                            width=150,
                            height=24,
                            name="simready_mode_selector",
                        )
                        toolbar_self._simready_mode_combo.model.add_item_changed_fn(  # noqa: SLF001
                            lambda model, item: _on_combo_changed(toolbar_self, model, item)
                        )
                    ui.Spacer()

                FilePickerToolBar._build_ui(toolbar_self)

                disabled = (
                    toolbar_self._simready_mode_combo.model.get_item_value_model().get_value_as_int() == 0
                )  # noqa: SLF001
                _toggle_default_search_slot(toolbar_self, disabled)

        def _on_combo_changed(toolbar_self, model: ui.AbstractItemModel, _item: ui.AbstractItem):
            idx = model.get_item_value_model().get_value_as_int()
            if 0 <= idx < len(_MODE_OPTIONS):
                backend = _MODE_OPTIONS[idx][1]
                show_default_search = backend is None
                _toggle_default_search_slot(toolbar_self, show_default_search)
                if patch_self._on_mode_selected:
                    patch_self._on_mode_selected(backend)

        _patched_build_ui._simready_patched = True
        toolbar_cls._build_ui = _patched_build_ui

    def uninstall(self) -> None:
        try:
            from omni.kit.window.content_browser import tool_bar as cb_tool_bar
            from omni.kit.window.filepicker import ToolBar as FilePickerToolBar
        except Exception:  # noqa: BLE001
            return

        toolbar_cls = cb_tool_bar.ToolBar
        original_build_ui = getattr(toolbar_cls, "_simready_original_build_ui", None) or self._original_build_ui
        if original_build_ui is not None:
            toolbar_cls._build_ui = original_build_ui
        self._original_build_ui = None

        original_build_widgets = getattr(toolbar_cls, "_simready_original_build_widgets", None)
        if original_build_widgets is not None:
            toolbar_cls._build_widgets = original_build_widgets
            del toolbar_cls._simready_original_build_widgets

        _restore_filepicker_toolbar_build_ui(FilePickerToolBar)

    def _get_toolbar_instance(self) -> object | None:
        browser = self._get_content_browser()
        if browser is None:
            return None
        content_window = getattr(browser, "_window", None)
        widget = getattr(content_window, "widget", None)
        return getattr(widget, "_tool_bar", None)

    def rebuild_if_needed(self) -> None:
        browser = self._get_content_browser()
        if browser is None:
            return

        content_window = getattr(browser, "_window", None)
        widget = getattr(content_window, "widget", None)
        ui_window = getattr(content_window, "_window", None)
        if widget is None or ui_window is None or not hasattr(widget, "_build_ui"):
            return

        try:
            with ui_window.frame:
                widget._build_ui()
        except Exception as e:  # noqa: BLE001
            carb.log_warn(f"[SimReady] Failed to rebuild content browser toolbar: {e}")
