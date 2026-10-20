# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Callable, Dict, List, Optional

from omni import ui
from omni.kit.widget.searchfield import SearchField

from .browser_widget import BrowserWidget
from .style import UI_STYLES


class OptionMenuDescription:
    """
    Represent a menu item in options menu.
    Args:
        name (str): Name of menu item. If "" means a seperator.
        clicked_fn (callable): Function called when menu item clicked. Defualts None. Function signature: void clicked_fn()
        enabled_fn (callable): Function called to check menu item enabled or not before show. Default None means already enabled. Function signature: bool enabled_fn()
        enabled_fn (callable): Function called to show menu item or not. Default None means always show. Function signature: bool visible_fn()
        get_text_fn (callable): Function called to show menu item text. Default None to always use name. Function signature: str get_text_fn()
    """

    def __init__(
        self,
        name: str,
        clicked_fn: callable = None,
        enabled_fn: callable = None,
        visible_fn: callable = None,
        get_text_fn: callable = None,
    ):
        self.name = name
        self.clicked_fn = clicked_fn
        self.enabled_fn = enabled_fn
        self.visible_fn = visible_fn
        self.get_text_fn = get_text_fn


class OptionsMenu:
    """
    Represent the options menu, which shows when clicking the options button on search bar.
    User could add own menu items by append_menu_item.
    """

    def __init__(self):
        self._browser_widget = None
        self._options_menu: Optional[ui.Menu] = None
        self._menu_items: Dict[OptionMenuDescription] = {}
        self._menu_descs: List[OptionMenuDescription] = [
            OptionMenuDescription("Add Collection"),
            OptionMenuDescription(
                "Remove Current Collection",
                clicked_fn=self._on_remove_collection,
                enabled_fn=self._is_remove_collection_enabled,
            ),
        ]

    def destroy(self) -> None:
        """Destroys the options menu by setting the _options_menu reference to None."""
        self._options_menu = None

    def bind_browser_widget(self, browser_widget: BrowserWidget) -> None:
        """Bind browser widget used for search bar. Browser widget is created later, so need to bind it later.

        Args:
            browser_widget (BrowserWidget): Browser widget used for search bar.
        """
        self._browser_widget = browser_widget

    def set_add_collection_fn(self, on_add_collection_fn: Callable[[], None]) -> None:
        """
        Set function called when menu item "Add Collection" clicked.
        Args:
            on_add_collection_fn (callable): Function called when menu item "Add Collection" clicked. Function signature: void on_add_collection_fn()
        """
        self._menu_descs[0].clicked_fn = on_add_collection_fn

    def append_menu_item(self, desc: OptionMenuDescription) -> None:
        """Append a menu item to the options menu and refresh the menu if already created.

        Args:
            desc (OptionMenuDescription): Menu item description to append.
        """
        self._menu_descs.append(desc)
        if self._options_menu:
            self._options_menu = None

    def show(self) -> None:
        """
        Show options menu.
        """
        if self._options_menu is None:
            self._options_menu = ui.Menu(f"Browser Options Menu##{hash(self)}", menu_compatibility=False)
            with self._options_menu:
                for desc in self._menu_descs:
                    if desc.visible_fn is not None:
                        if not desc.visible_fn():
                            continue
                    if desc.name == "":
                        ui.Separator(menu_compatibility=False)
                    else:
                        self._menu_items[desc] = ui.MenuItem(desc.name, triggered_fn=desc.clicked_fn)

        for desc in self._menu_items:
            if desc.clicked_fn is None:
                self._menu_items[desc].enabled = False
            elif desc.enabled_fn is not None:
                self._menu_items[desc].enabled = desc.enabled_fn()
            else:
                self._menu_items[desc].enabled = True
            if desc.get_text_fn is not None:
                self._menu_items[desc].text = desc.get_text_fn()
        for desc in self._menu_items:
            if desc.visible_fn is not None:
                self._menu_items[desc].visible = desc.visible_fn()

        self._options_menu.show()

    def _on_add_collection(self) -> None:
        """
        Function called when "Add Collection" menu item in options menu clicked
        """
        if self._on_add_collection_fn is not None:
            self._on_add_collection_fn()

    def _on_remove_collection(self) -> None:
        if self._browser_widget is None or self._browser_widget.collection_index < 0:
            return
        else:
            browser_model = self._browser_widget.model
            collection_items = browser_model.get_collection_items()
            if browser_model.remove_collection(collection_items[self._browser_widget.collection_index]):
                # Update collection combobox and default none selected
                browser_model._item_changed(None)
                self._browser_widget.collection_index = -1

    def _is_remove_collection_enabled(self) -> None:
        if self._browser_widget is not None:
            return self._browser_widget.collection_index >= 0
        else:
            return False


