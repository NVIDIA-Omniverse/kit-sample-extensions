# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

import dataclasses
import fnmatch
from typing import Callable, Optional

import carb
import omni.kit.app
import omni.kit.async_engine
import omni.ui as ui
from omni.ui import color as cl

from .._config import get_extension_config
from .._msg import (
    IndexFilesClicked,
    MatchModeChanged,
    Msg,
    SearchClicked,
    SearchParamsChanged,
    WizardUiClosed,
)
from .._state import State, UiPhase
from ..search import SearchBackend, SearchParams

# Style constants
LABEL_WIDTH = 60
FIELD_HEIGHT = 24
PADDING = 10
SPACING = 8

_EXTENSION_NAME = "omni.simready.content.browser"


def _get_extension_version() -> str:
    """Return the enabled extension package version, or empty string on failure."""
    try:
        manager = omni.kit.app.get_app().get_extension_manager()
        ext_id = manager.get_enabled_extension_id(_EXTENSION_NAME)
        ext_dict = manager.get_extension_dict(ext_id)
        return ext_dict.get("package", {}).get("version")
    except (KeyError, TypeError, AttributeError):
        return ""


class AutocompletePopup:
    """A popup window that shows autocomplete suggestions without stealing focus."""

    # Window flags to create a non-focus-stealing popup
    WINDOW_FLAGS = (
        ui.WINDOW_FLAGS_NO_TITLE_BAR
        | ui.WINDOW_FLAGS_NO_SCROLLBAR
        | ui.WINDOW_FLAGS_NO_RESIZE
        | ui.WINDOW_FLAGS_NO_MOVE
        | ui.WINDOW_FLAGS_NO_DOCKING
        | ui.WINDOW_FLAGS_NO_CLOSE
        | ui.WINDOW_FLAGS_NO_FOCUS_ON_APPEARING
    )

    def __init__(self, on_select: Callable[[str], None]):
        self._on_select = on_select
        self._window: Optional[ui.Window] = None
        self._mouse_over = False
        self._mouse_pressed_inside = False
        self._container: Optional[ui.Widget] = None

    @property
    def mouse_over(self) -> bool:
        """Check if mouse is over the popup."""
        return self._mouse_over

    def show(self, suggestions: list[str], field: ui.Widget):
        """Show the popup with the given suggestions, positioned below the field."""
        if not suggestions:
            self.hide()
            return

        # Destroy existing window before creating new one
        if self._window:
            self._window.destroy()
            self._window = None

        # Calculate dimensions
        item_height = 24
        popup_height = len(suggestions) * item_height + 4
        popup_width = max(200, int(field.computed_width))

        # Create popup window
        self._window = ui.Window(
            f"{hash(str(suggestions))}autocomplete",
            width=popup_width,
            height=popup_height,
            flags=self.WINDOW_FLAGS,
        )

        # Position below the field
        self._window.position_x = field.screen_position_x
        self._window.position_y = field.screen_position_y + field.computed_height + 2

        with self._window.frame:
            # Container to track mouse hover
            self._container = ui.ZStack()
            with self._container:
                # Grey base fill; the per-item hover style paints blue on top
                ui.Rectangle(style={"background_color": cl(0.2, 0.2, 0.2), "border_radius": 3})
                with ui.VStack(spacing=0):
                    for suggestion in suggestions:
                        self._build_item(suggestion)

            self._container.set_mouse_hovered_fn(self._on_container_hovered)

        self._window.visible = True

    def _on_container_hovered(self, hovered: bool):
        """Track mouse hover on popup container."""
        self._mouse_over = hovered

    def _build_item(self, suggestion: str):
        """Build a single suggestion item using mouse events instead of button."""
        item = ui.ZStack(height=24)
        with item:
            # Transparent by default so the container's grey backdrop shows
            # through; `on_hover` paints blue over this when highlighted.
            bg = ui.Rectangle(style={"background_color": 0x00000000})
            with ui.HStack():
                ui.Spacer(width=8)
                ui.Label(suggestion, height=24, style={"color": 0xFFCCCCCC})
                ui.Spacer(width=8)

        # Track hover for highlighting
        def on_hover(hovered: bool):
            # Item hover is more reliable than container hover after switching fields.
            self._mouse_over = hovered
            bg.set_style({"background_color": cl(0.3, 0.3, 0.8) if hovered else 0x00000000})

        def on_mouse_pressed(x, y, btn_idx, mod):
            if btn_idx == 0:
                self._mouse_pressed_inside = True
                self._mouse_over = True

        # Handle mouse release (more reliable than button click)
        def on_mouse_released(x, y, btn_idx, mod):
            if btn_idx == 0:  # Left click
                self._mouse_pressed_inside = False
                self._on_select(suggestion)
                self.hide()

        item.set_mouse_hovered_fn(on_hover)
        item.set_mouse_pressed_fn(on_mouse_pressed)
        item.set_mouse_released_fn(on_mouse_released)

    def hide(self):
        """Hide the popup window."""
        if self._window:
            self._window.visible = False
        self._mouse_over = False
        self._mouse_pressed_inside = False

    def hide_if_not_hovered(self):
        """Hide only if mouse is not over the popup."""
        if not self._mouse_over and not self._mouse_pressed_inside:
            self.hide()

    def destroy(self):
        """Destroy the popup window. Call when parent widget is destroyed."""
        if self._window:
            self._window.visible = False
            self._window.destroy()
            self._window = None
        self._container = None
        self._mouse_over = False
        self._mouse_pressed_inside = False

    @property
    def visible(self) -> bool:
        return self._window is not None and self._window.visible


