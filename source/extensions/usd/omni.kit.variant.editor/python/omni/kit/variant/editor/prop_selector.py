# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import weakref
from enum import IntEnum
from functools import partial
from typing import Dict, List, Optional, Set, Union

import carb
import omni
import omni.ui as ui
from pxr import Sdf, Tf, Usd, UsdShade

from . import ui_const as ui_c
from .core import VariantEditorCore, cache_shader_display_name, get_shader_display_name
from .list import ListItem, ListModel, ListView
from .placeholder_attribute import PlaceholderAttribute


class Column(IntEnum):
    NAME = 1
    TYPE = 2
    ID = 0
    COUNT = 3


class PropertySelectionCard:
    PROPERTYSELECTION = "propertySelection"

    @staticmethod
    def create(type, **kwargs):
        if type == PropertySelectionCard.PROPERTYSELECTION:
            return PropertySelectionCard(**kwargs)
        else:
            carb.log_error(f"[variant editor] Unknown property selection card type: {type}")
            return None

    def __init__(
        self,
        name: str,
        path: str,
        prop: Usd.Property,
        metadata: dict,
        prop_type: type,
        layer: Sdf.Layer,
    ):
        self.type = self.PROPERTYSELECTION
        self.name = name
        self.path = path
        self.prop = prop
        self.prop_type = prop_type
        self.metadata = metadata
        self.layer = layer


class PropertySelectionCardItem(ListItem):
    """Single item of PropertySelection card"""

    def __init__(self, card: PropertySelectionCard, index):
        super().__init__(
            [
                f"{index+1}##int",
                card.name,
                card.type,
                card.prop,
                card.prop_type,
                card.path,
                card.metadata,
                card.layer,
            ]
        )
        self._sub_id = None

        self.data = card

    @property
    def name_model(self):
        return ui.SimpleStringModel(self.data.name)

    @property
    def type_model(self):
        return self.get_value_model(Column.TYPE)

    @property
    def index_model(self):
        return self.get_value_model(Column.ID)

    @property
    def path_model(self):
        return ui.SimpleStringModel(str(self.data.path))

    @property
    def prop_type_model(self):
        return ui.SimpleStringModel(str(self.data.prop_type))

    @property
    def prop_model(self):
        return ui.SimpleStringModel(str(self.data.prop))

    @property
    def metadata_model(self):
        return ui.SimpleStringModel(str(self.data.metadata))

    @property
    def layer_model(self):
        return ui.SimpleStringModel(str(self.data.layer))

    def _get_values(self, card: PropertySelectionCard, index):
        return [
            f"{index}##int",
            card.name,
            card.type,
            card.path,
            card.prop,
            card.prop_type,
            card.metadata,
            card.layer,
        ]

    def change_index(self, differ):
        # print(f"{self.name_model.as_string}: index change from {self.index_model.as_int} to {self.index_model.as_int + differ}")
        self.index_model.set_value(self.index_model.as_int + differ)

    def set_index(self, index):
        # print(f"{self.name_model.as_string}: index set from {self.index_model.as_int} to {index+1}")
        self.index_model.set_value(index + 1)

    def subscribe_index_changed_fn(self, fn):
        self._sub_id = self.index_model.subscribe_value_changed_fn(fn)

    def get_value_model(self, index=0):
        if index == Column.NAME:
            return self.name_model
        else:
            return super().get_value_model(index)

    def __repr__(self):
        return f'"{self.index_model.as_string}: {self.name_model.as_string} {self.type_model.as_string} {self.path_model.as_string} {self.prop_model.as_string} {self.prop_type_model.as_string} {self.metadata_model.as_string} {self.layer_model.as_string}"'


