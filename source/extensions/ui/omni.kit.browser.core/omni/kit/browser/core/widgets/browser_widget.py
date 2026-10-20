# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from typing import Callable, Dict, List, Optional, Union

import carb
from omni import ui
from omni.kit.widget.zoombar import ZoomBar

from ..models import (
    AbstractBrowserModel,
    CategoryItem,
    ChildrenModelWrapper,
    CollectionItem,
    CollectionModelWrapper,
    DetailItem,
    SingleLevelWrapper,
)
from .category_delegate import CategoryDelegate
from .category_view import CategoryView
from .detail_delegate import DetailDelegate
from .overview_view import OverviewView
from .style import DETAIL_VIEW_PADDING, UI_STYLES
from .thumbnail_view import ThumbnailView


class BrowserWidget:
    """
    Represents the browser widget, including a collection combobox, a category list view, a detail grid view and a overview grid view (if required)
    Args:
        model (BrowserModel): Data model used by the widget.

    Keyword Args:
        style (dict): Extra UI style of this widget. Default is empty.
        category_delegate (CatetoryDelegate): delegate object to represent category item. Default using CategoryDelegate.
        category_width (int): width of category view, in pixel. Default 120.
        detail_delegate (DetailDelegate): delegate object to represent detail item. Default using DetailDelegate.
        min_thumbnail_size (int): min thumbnail size used in zoom bar. Default 32.
        max_thumbnail_size (int): max thumbnail size used in zoom bar. Default 512.
        detail_thumbnail_size (int): size of detail item thumbnail, in pixel. Default 128.
        thumbnail_aspect (float): Aspect ratio of thumbnail. Default 1.0 (width / height).
        extra_filter_fn (callable): Extra filter function called to filter items. Return True to show item otherwise hide.
            Default None. Function signure: bool extra_filter_fn(item: DetailItem)
        category_tree_mode (bool): Show category in tree mode or flat mode. Default flat mode (No branches).
        overview_delegate (DetailDelegate): Delegate object to represent item in overview. Default using DetailDelegate.
        overview_thumbnail_size (int): size of overview item thumbnail, in pixel. Default 192.
        overview_thumbnail_aspect (float): Aspect ratio of overview thumbnail. Default 1.0 (width / height).
        overview_thumbnail_padding_width (int): Padding in overview thumbnail width. Default 10.
        overview_thumbnail_padding_height (int): Padding in overview thumbnail height. Default 1.
        always_select_category (bool): Always select category if collect changed. Default True.
        show_category_splitter (bool): Show splitter between category and detail. Default False.
        splitter_extra_width (int): Width added to vertical splitter between category view and detail view.
        show_collection (bool): True to show collection combobox. Default True.
        on_category_selection_changed_fn (Callable[[CategoryItem], None]): Callback when category selection changed.
        multiple_drag (bool): True to allow drag multiple items. Default False.

    Properties:
        collection_index (int): index of selected collection item. Read and write.
        collection_selection (Optional[Collection]): selected collection item. Readonly.
        category_selection (List[CategoryItem]): selected category item. Readonly.
        detail_selection (List[DetailItem]): selected detail item. Readonly.
    """

    def __init__(
        self,
        model: AbstractBrowserModel,
        style={},
        category_delegate=None,
        category_width: float = 120,
        detail_delegate=None,
        min_thumbnail_size: int = 32,
        max_thumbnail_size: int = 512,
        detail_thumbnail_size: int = 128,
        thumbnail_aspect: float = 1.0,
        extra_filter_fn: callable = None,
        category_tree_mode: bool = False,
        overview_delegate=None,
        overview_thumbnail_size: int = 192,
        overview_thumbnail_aspect: float = 1.0,
        overview_thumbnail_padding_width: int = 10,
        overview_thumbnail_padding_height: int = 1,
        always_select_category: bool = True,
        show_category_splitter: bool = False,
        splitter_extra_width: int = 4,
        show_collection: bool = True,
        on_category_selection_changed_fn: Callable[[CategoryItem], None] = None,
        extra_ui_style: Dict = {},
        multiple_drag: bool = False,
    ):
        self._extra_ui_style = style
        self._category_view_width = category_width
        self._splitter_extra_width = splitter_extra_width
        self._min_thumbnail_size = min_thumbnail_size
        self._max_thumbnail_size = max_thumbnail_size if max_thumbnail_size > min_thumbnail_size else min_thumbnail_size
        self._detail_thumbnail_size = detail_thumbnail_size
        self._filter_words: Optional[List[str]] = None
        self._always_select_category = always_select_category
        self._show_category_splitter = show_category_splitter
        self._show_collection = show_collection
        self._collection_combobox: Optional[ui.ComboBox] = None
        self._on_category_selection_changed_fn = on_category_selection_changed_fn
        self._multiple_drag = multiple_drag

        # Category view kwargs
        category_delegate = category_delegate or CategoryDelegate(tree_mode=category_tree_mode)
        self._category_kwargs = {"delegate": category_delegate}

        self._models = {}
        self._model_sub_id: Dict[AbstractBrowserModel, callable] = {}
        self._build_models(model)

        # Detail view kwargs
        self._detail_kwargs = {
            "delegate": detail_delegate or DetailDelegate(self._browser_model),
            "thumbnail_size": detail_thumbnail_size,
            "thumbnail_aspect": thumbnail_aspect,
            "extra_filter_fn": extra_filter_fn,
            "multiple_drag": multiple_drag,
        }

        # Overview view kwargs
        self._overview_kwargs = {
            "delegate": overview_delegate or DetailDelegate(self._browser_model),
            "thumbnail_size": overview_thumbnail_size,
            "thumbnail_aspect": overview_thumbnail_aspect,
            "thumbnail_padding_width": overview_thumbnail_padding_width,
            "thumbnail_padding_height": overview_thumbnail_padding_height,
        }

        self._on_thumbnail_size_changed_fns: List[callable] = []
        self._on_filter_changed_fns: List[callable] = []

        self._detail_view: Optional[ThumbnailView] = None
        self._overview_view = None
        self._zoom_bar = None
        self._current_selected_item = None
        self._build_ui()

    def destroy(self):
        """Destroys widget UI components and cleans up callbacks.

        This method destroys UI components such as the zoom bar, detail view, and overview view if they exist, and clears registered callbacks.
        """
        if self._zoom_bar is not None:
            self._zoom_bar.destroy()
            self._zoom_bar = None
        for model in self._models:
            model.remove_item_changed_fn(self._models[model]["change_sub"])
        for sub_id in range(len(self._on_thumbnail_size_changed_fns)):
            self._on_thumbnail_size_changed_fns[sub_id] = None
        self._model_sub_id = None
        self._current_selected_item = None
        if self._detail_view is not None:
            self._detail_view.destroy()
        if self._overview_view is not None:
            self._overview_view.destroy()
        # Delegates that hold running work of their own - the tree delegate spins a rotation per
        # loading row - have to be told, or it outlives the widget.
        delegate = self._category_kwargs.get("delegate")
        if delegate is not None and hasattr(delegate, "destroy"):
            delegate.destroy()

    @property
    def visible(self) -> bool:
        """widget visibility"""
        return self._frame.visible

    @visible.setter
    def visible(self, value) -> None:
        """Sets widget visibility.

        Args:
            value (bool): New visibility state for the widget.
        """
        self._frame.visible = value

    @property
    def model(self) -> ui.AbstractItemModel:
        """Model used in this widget"""
        return self._browser_model

    @model.setter
    def model(self, new_model: AbstractBrowserModel) -> None:
        """Sets the widget model.

        Args:
            new_model (AbstractBrowserModel): New browser model to use and refresh widget views.
        """
        # Refresh data models
        self._build_models(new_model)

        # Refresh widget models
        if self._collection_combobox is not None:
            self._collection_combobox.model = self._collection_model
        if self._category_view is not None:
            self._category_view.model = self._category_model
        if self._detail_view is not None:
            self._detail_view.model = self._detail_model
        if self._overview_view is not None:
            self._overview_view.model = self._overview_model

        # Refresh UI
        self.collection_index = -1
        self.collection_index = 0

    @property
    def collection_index(self) -> int:
        """Gets the index of the selected collection item.

        Returns:
            int: Selected collection index.
        """
        return self._collection_model.current_index

    @collection_index.setter
    def collection_index(self, value):
        """Sets the collection index for the selected collection item.

        Args:
            value (int): New collection index.
        """
        self._collection_model.current_index = value

    @property
    def collection_selection(self) -> Optional[CollectionItem]:
        """Gets the currently selected collection item.

        Returns:
            Optional[CollectionItem]: Selected collection item, or None if no selection exists.
        """
        if self._collection_model.current_index < 0:
            return None
        else:
            collection_items = self._collection_model.get_item_children(None)
            return collection_items[self._collection_model.current_index]

    @property
    def category_selection(self) -> List[CategoryItem]:
        """Selected category items"""
        return self._category_view.selection

    @category_selection.setter
    def category_selection(self, items: List[CategoryItem]) -> None:
        """Sets the selected category items.

        Args:
            items (List[CategoryItem]): Category items to select.
        """
        self._category_view.selection = items

    @property
    def detail_selection(self) -> List[DetailItem]:
        """Selected detail items"""
        return self._detail_view.selection

    @detail_selection.setter
    def detail_selection(self, selection: List[DetailItem]) -> None:
        """Sets the selected detail items.

        Args:
            selection (List[DetailItem]): Detail items to select.
        """
        self._detail_view.selection = selection

    def add_thumbnail_size_changed_fn(self, on_thumbnail_size_changed_fn: Callable[[int], None]) -> int:
        """Adds a callback function for thumbnail size changes and returns its identifier.

        Args:
            on_thumbnail_size_changed_fn (callable): Function called when thumbnail size changes.

        Returns:
            int: Identifier for the added callback function.
        """
        self._on_thumbnail_size_changed_fns.append(on_thumbnail_size_changed_fn)
        return len(self._on_thumbnail_size_changed_fns) - 1

    def remove_thumbnail_size_changed_fn(self, sub_id: int) -> None:
        """Removes the callback function for thumbnail size changes using its function identifier.

        Args:
            sub_id (int): Identifier of the callback function to remove.
        """
        if sub_id < len(self._on_thumbnail_size_changed_fns) and sub_id >= 0:
            self._on_thumbnail_size_changed_fns[sub_id] = None

    def filter_details(self, filter_words: Optional[List[str]]):
        """Filter detail items.

        Args:
            filter_words (Optional[List[str]]): A string list to filter detail items. None means filtering nothing.
        """
        self._filter_words = filter_words
        if self._detail_view is not None:
            self._detail_view.filter(filter_words)
        if self._overview_view is not None:
            self._overview_view.filter(filter_words)

        # Notifications
        if len(self._on_filter_changed_fns) > 0:
            for fn in self._on_filter_changed_fns:
                fn(filter_words)

    def add_filter_changed_fn(self, on_filter_changed_fn: Callable[[Optional[List[str]]], None]) -> int:
        """Add callback function on filter changed. Return function id used for remove_filter_changed_fn.

        Args:
            on_filter_changed_fn (Callable[[Optional[List[str]]], None]): Function called when filter changed. Function signature: void on_filter_changed_fn(filter_words: Optional[List[str]])

        Returns:
            int: Callback function id.
        """
        self._on_filter_changed_fns.append(on_filter_changed_fn)
        return len(self._on_filter_changed_fns) - 1

    def remove_filter_changed_fn(self, sub_id: int) -> None:
        """Remove callback function on filter changed.

        Args:
            sub_id (int): Function id from add_filter_changed_fn.
        """
        if sub_id < len(self._on_filter_changed_fns) and sub_id >= 0:
            self._on_filter_changed_fns[sub_id] = None

    def refresh_details(self) -> None:
        """
        Refresh detail view for item visibilities.
        """
        self._detail_view.refresh()

    def show_widgets(
        self,
        collection: Optional[bool] = None,
        category: Optional[bool] = None,
        detail: Optional[bool] = None,
    ) -> None:
        """
        Show/Hide collection/category/detail widget.
        Args:
            collection (Optional[bool]): True to show collection combobox and False to hide. Default None means no change.
            category (Optional[bool]): True to show category view and False to hide. Default None means no change.
            detail (Optional[bool]): True to show detail view and False to hide. Default None means no change.
        """
        if collection is not None and self._collection_combobox:
            self._collection_combobox.visible = collection
        if category is not None:
            self._category_frame.visible = category
        if (self._collection_combobox and self._collection_combobox.visible) or self._category_frame.visible:
            self._navigation_container.visible = True
        else:
            self._navigation_container.visible = False

        if detail is not None:
            self._detail_container.visible = detail

    def sort_changed(self) -> None:
        """
        Notify sort changed. Refresh thumbnail view if necessary.
        """
        self._browser_model.sort_changed()
        if self._detail_view is not None:
            self._browser_model._item_changed(self._detail_view.model._root_item)
            self._detail_view.model._item_changed(None)

    def _build_models(self, model: AbstractBrowserModel) -> None:
        self._browser_model = model
        if model not in self._models:
            self._models[model] = {
                "change_sub": self._browser_model.add_item_changed_fn(
                    lambda model, item: self._on_model_item_changed(item)
                ),
                "collection": CollectionModelWrapper(self._browser_model, None),
                "category": SingleLevelWrapper(),
                "detail": SingleLevelWrapper(),
                "overview": ChildrenModelWrapper(),
            }
            self._models[model]["collection"].add_selection_changed_fn(self._on_collection_selected)

        self._collection_model = self._models[model]["collection"]
        self._category_model = self._models[model]["category"]
        self._detail_model = self._models[model]["detail"]
        self._overview_model = self._models[model]["overview"]

    def _build_ui(self) -> None:
        self._frame = ui.Frame(style=UI_STYLES)
        with self._frame:
            with ui.HStack(style=self._extra_ui_style, spacing=self._splitter_extra_width):
                self._build_left_panel()
                self._build_right_panel()

    def _build_left_panel(self):
        self._navigation_container = ui.ZStack(width=0)
        with self._navigation_container:
            self._category_container = ui.VStack(width=self._category_view_width, spacing=4)
            with self._category_container:
                if self._show_collection:
                    self._collection_combobox = ui.ComboBox(
                        self._collection_model, height=0, style_type_name_override="CollectionList"
                    )
                self._build_category_view()

            if self._show_category_splitter:
                self._h_splitter = ui.Placer(offset_x=self._category_view_width, draggable=True, drag_axis=ui.Axis.X)
                with self._h_splitter:
                    ui.Rectangle(width=4, style_type_name_override="Splitter")

                self._h_splitter.set_offset_x_changed_fn(self._splitter_offset_x_changed)

    def _build_right_panel(self):
        with ui.ZStack():
            self._build_detail_view()
            self._build_overview_view()

    def _build_category_view(self):
        self._category_frame = ui.ScrollingFrame(
            style_type_name_override="TreeView.Frame",
            vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
            horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
        )
        with self._category_frame:
            self._category_view = CategoryView(
                self._category_model,
                on_category_selected_fn=self._on_category_selected,
                **self._category_kwargs,
            )

    def _build_overview_view(self):
        self._overview_container = ui.ScrollingFrame(
            style_type_name_override="GridView.Frame",
            vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_ON,
            horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
        )
        with self._overview_container:
            self._overview_view = OverviewView(self._overview_model, **self._overview_kwargs)
        self._overview_container.visible = False

    def _build_detail_view(self):
        self._detail_container = ui.ZStack(spacing=10)

        # If overview enabled, only create detail view when visible
        if self._browser_model.overview_name is None:
            self._build_detail_view_internal()

    def _build_detail_view_internal(self):
        with self._detail_container:
            # Detail view
            self._detail_scrolling_frame = ui.ScrollingFrame(
                style_type_name_override="GridView.Frame",
                vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_ON,
                horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
            )
            with self._detail_scrolling_frame:
                with ui.HStack():
                    ui.Spacer(width=DETAIL_VIEW_PADDING)
                    with ui.VStack():
                        ui.Spacer(height=DETAIL_VIEW_PADDING)
                        self._detail_view = ThumbnailView(self._detail_model, **self._detail_kwargs)
                        ui.Spacer(height=DETAIL_VIEW_PADDING)
                    ui.Spacer(width=DETAIL_VIEW_PADDING)

            # Zoom bar for thunbnail size
            if self._max_thumbnail_size > self._min_thumbnail_size:
                with ui.VStack():
                    ui.Spacer()
                    self._zoom_bar = ZoomBar(
                        min=self._min_thumbnail_size,
                        max=self._max_thumbnail_size,
                        value=self._detail_thumbnail_size,
                        icon_mode=True,
                        on_value_changed_fn=self.__on_thumbnail_size_changed,
                    )
                    ui.Spacer(height=4)
            else:
                self._zoom_bar = None

    def _extra_ui_style_update(self, add_on_style: dict):
        for key, value in add_on_style.items():
            self._extra_ui_style[key].update(value)

    def _on_model_item_changed(self, item: Union[CollectionItem, CategoryItem, DetailItem]) -> None:
        if isinstance(item, CollectionItem):
            # Collection changed, update category view if necessary
            # It happens when collection refreshed
            collection_items = self._browser_model.get_item_children(None)
            if item in collection_items:
                index = collection_items.index(item)
                if index == self._collection_model.current_index:
                    # Force to refresh category view since categories refreshed
                    self._category_view.model._item_changed(None)
                    self._on_collection_selected(item)

    def _on_collection_selected(self, collection_item: CollectionItem) -> None:
        if self._category_view is None:
            return

        # Refresh category view
        if collection_item is None:
            self._category_view.model.set_sources(None, None)
            # Nothing is shown, so nothing is still working: without this the rows of the
            # collection that has just gone keep their spinners turning.
            self.__prune_category_delegate([])
            # Force to update detail view
            self._category_view.selection = []
        else:
            self._category_view.model.set_sources(self._browser_model, collection_item)
            category_items = self._category_view.model.get_item_children(None)
            # The tree has just been rebuilt, so this is where a row that has gone is known to have
            # gone. A delegate holding work per row - the tree delegate spins one per loading row -
            # has no other way to find out.
            self.__prune_category_delegate(self._live_category_items())

            if len(category_items) > 0:
                if self._always_select_category:
                    # Default select first category
                    self._category_view.selection = [category_items[0]]
            else:
                self._detail_view.model.set_sources(None, None)

    def _live_category_items(self) -> List[CategoryItem]:
        """
        Every row the tree can show, root to leaf.

        The top level alone is not the tree: a category has children, and they are rows too. Handing
        a delegate only the roots tells it every nested row has gone, and it would stop the spinner
        of one that is on screen and still scanning.

        Cheap to walk - a category item's children are a list it already holds, so nothing is built
        to answer this.
        """
        model = self._category_view.model
        live = []
        stack = list(model.get_item_children(None) or [])
        while stack:
            item = stack.pop()
            live.append(item)
            stack.extend(model.get_item_children(item) or [])
        return live

    def __prune_category_delegate(self, live_items: List[CategoryItem]) -> None:
        """Tell a category delegate which rows survived, if it keeps anything per row."""
        delegate = self._category_kwargs.get("delegate")
        if delegate is not None and hasattr(delegate, "_prune_rows"):
            delegate._prune_rows(live_items)

    def _on_category_selected(self, category_item: CategoryItem) -> None:
        if self._on_category_selection_changed_fn:
            self._on_category_selection_changed_fn(category_item)

        # Refresh detail view
        if category_item is None:
            if self._always_select_category:
                if self._current_selected_item:
                    if self.category_selection:
                        if self._current_selected_item not in self.category_selection:
                            self.category_selection = [self._current_selected_item]
                    else:
                        self.category_selection = [self._current_selected_item]
                else:
                    category_items = self._category_view.model.get_item_children(None)
                    self._category_view.selection = [category_items[0]]
            else:
                self._detail_view.model.set_sources(None, None)
        else:
            self._current_selected_item = category_item

            if self._browser_model.overview_name is None:
                self._detail_view.model.set_sources(self._browser_model, category_item)
            else:
                self._overview_container.visible = category_item.name == self._browser_model.overview_name
                if self._overview_container.visible:
                    self._overview_view.model.set_sources(self._browser_model, category_item)

                self._detail_container.visible = not self._overview_container.visible
                if self._detail_container.visible:
                    if self._detail_view is None:
                        self._build_detail_view_internal()
                        self._detail_view.filter(self._filter_words)
                    self._detail_view.model.set_sources(self._browser_model, category_item)

    def __on_thumbnail_size_changed(self, thumbnail_size: int) -> None:
        # Notifications
        if len(self._on_thumbnail_size_changed_fns) > 0:
            for fn in self._on_thumbnail_size_changed_fns:
                fn(thumbnail_size)

        # Update thumbnail size in detail view
        self._detail_view.thumbnail_size = thumbnail_size

    def _splitter_offset_x_changed(self, offset_x: ui.Length) -> None:
        self._category_container.width = offset_x