class AutocompleteField:
    """A text field with autocomplete dropdown suggestions.

    Shows a popup with filtered suggestions as the user types.
    Uses WINDOW_FLAGS_NO_FOCUS_ON_APPEARING to prevent stealing focus.
    """

    MAX_SUGGESTIONS = 8

    def __init__(
        self,
        suggestions: list[str],
        initial_value: str = "",
        height: int = FIELD_HEIGHT,
        on_value_changed: Optional[Callable[[str], None]] = None,
        on_commit: Optional[Callable[[str], None]] = None,
        tooltip: str = "",
    ):
        self._suggestions = suggestions
        self._on_value_changed = on_value_changed
        self._on_commit = on_commit
        self._popup = AutocompletePopup(on_select=self._select_suggestion)
        self._subscriptions: list = []
        self._is_editing = False
        self._last_value = initial_value

        # Create the model and field
        self._model = ui.SimpleStringModel()
        self._model.set_value(initial_value)

        self._field = ui.StringField(model=self._model, height=height, tooltip=tooltip or "")

        # Subscribe to value changes for filtering suggestions
        sub = self._model.subscribe_value_changed_fn(self._on_text_changed)
        self._subscriptions.append(sub)

        # Track when editing begins
        begin_edit_id = self._model.add_begin_edit_fn(self._on_edit_began)
        self._subscriptions.append(begin_edit_id)

        # Track when editing ends
        end_edit_id = self._model.add_end_edit_fn(self._on_edit_ended)
        self._subscriptions.append(end_edit_id)

    @property
    def model(self) -> ui.SimpleStringModel:
        return self._model

    def _on_edit_began(self, model: ui.AbstractValueModel):
        """Track that editing has started and show suggestions immediately."""
        self._is_editing = True
        self._last_value = model.get_value_as_string()
        # Show suggestions immediately when user clicks on the field
        self._show_suggestions()

    def _on_text_changed(self, model: ui.AbstractValueModel):
        """Filter and show suggestions as user types."""
        current_value = model.get_value_as_string()

        if self._on_value_changed:
            self._on_value_changed(current_value)

        # Show suggestions when value changes while editing
        if self._is_editing:
            self._last_value = current_value
            self._show_suggestions()

    def _on_edit_ended(self, model: ui.AbstractValueModel):
        """Handle edit ended — defer popup hiding and commit.

        Clicking on the popup window causes end_edit to fire *before* the
        popup's mouse-press event is delivered.  We defer to the next frame so
        that popup clicks can complete first.  If the popup is still being
        pressed we skip both hiding and committing — the popup selection path
        (_select_suggestion) handles the commit instead.
        """
        self._is_editing = False
        omni.kit.async_engine.run_coroutine(self._deferred_end_edit())

    async def _deferred_end_edit(self):
        """Deferred end-edit: hide popup and commit if appropriate."""
        await omni.kit.app.get_app().next_update_async()
        if self._is_editing:
            carb.log_info("[SimReady Search] deferred end-edit skipped: editing resumed")
            return
        self._popup.hide_if_not_hovered()
        if self._popup._mouse_pressed_inside:
            carb.log_info("[SimReady Search] deferred end-edit skipped: popup press in flight")
            return
        if self._on_commit:
            carb.log_info(f"[SimReady Search] deferred end-edit commit: {self._model.get_value_as_string()!r}")
            self._on_commit(self._model.get_value_as_string())

    def _get_filtered_suggestions(self) -> list[str]:
        """Get suggestions that match current input.

        Each space-separated value is treated as a separate filter chip:
        - If input ends with space, show all unused suggestions (starting new chip)
        - Otherwise, filter based on the partial word being typed using fnmatch
        - If no matches found, show all unused suggestions (reset to full list)
        - Already-used values are excluded from suggestions
        - Matching is case-insensitive and supports glob patterns (*, ?)

        The popup stays visible during editing - if nothing matches, it shows all options.
        """
        current_text = self._model.get_value_as_string()

        # Get already-used values to exclude them
        used_values = set(current_text.split())

        # Get all unused suggestions (used as fallback when no matches)
        all_unused = [s for s in self._suggestions if s not in used_values]

        # Check if user is starting a new word (trailing space or empty)
        if current_text.endswith(" ") or not current_text:
            # Show all unused suggestions
            return all_unused[: self.MAX_SUGGESTIONS]

        # Filter based on partial word being typed
        words = current_text.split()
        search_term = words[-1] if words else ""

        if not search_term:
            return all_unused[: self.MAX_SUGGESTIONS]

        # Exclude the partial word from used values (it's being typed)
        used_values.discard(search_term)
        all_unused_for_filter = [s for s in self._suggestions if s not in used_values]

        # Filter suggestions using fnmatch (case-insensitive)
        # If pattern has no wildcards, treat it as *pattern* for substring matching
        pattern = search_term.lower()
        if "*" not in pattern and "?" not in pattern:
            pattern = f"*{pattern}*"

        filtered = [s for s in all_unused_for_filter if fnmatch.fnmatch(s.lower(), pattern)]

        # If no matches, show all unused suggestions instead of empty list
        if not filtered:
            return all_unused_for_filter[: self.MAX_SUGGESTIONS]

        return filtered[: self.MAX_SUGGESTIONS]

    def _show_suggestions(self):
        """Show the suggestions popup."""
        filtered = self._get_filtered_suggestions()
        self._popup.show(filtered, self._field)

    def _select_suggestion(self, suggestion: str):
        """Called when user selects a suggestion from the popup."""
        carb.log_info(f"[SimReady Search] autocomplete suggestion picked: {suggestion!r}")
        current = self._model.get_value_as_string()

        if current.endswith(" ") or not current:
            new_value = current + suggestion
        else:
            parts = current.split()
            if parts:
                parts[-1] = suggestion
                new_value = " ".join(parts)
            else:
                new_value = suggestion

        self._model.set_value(new_value)

        if self._on_value_changed:
            self._on_value_changed(new_value)
        if self._on_commit:
            self._on_commit(new_value)

    def destroy(self):
        """Clean up resources."""
        self._popup.destroy()
        self._subscriptions.clear()


