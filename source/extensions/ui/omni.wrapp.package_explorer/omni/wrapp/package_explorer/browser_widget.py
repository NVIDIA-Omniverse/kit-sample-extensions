# Copyright (c) 2023-2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

import functools
import os
from typing import List, Optional

import carb
import omni.client as omni_client
import omni.kit.app
import omni.ui as ui
from omni.kit.browser.folder.core import FolderCategoryItem
from omni.kit.widget.searchfield import SearchField
from omni.kit.widget.zoombar import ZoomBar

from .browser_delegate import DetailListViewDelegate
from .browser_model import DetailListViewModel
from .browser_with_property_widget import BrowserWithPropertyWidget
from .category_delegate import WrappPackageCategoryDelegate
from .context_menu import ContextMenu
from .search_bar import WrappBrowserSearchBar
from .settings_dialog import SettingsDialog
from .style import ICON_PATH
from .utils import (
    REFRESH_ANIMATION_TIMEOUT,
    call_async,
    get_default_wrapp_repo_config_url_for_stage,
    get_settings_dialog,
    get_wrapp_repo_config_url_for_stage,
    load_asset_repos_from_wrapp_config,
    save_asset_repos_to_wrapp_config,
    wrapp_scheduler_context,
)

# Threshold below which to switch from grid view to list view (in pixels)
LIST_VIEW_THRESHOLD = 64


