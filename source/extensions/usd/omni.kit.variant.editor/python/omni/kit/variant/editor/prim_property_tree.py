# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from __future__ import annotations

import asyncio
import weakref
from typing import Optional, Union

import carb
import omni.kit.app
import omni.kit.notification_manager as nm
import omni.ui as ui
from carb.eventdispatcher import get_eventdispatcher
from omni.kit.property.usd.prim_selection_payload import PrimSelectionPayload
from omni.kit.window.file_importer import get_file_importer
from pxr import Sdf, Usd

from . import ui_const as ui_c
from .list import ListView
from .placeholder_attribute import PlaceholderAttribute
from .prop_selector import PropertySelectionCard, PropertySelectorButton
from .references_widget import UsdVariantPayloadReferenceWidget, pick_ref_asset
from .variant_as_prop_widget import VariantsWidget
from .variant_material_binding_widget_builder import VariantMaterialBindingWidgetBuilder
from .variant_property_widget_builder import UsdVariantPropertiesWidgetBuilder
from .variant_tree import VariantTreeModel
from .variant_tree_items import (
    Column,
    PrimCardItem,
    PropertyCard,
    PropertyCardItem,
    VariantCardItem,
    VariantTreeHelperItem,
)

DEFAULT_FILE_EXTS = ("*.*", "All Files")


class PrimPropertyView(ListView):
    def __init__(
        self,
        model: VariantTreeModel,
        delegate: PrimPropertyDelegate,
        keep_expanded=False,
    ):
        super().__init__(
            model=model,
            column_widths=[ui.Fraction(1)],
            on_item_selected_fn=self._on_item_selected,
            delegate=delegate,
            drop_between_items=True,
            vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
            horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
            scrolling_frame=True,
            keep_expanded=keep_expanded,
        )

    def _on_item_selected(self, item):
        if not self._tree_view.is_expanded(item):
            self._tree_view.set_expanded(item, True, False)
        else:
            self._tree_view.set_expanded(item, False, False)

    # Prim list will evaluate the prim dragged into the list to see if it is the target prim or any of its children
    def _on_accept_drop(self, item):
        model: VariantTreeModel = self._tree_view.model
        target_and_children = []
        target_prim = model._editor_core._stage.GetPrimAtPath(model._editor_core._target_prim_path)
        target_children = self.get_all_children(target_prim)
        target_and_children.append(model._editor_core._target_prim_path)
        for child in target_children:
            target_and_children.append(child)
        if isinstance(item, str):
            item = item.split("\n")
        if any(check in item for check in target_and_children):
            return True
        nm.post_notification(
            f"Only {target_prim} or its descendents can be modified by this variant",
            duration=3,
            status=nm.NotificationStatus.INFO,
        )
        return False

    def get_all_children(self, prim):
        children_list = set([])
        queue = [prim]
        while len(queue) > 0:
            child_prim = queue.pop()
            for child in child_prim.GetAllChildren():
                children_list.add(child.GetPath())
                queue.append(child)

        return children_list

    # If the prim is accepted, get prim selections instead of evaluating dragged prims.
    # Drag data can apparently only actually supply one object at a time.
    # Check again on the selections and only add the ones that meet the criteria
    def _on_drop(self, item):
        model: VariantTreeModel = self._tree_view.model
        path_list = model._editor_core._usd_context.get_selection().get_selected_prim_paths()
        target_and_children = []
        target_prim = model._editor_core._stage.GetPrimAtPath(model._editor_core._target_prim_path)
        target_children = self.get_all_children(target_prim)
        target_and_children.append(model._editor_core._target_prim_path)
        for child in target_children:
            target_and_children.append(child)

        for path in path_list:
            if path in target_and_children and bool(model._editor_core.active_variant):
                continue
            else:
                path_list.remove(path)

        model.ensure_add_prims_to_variant(path_list)