class ReadyState:
    def __init__(
        self,
        state: State,
        dispatch: Callable[[Msg], None],
    ):
        self._state = state
        self._dispatch = dispatch
        self._subscriptions: list = []
        self._fields: dict[str, ui.StringField] = {}
        self._autocomplete_fields: list[AutocompleteField] = []
        self._committed_values: dict[str, str] = {}

    def destroy(self):
        for autocomplete in self._autocomplete_fields:
            autocomplete.destroy()
        self._autocomplete_fields.clear()
        self._subscriptions.clear()
        self._fields.clear()

    def build(self):
        backend = self._state.active_backend

        with ui.VStack(spacing=SPACING):
            if backend == SearchBackend.WORKSPACE_CACHE:
                self._build_match_mode_selector()
                ui.Spacer(height=SPACING)

            with ui.VStack(spacing=SPACING):
                match backend:
                    case SearchBackend.FILE_INDEX | SearchBackend.WORKSPACE_CACHE:
                        self._build_filter_row(
                            "Name:",
                            self._state.search_params.name_filter,
                            tooltip="Filter by path or file name.",
                        )
                        if backend == SearchBackend.WORKSPACE_CACHE:
                            self._build_filter_row(
                                "Profile:",
                                self._state.search_params.profile_filter,
                                suggestions=self._state.available_profiles,
                                tooltip="Restrict to SimReady profiles. Pick from suggestions or type.",
                            )
                            self._build_filter_row(
                                "Feature:",
                                self._state.search_params.feature_filter,
                                suggestions=self._state.available_features,
                                tooltip="Restrict to asset features. Suggestions come from the loaded workspace cache.",
                            )
                    case SearchBackend.USD_SEARCH:
                        with ui.HStack(height=FIELD_HEIGHT):
                            ui.Spacer(width=PADDING)
                            ui.Label(
                                "Relevance cutoff:",
                                width=LABEL_WIDTH,
                                tooltip="Minimum match score; higher keeps stricter results.",
                            )
                            ui.Spacer(width=PADDING)
                            model = ui.SimpleFloatModel()

                            def _model_value_changed(_model):
                                new_params = dataclasses.replace(
                                    self._state.search_params,
                                    relevance_cutoff=_model.get_value_as_float(),
                                )
                                self._dispatch(SearchParamsChanged(new_params))

                            model.add_end_edit_fn(_model_value_changed)
                            model.set_min(0.0)
                            model.set_max(1.0)
                            model.set_value(self._state.search_params.relevance_cutoff)
                            ui.FloatDrag(
                                model=model,
                                height=FIELD_HEIGHT,
                                step=0.05,
                                min=0.0,
                                max=1.0,
                                tooltip="Drag or type a minimum match score; higher keeps stricter results.",
                            )
                            ui.Spacer(width=PADDING)
                        self._build_filter_row(
                            "Phrase:",
                            self._state.search_params.phrase_filter,
                            tooltip="Natural-language phrase sent to the USD search service.",
                        )

            # Manually trigger search button
            if backend == SearchBackend.FILE_INDEX:
                ui.Spacer(height=SPACING)
                with ui.HStack(height=FIELD_HEIGHT):
                    ui.Spacer(width=PADDING)
                    btn = ui.Button(
                        "Index Files",
                        height=FIELD_HEIGHT,
                        enabled=self._state.search_location_anchor is not None,
                        tooltip="Scan the selected folder and refresh the local file index used for search.",
                    )
                    ui.Spacer(width=PADDING)
                btn.set_clicked_fn(self._on_index_clicked)

            ui.Spacer(height=SPACING)
            with ui.HStack(height=FIELD_HEIGHT):
                ui.Spacer(width=PADDING)
                search_btn = ui.Button(
                    "Search",
                    height=FIELD_HEIGHT,
                    style={
                        "Button": {"background_color": cl(0.1, 0.451, 0.05)},
                        "Button:hovered": {"background_color": cl(0.14, 0.52, 0.08)},
                        "Button:pressed": {"background_color": cl(0.1, 0.451, 0.05)},
                    },
                    tooltip="Run search with the current filters against the active search mode.",
                )
                ui.Spacer(width=PADDING)
            search_btn.set_clicked_fn(self._on_search_clicked)

            ui.Spacer()

            if backend == SearchBackend.USD_SEARCH:
                self._build_usd_search_service_footer()

    def _build_usd_search_service_footer(self):
        """Show configured USD search endpoint and index location (AI search mode)."""
        cfg = get_extension_config()
        endpoint = cfg.default_usd_search_endpoint or "(not set)"
        index_location = cfg.default_usd_search_index_mapping.get(cfg.default_usd_search_endpoint, "")
        if not index_location:
            index_location = "(not mapped)"

        dim = {"font_size": 12, "color": cl(0.55, 0.55, 0.58)}
        with ui.VStack(spacing=4, height=0):
            ui.Spacer(height=SPACING)
            ui.Separator(height=1, width=0)
            with ui.HStack(height=0):
                ui.Spacer(width=PADDING)
                ui.Label("Service endpoint:", width=LABEL_WIDTH + 40, style=dim)
                ui.Label(
                    endpoint,
                    word_wrap=True,
                    style=dim,
                    alignment=ui.Alignment.LEFT_TOP,
                    height=0,
                )
                ui.Spacer(width=PADDING)
            with ui.HStack(height=0):
                ui.Spacer(width=PADDING)
                ui.Label("Index location:", width=LABEL_WIDTH + 40, style=dim)
                ui.Label(
                    index_location,
                    word_wrap=True,
                    style=dim,
                    alignment=ui.Alignment.LEFT_TOP,
                    height=0,
                )
                ui.Spacer(width=PADDING)

    def _build_match_mode_selector(self):
        """Build the Any/All match mode radio buttons"""
        from pathlib import Path

        from .. import get_extension_path

        icon_path = (Path(get_extension_path()) / "icons").as_posix()
        radio_style = {
            "RadioButton.Image": {
                "background_color": cl.transparent,
                "image_url": f"{icon_path}/radio_off.svg",
            },
            "RadioButton.Image:checked": {"image_url": f"{icon_path}/radio_on.svg"},
        }
        self._radio_collection = ui.RadioCollection()

        with ui.VStack(height=FIELD_HEIGHT):
            # Flat HStack: labels shrink to content (no `width=LABEL_WIDTH`
            # on the "Any"/"All" labels), and a single flexible trailing
            # `ui.Spacer()` consumes the leftover row width so everything
            # packs tight to the left. Wrapping each radio+label pair in
            # its own HStack would give each pair `ui.Fraction(1)` width
            # by default and blow out the spacing again.
            with ui.HStack(height=FIELD_HEIGHT):
                ui.Spacer(width=PADDING)
                ui.Label(
                    "Filter match:",
                    width=LABEL_WIDTH,
                    tooltip="How multiple filter tokens are combined.",
                )
                ui.Spacer(width=PADDING)
                ui.RadioButton(
                    radio_collection=self._radio_collection,
                    width=25,
                    height=25,
                    style=radio_style,
                    tooltip="Match any filter token (OR).",
                )
                ui.Spacer(width=4)
                ui.Label("Any", width=0)
                ui.Spacer(width=SPACING * 2)
                ui.RadioButton(
                    radio_collection=self._radio_collection,
                    width=25,
                    height=25,
                    style=radio_style,
                    tooltip="Require every filter token (AND).",
                )
                ui.Spacer(width=4)
                ui.Label("All", width=0)
                ui.Spacer()

        # Set initial value: 0 = ANY, 1 = ALL
        self._radio_collection.model.set_value(0 if self._state.search_params.match_mode == "any" else 1)

        # Subscribe to changes
        sub = self._radio_collection.model.subscribe_value_changed_fn(self._on_match_mode_changed)
        self._subscriptions.append(sub)

    def _build_filter_row(
        self,
        label: str,
        initial_value: str,
        suggestions: Optional[list[str]] = None,
        tooltip: str = "",
    ) -> ui.SimpleStringModel:
        """Build a single filter input row with label and text field.

        Args:
            label: The label text for the row
            initial_value: Initial value for the field
            suggestions: Optional list of autocomplete suggestions
            tooltip: Hover text for the filter field
        """
        with ui.HStack(height=FIELD_HEIGHT):
            ui.Spacer(width=PADDING)
            ui.Label(label, width=LABEL_WIDTH)

            self._committed_values[label] = initial_value

            if suggestions:
                autocomplete = AutocompleteField(
                    suggestions=suggestions,
                    initial_value=initial_value,
                    height=FIELD_HEIGHT,
                    on_value_changed=lambda v, lbl=label: self._update_search_params(lbl, v),
                    on_commit=lambda v, lbl=label: self._on_autocomplete_commit(lbl, v),
                    tooltip=tooltip or "",
                )
                self._autocomplete_fields.append(autocomplete)
                model = autocomplete.model
            else:
                # Use regular StringField
                model = ui.SimpleStringModel()
                model.set_value(initial_value)

                field = ui.StringField(model=model, height=FIELD_HEIGHT, tooltip=tooltip or "")
                self._fields[label] = field

                # Trigger search only on Enter or focus lost (end_edit), and only if the value changed
                end_edit_id = model.add_end_edit_fn(lambda m, lbl=label: self._on_field_end_edit(lbl, m))
                self._subscriptions.append(end_edit_id)

            ui.Spacer(width=PADDING)

        return model

    # ------------------------------------------------------------------
    # Helpers that build a new SearchParams and dispatch
    # ------------------------------------------------------------------

    def _make_updated_params(self, label: str, value: str) -> SearchParams:
        """Return a new SearchParams with the field for *label* updated to *value*."""
        mapping = {
            "Profile:": "profile_filter",
            "Feature:": "feature_filter",
            "Tag:": "tag_filter",
            "Name:": "name_filter",
            "Phrase:": "phrase_filter",
        }
        field_name = mapping.get(label)
        if field_name:
            return dataclasses.replace(self._state.search_params, **{field_name: value})
        return self._state.search_params

    def _update_search_params(self, label: str, value: str):
        """Update the local state snapshot — does NOT dispatch (no search triggered yet)."""
        new_params = self._make_updated_params(label, value)
        self._state = dataclasses.replace(self._state, search_params=new_params)

    def _on_autocomplete_commit(self, label: str, value: str):
        """Commit an autocomplete field value — dispatch only if changed."""
        previous = self._committed_values.get(label, "")
        if value != previous:
            carb.log_info(f"[SimReady Search] autocomplete commit {label} {previous!r} -> {value!r}")
            self._committed_values[label] = value
            new_params = self._make_updated_params(label, value)
            self._state = dataclasses.replace(self._state, search_params=new_params)
            self._dispatch(SearchParamsChanged(new_params))
        else:
            carb.log_info(f"[SimReady Search] autocomplete commit {label} ignored: unchanged ({value!r})")

    def _on_match_mode_changed(self, model: ui.AbstractValueModel):
        """Handle match mode radio button changes.

        Dispatches ``MatchModeChanged`` (not ``SearchParamsChanged``) so the
        runtime records the new mode without triggering a search — the Any/All
        toggle is a combinator and should only take effect on the next
        user-initiated Search click or filter-field edit.
        """
        new_mode = "any" if model.get_value_as_int() == 0 else "all"
        # Keep the local snapshot in sync so subsequent field edits see the
        # updated mode even before the runtime pushes state back.
        self._state = dataclasses.replace(
            self._state,
            search_params=dataclasses.replace(self._state.search_params, match_mode=new_mode),
        )
        self._dispatch(MatchModeChanged(new_mode))

    def _on_index_clicked(self):
        self._dispatch(IndexFilesClicked())

    def _on_search_clicked(self):
        carb.log_info(f"[SimReady Search] Search button clicked with params={self._state.search_params}")
        self._dispatch(SearchClicked())

    def _on_field_end_edit(self, label: str, model: ui.AbstractValueModel):
        """Trigger search on Enter or focus lost, but only if the value actually changed."""
        current = model.get_value_as_string()
        previous = self._committed_values.get(label, "")
        if current != previous:
            carb.log_info(f"[SimReady Search] field commit {label} {previous!r} -> {current!r}")
            self._committed_values[label] = current
            new_params = self._make_updated_params(label, current)
            self._state = dataclasses.replace(self._state, search_params=new_params)
            self._dispatch(SearchParamsChanged(new_params))
        else:
            carb.log_info(f"[SimReady Search] field commit {label} ignored: unchanged ({current!r})")