class PropertySelectionListModel(ListModel):
    """Represents PropertySelection lists"""

    def __init__(
        self,
        name,
        on_changed_fn: callable = None,
        system=False,
        on_dropped_fn: callable = None,
        path: Optional[str] = None,
    ):
        super().__init__(enable_drag_drop=True)

        self._name = name
        if path is None:
            stage = omni.usd.get_context().get_stage()
            self.path = omni.usd.get_stage_next_free_path(stage, f"{omni.usd.make_valid_identifier(name)}", False)
        else:
            self.path = path
        self._on_changed_fn = on_changed_fn
        self._on_dropped_fn = on_dropped_fn
        self._system = system

        # Get the Variant Editor Core instance
        self._editor_core = VariantEditorCore.get_instance()

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def attributes(self):
        return self._attributes

    @attributes.setter
    def attributes(self, value):
        self._attributes = value

    @property
    def system(self):
        return self._system

    @property
    def auto_save(self):
        return not self._system

    @property
    def can_change(self):
        return not self._system

    def set_dropped_fn(self, on_dropped_fn: callable):
        self._on_dropped_fn = on_dropped_fn

    def set_changed_fn(self, on_changed_fn: callable):
        self._on_changed_fn = on_changed_fn

    def add_value_changed_fn(self, on_changed_fn: callable):
        self._on_changed_fn = on_changed_fn

    def check_update(self):
        return

    def save(self) -> None:
        if self._on_changed_fn is not None:
            self._on_changed_fn(self)

    def _update_children_paths(self, set_name):
        children = self.get_item_children()
        for child in children:
            self._update_child_path(child, set_name)

    def _update_child_path(self, item: PropertySelectionCardItem, set_name):
        parent_path = self._editor_core._get_root_prim_path()
        child_name = item.data.name
        child_path = Sdf.Path(parent_path).AppendVariantSelection(set_name, child_name)
        item.data.path = child_path

    def insert_item(
        self,
        item: Union[PropertySelectionCardItem, PropertySelectionCard],
        index=-1,
        notify=True,
    ):
        """Insert new card"""
        if index == -1:
            index = len(self._children)

        if isinstance(item, PropertySelectionCard):
            # item is list card
            item = PropertySelectionCardItem(item, index)
        else:
            # Update item index
            item.set_index(index)
        super().insert_item(item, index)

        # change item index after inserted location
        for item in self._children[index + 1 :]:
            item.change_index(1)

        if notify:
            self._item_changed(None)
            if self._on_changed_fn is not None:
                self._on_changed_fn(self)

        return index

    def remove_item(self, item: Union[int, PropertySelectionCardItem]):
        if isinstance(item, int):
            index = item
        else:
            index = self._children.index(item)
        self.remove_index(index)

    def remove_index(self, index: int):
        super().remove_index(index)

        for item in self._children[index:]:
            item.change_index(-1)

        self._item_changed(None)
        if self._on_changed_fn is not None:
            self._on_changed_fn(self)

    def clear(self):
        super().clear()