class PrimPropertyDelegate(ui.AbstractItemDelegate):
    """
    Delegate for rendering PrimPropertyView
    """

    def __init__(self):
        super().__init__()

        self._mdl_prop_list = [
            "info:mdl:sourceAsset",
            "info:mdl:sourceAsset:subIdentifier",
        ]
        self._context_menu = ui.Menu("Prim List context menu", menu_compatibility=False, tearable=False)
        self._paste_prop: Optional[ui.MenuItem] = None
        self._paste_prim: Optional[ui.MenuItem] = None
        self._paste_prim_all: Optional[ui.MenuItem] = None
        self._can_edit = True

    def belongs_to_active_variant(self, model: VariantTreeModel, item):
        # check if item belongs to current active variant
        if isinstance(item, PrimCardItem):
            variant_item = model.get_parent_item(item)

        elif isinstance(item, PropertyCardItem) or isinstance(item, VariantTreeHelperItem):
            prim_item = model.get_parent_item(item)
            variant_item = model.get_parent_item(prim_item)

        elif isinstance(item, VariantCardItem):
            variant_item = item

        else:
            variant_item = None

        if variant_item is not None:
            if isinstance(variant_item.data.path, Sdf.Path):
                variant_path = variant_item.data.path.pathString
            else:
                variant_path = variant_item.data.path

            if variant_path != model._editor_core.active_variant:
                return False

        return True

    def build_branch(self, model, item, column_id, level, expanded):
        """Create a branch widget that opens or closes subtree"""
        if not self.belongs_to_active_variant(model, item):
            return

        if isinstance(item, PrimCardItem):
            with ui.VStack():
                ui.Spacer(height=5)
                with ui.HStack():
                    ui.Spacer(width=5)
                    with ui.ZStack(height=30):
                        ui.Rectangle(style={"background_color": ui_c.COLORS.CLR_3})

                        with ui.HStack():
                            ui.Spacer(width=10)

                            with ui.HStack(width=24):
                                with ui.VStack():
                                    ui.Spacer()
                                    style = ui_c.STYLE_EXPAND_BUTTON if expanded else ui_c.STYLE_COLLAPSE_BUTTON
                                    ui.Image(
                                        width=14,
                                        height=14,
                                        style=style,
                                    )
                                    ui.Spacer()

    def build_widget(
        self,
        model: VariantTreeModel,
        item: Union[PrimCardItem, PropertyCardItem],
        column_id,
        level,
        expanded,
    ):
        """Create a widget per column per item"""
        if not self.belongs_to_active_variant(model, item):
            return

        if column_id == 0:
            self._can_edit = model._editor_core.validate_variant_edit(False)
            if self._can_edit:
                tooltip_text = ""
            else:
                tooltip_text = f"Cannot edit variant because it is authored in a referenced layer: {model._editor_core.ref_prim_path}"
            if isinstance(item, PrimCardItem):
                """build widgets for prim cards"""
                with ui.VStack():
                    ui.Spacer(height=5)
                    with ui.ZStack():
                        ui.Rectangle(style={"background_color": ui_c.COLORS.CLR_3})
                        if item.data.highlight:
                            HighlightRect(model, item)

                        with ui.VStack():
                            prim_widget = ui.HStack(
                                mouse_pressed_fn=lambda x, y, btn, flag, model=model, item=item: self._on_prim_item_clicked(
                                    btn, model, item
                                ),
                                mouse_hovered_fn=lambda hovered, item=item: self._on_prim_item_hover(item, hovered),
                                # style=ui_c.STYLE_PRIM_LIST,
                                enabled=self._can_edit,
                            )
                            with prim_widget:
                                ui.Spacer(width=1)
                                # NAME
                                name_model = model.get_item_value_model(item, Column.NAME)
                                name = name_model.as_string

                                # Prim List
                                stack = ui.HStack(height=30)
                                with stack:
                                    # Isolate the target prim icon and label for expand/collapse clicks
                                    target_prim_stack = ui.HStack()
                                    with target_prim_stack:
                                        ui.Spacer(width=10)
                                        with ui.HStack():
                                            ui.Label(
                                                "Target Prim:",
                                                width=50,
                                                style=ui_c.STYLE_TEXT_LABEL,
                                            )
                                            ui.Spacer(width=20)
                                            ui.Label(
                                                item.name_model.as_string,
                                                name=name,
                                                elided_text=True,
                                                tooltip_fn=lambda: self._create_tooltip(item.name_model.as_string),
                                                style=ui_c.STYLE_PRIM_STRING,
                                            )

                                    # Remove Button
                                    with ui.VStack(width=0):
                                        # Add Button
                                        ui.Spacer()
                                        ui.Button(
                                            clicked_fn=lambda model=model, item=item: self._on_prim_item_delete(
                                                model, item
                                            ),
                                            image_url=f"{ui_c.PATH_EXTENSION}{ui_c.PATH_ICON_REMOVE_DARK}",
                                            # declaring image width and height necessary for nice antialiasing
                                            image_height=18,
                                            image_width=18,
                                            width=24,
                                            height=24,
                                            style=ui_c.STYLE_REMOVE_BUTTON,
                                        )
                                        ui.Spacer()

                                    ui.Spacer(width=2)
                        if not self._can_edit:
                            with ui.VStack(tooltip=tooltip_text, style=ui_c.STYLE_TOOLTIP):
                                OverlayBlocker()

            elif isinstance(item, VariantTreeHelperItem):
                # build widget for ProperyCardItem
                with ui.HStack():
                    ui.Spacer(width=5)
                    with ui.ZStack():
                        ui.Rectangle(style={"background_color": ui_c.COLORS.CLR_3})
                        with ui.VStack():
                            ui.Spacer(height=5)
                            SHORTCUT_BUTTON_SIZE = 24
                            with ui.HStack(height=SHORTCUT_BUTTON_SIZE, spacing=3):
                                ui.Spacer(width=3)
                                # Property Selection Window
                                parent_prim_item = model.get_parent_item(item)
                                prim_path = Sdf.Path(parent_prim_item.data.path).StripAllVariantSelections()
                                with ui.ZStack(style={"margin": 0, "padding": 0}):
                                    if self._can_edit:
                                        on_select_fn = (
                                            lambda cards, add_all, item=item, model=model: asyncio.ensure_future(
                                                self._on_props_picked(cards, parent_prim_item, model, add_all)
                                            )
                                        )
                                    else:
                                        on_select_fn = None
                                    PropertySelectorButton(
                                        label="Add Property",
                                        target_prim=prim_path,
                                        on_select_fn=on_select_fn,
                                        tooltip_fn=lambda: self._create_tooltip(ui_c.TOOLTIP_BUTTON_ADD_PROPERTY),
                                        targets_limit=1000,
                                        height=SHORTCUT_BUTTON_SIZE,
                                        width=130,
                                        style=ui_c.STYLE_BUTTON,
                                    )
                                    with ui.HStack():
                                        ui.Spacer(width=5)
                                        with ui.VStack():
                                            ui.Spacer()
                                            ui.ImageWithProvider(
                                                f"{ui_c.PATH_EXTENSION}{ui_c.PATH_ICON_ADD_DARK}",
                                                width=16,
                                                height=16,
                                                style=ui_c.STYLE_ICON_NO_HOVER,
                                            )
                                            ui.Spacer()

                            ui.Spacer(height=5)
                        if not self._can_edit:
                            with ui.VStack(tooltip=tooltip_text, style=ui_c.STYLE_TOOLTIP):
                                OverlayBlocker()

            elif isinstance(item, PropertyCardItem):
                """build widgets for properties"""
                props_widget = ui.HStack(
                    height=40,
                    mouse_pressed_fn=lambda x, y, btn, flag, model=model, item=item: self._on_prop_item_clicked(
                        btn, model, item
                    ),
                    style=ui_c.STYLE_PROPERTY_LIST,
                    enabled=self._can_edit,
                )
                with props_widget:
                    # NAME
                    ui.Spacer(width=5)
                    with ui.ZStack(style={"margin": 0, "padding": 0}):
                        ui.Spacer(height=40)
                        ui.Rectangle(style={"background_color": ui_c.COLORS.CLR_3})
                        with ui.HStack(style={"margin": 0, "padding": 2, "border_radius": 2}):
                            ui.Spacer(width=5)
                            prop_widget = ui.VStack(content_clipping=1, enabled=self._can_edit)
                            with prop_widget:
                                if type(item.data.prop) == Usd.Attribute or type(item.data.prop) == Sdf.AttributeSpec:
                                    ui.Spacer()
                                    item.attr_model = UsdVariantPropertiesWidgetBuilder.build(
                                        model._editor_core._stage,
                                        item.data.name,
                                        item.data.metadata,
                                        Usd.Attribute,
                                        [Sdf.Path(item.data.path).GetPrimPath()],
                                        additional_label_kwargs={
                                            "enabled": self._can_edit,
                                            "style": ui_c.STYLE_PROPERTY_CARD,
                                            "prop_path": item.data.path,
                                        },
                                        additional_widget_kwargs={
                                            "style": ui_c.STYLE_PROPERTY_CONTENTS,
                                            "enabled": self._can_edit,
                                        },
                                    )
                                    ui.Spacer()
                                # Use Relationship Builder for Relationships.  Does not need or accept a "type" arg
                                elif (
                                    type(item.data.prop) == Usd.Relationship
                                    or type(item.data.prop) == Sdf.RelationshipSpec
                                ):
                                    if item.data.name == "material:binding":
                                        VariantMaterialBindingWidgetBuilder.build_material_binding(
                                            model._editor_core._stage,
                                            item.data.name,
                                            item.data.metadata,
                                            [Sdf.Path(item.data.path).StripAllVariantSelections().GetPrimPath()],
                                            self._can_edit,
                                        )
                                    else:
                                        ui.Spacer(height=13)
                                        item.attr_model = UsdVariantPropertiesWidgetBuilder.build(
                                            model._editor_core._stage,
                                            item.data.name,
                                            item.data.metadata,
                                            Usd.Relationship,
                                            [Sdf.Path(item.data.path).StripAllVariantSelections().GetPrimPath()],
                                            additional_label_kwargs={
                                                "enabled": self._can_edit,
                                                "style": ui_c.STYLE_PROPERTY_CARD,
                                                "prop_path": item.data.path,
                                            },
                                            additional_widget_kwargs={
                                                "style": ui_c.STYLE_PROPERTY_CONTENTS,
                                                "enabled": self._can_edit,
                                            },
                                        )
                                        ui.Spacer(height=13)
                                # Use UsdVariantPayloadReferenceWidget for References
                                elif item.data.type == PropertyCard.REFERENCES:
                                    ui.Spacer(height=13)
                                    with ui.HStack(spacing=4):
                                        UsdVariantPropertiesWidgetBuilder.create_label(
                                            item.data.name,
                                            item.data.metadata,
                                            additional_label_kwargs={
                                                "tooltip": ui_c.TOOLTIP_LABEL_REFERENCES,
                                                "is_references": True,
                                                "prop_path": item.data.prim_path,
                                            },
                                        )
                                        stage = weakref.ref(model._editor_core._stage)
                                        pspayload = PrimSelectionPayload(stage, item.data.properties)
                                        payref_widget = UsdVariantPayloadReferenceWidget(
                                            model,
                                            item,
                                            Sdf.Path(item.data.prim_path).StripAllVariantSelections(),
                                            use_payloads=False,
                                        )
                                        payref_widget.on_new_payload(pspayload)
                                        payref_widget.build_items()
                                        item.attr_model = payref_widget
                                        payref_widget.enabled = self._can_edit
                                    ui.Spacer(height=13)
                                # Use UsdVariantPayloadReferenceWidget for Payloads
                                elif item.data.type == PropertyCard.PAYLOADS:
                                    ui.Spacer(height=13)
                                    with ui.HStack(spacing=4):
                                        UsdVariantPropertiesWidgetBuilder.create_label(
                                            item.data.name,
                                            item.data.metadata,
                                            additional_label_kwargs={
                                                "tooltip": ui_c.TOOLTIP_LABEL_PAYLOADS,
                                                "is_payloads": True,
                                                "prop_path": item.data.prim_path,
                                            },
                                        )
                                        stage = weakref.ref(model._editor_core._stage)
                                        pspayload = PrimSelectionPayload(stage, item.data.properties)
                                        payref_widget = UsdVariantPayloadReferenceWidget(
                                            model,
                                            item,
                                            Sdf.Path(item.data.prim_path).StripAllVariantSelections(),
                                            use_payloads=True,
                                        )
                                        payref_widget.on_new_payload(pspayload)
                                        payref_widget.build_items()
                                        item.attr_model = payref_widget
                                        payref_widget.enabled = self._can_edit
                                    ui.Spacer(height=13)
                                elif type(item.data.prop) == Usd.VariantSet:
                                    ui.Spacer()
                                    with ui.HStack(spacing=4):
                                        stage = weakref.ref(model._editor_core._stage)
                                        pspayload = PrimSelectionPayload(stage, [item.data.prim_path])
                                        vset_widget = VariantsWidget(
                                            item.data.name,
                                            item.data.prim_path,
                                            item.data.path,
                                        )
                                        vset_widget.on_new_payload(pspayload)
                                        vset_widget.build_items()
                                        vset_widget.enabled = self._can_edit
                                    ui.Spacer()

                            ui.Spacer(width=5)
                            with ui.HStack(width=20):
                                # "X" buttons for removing a variant
                                remove_prop_widget = ui.VStack(
                                    identifier="remove_prop_widget vstack",  # for unit test
                                    mouse_pressed_fn=lambda x, y, btn, flag, model=model, item=item: (
                                        self._on_prop_item_delete(btn, model, item) if self._can_edit else None
                                    ),
                                )
                                with remove_prop_widget:
                                    with ui.VStack():
                                        ui.Spacer()
                                        ui.ImageWithProvider(
                                            f"{ui_c.PATH_EXTENSION}{ui_c.PATH_ICON_CIRCLE_X}",
                                            width=18,
                                            height=18,
                                            style=ui_c.STYLE_ROUND_REMOVE_BUTTON,
                                        )
                                        ui.Spacer()
                            ui.Spacer(width=5)
                        if not self._can_edit:
                            with ui.VStack(tooltip=tooltip_text, style=ui_c.STYLE_TOOLTIP):
                                OverlayBlocker()

    def _create_tooltip(self, text: str):
        with ui.ZStack(style=ui_c.STYLE_TOOLTIP):
            ui.Rectangle()
            ui.Label(text, style=ui_c.STYLE_TOOLTIP_TEXT)

    def _on_prim_item_clicked(self, btn: int, model: VariantTreeModel, item: PrimCardItem) -> None:
        if btn != 1:
            return True

        if self._context_menu is not None:
            self._context_menu.clear()
        with self._context_menu:
            ui.MenuItem(
                "Remove Item",
                triggered_fn=lambda model=model, item=item: self._on_prim_item_delete(model, item),
            )
            ui.MenuItem(
                "Select Prim In Stage",
                triggered_fn=lambda i=item: self._select_prim(model, item),
            )
            ui.MenuItem(
                "Copy All Properties",
                triggered_fn=lambda btn=0, model=model, item=item: self._on_prim_item_copy(btn, model, item),
            )
            if model.can_paste_to_prim(item):
                self._paste_prim = ui.MenuItem(
                    "Paste Property",
                    triggered_fn=lambda btn=0, model=model, item=item: self._on_prim_item_paste(btn, model, item),
                )
            elif model.can_paste_all_to_prim(item):
                self._paste_prim_all = ui.MenuItem(
                    "Paste All Properties",
                    triggered_fn=lambda btn=0, model=model, item=item: self._on_prim_item_paste(btn, model, item),
                )
        if self._can_edit:
            self._context_menu.show()

        return True

    def _on_prim_item_hover(self, item: PrimCardItem, hovered: bool) -> None:
        pass

    def _on_prim_item_delete(self, model: VariantTreeModel, item: PrimCardItem) -> None:
        if not model._editor_core.validate_variant_edit():
            return

        model.remove_item(item)

    def _on_prim_item_copy(self, btn: int, model: VariantTreeModel, item: PrimCardItem) -> None:
        if btn == 0:
            model.copy_variant_prim(item)

    def _on_prim_item_paste(self, btn: int, model: VariantTreeModel, item: PrimCardItem) -> None:
        if btn == 0:
            model.paste_to_variant_prim(item)

    def _select_prim(self, model: VariantTreeModel, item: PrimCardItem):
        selection = model._editor_core._usd_context.get_selection()
        prim_path = model.get_item_value_model(item, Column.NAME).as_string
        selection.set_selected_prim_paths([prim_path], True)

    def _on_prop_item_clicked(self, btn: int, model: VariantTreeModel, item: PropertyCardItem) -> None:
        if btn != 1:
            return True

        if self._context_menu is not None:
            self._context_menu.clear()

        with self._context_menu:
            ui.MenuItem(
                "Remove Property",
                triggered_fn=lambda btn=0, model=model, item=item: self._on_prop_item_delete(btn, model, item),
            )
            ui.MenuItem(
                "Copy",
                triggered_fn=lambda btn=0, model=model, item=item: self._on_prop_item_copy(btn, model, item),
            )
            if model.can_paste_to_prop(item):
                self._paste_prop = ui.MenuItem(
                    "Paste",
                    triggered_fn=lambda btn=0, model=model, item=item: self._on_prop_item_paste(btn, model, item),
                )
        if self._can_edit:
            self._context_menu.show()

        return True

    def _on_prop_item_delete(self, btn: int, model: VariantTreeModel, item: PropertyCardItem) -> None:
        if not model._editor_core.validate_variant_edit():
            return

        if btn == 0:
            model.remove_item(item)

    def _on_prop_item_copy(self, btn: int, model: VariantTreeModel, item: PropertyCardItem) -> None:
        if btn == 0:
            model.copy_variant_prop(item)

    def _on_prop_item_paste(self, btn: int, model: VariantTreeModel, item: PropertyCardItem) -> None:
        if btn == 0:
            model.paste_to_variant_prop(item)

    # Collect data in order to make property cards for the property list
    async def _on_props_picked(
        self,
        cards: list(PropertyCard),
        item: PrimCardItem,
        model: VariantTreeModel,
        add_all: bool,
    ):
        # For each "property" selected, collect information about that property
        # Get the property list associated with this prim card and collect all the existing cards
        property_card_items = item.children[1:]

        async def add_props(prim_items):
            with omni.kit.undo.group():
                invalid_prims = []
                for prim_item in prim_items:

                    prim_path = Sdf.Path(prim_item.data.path).StripAllVariantSelections().pathString
                    for card in cards:
                        if "VariantSet" in card.data.name:
                            pass

                        if card.data.name == "Reference" or card.data.name == "Payload":
                            # If "reference" or "payload" was selected, open window to select asset
                            asset_path = await pick_ref_asset(model)
                            if asset_path:
                                model.add_ref_or_payload_variant_to_prim(
                                    prim_item, prim_path, asset_path, card.data.name
                                )
                            else:
                                carb.log_warn("No valid asset path provided.")

                    card_paths = [
                        Sdf.Path(card_item.data.path).StripAllVariantSelections().pathString
                        for card_item in property_card_items
                    ]

                    for card in cards:
                        # If a card already exists for a given property, skip it and move onto the next one
                        if card.data.path in card_paths:
                            continue

                        if add_all:
                            # If a prim doesn't already contain a given property, skip it.
                            # We don't want to create new properties when doing an "add all" operation, only add overs for existing properties
                            prim_path = Sdf.Path(prim_item.data.path).StripAllVariantSelections()
                            attr_string = Sdf.Path(card.data.path).elementString[1:]
                            prim_has_prop = model._editor_core.check_prim_for_property(prim_path, attr_string)
                            if not prim_has_prop:
                                invalid_prims.append(prim_path)
                                continue

                        # If the property is a PlaceholderAttribute, create the attribute
                        if type(card.data.prop) == PlaceholderAttribute:
                            attribute = card.data.prop.CreateAttribute(
                                set_default_value=False
                            )  # don't set the default value because it'll become a stonger opinion than the variant opinion
                            # replace Placeholder since the attribute is now created
                            card.data.prop = attribute

                        # Collect information about the property
                        if type(card.data.prop) in [
                            Usd.Attribute,
                            Sdf.AttributeSpec,
                            Usd.Relationship,
                            Sdf.RelationshipSpec,
                            Usd.Property,
                            Sdf.PropertySpec,
                        ]:

                            model.add_property_variant_to_prim(prim_item, card)

                        if type(card.data.prop) in [Usd.VariantSet]:
                            propName = card.data.name.split("VariantSet: ")[-1]
                            model.add_property_variant_to_prim(prim_item, card, propName)

                if len(invalid_prims) == 1:
                    nm.post_notification(
                        f"{invalid_prims[0]} doesn't contain the property {card.data.name} so it was skipped.",
                        duration=3,
                        status=nm.NotificationStatus.INFO,
                    )
                elif 1 < len(invalid_prims) <= 5:
                    path_list = "\n".join(map(str, invalid_prims))
                    nm.post_notification(
                        f"The following {len(invalid_prims)} prims don't contain the property {card.data.name} so they were skipped \n{path_list}",
                        duration=3,
                        status=nm.NotificationStatus.INFO,
                    )
                elif len(invalid_prims) > 5:
                    path_list = "\n".join(map(str, invalid_prims[:5])) + "\n ..."
                    nm.post_notification(
                        f"The following {len(invalid_prims)} prims don't contain the property {card.data.name} so they were skipped \n{path_list}",
                        duration=3,
                        status=nm.NotificationStatus.INFO,
                    )

        if add_all:
            prim_items = []
            variant_item = model.get_parent_item(item)
            if variant_item.children:
                for prim in variant_item.children:
                    prim_items.append(prim)
                    continue
                asyncio.ensure_future(add_props(prim_items))
        else:
            asyncio.ensure_future(add_props([item]))


class HighlightRect(ui.Rectangle):
    def __init__(self, model: VariantTreeModel, item, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_sub = get_eventdispatcher().observe_event(
            observer_name="variant.editor.alpha_fade",
            event_name=omni.kit.app.GLOBAL_EVENT_UPDATE,
            on_event=self.__on_update,
        )

        self.__alpha = 0.66
        self._model = model
        self._item = item

    def __on_update(self, event: carb.eventdispatcher.Event):
        dt = event["dt"]
        self.__alpha = max(0, self.__alpha - dt * 0.33)
        if self.__alpha <= 0:
            self._update_sub = None
            self.visible = False
            self._item.data.highlight = False
            return

        self.set_style({"background_color": ui.color(0.062, 0.757, 1.0, self.__alpha)})


class OverlayBlocker(ui.Rectangle):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_style({"background_color": ui.color(0.3, 0.3, 0.3, 0.66)})
