# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from functools import partial
from typing import Callable, Dict, Optional

from omni import ui

from ..models import AbstractBrowserModel, DetailItem


class DetailDelegate(ui.AbstractItemDelegate):
    """
    Delegate to represent detail item.
    Keyword Args:
        model: Browser model. Used to execute detail item when double click. Default is None.
    Overridden functions:
        str get_thumbnail(item: DetailItem): Function returns thumbnail url when the delegate asks it. Default using thumbnail defined in detail item.
        str get_label(item: DetailItem): Function returns label string when the delegate asks it. Default using name defined in detail item. Label will be invisible if returns None.
        int get_label_height(item: DetailItem): Function return label height when display item label. Default is 20.
        str get_tooltip(item: DetailItem): Function returns tooltip string when the detail delegate asks it.
        void on_click(item: DetailItem): Function called when clicked on the detail delegate.
        void on_right_click(item: DetailItem): Function called when right clicked on the detail delegate.
        void on_double_click(item: DetailItem) Function called when double clicked on the detail delegate. Default to execute the detail item.
        str on_drag(item: DetailItem): Function called when dragging the detail delegate.
        void build_thumbnail(item: DetailItem): Function called when drarwing thumbnail
    """

    def __init__(self, model: AbstractBrowserModel = None):
        super().__init__()

        self._model = model
        self._cached_label_widgets: Dict[DetailItem, ui.Label] = {}
        self._cached_thumbnail_widgets: Dict[DetailItem, ui.Image] = {}
        self._current_model = None
        self.thumbnail_size: int = 0
        self.__on_drag_fn: Callable[[DetailItem], str] = None

    def destroy(self):
        """
        Clean up.
        """
        self._clean_cached_widgets()

    def set_drag_fn(self, drag_fn: Callable[[DetailItem], str]) -> None:
        """Set the drag function for the detail delegate.

        Args:
          drag_fn (Callable[[DetailItem], str]): drag function to handle drag action.
        """
        self.__on_drag_fn = drag_fn

    def build_branch(
        self, model: ui.AbstractItemModel, item: DetailItem, column_id: int = 0, level: int = 0, expanded: bool = False
    ):
        """Create a branch widget that opens or closes subtree.

        Args:
          model (AbstractItemModel): Detail data model.
          item (CategoryItem): Detail item.
          column_id (int): ignore.
          level (int): ignore.
          expanded (bool): ignore.
        """
        pass

    def build_widget(
        self, model: ui.AbstractItemModel, item: DetailItem, index: int = 0, level: int = 0, expand: bool = False
    ):
        """
        Create a widget per detail item
        Args:
            model (AbstractItemModel): Detail data model
            item (DetailItem): Detail item
            index (int): ignore
            level (int): ignore
            expand (int): ignore
        """

        def on_image_progress(loading_image: ui.Image, thumbnail_image: ui.Image, progress: float):
            """Called when the image loading progress is changed."""
            if progress != 1.0:
                # We only need to catch the moment when the image is loaded.
                return

            # Hide the loading_image at the back.
            loading_image.visible = False

            # Remove the callback to avoid circular references.
            if hasattr(thumbnail_image, "set_progress_changed_fn"):
                thumbnail_image.set_progress_changed_fn(None)

        if model != self._current_model:
            # Model changed, clean up cached widgets
            self._clean_cached_widgets()
            self._current_model = model
        else:
            if item in self._cached_label_widgets:
                self._cached_label_widgets[item] = None
            if item in self._cached_thumbnail_widgets:
                self._cached_thumbnail_widgets[item] = None

        stack = ui.ZStack(
            mouse_pressed_fn=lambda x, y, btn, flag, item=item: self._on_mouse_pressed(btn, item),
            mouse_double_clicked_fn=lambda x, y, btn, flag, item=item: self._on_mouse_double_clicked(btn, item),
            mouse_hovered_fn=lambda hovered, item=item: self.on_hover(item, hovered),
        )
        with stack:
            with ui.VStack():
                with ui.ZStack():
                    # when the thumbnail is loading, show a placeholder image first
                    with ui.HStack():
                        ui.Spacer()
                        loading_image = ui.Image(
                            width=ui.Percent(70), style_type_name_override="GridView.Image.Placeholder"
                        )
                        ui.Spacer()
                    thumbnail_image = self.build_thumbnail(item)
                    if hasattr(thumbnail_image, "set_progress_changed_fn"):
                        thumbnail_image.set_progress_changed_fn(
                            partial(on_image_progress, loading_image, thumbnail_image)
                        )
                    self._cached_thumbnail_widgets[item] = thumbnail_image

                self._cached_label_widgets[item] = self._build_label(item)

        if self.__on_drag_fn:
            stack.set_drag_fn(lambda item=item: self.__on_drag_fn(item))
        else:
            stack.set_drag_fn(lambda item=item: self.on_drag(item))
        # OM-34642: disable tooltips now due to OM-32537
        """
        tooltip = self.get_tooltip(item)
        if tooltip is not None:
            stack.set_tooltip(tooltip)
        """

    def item_changed(self, model: ui.AbstractItemModel, item: Optional[DetailItem]) -> None:
        """
        Update the widget when detail item changed.
        Now will update detail lable text and thumbail url.
        Args:
            model (AbstractItemModel): Detail data model. Ignored now.
            item (DetailItem): Detail item. None to change all items.
        """
        if item is None:
            for item in self._cached_label_widgets:
                self._single_item_changed(item)
        elif item in self._cached_label_widgets:
            self._single_item_changed(item)

    def get_thumbnail(self, item: DetailItem) -> Optional[str]:
        """Returns thumbnail of detail item when the delegate asks it.
        Returns None means do not display thumbnail.
        Default using thumbnail defined in detail item.

        Args:
          item (DetailItem): detail item to display.

        Returns:
          Optional[str]: Thumbnail url or None.
        """
        return item.thumbnail

    def get_label(self, item: DetailItem) -> Optional[str]:
        """Returns label string of detail item when the delegate asks it.
        Returns None means do not display label.
        Default using item name.

        Args:
          item (DetailItem): detail item to display.

        Returns:
          Optional[str]: Label text or None.
        """
        return item.name

    def get_label_height(self) -> int:
        """Return label height for detail items.

        Returns:
          int: Label height in pixels.
        """
        return 20

    def get_tooltip(self, item: DetailItem) -> Optional[str]:
        """Returns tooltip of detail item when the delegate asks it.
        Returns None means do not display tooltip.
        Default is None.

        Args:
          item (DetailItem): detail item to display.

        Returns:
          Optional[str]: Tooltip text or None.
        """
        return None

    def on_hover(self, item: DetailItem, hovered: bool) -> None:
        """
        Function called when hovering on the detail delegate.
        Args:
            item (DetailItem): detail item to display
            hovered (bool): hovered not not
        """
        return

    def on_click(self, item: DetailItem) -> None:
        """
        Function called when clicking on the detail delegate.
        Args:
            item (DetailItem): detail item to display
        """
        return

    def on_right_click(self, item: DetailItem) -> None:
        """
        Function called when right clicking on the detail delegate.
        Args:
            item (DetailItem): detail item to display
        """
        return

    def on_double_click(self, item: DetailItem) -> None:
        """
        Function called when double clicking on the detail delegate.
        Default to execute this item
        Args:
            item (DetailItem): detail item to display
        """
        if self._model is not None:
            # Execute the detail item
            self._model.execute(item)

    def on_drag(self, item: DetailItem) -> str:
        """Function called when dragging on the detail delegate. Used to create widgets for dragged item.

        Args:
          item (DetailItem): detail item to display.

        Returns:
          str: Drag string for detail item.
        """
        return ""

    def on_multiple_drag(self, item: DetailItem) -> str:
        """Function called when dragging on the detail delegate with other items. Default same as on_drag.

        Args:
          item (DetailItem): detail item to display.

        Returns:
          str: Drag string for detail item.
        """
        return self.on_drag(item)

    def build_thumbnail(self, item: DetailItem) -> Optional[ui.Image]:
        """Display thumbnail per detail item.

        Args:
          item (DetailItem): detail item to display.

        Returns:
          Optional[ui.Image]: Image widget for detail item thumbnail.
        """
        thumbnail = self.get_thumbnail(item)

        # Always create a image to change source url later
        return ui.Image(thumbnail or "", fill_policy=ui.FillPolicy.STRETCH, style_type_name_override="GridView.Image")

    def _build_label(self, item: DetailItem) -> ui.Label:
        """
        Display label per detail item
        Args:
            item (DetailItem): detail item to display
        """

        # Always create a label to change the text later
        label = self.get_label(item)

        widget = ui.Label(
            label or "",
            height=self.get_label_height(),
            word_wrap=True,
            elided_text=True,
            skip_draw_when_clipped=True,
            alignment=ui.Alignment.CENTER_TOP,
            style_type_name_override="GridView.Item",
        )
        if label is None:
            widget.visible = False
        return widget

    def _on_mouse_pressed(self, btn: int, item: DetailItem) -> None:
        if btn == 0:
            self.on_click(item)
        elif btn == 1:
            self.on_right_click(item)

    def _on_mouse_double_clicked(self, btn: int, item: DetailItem) -> None:
        if btn == 0:
            self.on_double_click(item)

    def _single_item_changed(self, item: DetailItem):
        # Set label visible
        if self._cached_label_widgets[item] is not None:
            new_label = self.get_label(item)
            if self._cached_label_widgets[item].text != new_label:
                self._cached_label_widgets[item].visible = new_label is not None
                self._cached_label_widgets[item].text = new_label or ""
            self._cached_label_widgets[item].height = ui.Pixel(self.get_label_height())

        # Update thumbnail
        if self._cached_thumbnail_widgets[item] is not None:
            new_thumbnail = self.get_thumbnail(item)
            if self._cached_thumbnail_widgets[item].source_url != new_thumbnail and new_thumbnail:
                self._cached_thumbnail_widgets[item].source_url = new_thumbnail

    def _clean_cached_widgets(self):
        for item in self._cached_label_widgets:
            self._cached_label_widgets[item] = None
        self._cached_label_widgets = {}
        for item in self._cached_thumbnail_widgets:
            self._cached_thumbnail_widgets[item] = None
        self._cached_thumbnail_widgets = {}
