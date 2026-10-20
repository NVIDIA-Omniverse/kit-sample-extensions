# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
__all__ = ["GraphEditorCoreCatalog"]


from typing import Callable, List, Optional

import omni.ui as ui
from omni.kit.widget.searchfield import SearchField

from .graph_editor_core_tree_delegate import GraphEditorCoreTreeDelegate


class GraphEditorCoreCatalog:
    """The common widget for Graph extensions"""

    def __init__(
        self,
        model: ui.AbstractItemModel,
        delegate: ui.AbstractItemDelegate = None,
        on_context_menu_fn: Optional[Callable[[List[ui.AbstractItem]], None]] = None,
        **kwargs,
    ):
        self.__model = model

        if delegate:
            self.__delegate = delegate
            self.__delegate_created = False
        else:
            self.__delegate = GraphEditorCoreTreeDelegate()
            self.__delegate_created = True

        self.__delegate.set_on_expand_fn(self.__on_expansion)

        self._tree_view = None
        self.__search_field = None

        self.__search_field_style = kwargs.pop("search_field_style", None)

        self.__filter_subscription = None

        self.__on_context_menu_fn: Optional[Callable[[List[ui.AbstractItem]], None]] = on_context_menu_fn

        self.__frame = ui.Frame(**kwargs)
        self.__frame.set_build_fn(self._on_build)

    def destroy(self):
        self.__frame = None

        self.__on_context_menu_fn = None

        self.__filter_subscription = None

        if self.__search_field:
            self.__search_field.destroy()
        self.__search_field = None

        self._tree_view = None

        if self.__delegate_created and self.__delegate:
            self.__delegate.destroy()
        self.__delegate = None

        self.__model = None

    def __on_expansion(self, item, expanded):
        if not self._tree_view:
            return
        self._tree_view.set_expanded(item, expanded, False)

    def __filter_by_text(self, filter_name_text: str):
        """Called when the user changes the search field"""
        self._tree_view.keep_expanded = not not filter_name_text
        self.__delegate.filter_by_text(filter_name_text)
        self.__model.filter_by_text(filter_name_text)

    def __on_mouse_pressed(self, x, y, button, modifier):
        """Called by TreeView when mouse pressed"""
        if not self.__on_context_menu_fn or not self._tree_view or not self.__model or button != 1:
            return

        # Context menu
        selection = [i for i in self._tree_view.selection if not self.__model.can_item_have_children(i)]
        self.__on_context_menu_fn(selection)

    def _on_build(self):
        """Create a pannel used to create new nodes"""
        with ui.HStack():
            with ui.VStack():
                # Area with the search filed
                self.__search_field = SearchField(show_tokens=False, style=self.__search_field_style)

                # List Widget (on the bottom)
                with ui.ScrollingFrame(
                    horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                    vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                    style_type_name_override="TreeView",
                ):
                    self._tree_view = ui.TreeView(
                        self.__model,
                        delegate=self.__delegate,
                        root_visible=False,
                        header_visible=False,
                        mouse_pressed_fn=self.__on_mouse_pressed,
                    )

            ui.Spacer(width=10)

        # The filtering logic
        # SearchField doesn't have a way to callback in the middle of the
        # editing on_search_fn is executed when the user pressed enter. So we
        # use the model directly.
        field_model = self.__search_field._search_field.model
        self.__filter_subscription = field_model.subscribe_value_changed_fn(
            lambda m: self.__filter_by_text(m.as_string)
        )