class BrowserSearchBar:
    """
    Represent a search bar for browser widget.
    Keyword args:
        enable_navigation_visibility (bool): True to show navigation butoon, False to hide. Default True.
        options_menu (Optional[OptionsMenu]): Options menu displayed when option button clicked. If None, no option button displayed. Default is standard options menu.
        style (Dict): Extra ui style for search bar. Default is empty.
        subscribe_edit_changed (bool): Default True to search when input changed. False only search when input ended.
    """

    def __init__(
        self,
        enable_navigation_visibility: bool = True,
        options_menu: Optional[OptionsMenu] = OptionsMenu(),
        style={},
        subscribe_edit_changed=True,
    ):
        self._enable_navigation_visibility = enable_navigation_visibility
        self._options_menu = options_menu
        self._extra_ui_style = style
        self._subscribe_edit_changed = subscribe_edit_changed

        self._browser_widget: Optional(BrowserWidget) = None
        self._show_navigation_button: Optional(ui.Button) = None
        self._options_button: Optional(ui.Button) = None
        self._navigation_visible = True
        self._on_search_fns: List[callable] = []

        self._build_ui()

    @property
    def width(self) -> ui.Length:
        """Width of search bar"""
        return self._frame.width

    @width.setter
    def width(self, value: ui.Length) -> None:
        """Sets the width of the search bar.

        Args:
            value (ui.Length): New width to set for the search bar.
        """
        self._frame.width = value

    @property
    def navigation_button(self) -> ui.Button:
        """Gets the navigation button of the search bar.

        Returns:
            ui.Button: Navigation button widget.
        """
        return self._show_navigation_button

    def destroy(self) -> None:
        """
        Clean up
        """
        if self._options_menu is not None:
            self._options_menu.destroy()
            self._options_menu = None
        self._search_field.destroy()

    def bind_browser_widget(self, browser_widget: BrowserWidget) -> None:
        """Bind browser widget used for search bar. Browser widget is created after search bar, so need to bind it later.

        Args:
            browser_widget (BrowserWidget): Browser widget used for search bar.
        """
        self._browser_widget = browser_widget
        if self._options_menu is not None:
            self._options_menu.bind_browser_widget(browser_widget)

    def set_navigation_clicked_fn(self, on_clicked_fn: Optional[callable]):
        """
        Change click callback for navigation button.
        Args:
            on_clicked_fn (Optional[callable]): Function called when naviagation button clicked. None to set to default callback. Otherwise change to new callback. Function signure: void on_clicked_fn()
        """
        if on_clicked_fn is not None:
            self._show_navigation_button.set_clicked_fn(on_clicked_fn)
        else:
            self._show_navigation_button.set_clicked_fn(self._trigger_show_navigation)

    def add_on_search_fn(self, on_search_fn: Callable[[Optional[List[str]]], None]) -> None:
        """
        Add extra function called when searching.
        Args:
            on_search_fn (callable): Function called when searching. Function signature: void on_search_fn(Optional[List[str]])
        """
        if on_search_fn not in self._on_search_fns:
            self._on_search_fns.append(on_search_fn)

    def remove_on_search_fn(self, on_search_fn: callable) -> bool:
        """Remove extra function called when searching.

        Args:
            on_search_fn (callable): Function called when searching.

        Returns:
            bool: True if the function was found and removed, False otherwise.
        """
        if on_search_fn in self._on_search_fns:
            self._on_search_fns.remove(on_search_fn)
            return True
        else:
            return False

    def clear_search(self):
        """Clears the current search input in the search field."""
        self._search_field.clear()

    def _build_ui(self):
        self._frame = ui.Frame(style=UI_STYLES)
        with self._frame:
            with ui.HStack(spacing=4, height=0, style=self._extra_ui_style):

                if self._enable_navigation_visibility:
                    with ui.VStack(width=26):
                        ui.Spacer()
                        self._show_navigation_button = ui.Button(
                            image_width=20,
                            image_height=20,
                            width=26,
                            height=26,
                            spacing=2,
                            selected=self._navigation_visible,
                            name="navigation",
                            clicked_fn=self._trigger_show_navigation,
                            style_type_name_override="SearchBar.Button",
                        )
                        ui.Spacer()

                self._search_field = SearchField(
                    on_search_fn=self._on_search,
                    subscribe_edit_changed=self._subscribe_edit_changed,
                    style=self._extra_ui_style,
                )
                if self._options_menu:
                    with ui.VStack(width=26):
                        ui.Spacer()
                        self._options_button = ui.Button(
                            image_width=20,
                            image_height=20,
                            width=26,
                            height=26,
                            name="options",
                            clicked_fn=self._trigger_options_menu,
                            style_type_name_override="SearchBar.Button",
                        )
                        ui.Spacer()

    def _trigger_show_navigation(self) -> None:
        self._navigation_visible = not self._navigation_visible
        self._show_navigation_button.selected = self._navigation_visible
        if self._browser_widget is not None:
            self._browser_widget.show_widgets(collection=self._navigation_visible, category=self._navigation_visible)

    def _trigger_options_menu(self) -> None:
        if self._options_menu is not None:
            self._options_menu.show()

    def _on_search(self, search_words: Optional[List[str]]) -> None:
        if self._browser_widget:
            # Filter detail items
            self._browser_widget.filter_details(search_words)

        for fn in self._on_search_fns:
            fn(search_words)
