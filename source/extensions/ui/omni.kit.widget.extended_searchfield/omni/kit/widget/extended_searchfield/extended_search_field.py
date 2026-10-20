# SPDX-FileCopyrightText: Copyright (c) 2018-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
import os
from datetime import datetime
from functools import partial
from typing import Callable, Dict, List, Optional, Tuple

import carb
import omni.appwindow
import omni.client
from omni import ui
from omni.kit.widget.search_delegate import SearchDelegate

from ....search_grammar import GrammarPrefix, create_filters, get_max_results, get_similarity_threshold, parse_query
from .begin_search_popup import BeginSearchPopup
from .browser_delegate import BrowserDelegate
from .engine_selection import EngineSelection
from .image_menu import ImageMenu
from .search_field_popup import SearchFieldPopup
from .search_menu import SearchMenu
from .searchimage import SearchImageButton
from .searchword import SearchWordButton
from .style import ICON_PATH, UI_STYLE
from .utils import (
    IMAGE_TYPES,
    combine_queries,
    get_username,
    has_thumbnail_or_image,
    is_omniverse_url,
    quotify,
    remove_quotes,
    split_with_quotes,
)


class ExtendedSearchField(SearchDelegate):
    """
    Represents a search field to input search words

    Keyword Args:
        width (Optional[ui.Length]): Widget width. Default None, means auto.
        height (Optional[ui.Length]): Widget height. Default ui.Pixel(26). Use None for auto.
        on_search_fn (callable): Function called to do searching. Function signature:
            void on_search_fn(search_words: Optional[List[str]])
        engine_delegate (EngineSelection): The class for getting and setting the search engine,
            and getting all available engines.
        subscribe_edit_changed (bool): True to retrieve on_search_fn called when input changed.
            Default False only retrieve on_search_fn called when input ended.
        show_tokens (bool): Default True to show tokens if end edit. Do nothing if False.
        style (Dict): Widget additional style. Default None, means using default style.
        show_search_button (bool): If True - show search button. Defaults to True.
        max_tokens (int): Maximum number of tokens shown in the search bar. Defaults to 5.
        max_search_word_length (int, optional): Maximum length of the search word displayed in the search bar. Defaults to 30.

    Properties:
        visible (bool): Widget visibility.
        enabled (bool): Enable/Disable widget.
    """

    def __init__(
        self,
        width: Optional[ui.Length] = None,
        height: Optional[ui.Length] = ui.Pixel(26),
        on_search_fn: Callable[[List[str], str, callable], None] = None,
        engine_delegate: EngineSelection = EngineSelection(),
        browser_delegate: BrowserDelegate = None,
        subscribe_edit_changed: bool = False,
        show_tokens: bool = True,
        show_image_menu: bool = True,
        style: Dict = None,
        auto_close_popups: bool = True,
        auto_search_delay: Optional[float] = None,
        parent_window: Optional[ui.Window] = None,
        show_search_button: bool = True,
        max_tokens: int = 5,
        max_search_word_length: Optional[int] = 30,
    ):
        super().__init__()

        # The popup windows would ideally stay open when clicking elsewhere, so the image popup could function
        # as a drop target for images. This is not yet supported by omni.ui, so the popups will auto-close for now.
        self._auto_close_popups: bool = auto_close_popups

        self._container_args = {"style": UI_STYLE.copy() if not style else style}
        if width:
            self._container_args["width"] = width
        if height:
            self._container_args["height"] = height

        self._on_search_fn: Callable[[List[str], str, callable], None] = on_search_fn
        self._subscribe_edit_changed: bool = subscribe_edit_changed
        self._show_tokens: bool = show_tokens
        self._show_search_button: bool = show_search_button

        self._image_search_visible = False
        self._search_filter_visible = False
        self._image_path = None
        self._search_words: List[str] = []
        self._search_tokens: List[Optional[SearchWordButton]] = []
        self._search_before_edit = None
        self._force_search = False
        self._last_typed = datetime.now()
        self._delayed_search_task = None
        self._username_task = None
        self._search_counter = 0
        self._in_searching = False
        self._mouse_over = False
        self._max_tokens = max_tokens
        self._max_search_word_length = max_search_word_length
        self._is_editing = False
        self._query_parsing_succeeded: Optional[bool] = None

        # seconds to wait before searching while typing. None if no delayed search.
        self._auto_search_delay: Optional[float] = auto_search_delay

        self._engine_delegate: EngineSelection = engine_delegate
        self._prefix_task: Optional[asyncio.Future] = None
        self._current_host_engine: Optional[Tuple[str, str]] = None
        self._prefix_refresh_flag: Optional[asyncio.Event] = None

        # Map the host and search engine to a list of supported prefixes
        self._current_prefixes: List[str] = []
        self._prefixes: Dict[Tuple[str, str], List[str]] = {}

        self._popup_menus: List[SearchFieldPopup] = []
        if show_image_menu:
            self._popup_menus.append(
                ImageMenu(
                    popup=self._auto_close_popups,
                    browser_delegate=browser_delegate,
                    title="Image Search",
                    ok_handler=self._on_select_image,
                    cancel_handler=lambda _: self._update_button_visibility(),
                ),
            )
        self._popup_menus.append(
            SearchMenu(
                popup=self._auto_close_popups,
                title="Search Options",
                ok_handler=self._receive_query,
                cancel_handler=lambda _: self._update_button_visibility(),
            )
        )
        if self._show_search_button:
            self._begin_popup = BeginSearchPopup(ok_handler=lambda: self._search())

        self._detects_parent_window_keys = False
        if parent_window:
            self._detects_parent_window_keys = True
            parent_window.set_key_pressed_fn(self._on_key_pressed)

        self._resize_sub = (
            omni.appwindow.get_default_app_window()
            .get_window_resize_event_stream()
            .create_subscription_to_pop(
                self._on_app_window_resize, name="BeginSearchPopup AppWindowResize event", order=0
            )
        )

    def _on_app_window_resize(self, _):
        # After resizing the app window, all the popups might be in strange positions. The best way to solve this is
        # to deselect the search and close all the popups.
        if self._in_searching:
            self._search_field.focus_keyboard(False)
        for popup in self._popup_menus:
            popup.hide()

    @property
    def visible(self) -> bool:
        """
        Widget visibility
        """
        return self._container.visible

    @visible.setter
    def visible(self, value: bool):
        self._container.visible = value

    @property
    def enabled(self) -> bool:
        """
        Enable/disable Widget
        """
        return self._container.enabled

    @enabled.setter
    def enabled(self, value: bool):
        self._container.enabled = value

    def _has_valid_image(self, path: str) -> bool:
        if "image" not in self._current_prefixes:
            return False
        return has_thumbnail_or_image(path)

    def valid_drag_drop_location(self, pos_x: float, pos_y: float) -> bool:
        """Validate the mouse position before a drag and drop.

        Args:
            pos_x (float): Mouse X position
            pos_y (float): Mouse Y position

        Returns:
            bool: True if the mouse is over the search field or its popups.
        """

        def contains(frame: ui.Widget, pos_x: float, pos_y: float) -> bool:
            return (
                pos_x > frame.screen_position_x
                and pos_y > frame.screen_position_y
                and pos_x < frame.screen_position_x + frame.computed_width
                and pos_y < frame.screen_position_y + frame.computed_height
            )

        # allow drag drop on the search field or on either popup
        return contains(self._container, pos_x, pos_y) or any(
            [popup.visible and contains(popup._window.frame, pos_x, pos_y) for popup in self._popup_menus]
        )

    def handle_drag_drop(self, payload: List[str]) -> bool:
        if len(payload) != 1:
            return False
        path = payload[0]
        if self._has_valid_image(path):
            self._on_select_image(dialog=None, path=path)
        return True

    @property
    def search_dir(self):
        return self._search_dir

    @search_dir.setter
    def search_dir(self, search_dir: str):
        for popup_menu in self._popup_menus:
            popup_menu.show_button(False)

        self._search_dir = search_dir
        self._engine_delegate.search_dir = search_dir
        self._force_search = True
        if self._username_task and not self._username_task.done():
            self._username_task.cancel()
        self._username_task = asyncio.ensure_future(self._get_username(search_dir))
        self._refresh_ui()

    async def _get_username(self, url: str):
        username = await get_username(url)
        for popup_menu in self._popup_menus:
            popup_menu.username = username

    def _get_search_prefixes(self) -> list:
        if not self._search_dir or not self._engine_delegate.current_engine:
            return []
        broken_url = omni.client.break_url(self._search_dir)
        if not self.is_supported_url(broken_url.scheme):
            return []

        host = broken_url.host
        # start task only once
        if not self._prefix_task or self._prefix_task.done():
            self._prefix_task = asyncio.ensure_future(self._update_prefixes_async())
        if self._current_host_engine != (host, self._engine_delegate.current_engine):
            self._current_host_engine = (host, self._engine_delegate.current_engine)
            # force task to refresh prefixes if we change host or engine
            if self._prefix_refresh_flag:
                self._prefix_refresh_flag.set()
        if self._current_host_engine in self._prefixes:
            return self._prefixes[self._current_host_engine]
        return []

    def _check_prefix(self, word: str) -> bool:
        if len(self._current_prefixes) == 0:
            return True
        colon_position = word.find(":")
        quote_position = word.find('"')
        # ignore : inside quotes
        if colon_position >= 0 and (quote_position == -1 or colon_position < quote_position):
            prefix = word[:colon_position]
            if prefix not in self._current_prefixes:
                return False
        # verify query by parsing it
        return self.verify_query(word)

    @staticmethod
    def is_supported_url(scheme: str) -> bool:
        """Check if th scheme is either omniverse (for Nucleus servers) or https (for s3 buckets)

        Args:
            scheme (str): URL scheme

        Returns:
            bool: True if supported
        """
        if scheme in ["omniverse", "https"]:
            return True
        return False

    async def _update_prefixes_async(self):
        """Check the prefixes for the current host and engine. This task runs in the background and
        re-checks the prefixes of the host every 60 seconds, or when the host/engine change.

        If the available prefixes change, info will be written to the console. If the prefixes are
        lost or suddenly unavailable, it will show a warning.
        """
        self._prefix_refresh_flag = asyncio.Event()
        while True:
            search_dir = self._search_dir
            engine = self._engine_delegate.current_engine
            broken_url = omni.client.break_url(search_dir)
            prev_prefixes = []
            # check if the URL scheme is supported
            if self.is_supported_url(broken_url.scheme):
                host = broken_url.host
                if (host, engine) in self._prefixes:
                    prev_prefixes = self._prefixes[(host, engine)]

                new_prefixes = await self._engine_delegate.prefixes_for_dir(search_dir)
                refresh = True
                if not prev_prefixes and new_prefixes:
                    carb.log_info(f"Search: {engine} found new search prefixes on host {host}")
                elif prev_prefixes and not new_prefixes:
                    carb.log_warn(f"Search: {engine} found no search prefixes on host {host}")
                elif prev_prefixes == new_prefixes:
                    refresh = False
                else:
                    carb.log_info(f"Search: {engine} updated search prefixes on host {host}")

                if refresh:
                    self._prefixes[(host, engine)] = new_prefixes
                    self._refresh_ui()
                prev_prefixes = new_prefixes

            try:
                await asyncio.wait_for(self._prefix_refresh_flag.wait(), timeout=60)
            except asyncio.TimeoutError:
                pass
            self._prefix_refresh_flag.clear()

    def _refresh_ui(self) -> None:
        prefixes = self._get_search_prefixes()
        if self._current_prefixes != prefixes:
            self._current_prefixes = prefixes

            self._popup_menu_container.clear()
            with self._popup_menu_container:
                self._build_popup_menus(prefixes)
            self._build_search_tokens()
        self._update_button_visibility()

    def _build_popup_menus(self, prefixes: list = []):
        if not prefixes:
            return

        for popup_menu in self._popup_menus:
            if popup_menu.validate_prefixes(prefixes):
                popup_menu.build_ui_for_prefixes(prefixes)
                popup_menu.build_button(clicked_fn=lambda e=popup_menu: self._toggle_popup_menu(e))

    def _on_select_image(self, dialog: Optional[SearchFieldPopup], path: str):
        """Called by the ImageMenu when search is clicked, or when an image is dragged and dropped

        The image path might contain /./ if it is an omniverse search result, so first we remove that.
        Then the search tokens are built, including the image token for the path.
        Then we search for the new search terms (and image).
        """
        if dialog:
            dialog.hide()
        if not path.strip():
            return
        if "image" not in self._current_prefixes:
            return

        # remove quotes and "/./" inside relative path if necessary.
        path = remove_quotes(path).replace("/./", "/").strip()
        self._image_path = path

        self._build_search_tokens()
        if path is not None:
            self._set_in_searching(True)
            self._search_model.set_value("")
            self._search()

        # Close popups
        if self._in_searching:
            self._search_field.focus_keyboard(False)
        for popup in self._popup_menus:
            popup.hide()

    def _receive_query(self, dialog: Optional[SearchFieldPopup], search_words: List[str]):
        """Called by the SearchMenu when search is clicked. Receives the list of strings
        to be turned into tokens and begins a search.
        """
        if search_words:
            # Combine current query with incoming query
            self._search_words = combine_queries(self._search_words, search_words)
            self._set_in_searching(True)
            self._build_search_tokens()
            if not self._show_tokens:
                self._search_model.set_value(" ".join(self._search_words))
            self._search()
        if dialog:
            dialog.hide()

    def _show_popup_menu_buttons(self, entered: bool):
        """Hovering the mouse over the searchfield shows the popup_menu buttons"""
        self._mouse_over = entered
        self._update_button_visibility()

    def _update_button_visibility(self):
        # close button is visible if there is any kind of search text or token
        visible = bool(
            self._image_path or any(self._search_words) or self._search_field.model.get_value_as_string().strip()
        )
        self._clear_button.visible = visible

        # popup buttons are visible if the close button is, if mousing over, or if the popup is open
        visible = visible or self._mouse_over or self._in_searching
        # if one popup is visible, show all buttons to empty prevent gaps
        visible = visible or any([popup_menu.visible for popup_menu in self._popup_menus])
        for popup_menu in self._popup_menus:
            popup_menu.show_button(popup_menu.validate_prefixes(self._current_prefixes) and visible)

    def _toggle_popup_menu(self, popup_menu: SearchFieldPopup):
        """Show or hide the popup menu."""
        if self._auto_close_popups:

            def visibility_changed(visible: bool, popup_menu: SearchFieldPopup):
                alt_text = popup_menu.alternate_search_text
                if alt_text:
                    if visible:
                        self._search_hint.text = alt_text
                    else:
                        self._search_hint.text = "Search"
                self._update_button_visibility()

            popup_menu.set_visibility_changed_fn(lambda v, p=popup_menu: visibility_changed(v, p))
            popup_menu.show(parent=self._container, offset_x=-1, offset_y=24)
            if hasattr(popup_menu, "populate_fields"):
                popup_menu.populate_fields(self._search_words)
        else:
            if not popup_menu.visible:
                for other in self._popup_menus:
                    if other != popup_menu:
                        other.hide()
                popup_menu.show(parent=self._container, offset_x=-1, offset_y=24)
                if hasattr(popup_menu, "populate_fields"):
                    popup_menu.populate_fields(self._search_words)
            else:
                popup_menu.hide()

    def _on_key_pressed(self, key, mod, pressed):
        """Called when the user presses a key in the content window"""
        if pressed and self._is_editing:
            if key == int(carb.input.KeyboardInput.ENTER):
                self._force_search = True
                return
            elif key == int(carb.input.KeyboardInput.ESCAPE):
                self._search_field.focus_keyboard(False)
                self._cancel_search()
                return
            # if auto_search_delay is enabled, start searching after a few seconds.
            if self._auto_search_delay:
                self._last_typed = datetime.now()
                if not self._delayed_search_task or self._delayed_search_task.done():
                    self._delayed_search_task = asyncio.ensure_future(self._delayed_search())

    async def _delayed_search(self):
        """Begin a search after a delay. The delay is updated whenever the user types into the
        search field. Only search if the search words have changed.
        """
        if self._auto_search_delay:
            while (datetime.now() - self._last_typed).total_seconds() < self._auto_search_delay:
                await asyncio.sleep(0.1)
            search_words = self._get_search_words()
            if self._search_before_edit != search_words:
                self._search(extra_search_words=search_words)
            self._search_before_edit = search_words

    def build_ui(self):
        self._container = ui.ZStack(**self._container_args)
        with self._container:
            # background
            self._background = ui.Rectangle(style_type_name_override="ExtendedSearchField.Frame")
            self._background.set_mouse_hovered_fn(self._show_popup_menu_buttons)
            with ui.HStack():
                self._progress_container = ui.VStack(width=0)
                with self._progress_container:
                    progress_button = ui.Button(
                        image_url=f"{ICON_PATH}/search_in_progress.svg",
                        width=24,
                        height=24,
                        style_type_name_override="SearchProgress.Button",
                    )
                    progress_button.set_clicked_fn(lambda: self._cancel_search())
                self._progress_container.visible = False
                # initialize Search Button container stack
                self._search_button_container = self._get_search_button_container()

                with ui.ZStack():
                    with ui.HStack():
                        # Individual word widgets
                        self._words_container = ui.HStack(spacing=5)
                        self._build_search_tokens()
                        # string field to accept user input, here ui.Spacer for border of ExtendedSearchField.Frame
                        with ui.VStack():
                            ui.Spacer()
                            with ui.HStack(height=0):
                                ui.Spacer(width=2)
                                self._search_model = ui.SimpleStringModel()
                                self._search_field = ui.StringField(
                                    self._search_model,
                                    style_type_name_override="ExtendedSearchField",
                                )
                                if not self._detects_parent_window_keys:
                                    # This will only work when the mouse is over the string field,
                                    # but perhaps it is better than nothing. See OM-47519
                                    self._search_field.set_key_pressed_fn(self._on_key_pressed)
                                self._search_field.set_accept_drop_fn(self._has_valid_image)
                                self._search_field.set_drop_fn(lambda e: self._on_select_image(None, e.mime_data))
                                # Workaround for OM-46105
                                self._search_model.set_value(" " * 256)
                                self._search_model.set_value("")
                                # Show/Hide the Close button when typing
                                self._search_model.add_value_changed_fn(lambda _: self._update_button_visibility())

                            ui.Spacer()

                    self._hint_container = ui.HStack(spacing=5)
                    with self._hint_container:
                        ui.Spacer(width=4)
                        self._search_hint = ui.Label("Search", style_type_name_override="ExtendedSearchField.Hint")
                    # OM-75246: hide the hint container if there's search tokens built
                    if self._search_tokens:
                        self._hint_container.visible = False

                ui.Spacer(width=2)
                with ui.VStack(width=0):
                    with ui.HStack(spacing=0):

                        # Close icon
                        with ui.VStack(width=20):
                            ui.Spacer()
                            self._clear_button = ui.Button(
                                image_height=10,
                                image_width=10,
                                style_type_name_override="SearchField.ClearButton",
                                clicked_fn=self._on_clear_clicked,
                            )
                            ui.Spacer()

                        self._popup_menu_container = ui.HStack()
                        with self._popup_menu_container:
                            self._build_popup_menus(self._current_prefixes)

                ui.Spacer(width=2)
                self._clear_button.visible = False

        self._sub_begin_edit = self._search_model.subscribe_begin_edit_fn(self._on_begin_edit)
        self._sub_end_edit = self._search_model.subscribe_end_edit_fn(self._on_end_edit)
        if self._subscribe_edit_changed:
            self._sub_text_edit = self._search_model.subscribe_value_changed_fn(self._on_text_edit)
        else:
            self._sub_text_edit = None

    def _get_search_button_container(self) -> ui.VStack:
        container = ui.VStack(width=0)
        with container:
            search_button = ui.Button(image_width=16, image_height=16, style_type_name_override="SearchField.Button")
            search_button.set_clicked_fn(
                lambda b=search_button: self._show_engine_menu(
                    b.screen_position_x, b.screen_position_y + b.computed_height
                )
            )
        return container

    def _get_search_words(self) -> List[str]:
        """Convert the search string to a list of space separated words."""
        # Split the input string to words and filter invalid
        search_string = self._search_model.get_value_as_string()
        search_words = []

        try:
            for word in split_with_quotes(search_string):
                colon_idx = word.find(":")
                quote_idx = word.find('"')
                if colon_idx >= 0 and (quote_idx == -1 or colon_idx < quote_idx):
                    # Do not use split here, there can be : characters in the suffix
                    prefix = word[:colon_idx]
                    suffix = quotify(word[colon_idx + 1 :])
                    search_words.append(f"{prefix}:{suffix}")
                elif quote_idx == -1:
                    # add quotes around words with spaces
                    search_words.append(quotify(word))
                else:
                    # if the user included quotes, keep the word as it is
                    search_words.append(word)
        except ValueError as e:
            # bad quotation marks
            carb.log_error(f"Error: {e}")
            search_words = search_string.split()

        if len(search_words) == 0:
            return []
        elif len(search_words) == 1 and search_words[0] == "":
            # If empty input, regard as clear
            return []

        # if there is an image: in the text, make the 1st one an official image search.
        for idx, word in enumerate(search_words):
            image_prefix = GrammarPrefix.IMAGE + ":"
            if word.startswith(image_prefix):
                self._image_path = remove_quotes(word[len(image_prefix) :]).replace("/./", "/")
                return search_words[:idx] + search_words[idx + 1 :]
        return search_words

    def _on_begin_edit(self, model: ui.AbstractValueModel):
        self._convert_tokens_to_string()
        self._is_editing = True
        self._set_in_searching(True)
        self._search_before_edit = self._get_search_words()

        async def show_popup(popup, container):
            # Wait for the search field to redraw before showing so the size of the popup is correct.
            await omni.kit.app.get_app().next_update_async()
            if self._is_editing:
                popup.show(parent=container, offset_x=-1, offset_y=24)

        if self._show_search_button:
            asyncio.ensure_future(show_popup(self._begin_popup, self._container))

    def _on_end_edit(self, model: ui.AbstractValueModel) -> None:
        if self._show_search_button:
            self._begin_popup.hide_if_not_hovered()
        self._is_editing = False
        search_words = self._get_search_words()
        if not search_words:
            if len(self._search_words) == 0 and not self._image_path:
                self._set_in_searching(False)
            self._build_search_tokens()
            self._search_model.set_value("")
        else:
            if self._show_tokens:
                self._search_words.extend(search_words)
                self._build_search_tokens()
                self._search_model.set_value("")
            else:
                self._build_search_tokens()
                self._search_words = search_words
                self._search_model.set_value(" ".join(search_words))
        if self._force_search:
            self._force_search = False
            self._search()

    def _on_text_edit(self, model: ui.AbstractValueModel) -> None:
        # Add current input to search words
        self._search(extra_search_words=self._get_search_words())

    def _convert_tokens_to_string(self) -> None:
        """Convert tokens to string when the search field is double clicked."""
        string = ""
        if self._image_path:
            string += GrammarPrefix.IMAGE + ":" + quotify(self._image_path.strip()) + " "
            self._image_path = None

        if self._show_tokens:
            # convert existing search words back to string
            words = [word for word in self._search_words if word]
            self._search_words = []

            string += " ".join(words) + " "

        # Append current input
        current_input = self._search_model.get_value_as_string()
        if current_input:
            string += current_input

        self._words_container.clear()
        self._words_container.visible = False

        try:
            self._search_model.set_value(string)
        except BaseException as e:
            carb.log_error(f"Error setting string model: {str(e)}")

    def _on_clear_clicked(self) -> None:
        # Update UI
        self._set_in_searching(False)
        self._search_model.set_value("")
        self._search_words = []
        self._search_tokens = []
        self._image_path = None
        self._build_search_tokens()

        for popup_menu in self._popup_menus:
            popup_menu.clear()
        self._update_button_visibility()
        self._cancel_search()

    def _set_in_searching(self, in_searching: bool) -> None:
        self._in_searching = in_searching
        # Background outline
        self._background.selected = in_searching
        # Show/Hide hint frame (search icon and hint lable)
        self._hint_container.visible = not in_searching
        # Show/Hide buttons
        self._update_button_visibility()

    async def _double_click_token(self):
        self._convert_tokens_to_string()
        self._search_field.focus_keyboard()

    def _build_search_tokens(self):
        """Change self._search_words and self._image_path into ui tokens."""
        self._words_container.clear()
        self._words_container.visible = True
        if not any(self._search_words) and self._image_path is None:
            return

        self._search_words = [word for word in self._search_words if word]
        self._search_tokens = []

        with self._words_container:
            if self._image_path is not None and "image" in self._current_prefixes:
                SearchImageButton(
                    self._image_path, large=False, on_close_fn=lambda widget: self._hide_search_image(widget)
                )
                ui.Spacer(width=4)
            elif self._image_path:
                # image prefix not supported, so just display the image_path as a normal text query.
                self._search_tokens.append(
                    SearchWordButton(
                        GrammarPrefix.IMAGE + ":" + quotify(self._image_path),
                        on_close_fn=lambda widget: self._hide_search_image(widget),
                        on_dbl_click=lambda x, y, btn, m: asyncio.ensure_future(self._double_click_token()),
                        supported=False if len(self._current_prefixes) > 0 else True,
                    )
                )

            if not self._show_tokens:
                return

            for index, word in enumerate(self._search_words):
                if index == self._max_tokens:
                    n_words = len(self._search_words)
                    self._search_tokens.append(
                        SearchWordButton(
                            "...",
                            on_close_fn=lambda widget, idx=index, n=n_words: self._hide_search_word(
                                widget, idx, n_words
                            ),
                            on_dbl_click=lambda x, y, btn, m: asyncio.ensure_future(self._double_click_token()),
                            supported=all([self._check_prefix(word) for word in self._search_words[index:]]),
                        )
                    )
                elif index < self._max_tokens:
                    self._search_tokens.append(
                        SearchWordButton(
                            self._clip_search_word(word),
                            on_close_fn=lambda widget, idx=index: self._hide_search_word(widget, idx),
                            on_dbl_click=lambda x, y, btn, m: asyncio.ensure_future(self._double_click_token()),
                            supported=self._check_prefix(word),
                        )
                    )
                else:
                    self._search_tokens.append(None)

    def _clip_search_word(self, word: str, ending_length: int = 2) -> str:
        if self._max_search_word_length is None or len(word) <= self._max_search_word_length:
            return word

        return f"{word[:self._max_search_word_length-3-ending_length]}...{word[-ending_length:]}"

    def _hide_search_image(self, widget: SearchWordButton) -> None:
        # Here we cannot remove the widget since this function is called by the widget
        # So just set invisible and change the image_path to None
        # It will be removed later if cleared or done editing.
        widget.visible = False
        self._image_path = None
        if not any(self._search_words):
            self._set_in_searching(False)
            self._search_words = []
            self._search_tokens = []
            self._cancel_search()

    def _hide_search_word(self, widget: SearchWordButton, start_index: int, end_index: Optional[int] = None) -> None:
        # Here we cannot remove the widget since this function is called by the widget
        # So just set invisible and change the word to an empty string
        # It will be removed later if cleared or done editing.
        widget.visible = False

        end_index = start_index + 1 if end_index is None else end_index
        for i in range(start_index, end_index):
            self._search_words[i] = ""
            self._search_tokens[i] = None

        if not self._image_path and not any(self._search_words):
            self._set_in_searching(False)
            self._search_words = []
            self._search_tokens = []
            self._cancel_search()

        async def refresh_tokens():
            self._build_search_tokens()

        if any(self._search_words):
            asyncio.ensure_future(refresh_tokens())

    def _show_engine_menu(self, x, y):
        self._search_engine_menu = ui.Menu("Engines")
        self._engine_delegate.search_dir = self.search_dir
        engines = self._engine_delegate.engines
        if not engines:
            return

        def set_current_engine(engine_name):
            for popup_menu in self._popup_menus:
                popup_menu.show_button(False)

            self._engine_delegate.current_engine = engine_name
            self._force_search = True
            self._refresh_ui()

        if not self._engine_delegate.current_engine in engines:
            set_current_engine(engines[0])

        with self._search_engine_menu:
            for name in engines:
                ui.MenuItem(
                    name,
                    checkable=True,
                    checked=self._engine_delegate.current_engine == name,
                    triggered_fn=lambda n=name: set_current_engine(n),
                )
        self._search_engine_menu.show_at(x, y)

    @staticmethod
    def _convert_image(image_path: str):
        try:
            from omni.deepsearch.helper.utils import image_to_base64
            from PIL import Image

            img = Image.open(image_path)
            # resize the smaller dimension to this size
            target_size = 244
            if img.size[0] > target_size and img.size[1] > target_size:
                ratio = float(img.size[1]) / float(img.size[0])
                if ratio > 1.0:
                    img = img.resize((target_size, int(target_size * ratio)), Image.Resampling.LANCZOS)
                else:
                    img = img.resize((int(target_size / ratio), target_size), Image.Resampling.LANCZOS)

            return image_to_base64(img)
        except ImportError as e:
            carb.log_warn(f"Import error in extended_searchfield: {e}")
        except BaseException as e:
            carb.log_error(f"Error {str(e)}")
        return None

    def _after_search_fn(self, search_counter: int):
        try:
            if self._search_counter == search_counter:
                self._progress_container.visible = False
                self._search_button_container.visible = True
        except AttributeError:
            # This happens if the callback occurs after the searchfield has been destroyed
            pass

    def _cancel_search(self) -> None:
        self._progress_container.visible = False
        self._search_button_container.visible = True
        if self._show_search_button:
            self._begin_popup.hide()
        if self._search_dir and self._on_search_fn:
            self._on_search_fn(None, self._search_dir)

    def search(self, search_query: str = None, image_path: str = None):
        """Force a search of whatever is present in the query, or overwrite what is in the query with
        the given query/image data.

        Args:
            search_query (str, optional): A new search query. Defaults to None.
            image_url (str, optional): An image query. Defaults to None.
        """
        self._cancel_search()
        if search_query is not None:
            self._on_clear_clicked()
            self._search_words = [search_query]
        if image_path is not None:
            self._on_clear_clicked()
            self._image_path = image_path
            # self._search_model.set_value(GrammarPrefix.IMAGE + ":" + quotify(image_query))
        self._set_in_searching(True)
        self._build_search_tokens()
        self._search()

    def verify_query(
        self, search_query: Optional[str], path: str = "/", logger: Callable[[str], None] = carb.log_warn
    ) -> bool:
        """Verify that query input is valid.

        Args:
            search_query (Optional[str]): Input Search query
            path (str, optional): path, where the search is happening. Defaults to "/".

        Returns:
            bool: Query validity
        """
        if search_query is None:
            return True

        # parse query into a dictionary
        try:
            parsed_query = parse_query(search_query)
        except Exception as exc_info:
            logger(f"basic query parsing failed: {exc_info}")
            return False

        # NOTE: this implementation is suboptimal, some filters for search backend are being constructed
        #   that are not needed in this context. The is a ticket to verify field types in search grammar
        #   https://nvidia-omniverse.atlassian.net/browse/OM-53841 when it is going to be completed. This
        #   verification functionality need to be adjusted.

        # try creating query filters
        try:
            _ = create_filters(parsed_query, path)
        except Exception as exc_info:
            logger(f"filter creation failed: {exc_info}")
            return False

        # try parsing max results
        if GrammarPrefix.MAX_RESULTS in parsed_query:
            try:
                _ = get_max_results(parsed_query)
            except Exception as exc_info:
                logger(f"max results parsing failed: {exc_info}")
                return False

        # try getting similarity threshold
        if GrammarPrefix.SIMILARITY_THRESHOLD in parsed_query:
            try:
                _ = get_similarity_threshold(parsed_query)
            except Exception as exc_info:
                logger(f"similarity threshold parsing failed: {exc_info}")
                return False

        return True

    def _search(self, extra_search_words: List[str] = []) -> None:

        if self._show_search_button:
            self._begin_popup.hide()
        search_words = self._search_words + extra_search_words

        if not self._search_dir and (self._image_path or any(search_words)):
            carb.log_info("Select a search location to see search results.")
            self._cancel_search()
            return

        if self._on_search_fn is None:
            carb.log_warn("No search function was supplied")
            return

        if not self._engine_delegate.current_engine:
            carb.log_warn("No search engines registered! Please import a search extension.")
            return

        filter_words = [word for word in search_words if word]

        # verify query
        self._query_parsing_succeeded = True
        is_valid = self.verify_query(search_query=" ".join(filter_words), path=self._search_dir, logger=carb.log_info)
        if not is_valid:
            self._query_parsing_succeeded = False
            self._cancel_search()
            return

        if self._image_path:
            if is_omniverse_url(self._image_path):
                filter_words += [GrammarPrefix.IMAGE + ":" + quotify(self._image_path)]
            else:
                if os.path.splitext(self._image_path)[1].lower() in IMAGE_TYPES:
                    base64 = self._convert_image(self._image_path)
                    if base64 is not None:
                        filter_words += [GrammarPrefix.IMAGE + ":" + base64]
                else:
                    carb.log_warn("Search Error: Local file must be a valid image type.")

        if len(filter_words) == 0:
            self._on_search_fn(None, self._search_dir)
            self._progress_container.visible = False
            self._search_button_container.visible = True
        else:
            self._progress_container.visible = True
            self._search_button_container.visible = False
            self._search_counter += 1
            self._on_search_fn(
                filter_words, self._search_dir, callback=partial(self._after_search_fn, self._search_counter)
            )

    def parsing_succeeded(self) -> Optional[bool]:
        return self._query_parsing_succeeded

    def destroy(self):
        self._after_search_sub = None
        self._on_search_fn = None
        self._sub_begin_edit = None
        self._sub_end_edit = None
        self._sub_text_edit = None

        def cancel_task(task):
            if task and not task.done():
                task.cancel()
            return None

        # pending tasks
        self._delayed_search_task = cancel_task(self._delayed_search_task)
        self._prefix_task = cancel_task(self._prefix_task)
        self._username_task = cancel_task(self._username_task)

        # UI elements
        self._background = None
        self._search_field = None
        self._search_model = None
        self._hint_container = None
        self._clear_button = None
        self._container = None
        self._words_container = None
        self._progress_container = None
        self._search_engine_menu = None
        self._search_button_container = None
        self._search_hint = None
        for popup_menu in self._popup_menus:
            popup_menu.destroy()
        self._popup_menus = []
        self._begin_popup = None

        self._resize_sub = None
        self._engine_delegate = None
