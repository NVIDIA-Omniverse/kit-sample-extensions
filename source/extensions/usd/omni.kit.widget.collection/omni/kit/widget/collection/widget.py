# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from functools import partial

import omni.ui as ui
from omni.kit.context_menu import ContextMenuExtension
from pxr import Sdf, Tf, Usd

from .delegate import CollectionDelegate
from .icons import CollectionIcons
from .model import CollectionModel


class CollectionWidget:
    def __init__(self, stage: Usd.Stage, **kwargs):

        # `create_stage_update_node` calls `_on_attach`, and the models will be created there.
        self._stage = stage
        self._model = None
        self._tree_view = None
        self._delegate = CollectionDelegate()
        self._selection = None
        self._filter_initial_state = True
        self._collection_watch = kwargs.get("collection_watch", None)

        self.open_stage(stage)

        self._root_frame = ui.Frame(**kwargs)
        self.build_layout()

        # The filtering logic
        self._begin_filter_subscription = self._search.subscribe_begin_edit_fn(
            lambda _: CollectionWidget._set_widget_visible(self._search_label, False)
        )
        self._end_filter_subscription = self._search.subscribe_end_edit_fn(
            lambda m: self._filter_by_text(m.as_string)
            or CollectionWidget._set_widget_visible(self._search_label, not m.as_string)
        )

        # Update icons when they changed
        self._icons_subscription = CollectionIcons().subscribe_icons_changed(self.update_icons)

    def build_layout(self):
        """Creates all the widgets in the window"""
        self._menu_cache = []
        self._style = "NvidiaDark"
        style = {
            "Button.Image::filter": {"image_url": CollectionIcons().get("filter"), "color": 0xFF8A8777},
            "Button.Image::options": {"image_url": CollectionIcons().get("options"), "color": 0xFF8A8777},
            "Button.Image::visibility": {"image_url": CollectionIcons().get("eye_on"), "color": 0xFF8A8777},
            "Button.Image::visibility:checked": {"image_url": CollectionIcons().get("eye_off")},
            "Button.Image::visibility:disabled": {"color": 0x608A8777},
            "Button.Image::visibility:selected": {"color": 0xFF23211F},
            "Button::filter": {"background_color": 0x0, "margin": 0},
            "Button::options": {"background_color": 0x0, "margin": 0},
            "Button::visibility": {"background_color": 0x0, "margin": 0, "margin_width": 1},
            "Button::visibility:checked": {"background_color": 0x0},
            "Button::visibility:hovered": {"background_color": 0x0},
            "Button::visibility:pressed": {"background_color": 0x0},
            "Label::search": {"color": 0xFF808080, "margin_width": 4},
            "Menu.CheckBox": {"background_color": 0x0, "margin": 0},
            "Menu.CheckBox::drag": {
                "image_url": CollectionIcons().get("drag"),
                "color": 0xFF505050,
                "alignment": ui.Alignment.CENTER,
            },
            "Menu.CheckBox.Image": {"image_url": CollectionIcons().get("check_off"), "color": 0xFF8A8777},
            "Menu.CheckBox.Image:checked": {"image_url": CollectionIcons().get("check_on")},
            "TreeView": {
                "background_color": 0xFF23211F,
                "background_selected_color": 0x664F4D43,
                "secondary_color": 0xFF403B3B,
            },
            "TreeView.ScrollingFrame": {"background_color": 0xFF23211F},
            "TreeView.Header": {"background_color": 0xFF343432, "color": 0xFFCCCCCC, "font_size": 13.0},
            "TreeView.Header::visibility_header": {"image_url": CollectionIcons().get("eye_header")},
            "TreeView.Image::object_icon_grey": {"color": 0x80FFFFFF},
            "TreeView.Image:disabled": {"color": 0x60FFFFFF},
            "TreeView.Item": {"color": 0xFF8A8777},
            "TreeView.Item:disabled": {"color": 0x608A8777},
            "TreeView.Item::object_name_grey": {"color": 0xFF4D4B42},
            "TreeView.Item::object_name_missing": {"color": 0xFF6F72FF},
            "TreeView.Item::explicit_member": {"color": 0xFFFFFFFF},
            "TreeView.Item:selected": {"color": 0xFF23211F},
            "TreeView:selected": {"background_color": 0xFF8A8777},
        }

        with self._root_frame:
            # Options menu
            self._options_menu = ContextMenuExtension.uiMenu("Options", style=style)
            with self._options_menu:
                self._menu_cache.append(ContextMenuExtension.uiMenuItem("Reset", triggered_fn=self._on_reset))

            # # Filter menu
            self._filter_menu = ContextMenuExtension.uiMenu("Filter", style=style)
            with self._filter_menu:
                self._menu_cache.append(ContextMenuExtension.uiMenuItem("Filter", enabled=False))
                self._menu_cache.append(ui.Separator())

                self._coll1_menu = ContextMenuExtension.uiMenuItem(
                    "Prims with Collections",
                    checkable=True,
                    checked_changed_fn=lambda c: self._filter_by_api_type(Usd.CollectionAPI, c),
                    checked=self._filter_initial_state,
                )
                self._coll2_menu = ContextMenuExtension.uiMenuItem(
                    "Collections",
                    checkable=True,
                    checked_changed_fn=lambda c: self._filter_by_property_namespace("collection", c),
                    checked=self._filter_initial_state,
                )
                self._coll4_menu = ContextMenuExtension.uiMenuItem(
                    "Contents - Prims",
                    checkable=True,
                    checked_changed_fn=lambda c: self._filter_by_object_type(Usd.Prim, c),
                    checked=self._filter_initial_state,
                )
                self._coll3_menu = ContextMenuExtension.uiMenuItem(
                    "Contents - Properties",
                    checkable=True,
                    checked_changed_fn=lambda c: self._filter_by_object_type(Usd.Attribute, c),
                    checked=self._filter_initial_state,
                )
                self._coll5_menu = ContextMenuExtension.uiMenuItem(
                    "Contents - Relationships",
                    checkable=True,
                    checked_changed_fn=lambda c: self._filter_by_object_type(Usd.Relationship, c),
                    checked=self._filter_initial_state,
                )
                self._menu_cache.append(ContextMenuExtension.uiMenuItem("Clear", triggered_fn=self._clear_filter_types))
                self._menu_cache.append(
                    ContextMenuExtension.uiMenuItem("Set Default", triggered_fn=self._reset_filter_types)
                )

            with ui.VStack(style=style):
                ui.Spacer(height=4)
                with ui.ZStack(height=0):
                    with ui.HStack(spacing=4):
                        # Search filed
                        self._search = ui.StringField(name="search").model
                        # Filter button
                        ui.Button(name="filter", width=20, height=20, clicked_fn=lambda: self._filter_menu.show())
                        # Options button
                        ui.Button(name="options", width=20, height=20, clicked_fn=lambda: self._options_menu.show())
                    # The label on the top of the search field
                    self._search_label = ui.Label("Search", name="search")
                ui.Spacer(height=7)
                with ui.ScrollingFrame(
                    horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                    style_type_name_override="TreeView.ScrollingFrame",
                    # This makes the context menu show across the whole current row, not just the text
                    mouse_pressed_fn=lambda x, y, b, _: self._delegate.on_mouse_pressed(b, None, False, self),
                ):
                    with ui.ZStack():
                        self._tree_view = ui.TreeView(
                            self._model,
                            delegate=self._delegate,
                            header_visible=True,
                            root_visible=False,
                            columns_resizable=False,
                        )

    def set_selection_watch(self, selection):
        self._selection = selection
        if self._selection:
            if self._tree_view.visible:
                self._selection.set_tree_view(self._tree_view)

    def set_collection_watch(self, collection_watch):
        self._collection_watch = collection_watch

    def expand(self, path: Sdf.Path):
        """
        Set the given path expanded
        I think this is just used by unit tests?
        """
        if isinstance(path, str):
            path = Sdf.Path(path)

        if self._tree_view.visible:
            widget = self._tree_view
        else:
            return

        # Get the selected item and its parents. Expand all the parents of the new selection.
        full_chain = widget.model.find_full_chain(path.pathString)
        if full_chain:
            for item in full_chain:
                widget.set_expanded(item, True, False)

    def destroy(self):
        """
        Called by extension before destroying this object. It doesn't happen automatically.
        Without this hot reloading doesn't work.
        """
        self._begin_filter_subscription = None
        self._end_filter_subscription = None
        self._icons_subscription = None

        self._tree_view = None
        self._search_label = None

        if self._model:
            self._model.destroy()
            self._model = None
        self._delegate = None
        self._stage_subscription = None

        self._selection = None

        self._options_menu = None
        self._filter_menu = None
        self._coll1_menu = None
        self._coll2_menu = None
        self._coll3_menu = None
        self._coll4_menu = None
        self._coll5_menu = None
        self._root_frame = None

    def _clear_filter_types(self):
        self._coll1_menu.checked = False
        self._coll2_menu.checked = False
        self._coll3_menu.checked = False
        self._coll4_menu.checked = False
        self._coll5_menu.checked = False

    def _reset_filter_types(self):
        self._coll1_menu.checked = True
        self._coll2_menu.checked = True
        self._coll3_menu.checked = True
        self._coll4_menu.checked = True
        self._coll5_menu.checked = True

    def _on_reset(self):
        """Toggle "Reset" menu"""
        self._model.reset()

    def _on_show_root_changed(self, show):
        """Called to trigger "Show Root" menu item"""
        self._tree_view.root_visible = show

    @staticmethod
    def _set_widget_visible(widget: ui.Widget, visible):
        """Utility for using in lambdas"""
        widget.visible = visible

    def _filter_by_type(self, usd_types, enabled):
        """
        Set filtering by USD type.

        Args:
            usd_types: The type or the list of types it's necessary to add or remove from filters.
            enabled: True to add to filters, False to remove them from the filter list.
        """

        def _is_prim_of_type(prim_type, obj, flat):
            """
            the value of stage.GetObjectAtPath() method which is passed to this
            returns a Prim, an Object, or a Property
            """
            if not type(obj) is Usd.Prim:
                return False

            return obj.IsA(prim_type)

        if not isinstance(usd_types, list):
            usd_types = [usd_types]

        for usd_type in usd_types:
            # Create a filter
            is_prim_type_fn = partial(_is_prim_of_type, usd_type)
            name_to_fn_dict = {Tf.Type(usd_type).typeName: is_prim_type_fn}
            self._filter_by_lambda(name_to_fn_dict, enabled)

    def _filter_by_api_type(self, api_types, enabled):
        """
        Set filtering by USD api type.

        Args:
            api_types: The api type or the list of types it's necessary to add or remove from filters.
            enabled: True to add to filters, False to remove them from the filter list.
        """

        def _is_prim_of_type(api_type, obj: Usd.Object, flat: bool):
            """
            Args
                obj: the object being filtered
                flat: are we being filtered in a CollectionContentItem, ie. with flattened/no child output
            """
            if not type(obj) is Usd.Prim:
                return False
            return obj.HasAPI(api_type)

        if not isinstance(api_types, list):
            api_types = [api_types]

        for api_type in api_types:
            # Create a lambda filter
            is_prim_type_fn = partial(_is_prim_of_type, api_type)
            name_to_fn_dict = {Tf.Type(api_type).typeName: is_prim_type_fn}
            self._filter_by_lambda(name_to_fn_dict, enabled)

    def _filter_by_object_type(self, object_types, enabled):
        def _is_object_of_type(objtype, obj: Usd.Object, flat: bool):
            """
            Args
                objtype: Usd.Prim, Usd.Property etc
                obj: the object being filtered
                flat: are we being filtered in a CollectionContentItem, ie. with flattened/no child output
            """
            return flat and type(obj) is objtype

        if not isinstance(object_types, list):
            object_types = [object_types]

        for obj_type in object_types:
            is_prim_type_fn = partial(_is_object_of_type, obj_type)
            name_to_fn_dict = {str(obj_type): is_prim_type_fn}
            self._filter_by_lambda(name_to_fn_dict, enabled)

    def _filter_by_property_namespace(self, namespaces, enabled):
        """
        Filters properties by their namespace (e.g "collection:")
        """

        def _property_has_namespace(namespace: str, obj: Usd.Object, flat: bool):
            """
            Args
                obj: the object being filtered
                flat: are we being filtered in a CollectionContentItem, ie. with flattened/no child output
            """
            if not type(obj) in (Usd.Property, Usd.Attribute):
                return False
            return True

        if not isinstance(namespaces, list):
            namespaces = [namespaces]

        for namespace in namespaces:
            is_prim_type_fn = partial(_property_has_namespace, namespace)
            name_to_fn_dict = {namespace: is_prim_type_fn}
            self._filter_by_lambda(name_to_fn_dict, enabled)

    def _apply_default_filters(self):
        if not self._tree_view:
            return

        filters = {}

        # 1. Prims that have CollectionAPI applied
        def _has_collection_api(obj: Usd.Object, flat: bool):
            return type(obj) is Usd.Prim and obj.HasAPI(Usd.CollectionAPI)

        filters[Tf.Type(Usd.CollectionAPI).typeName] = _has_collection_api

        # 2. Properties that belong to the "collection" namespace
        def _property_in_collection_ns(obj: Usd.Object, flat: bool):
            return type(obj) in (Usd.Property, Usd.Attribute)

        filters["collection"] = _property_in_collection_ns

        # 3-5. Object-type filters for Prim, Attribute and Relationship when
        #      listed inside Collection contents (flat == True)
        def _is_object_of_type(objtype, obj: Usd.Object, flat: bool):
            return flat and type(obj) is objtype

        for _obj_type in (Usd.Prim, Usd.Attribute, Usd.Relationship):
            filters[str(_obj_type)] = partial(_is_object_of_type, _obj_type)

        # Delegate to the common lambda-based filtering helper – ONE call only.
        self._filter_by_lambda(filters, True)

    def _filter_by_lambda(self, filters: dict, enabled):
        """
        Set filtering by lambda.

        Args:
            filters: The dictionary of this form: {"type_name_string", lambda UsdObject: True}. When lambda is True,
                     the object will be shown.
            enabled: True to add to filters, False to remove them from the filter list.
        """
        if not self._tree_view:
            return

        if self._tree_view.visible:
            tree_view = self._tree_view

        if enabled:
            tree_view.model.filter(add=filters)
            tree_view.keep_alive = True
            # self._delegate.set_highlighting(enable=True)

            if self._selection:
                self._selection.enable_filtering_checking(True)
        else:
            for lambda_name in filters.keys():
                keep_filtering = tree_view.model.filter(remove=lambda_name)
            if not keep_filtering:
                # Filtering is finished. Return it back to normal.
                tree_view.keep_alive = False
                tree_view.keep_expanded = False
                # self._delegate.set_highlighting(enable=False)

                if self._selection:
                    self._selection.enable_filtering_checking(False)

    def _filter_by_text(self, filter_text: str):
        """Set the search filter string to the models and widgets"""
        tree_view = self._tree_view

        if self._selection:
            self._selection.set_filtering(filter_text)

        # It's only set when the visibility is changed.
        was_visible_before = None
        is_visible_now = None

        if filter_text:
            # Check if _tree_view just became visible
            self._tree_view.visible = True

        if was_visible_before and is_visible_now:
            # The visibility is just changed.
            filter_types = was_visible_before.model.get_filters()
            # Set filter types on the new widget
            is_visible_now.model.filter(add=filter_types, clear=True)
            # Clear filter types on the old widget
            was_visible_before.model.filter(clear=True)
            # Replace treeview in the selection model will allow to use only one selection watch for two treeviews
            if self._selection:
                self._selection.set_tree_view(is_visible_now)

        tree_view.keep_alive = not not filter_text
        tree_view.model.filter_by_text(filter_text)

        self._delegate.set_highlighting(text=filter_text)

    def open_stage(self, stage: Usd.Stage):
        """Called when opening a new stage"""
        if stage != self._stage or not self._model:
            if self._model:
                self._model.destroy()
                del self._model

            self._model = CollectionModel(stage, self._collection_watch)

        # Widgets are not created if `_on_attach` is called from the constructor.
        if self._tree_view:
            self._tree_view.model = self._model

            # If we want to start off with filters on, we need to call them explicitly
            if self._filter_initial_state:
                # Consolidated into a single call for better performance.
                self._apply_default_filters()

    def update_icons(self):
        """Called to update icons in the TreeView"""
        self._tree_view.dirty_widgets()