class LoadingErrorState:
    def __init__(self, state: State):
        self._state = state

    def build(self):
        with ui.VStack(spacing=10):
            ui.Spacer(height=10)
            ui.Label(
                "Loading Error", style={"font_size": 18, "color": 0xFF0000FF}, alignment=ui.Alignment.CENTER, height=0
            )
            with ui.HStack():
                ui.Spacer(width=10)
                ui.Label(
                    f"{self._state.status_message}",
                    word_wrap=True,
                    style={"font_size": 16},
                    alignment=ui.Alignment.LEFT_TOP,
                )
                ui.Spacer(width=10)
            ui.Spacer()


class LoadingState:
    def build(self):
        with ui.HStack(spacing=10):
            ui.Spacer(width=10)
            ui.Label(
                "Loading Asset Library. Please wait.", style={"font_size": 18}, alignment=ui.Alignment.CENTER, height=0
            )
            ui.Spacer(width=10)


class UnsupportedMultipleItemsState:
    def build(self):
        with ui.VStack(spacing=10):
            ui.Spacer(height=10)
            ui.Label(
                "Multiple items selected",
                style={"font_size": 18},
                alignment=ui.Alignment.CENTER,
                height=0,
            )
            with ui.HStack():
                ui.Spacer(width=PADDING)
                ui.Label(
                    "Asset search is not available in multiple directories.\n" "Please select a single directory item.",
                    word_wrap=True,
                    style={"font_size": 16, "color": cl(0.7, 0.7, 0.7)},
                    alignment=ui.Alignment.LEFT_TOP,
                )
                ui.Spacer(width=PADDING)
            ui.Spacer()