class PropertySelectionListDelegate(ui.AbstractItemDelegate):

    def __init__(self, on_item_clicked: callable):
        super().__init__()
        self._on_item_clicked = on_item_clicked
        self.subscription = None
        self._widgets: Dict([PropertySelectionCardItem, ui.Widget]) = {}
        self._labels: Dict([PropertySelectionCardItem, ui.Widget]) = {}
        self._editor_core = VariantEditorCore.get_instance()

    def destroy(self):
        # _widgets/_labels are only ever written; without this they grow by every row of
        # every picker that is opened, for the lifetime of the process.
        self._widgets.clear()
        self._labels.clear()

    def build_branch(self, model, item, column_id, level, expanded):
        """Create a branch widget that opens or closes subtree"""
        pass

    def build_widget(
        self,
        model: PropertySelectionListModel,
        item: PropertySelectionCardItem,
        column_id,
        level,
        expanded,
    ):
        """Create a widget per column per item"""

        if column_id == 0:
            self._widgets[item] = ui.HStack(
                mouse_pressed_fn=lambda x, y, btn, flag, model=model, item=item: self._on_clicked(btn, model, item),
                mouse_hovered_fn=lambda hovered, item=item: self._on_hover(item, hovered),
                style=ui_c.STYLE_PROPERTY_SELECTION_LIST,
            )
            with self._widgets[item]:
                # NAME
                stack = ui.HStack(height=20)
                with stack:
                    name_model = model.get_item_value_model(item, Column.NAME)
                    ui.Spacer(width=2)
                    self._labels[item] = ui.Label(
                        name_model.as_string,
                        width=ui.Percent(75),
                        height=24,
                        name=name_model.as_string,
                        style=ui_c.STYLE_PROPERTY_SELECTION_CARD,
                    )

    def _on_selected(self, model: PropertySelectionListModel, item: PropertySelectionCardItem) -> None:
        carb.log_warn(f"Selected Property: {item.name_model.as_string}")

    def _on_clicked(
        self,
        btn: int,
        model: PropertySelectionListModel,
        item: PropertySelectionCardItem,
    ) -> None:
        return self._on_item_clicked(btn, model, item)

    def _on_hover(self, item: PropertySelectionCardItem, hovered: bool) -> None:
        pass

    def _on_delete(
        self,
        btn: int,
        model: PropertySelectionListModel,
        item: PropertySelectionCardItem,
    ) -> None:
        if btn == 0:
            model.remove_item(item)

    def _create_tooltip(self, text: str):
        with ui.ZStack(style=ui_c.STYLE_TOOLTIP):
            ui.Rectangle()
            ui.Label(text, style=ui_c.STYLE_TOOLTIP_TEXT)