class WrappBrowserWidget(BrowserWithPropertyWidget):
    def __init__(self, *args, **kwargs):
        kwargs["category_delegate"] = kwargs.pop("category_delegate", None) or WrappPackageCategoryDelegate()
        self._keep_search_words = True
        self._show_grid_view = True
        self._list_view_container: Optional[ui.Frame] = None
        self._list_view_frame: Optional[ui.Frame] = None
        self._list_view: Optional[ui.TreeView] = None
        self._list_view_zoom_overlay: Optional[ui.VStack] = None
        self._list_view_zoom_bar = None
        self._list_view_model: Optional[DetailListViewModel] = None
        self._list_view_delegate: Optional[DetailListViewDelegate] = None
        self._thumbnail_size_sub_id: Optional[int] = None
        self._list_view_selections: List = []  # Track selections in list view
        self._loading_overlay: Optional[ui.ZStack] = None
        self._loading_transform: Optional[ui.scene.Transform] = None
        self._loading_future = None
        self._keep_loading_animation = False
        super().__init__(*args, multiple_drag=True, **kwargs)

    @property
    def search_field(self) -> SearchField:
        return self._search_bar._search_field

    @property
    def category_all(self) -> FolderCategoryItem:
        return self._browser_model.get_item_children(self._browser_model._root_collection_item)[0]

    @property
    def browser_widget_model(self):
        return self._browser_widget.model

    def refresh(self):
        """Refresh the browser."""
        self.model.register_to_workspace()
        self.model.refresh_asset_folders(use_cache=False)

    def open_settings(self):
        """Handle add/remove/edit a new WRAPP repository."""

        def on_save_settings(repo_config_url: str, dialog: SettingsDialog):
            call_async(on_save_settings_async(repo_config_url, dialog))

        async def on_save_settings_async(repo_config_url: str, dialog: SettingsDialog):
            await save_asset_repos_to_wrapp_config(repo_config_url, dialog.asset_repos)
            try:
                from omni.cip.workspace import ProjectModel

                async with wrapp_scheduler_context(message="Reloading workspace from settings...") as scheduler:
                    await ProjectModel().load_workspace(
                        scheduler, os.path.dirname(omni_client.normalize_url(repo_config_url))
                    )
            except Exception:
                await self.browser_widget_model.refresh_asset_folders_async(wrapp_repo_config=repo_config_url)
            dialog.hide()

        async def open_settings_dialog():
            default_repo_config_url = get_default_wrapp_repo_config_url_for_stage()
            if not default_repo_config_url:
                carb.log_error(
                    "No wrapp repo config found for in-memory stage. Save your stage first to create a new one."
                )
                return

            repo_config_url = await get_wrapp_repo_config_url_for_stage()
            # If no repo config url, create a new one
            if not repo_config_url:
                # Create a new wrapp repo config file
                repo_config_url = await save_asset_repos_to_wrapp_config(default_repo_config_url)

            asset_repos = {}
            async for repo_name, asset_repo in load_asset_repos_from_wrapp_config(repo_config_url):
                asset_repos[repo_name] = asset_repo

            settings_dialog = get_settings_dialog(
                click_okay_handler=functools.partial(on_save_settings, repo_config_url),
                click_cancel_handler=lambda dialog: dialog.hide(),
                asset_repos=asset_repos,
            )
            settings_dialog.show()

        call_async(open_settings_dialog())

    def _build_search_bar(self):
        # Hide gear button in search bar
        self._search_bar = WrappBrowserSearchBar(
            style=self._extra_ui_style,
            refresh_browser_fn=self.refresh,
            open_settings_fn=self.open_settings,
            browser_widget=self,
        )

    def _build_browser_widget(self):
        # Create a ZStack wrapper to layer the loading overlay on top of the browser
        self._browser_wrapper = ui.ZStack()
        with self._browser_wrapper:
            # Build the original browser widget
            super()._build_browser_widget()

            # Build list view for small thumbnail sizes
            self._build_list_view()

            # Build loading overlay on top
            self._build_loading_overlay()

        # Here hack the filter function to remove category labels before filter
        self._browser_widget.filter_details = self._filter_details

        # Set up mouse hover tracking on the category view frame.
        # We only update the search words when user is hovering over the category view -
        # Real person is clicking on the category view, not refreshing the folders.
        if hasattr(self._browser_widget, "_category_frame"):
            self._browser_widget._category_frame.set_mouse_hovered_fn(self._on_category_view_hovered)

        # Subscribe to thumbnail size changes
        self._thumbnail_size_sub_id = self._browser_widget.add_thumbnail_size_changed_fn(
            self._on_thumbnail_size_changed
        )

        # Connect to model's refresh callback
        if hasattr(self, "_browser_model"):
            self._browser_model.set_start_refreshing_callback_fn(self._start_loading_animation, "browser_refresh")

    def _build_list_view(self):
        """Build a list view widget to display items when thumbnail size is too small."""
        if not hasattr(self._browser_widget, "_detail_container"):
            return

        # Create list view model and delegate
        self._list_view_model = DetailListViewModel()

        # Get the detail delegate to reuse its thumbnail provider
        detail_delegate = None
        if hasattr(self._browser_widget, "_detail_kwargs"):
            detail_delegate = self._browser_widget._detail_kwargs.get("delegate")

        # Get browser model for drag-and-drop support
        browser_model = self.browser_widget_model if hasattr(self._browser_widget, "model") else None
        self._list_view_delegate = DetailListViewDelegate(detail_delegate, browser_model)

        # Create list view inside the detail container
        with self._browser_widget._detail_container:
            self._list_view_container = ui.Frame(visible=False)
            with self._list_view_container:
                self._list_view_frame = ui.ScrollingFrame(
                    style_type_name_override="TreeView.Frame",
                    vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_ON,
                    horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                )
                with self._list_view_frame:
                    self._list_view = ui.TreeView(
                        self._list_view_model,
                        delegate=self._list_view_delegate,
                        root_visible=False,
                        header_visible=False,
                        style_type_name_override="TreeView",
                    )
                    self._list_view.set_selection_changed_fn(self._on_list_view_selection_changed)
                    # Set up right-click handler for context menu
                    self._list_view.set_mouse_pressed_fn(self._on_list_view_mouse_pressed)
                    # Note: drag-and-drop is handled at the widget level in DetailListViewDelegate

                    # Pass tree_view reference to delegate for custom selection handling
                    self._list_view_delegate._tree_view = self._list_view

            # Create a zoom bar overlay that is ALWAYS visible on top
            # This covers the original zoom bar, so we don't need to toggle visibility
            # and dragging across the threshold won't be interrupted
            if self._browser_widget._zoom_bar:
                self._list_view_zoom_overlay = ui.VStack()  # Always visible
                with self._list_view_zoom_overlay:
                    ui.Spacer()  # Push zoom bar to bottom
                    self._list_view_zoom_bar = ZoomBar(
                        min=self._browser_widget._min_thumbnail_size,
                        max=self._browser_widget._max_thumbnail_size,
                        value=self._browser_widget._detail_thumbnail_size,
                        icon_mode=self._show_grid_view,  # True = grid/thumbnail, False = list
                        on_value_changed_fn=self._browser_widget._BrowserWidget__on_thumbnail_size_changed,
                        on_view_mode_changed_fn=self._on_view_mode_changed,
                    )
                    ui.Spacer(height=4)

    def _build_loading_overlay(self):
        """Build a semi-transparent loading overlay with a spinning icon.

        Called from within _browser_wrapper ZStack context, so the overlay
        will appear on top of the browser widget content.
        """
        self._loading_overlay = ui.ZStack(visible=False)
        with self._loading_overlay:
            # Center container for spinner
            with ui.VStack():
                ui.Spacer()
                with ui.HStack():
                    ui.Spacer()
                    # Container for the rotating spinner icon
                    with ui.ZStack(width=32, height=32):
                        with ui.scene.SceneView(width=32, height=32).scene:
                            self._loading_transform = ui.scene.Transform()
                            with self._loading_transform:
                                ui.scene.Image(
                                    f"{ICON_PATH}/refresh.svg",
                                    width=4.5,
                                    height=4.5,
                                )
                    ui.Spacer()
                ui.Spacer()

    def _start_loading_animation(self):
        """Start the loading animation overlay."""
        self._keep_loading_animation = True
        if self._loading_future or not self._loading_overlay:
            return  # Already animating or no overlay

        self._loading_overlay.visible = True
        if self._browser_widget._detail_view:
            self._browser_widget._detail_view.visible = False
        if self._list_view:
            self._list_view.visible = False

        async def _animate_loading():
            angle = [0]
            elapsed_time = 0.0
            max_animation_time = REFRESH_ANIMATION_TIMEOUT  # Maximum animation time in seconds

            while self._keep_loading_animation:
                delta = await omni.kit.app.get_app().next_update_async()
                angle[0] -= delta * 3.0  # Rotation speed
                elapsed_time += delta

                if self._loading_transform:
                    transform = ui.scene.Matrix44.get_rotation_matrix(0, 0, angle[0])
                    self._loading_transform.transform = transform

                # Check if model has finished loading
                if hasattr(self, "_browser_model") and not self._browser_model.is_in_traversing():
                    break

                # Stop animation if max time exceeded
                if elapsed_time >= max_animation_time:
                    break

            self._stop_loading_animation()

        self._loading_future = call_async(_animate_loading())

    def _stop_loading_animation(self):
        """Stop the loading animation overlay."""
        self._keep_loading_animation = False
        self._loading_future = None

        if self._loading_overlay:
            self._loading_overlay.visible = False

        if self._browser_widget._detail_view:
            self._browser_widget._detail_view.visible = True
        if self._list_view:
            self._list_view.visible = True

        # Reset rotation to identity
        if self._loading_transform:
            self._loading_transform.transform = ui.scene.Matrix44.get_rotation_matrix(0, 0, 0)

    def _on_list_view_selection_changed(self, selections):
        """Handle selection changes in the list view.

        Instead of syncing to the grid view directly (which can cause KeyError
        when the grid view's delegates don't contain the item), we:
        1. Store the selection for later when switching back to grid view
        2. Trigger the detail selection changed callback for property view updates
        """
        self._list_view_selections = selections or []

        # Trigger the property view update through the detail selection changed callback
        if hasattr(self, "_on_detail_selection_changed") and selections:
            self._on_detail_selection_changed(selections)

    def _on_list_view_mouse_pressed(self, x, y, button, modifier):
        """Handle mouse press on list view for right-click context menu."""
        if button == 1:  # Right mouse button
            if self._list_view_selections:
                if not hasattr(self, "_list_view_context_menu") or self._list_view_context_menu is None:
                    self._list_view_context_menu = ContextMenu()
                self._list_view_context_menu.show_item(self._list_view_selections[0])

    def _on_view_mode_changed(self, icon_mode: bool) -> None:
        """Handle view mode toggle button click.

        Args:
            icon_mode: True for grid/thumbnail view, False for list view.
        """
        self._show_grid_view = icon_mode
        self._toggle_view_mode(icon_mode)

    def _on_thumbnail_size_changed(self, thumbnail_size: int) -> None:
        """
        Handle thumbnail size changes. When thumbnail size is too small,
        switch from grid view to list view for better readability.

        Args:
            thumbnail_size: The new thumbnail size in pixels.
        """
        if self._list_view_container is None:
            return

        should_show_grid = thumbnail_size >= LIST_VIEW_THRESHOLD

        if should_show_grid != self._show_grid_view:
            self._show_grid_view = should_show_grid
            self._toggle_view_mode(should_show_grid)

    def _toggle_view_mode(self, show_grid: bool) -> None:
        """
        Toggle between grid view (ThumbnailView) and list view.

        Args:
            show_grid: If True, show grid view; otherwise show list view.
        """
        if not hasattr(self._browser_widget, "_detail_scrolling_frame"):
            return

        if show_grid:
            # Show grid view, hide list view
            self._browser_widget._detail_scrolling_frame.visible = True
            self._list_view_container.visible = False

            # Restore selection to grid view if we have list view selections
            if self._list_view_selections and self._browser_widget._detail_view:
                try:
                    # Only set selection for items that exist in the grid view's delegates
                    detail_view = self._browser_widget._detail_view
                    valid_selections = [item for item in self._list_view_selections if item in detail_view._delegates]
                    if valid_selections:
                        detail_view.selection = valid_selections
                except Exception:
                    pass  # Ignore selection restore errors
        else:
            # Hide grid view, show list view
            self._browser_widget._detail_scrolling_frame.visible = False
            self._list_view_container.visible = True

            # Save current grid view selection before switching
            if self._browser_widget._detail_view is not None:
                grid_selections = self._browser_widget._detail_view.selection
                if grid_selections:
                    self._list_view_selections = grid_selections

            # Update list view with current items (with delay to ensure model sync)
            async def _delay_update_and_select():
                await omni.kit.app.get_app().next_update_async()
                self._update_list_view_items()
                # Restore selection in list view
                if self._list_view_selections and self._list_view:
                    try:
                        self._list_view.selection = self._list_view_selections
                    except Exception:
                        pass  # Ignore selection restore errors

            call_async(_delay_update_and_select())

    def _update_list_view_items(self) -> None:
        """Update the list view with items from the current detail view."""
        if not self._list_view_model or not self._browser_widget._detail_view:
            return

        detail_view = self._browser_widget._detail_view
        detail_model = detail_view.model

        if not detail_model:
            self._list_view_model.set_items([])
            return

        # Get items directly from the model (not from _delegates which may be stale)
        all_items = detail_model.get_item_children(None) or []

        # Apply filter if there are filter words
        filter_words = detail_view._filter_words
        visible_items = []
        for item in all_items:
            # Check if item passes filter
            if filter_words:
                if hasattr(item, "filter") and not item.filter(filter_words):
                    continue
            visible_items.append(item)

        self._list_view_model.set_items(visible_items)

    def _on_category_view_hovered(self, hovered: bool) -> None:
        """Handle mouse hover events on the category view."""
        self._keep_search_words = not hovered

    def _on_category_selection_changed(self, category_item: FolderCategoryItem) -> None:
        # Set search words with labels from selected category
        if category_item is None:
            return

        if self._keep_search_words:

            async def _delay_refresh_details_async():
                await omni.kit.app.get_app().next_update_async()
                self._refresh_detail_view(self.search_field.search_words)

            call_async(_delay_refresh_details_async())
        else:
            # Here user click category treeview and select a category
            self.search_field.search_words = self._get_search_words_from_category(category_item)
            self.search_field.suggestions = self._get_tags_from_category(category_item)

    def _filter_details(self, filter_words: Optional[List[str]]):
        """
        Filter detail items.
        Args:
            filter_words: A string list to filter detail items. None means filtering nothing.
        """

        async def _select_category_all_async() -> None:
            await omni.kit.app.get_app().next_update_async()
            self._keep_search_words = True
            self.category_selection = [self.category_all]

        if filter_words:
            # Check if all labels of current selected category in search words
            # If yes, keep searching in selected category
            # If no, change selected category to ALL then search
            search_labels = set([w.lower() for w in filter_words])
            selected_category = self.category_selection[0] if self.category_selection else None
            if selected_category and selected_category != self.category_all:
                selected_labels = set(l.lower() for l in self._get_search_words_from_category(selected_category))
                if not selected_labels or not selected_labels.issubset(search_labels):
                    call_async(_select_category_all_async())
                    return

            for category_item in self.category_selection:
                words = self._get_search_words_from_category(category_item)
                filter_words = [w for w in filter_words if w not in words]
        else:
            # No search words, always select ALL
            selected_category = self.category_selection[0] if self.category_selection else None
            if selected_category != self.category_all:
                call_async(_select_category_all_async())
                return

        self._refresh_detail_view(filter_words)

    def _refresh_detail_view(self, filter_words: Optional[List[str]]):

        if self._browser_widget._detail_view:
            detail_view = self._browser_widget._detail_view
            detail_view.filter(filter_words)

            # Update list view if currently visible (with delay to ensure model is updated)
            if not self._show_grid_view:

                async def _delay_update_list_view():
                    await omni.kit.app.get_app().next_update_async()
                    self._update_list_view_items()

                call_async(_delay_update_list_view())

            # Refresh suggestion words in search bar from results
            async def _refresh_suggestions_async():
                await omni.kit.app.get_app().next_update_async()
                tags = []
                count = 0
                for item in detail_view._delegates:
                    if detail_view._delegates[item].visible:
                        tags.extend(list(item.asset.tags))
                        count += 1
                tags = list(set(tags))
                tags.sort()
                self.search_field.suggestions = tags
                # TODO: Workaround for issue in omni.kit.widget.searchfield updated.
                if self.search_field._suggest_window:
                    self.search_field._suggest_window.suggestions = tags

            call_async(_refresh_suggestions_async())

    def _get_search_words_from_category(self, category_item: FolderCategoryItem) -> List[str]:
        # Get preset search words from category
        if category_item.name == self._browser_model.SUMMARY_FOLDER_NAME:
            return []
        else:
            # Use folder name (label) as preset search words
            return category_item.folder.name.split("/")

    def _get_tags_from_category(self, category_item: FolderCategoryItem) -> List[str]:
        if category_item.name == self._browser_model.SUMMARY_FOLDER_NAME:
            tags = []
            for item in self._browser_model.get_category_items(self._browser_model._root_collection_item):
                if item.name != self._browser_model.SUMMARY_FOLDER_NAME:
                    tags.extend(list(item.folder.asset_by_tags.keys()))
            tags = list(set(tags))
        else:
            tags = list(category_item.folder.asset_by_tags.keys())
        tags.sort()
        return tags

    def destroy(self):
        """Clean up resources when widget is destroyed."""
        # Stop any ongoing loading animation
        if self._loading_future:
            self._keep_loading_animation = False
            self._loading_future = None

        # Unsubscribe from thumbnail size changes
        if self._thumbnail_size_sub_id is not None:
            self._browser_widget.remove_thumbnail_size_changed_fn(self._thumbnail_size_sub_id)
            self._thumbnail_size_sub_id = None

        # Clear references
        self._loading_overlay = None
        self._loading_transform = None
        self._list_view = None
        self._list_view_model = None
        self._list_view_delegate = None

        # Call parent destroy
        super().destroy()