class SearchWizardUi:
    def __init__(self, state: State, dispatch: Callable[[Msg], None]):
        self._state = state
        self._dispatch = dispatch
        self._status_message_label: ui.Label | None = None
        self._current_frame: Optional[ReadyState] = None
        self._window = ui.Window("SimReady Asset Search", width=400, height=200)
        self._window.frame.set_build_fn(self._build_window)
        self._window.set_visibility_changed_fn(self._on_visibility_changed)
        omni.kit.async_engine.run_coroutine(self._dock_window())

    def set_state(self, state: State, rebuild: bool = True):
        """Push a new state snapshot into the view."""
        self._state = state
        if rebuild:
            self._window.frame.rebuild()
        else:
            # No full rebuild requested, but the status line is a cheap
            # direct update and must always track state — otherwise hints
            # set by the update loop (e.g. the "Set at least one filter..."
            # no-op hint) never reach the user.
            self.show_status_message(state.status_message)

    def show_status_message(self, message: str | None):
        if self._status_message_label:
            self._status_message_label.text = message or ""

    def _build_version_footer(self):
        """Pin the extension version to the bottom-right corner of the panel."""
        version = _get_extension_version()
        if not version:
            version = "unknown version"
        dim = {"font_size": 14, "color": cl(0.45, 0.45, 0.48)}
        with ui.HStack(height=0):
            ui.Spacer()
            ui.Label(
                f"v{version}",
                width=0,
                height=0,
                style=dim,
                alignment=ui.Alignment.RIGHT_CENTER,
                tooltip=f"{_EXTENSION_NAME} {version}",
            )
            ui.Spacer(width=PADDING)

    def _build_window(self):
        # Clean up previous frame before rebuilding
        if self._current_frame:
            self._current_frame.destroy()
            self._current_frame = None

        with self._window.frame:
            match self._state.ui_phase:
                case UiPhase.UnsupportedMultipleItems:
                    with ui.VStack(spacing=0):
                        ui.Spacer(height=PADDING)
                        UnsupportedMultipleItemsState().build()
                        ui.Spacer()
                        self._build_version_footer()
                case _:
                    with ui.VStack(spacing=0):
                        ui.Spacer(height=PADDING)
                        _anchor_text = (
                            "Select a location to index"
                            if self._state.active_backend == SearchBackend.FILE_INDEX
                            and self._state.search_location_anchor is None
                            else f"Anchor: {self._state.search_location_anchor}"
                        )
                        ui.Label(
                            _anchor_text,
                            width=self._window.frame.width,
                            height=FIELD_HEIGHT,
                            elided_text=True,
                            style={"font_size": 14, "color": cl(0.6, 0.8, 1.0)},
                        )
                        ui.Separator(height=SPACING, width=0)
                        ui.Spacer(height=SPACING)
                        match self._state.ui_phase:
                            case UiPhase.Loading:
                                LoadingState().build()
                            case UiPhase.Ready:
                                with ui.VStack(spacing=SPACING, alignment=ui.Alignment.TOP, height=0):
                                    self._current_frame = ReadyState(self._state, self._dispatch)
                                    self._current_frame.build()
                                    with ui.HStack(spacing=SPACING):
                                        ui.Spacer(width=PADDING)
                                        self._status_message_label = ui.Label(
                                            self._state.status_message or "",
                                            style={"font_size": 14, "color": cl(0.6, 0.8, 1.0)},
                                            alignment=ui.Alignment.LEFT_CENTER,
                                            height=0,
                                        )
                                        ui.Spacer(width=PADDING)
                            case UiPhase.LoadingError:
                                LoadingErrorState(self._state).build()
                        ui.Spacer()
                        self._build_version_footer()

    async def _dock_window(self):
        await omni.kit.app.get_app().next_update_async()
        content_window = ui.Workspace.get_window("Content")
        self._window.dock_in(content_window, ui.DockPosition.RIGHT, 0.25)
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()

    def _on_visibility_changed(self, visible):
        if visible:
            self._window.frame.rebuild()
        else:
            # Clean up autocomplete popups when window is hidden
            if self._current_frame:
                self._current_frame.destroy()
                self._current_frame = None
            # Let the runtime drop the tree-view filter so the Content
            # Browser returns to its default state while the wizard is gone.
            self._dispatch(WizardUiClosed())

    def show(self):
        self._window.visible = True

    def hide(self):
        self._window.visible = False

    @property
    def visible(self) -> bool:
        return self._window.visible

    def destroy(self):
        # Clean up autocomplete popups before destroying window
        if self._current_frame:
            self._current_frame.destroy()
            self._current_frame = None
        self._window.destroy()