class PropertySelectionListView(ListView):
    _property_selection_list_view_instance = None

    def __init__(self):
        self._empty_model = PropertySelectionListModel("", path="")
        self._property_selection_list_delegate = PropertySelectionListDelegate(self._on_item_clicked)
        self._context_menu = ui.Menu("Property Selection List context menu", menu_compatibility=False, tearable=False)
        self._editor_core = VariantEditorCore.get_instance()
        self._target_prim = None
        self._payref_selected = False
        self._search_words: Optional[Set[str]] = set()
        self._observers = []
        self._lookup_table = {
            # info
            "info:id": {"name": "ID", "group": "Info"},
            "info:implementationSource": {
                "name": "Implementation Source",
                "group": "Info",
            },
            "info:mdl:sourceAsset": {"name": "", "group": "Info"},
            "info:mdl:sourceAsset:subIdentifier": {"name": "", "group": "Info"},
            # nodegraph
            "ui:nodegraph:node:displayColor": {
                "name": "Display Color",
                "group": "UI Properties",
            },
            "ui:nodegraph:node:expansionState": {
                "name": "Expansion State",
                "group": "UI Properties",
            },
            "ui:nodegraph:node:icon": {"name": "Icon", "group": "UI Properties"},
            "ui:nodegraph:node:pos": {"name": "Position", "group": "UI Properties"},
            "ui:nodegraph:node:size": {"name": "Size", "group": "UI Properties"},
            "ui:nodegraph:node:stackingOrder": {
                "name": "Stacking Order",
                "group": "UI Properties",
            },
            # backdrop
            "ui:description": {"name": "Description", "group": "UI Properties"},
        }

    @property
    def payref_selected(self):
        return self._payref_selected

    @payref_selected.setter
    def payref_selected(self, value):
        self._payref_selected = value
        for callback in self._observers:
            callback(self._payref_selected)

    def bind_to(self, callback):
        # This view is a singleton shared by every PropertySelectorButton, so guard
        # against the same observer being registered once per window rebuild.
        if callback not in self._observers:
            self._observers.append(callback)

    def unbind_from(self, callback):
        if callback in self._observers:
            self._observers.remove(callback)

    @staticmethod
    def get_instance():
        if PropertySelectionListView._property_selection_list_view_instance is None:
            PropertySelectionListView._property_selection_list_view_instance = PropertySelectionListView()
        return PropertySelectionListView._property_selection_list_view_instance

    def build_list(self):
        # Rows from the previous picker window are gone by now, so drop the delegate's
        # per-item caches before rebuilding.
        self._property_selection_list_delegate.destroy()
        super().__init__(
            height=ui_c.PROPERTY_WINDOW_HEIGHT - 124,
            model=self._empty_model,
            column_widths=[ui.Fraction(1)],
            on_item_selected_fn=self._on_item_selected,
            multi_selection=True,
            delegate=self._property_selection_list_delegate,
            drop_between_items=True,
        )
        return self

    def destroy(self):
        self._observers.clear()
        self._property_selection_list_delegate.destroy()
        self._context_menu = None

    def clear_filter(self):
        self._search_words = set()

    def search(self, search_words: Optional[List[str]]):
        self._search_words = set(w.lower() for w in search_words) if search_words else set()

    @property
    def can_change(self):
        return self.model.can_change

    def _on_item_selected(self, item: PropertySelectionCardItem):
        pass

    def _on_selection_changed(self, selections):
        selection_names = []
        if len(selections) == 0:
            return

        if not self._multi_selection:
            # Disable multi selection
            if selections and len(selections) > 1:
                selections = selections[-1:]
                self._tree_view.selection = selections

        for item in selections:
            if self._on_item_selected_fn:
                self._on_item_selected_fn(item)
            selection_names.append(item.data.name)

        payrefs = ["Payload", "Reference"]
        if any(name in selection_names for name in payrefs):
            self.payref_selected = True
        else:
            self.payref_selected = False

    def update_data(self, property_selection_list_model: Optional[PropertySelectionListModel]):
        if property_selection_list_model is None:
            self._tree_view.model = self._empty_model

    @staticmethod
    def _get_display_name(attr_name, metadata):
        if not metadata:
            return attr_name
        return metadata.get(Sdf.PropertySpec.DisplayNameKey, attr_name)

    def add_property_selection_card(self, property_selection_list_model: PropertySelectionListModel, vset, vname):

        if not isinstance(vset, str):
            vset = vset.GetName()

        root_path = self._editor_core._get_root_prim_path()
        vpath = root_path.AppendVariantSelection(vset, vname)
        card = PropertySelectionCard.create(name=vname, type=PropertySelectionCard.PROPERTYSELECTION, path=vpath)
        property_selection_list_model.insert_item(card)

    def _populate_potential_properties(self, prim):
        from pxr import UsdGeom, UsdShade

        materail_applicable = prim.IsA(UsdGeom.Mesh) or prim.IsA(UsdGeom.Xform) or prim.IsA(UsdGeom.Xformable)
        if materail_applicable and not prim.GetProperty("material:binding"):
            purpose = UsdShade.Tokens.allPurpose
            return [UsdShade.MaterialBindingAPI(prim).GetDirectBindingRel(purpose)]
        return []

    def _populate_shader_inputs(self, prim):
        """
        For a shader prim, get all the possible inputs from the shader registry,
        including both existing and non-existing inputs.

        Returns a list of PropertySelectionCard objects for these inputs.
        """
        attrs = []
        usdshade_shader = UsdShade.Shader(prim)
        sdr_shader_node = usdshade_shader.GetShaderNodeForSourceType("mdl")

        if not sdr_shader_node:
            carb.log_warn(f"Could not get shader node for {prim.GetPath()}")
            return attrs

        # Get all inputs from the shader definition
        for name in sdr_shader_node.GetShaderInputNames():

            # Get input info from SDR
            sdr_shader_property = sdr_shader_node.GetShaderInput(name)

            display_name = sdr_shader_property.GetLabel()
            if display_name:
                cache_shader_display_name(name, display_name)

            ndr_sdr_type_indicator = sdr_shader_property.GetTypeAsSdfType()

            try:
                value_type_name = ndr_sdr_type_indicator[0]
            except TypeError as e:
                value_type_name = ndr_sdr_type_indicator.GetSdfType()

            # Check if the input already exists on the shader
            if not usdshade_shader.GetInput(name):
                attrs.append(PlaceholderAttribute(name=name, prim=prim, value_type_name=value_type_name))

        return attrs

    def populate_property_selections(self, path):
        self._target_prim = self._editor_core._stage.GetPrimAtPath(path)
        property_selections = self._target_prim.GetProperties()
        if self._target_prim.GetTypeName() == "Shader":
            property_selections += self._populate_shader_inputs(self._target_prim)
        property_selections += self._populate_potential_properties(self._target_prim)

        variant_set_names = self._target_prim.GetVariantSets().GetNames()
        paired_props = self._editor_core._paired_properties

        cards = []
        # Add a card for each potential type of property you might want to add.
        for p in property_selections:
            skip = False
            name = p.GetName()
            path = p.GetPath()
            metadata = p.GetAllMetadata()
            if self._editor_core.get_property_display_name(path):
                name = self._editor_core.get_property_display_name(path)
            elif name in self._lookup_table:
                lookup = self._lookup_table[name]
                if lookup["name"]:
                    name = lookup["name"]
            elif self._target_prim.GetTypeName() == "Shader":
                name = get_shader_display_name(name)
            else:
                name = self._get_display_name(name, metadata)
            if isinstance(p, Usd.Relationship):
                prop_type = "relationship"
            else:
                prop_type = p.GetTypeName()
            cpp_type_name = Sdf.ValueTypeNames.Find(metadata.get(Sdf.PrimSpec.TypeNameKey, "unknown type")).cppTypeName
            if "VtArray" in str(cpp_type_name):
                continue
            # Only add cards for the first member of any paired properties
            for list in paired_props:
                for index, prop in enumerate(list):
                    if name == prop and index > 0:
                        skip = True
                        break
            if not skip:
                if name == "info:mdl:sourceAsset":
                    name = "MDL Source Asset/SubID"
                card = PropertySelectionCard.create(
                    PropertySelectionCard.PROPERTYSELECTION,
                    name=name,
                    path=path,
                    prop=p,
                    prop_type=prop_type,
                    metadata=metadata,
                    layer="",
                )
                cards.append(card)

        cards = sorted(cards, key=lambda card: card.name)

        for name in variant_set_names:
            if (
                Sdf.Path(self._editor_core.active_variant).StripAllVariantSelections() == self._target_prim.GetPath()
                and Sdf.Path(self._editor_core.active_variant).GetVariantSelection()[0] == name
            ):
                pass
            else:
                vset = self._editor_core._get_variant_set_by_name(name)
                vselection = vset.GetVariantSelection()
                prim_stub = self._target_prim.GetName()
                path = vset.GetPrim().GetPath().AppendVariantSelection(name, vselection).AppendPath(prim_stub)
                display_name = f"VariantSet: {name}"
                prop = vset
                prop_type = "str"
                metadata = {}
                card = PropertySelectionCard.create(
                    PropertySelectionCard.PROPERTYSELECTION,
                    name=display_name,
                    path=path,
                    prop=prop,
                    prop_type=prop_type,
                    metadata=metadata,
                    layer="",
                )
                cards.append(card)

        # Add a card for adding a reference
        card = PropertySelectionCard.create(
            PropertySelectionCard.PROPERTYSELECTION,
            name="Reference",
            path=path,
            prop="",
            prop_type="",
            metadata={},
            layer="",
        )
        cards.append(card)
        # Add a card for adding a payload
        card = PropertySelectionCard.create(
            PropertySelectionCard.PROPERTYSELECTION,
            name="Payload",
            path=path,
            prop="",
            prop_type="",
            metadata={},
            layer="",
        )
        cards.append(card)

        def match_searching(card_name):
            return len(self._search_words) == 0 or all(w in card_name for w in self._search_words)

        for card in cards:
            if not match_searching(card.name.lower()):
                continue
            else:
                self.model.insert_item(card)

    def _on_item_clicked(
        self,
        btn: int,
        model: PropertySelectionListModel,
        item: PropertySelectionCardItem,
    ):
        if btn != 1:
            return True

        index = self.items.index(item)
        self.selection = [index]

        self._context_menu.clear()
        with self._context_menu:
            ui.MenuItem(
                "Remove Property_Selection",
                triggered_fn=lambda: self._on_remove_item(model, item),
                enabled=self.can_change,
            )

        self._context_menu.show()

        return True

    def _get_item_path(self, model, item):
        path = item.path_model.as_string
        return path

    def _on_remove_item(self, model, item):
        model.remove_item(item)
        self.remove_selected()

    def _clear_list(self, property_selection_list_model):
        for item in self.items:
            self._on_item_clicked(0, property_selection_list_model, item)


class PropertySelectorButton:
    _property_selector_instance = None

    # These buttons live in the property tree's delegate, so a fresh instance is built
    # every time the tree rebuilds -- which happens after each property is added. A
    # button therefore can't assume it owns the window it needs to replace. Only one
    # picker is ever open (it is modal), so track its owner on the class. It has to be
    # the owning button rather than the window: ui.Window.destroy() does not remove the
    # window from ui.Workspace, so the owner's reference has to be cleared too or the
    # window lingers and lookups by title stay ambiguous. Weak so a discarded button
    # stays collectable.
    __active_button = None

    def __init__(
        self,
        filter_type_list=[],
        label="",
        target_prim=None,
        on_select_fn=None,
        on_cancel_fn=None,
        tooltip_fn=None,
        style=None,
        style_type_name_override=None,
        targets_limit=0,
        width=100,
        height=24,
    ):
        self.__target_prim = target_prim
        self.__on_select_fn = on_select_fn
        self.__on_cancel_fn = on_cancel_fn
        self.__add_button = None
        self.__add_all_button = None
        self.__cancel_button = None
        self.__selected_paths = []
        self.__filter_type_list = filter_type_list
        self.__stage_button = None
        self.__window = None
        self._editor_core = VariantEditorCore.get_instance()
        self.__selector_widget = None
        if style is not None:
            self.__stage_button = ui.Button(
                label,
                clicked_fn=partial(self.__on_click),
                tooltip_fn=tooltip_fn,
                style=style,
                width=width,
                height=height,
            )
        else:
            self.__stage_button = ui.Button(
                label,
                clicked_fn=partial(self.__on_click),
                tooltip_fn=tooltip_fn,
                width=width,
                height=height,
            )
        if not self.__on_select_fn:
            self.enabled = False

    def __del__(self):
        # Deliberately does not destroy __selector_widget: it is the shared
        # PropertySelectionListView singleton. These buttons are rebuilt with the tree and
        # collected non-deterministically, so destroying it here would clear the observers
        # and delegate out from under a newer button's live window. __destroy_window only
        # unbinds from it.
        self.__destroy_window()
        self.__selected_paths = None
        self._editor_core = None

    def __destroy_window(self):
        # A fresh window is built on every click. Tear the previous one down first,
        # otherwise it stays registered in omni.ui and lookups by window title become
        # ambiguous. __selector_widget is the PropertySelectionListView singleton
        # shared with every other selector button, so unbind from it rather than
        # destroying it -- otherwise it keeps notifying buttons whose window is gone.
        if self.__selector_widget:
            self.__selector_widget.unbind_from(self._on_selections_updated)
        self.__selector_widget = None
        self.__add_button = None
        self.__add_all_button = None
        self.__cancel_button = None
        if self.__window:
            self.__window.visible = False
            self.__window.destroy()
            self.__window = None
        active = PropertySelectorButton.__active_button
        if active is not None and active() is self:
            PropertySelectorButton.__active_button = None

    def __on_click(self):
        if not self._editor_core.validate_variant_edit():
            return

        stage = self._editor_core._stage
        if self.__on_select_fn and stage:
            # The open window usually belongs to a previous, already-discarded button,
            # so ask that button to tear it down rather than only closing our own.
            active = PropertySelectorButton.__active_button
            previous = active() if active is not None else None
            if previous is not None and previous is not self:
                previous.__destroy_window()
            self.__destroy_window()
            window_title = "Select Properties"
            window_flags = ui.WINDOW_FLAGS_NO_RESIZE
            window_flags |= ui.WINDOW_FLAGS_MODAL
            window_flags |= ui.WINDOW_FLAGS_NO_SCROLLBAR
            self.__window = ui.Window(
                window_title,
                width=ui_c.PROPERTY_WINDOW_WIDTH,
                height=ui_c.PROPERTY_WINDOW_HEIGHT - 40,
                visible=True,
                flags=window_flags,
            )
            PropertySelectorButton.__active_button = weakref.ref(self)
            with self.__window.frame:
                with ui.VStack():
                    try:
                        from omni.kit.widget.searchfield import SearchField

                        with ui.HStack(height=22):
                            self._search_field = SearchField(
                                on_search_fn=self.__on_search,
                                subscribe_edit_changed=True,
                                show_tokens=False,
                            )
                    except ImportError:
                        self._search_field = None
                    with ui.ScrollingFrame(
                        style={"ScrollingFrame": {"background_color": ui_c.COLORS.TRANSPARENT}},
                        height=ui_c.PROPERTY_WINDOW_HEIGHT - 124,
                    ):
                        self.__selector_widget = PropertySelectionListView.get_instance()
                        self.__selector_widget.bind_to(self._on_selections_updated)
                        self.__selector_widget.clear_filter()
                        self.__selector_widget.build_list()
                        self.__selector_widget.model.clear()
                        self.__selector_widget.populate_property_selections(self.__target_prim)
                    ui.Spacer(height=5)
                    with ui.VStack():
                        with ui.HStack():
                            ui.Spacer(width=10)
                            self.__add_button = ui.Button("Add", height=10, clicked_fn=self.__on_add, enabled=True)
                            self.__add_all_button = ui.Button(
                                "Add To All Prims",
                                height=10,
                                clicked_fn=self.__on_add_to_all,
                                enabled=True,
                                style={"Button.Label:disabled": {"color": 0xFF606060}},
                            )
                            self.__cancel_button = ui.Button(
                                "Cancel",
                                height=10,
                                clicked_fn=self.__on_cancel,
                                enabled=True,
                            )
                            ui.Spacer(width=10)

    def __on_add(self):
        self.__on_select_fn(self.__selector_widget.selection_items, False)
        self.hide()

    def __on_add_to_all(self):
        self.__on_select_fn(self.__selector_widget.selection_items, True)
        self.hide()

    def __on_cancel(self):
        self.hide()

    def __on_search(self, search_words: Optional[List[str]]) -> None:
        self.__selector_widget.search(search_words)
        self.__selector_widget.model.clear()
        self.__selector_widget.populate_property_selections(self.__target_prim)

    def _on_selections_updated(self, value):
        # Bound before the buttons are built, and cleared by __destroy_window, so this can
        # fire while there is no button to update.
        if self.__add_all_button:
            self.__add_all_button.enabled = not value

    def hide(self):
        if self.__window:
            self.__window.visible = False

    def show(self):
        if self.__window:
            self.__window.visible = True

    @property
    def enabled(self):
        return self.__stage_button.enabled

    @enabled.setter
    def enabled(self, enabled):
        self.__stage_button.enabled = enabled
