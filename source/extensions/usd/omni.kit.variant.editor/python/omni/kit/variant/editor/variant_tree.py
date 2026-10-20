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
from typing import Dict, Optional, Union

import carb
import omni.kit.app
import omni.kit.notification_manager as nm
import omni.ui as ui
from pxr import Sdf, Tf, Usd

from . import editor_const as e_c
from . import ui_const as ui_c
from .core import VariantEditorCore, get_mdl_subids, has_local_opinion
from .list import ListModel, ListView
from .prop_selector import PropertySelectionCard
from .variant_property_models import (
    GfVecAttributeModelVariant,
    MdlEnumAttributeModelVariant,
    TfTokenAttributeModelVariant,
    UsdAttributeModelVariant,
    UsdVariant,
)
from .variant_tree_items import (
    Column,
    PrimCard,
    PrimCardItem,
    PropertyCard,
    PropertyCardItem,
    VariantCard,
    VariantCardItem,
    VariantSetCard,
    VariantSetCardItem,
    VariantTreeHelperItem,
)


class VariantTreeModel(ListModel):
    """
    Tree model to store variant set, variant and property data
    """

    def __init__(self):
        super().__init__(enable_drag_drop=True)
        # Get the Variant Editor Core instance
        self._editor_core = VariantEditorCore.get_instance()
        self._tree_view = None
        self._clipboard: Dict = None
        self._expanded_state: Dict[str, bool] = {}
        self._tree = None

        self._cmd_callback_ids = []
        self._cmd_callback_ids.append(
            omni.kit.commands.register_callback(
                "EditVariant",
                omni.kit.commands.POST_DO_CALLBACK,
                self._post_edit_variant_command,
            )
        )
        self._cmd_callback_ids.append(
            omni.kit.commands.register_callback(
                "EditVariant",
                omni.kit.commands.POST_UNDO_CALLBACK,
                self._post_edit_variant_command,
            )
        )
        self._cmd_callback_ids.append(
            omni.kit.commands.register_callback(
                "RefreshVariantUi",
                omni.kit.commands.POST_DO_CALLBACK,
                self._post_edit_variant_command,
            )
        )
        self._cmd_callback_ids.append(
            omni.kit.commands.register_callback(
                "RefreshVariantUi",
                omni.kit.commands.POST_UNDO_CALLBACK,
                self._post_edit_variant_command,
            )
        )
        self._cmd_callback_ids.append(
            omni.kit.commands.register_callback(
                "PasteVariant",
                omni.kit.commands.POST_DO_CALLBACK,
                self._post_edit_variant_command,
            )
        )
        self._cmd_callback_ids.append(
            omni.kit.commands.register_callback(
                "PasteVariant",
                omni.kit.commands.POST_UNDO_CALLBACK,
                self._post_edit_variant_command,
            )
        )

        self._editor_core.bind_to(self._on_set_active_variant)

    def _on_set_active_variant(self, variant_path, prev_variant_path):
        def item_changed(item):
            if isinstance(item, VariantSetCardItem):
                self._item_changed(item)
                for child in item.children:
                    self._item_changed(child)
            else:
                self._item_changed(item)
                for child in item.children:
                    item_changed(child)

        # Clear previous
        prev_item = self.get_active_variant_card_item_by_path(prev_variant_path)
        if prev_item is not None:
            item_changed(prev_item)

        # update newly selected variant in this set
        item = self.get_active_variant_card_item_by_path(variant_path)
        if item is not None:
            item_changed(item)  # Refresh properties of selected variant
            item_changed(self.get_parent_item(item))  # Refresh variant set

        # update previous selected variant item in the same set
        prev_variant_card_item = self.get_active_variant_card_item_by_path(prev_variant_path)
        if prev_variant_card_item is not None:
            item_changed(self.get_parent_item(prev_variant_card_item))  # Refresh variant set

    def destroy(self):
        self.clear()
        self._tree_view = None
        self._expanded_state = {}
        for id in self._cmd_callback_ids:
            omni.kit.commands.unregister_callback(id)
        self._cmd_callback_ids.clear()

    def clear(self):
        for child_item in self._children:
            child_item.destroy()

        self._children.clear()
        self._item_changed(None)

        self._editor_core.active_variant = None

    def insert_item(self, item, index=-1):
        """Insert item into list model"""
        if index < 0:
            self._children.append(item)
        else:
            self._children.insert(index, item)
        self._children.sort()
        self._item_changed(None)

    def can_item_have_children(self, item=None):
        # We don't want to show any children down the hierarchy except VariantSetCarItem
        if item is not None:
            if isinstance(item, VariantSetCardItem) or isinstance(item, PrimCardItem):
                return True

        return False

    def get_item_children(self, item=None):
        if item is None:
            return self._children

        return item.children

    def get_parent_item(self, item):
        if isinstance(item, VariantCardItem):
            for vset_item in self._children:
                if item in vset_item.children:
                    return vset_item

        elif isinstance(item, PrimCardItem):
            for vset_item in self._children:
                for v_item in vset_item.children:
                    if item in v_item.children:
                        return v_item

        elif isinstance(item, PropertyCardItem) or isinstance(item, VariantTreeHelperItem):
            for vset_item in self._children:
                for v_item in vset_item.children:
                    for prim_item in v_item.children:
                        if item in prim_item.children:
                            return prim_item

        return None

    def get_active_variant_card_item_by_name(self, vset_name: str, variant_name: str) -> VariantCardItem:
        # Search through data structure to find the item holding this variant
        for variant_set_item in self._children:
            if variant_set_item.data.name == vset_name:
                for variant_item in variant_set_item.children:
                    if variant_item.data.name == variant_name:
                        return variant_item

        return None

    def get_active_variant_card_item_by_path(self, variant_path: str) -> VariantCardItem:
        # Search through data structure to find the item holding this variant
        for variant_set_item in self._children:
            for variant_item in variant_set_item.children:
                if variant_item.data.path == variant_path:
                    return variant_item

        return None

    def get_layer_with_strongest_opinion_on_variant_selection(self, vset_name: str):
        # Iterate through layers in layer stack to find out which layer holds the strongest opinion on variant selection
        variant_selection_strongest_layer = None

        layer_stack: list = self._editor_core._stage.GetLayerStack()
        for layer in layer_stack:
            # Iterate through each layer from highest to lowest in layer stack, find out which layer holds the strongest opinion on variant selection
            prim_spec: Sdf.PrimSpec = layer.GetPrimAtPath(self._editor_core._get_root_prim_path())
            if prim_spec is not None:
                prim_variant_selections: dict = prim_spec.variantSelections
                if vset_name in prim_variant_selections:
                    variant_selection_strongest_layer = layer
                    break

        return variant_selection_strongest_layer

    def record_expand_state(self, item: VariantSetCardItem):
        if item is not None and self._tree:
            if item.data.name not in self._expanded_state.keys():
                self._expanded_state[item.data.name] = True
            else:
                self._expanded_state[item.data.name] = self._tree().is_expanded(item)

    def get_expanded(self, key: str):
        if key in self._expanded_state.keys():
            return self._expanded_state[key]
        else:
            return True

    def reset_expanded(self):
        self._expanded_state = {}

    def _post_edit_variant_command(self, info):
        if self._editor_core.authoring_variant:
            return

        for vset_item in self._children:
            for variant_item in vset_item.children:
                self._populate_prim_list(variant_item)
                self._item_changed(variant_item)
                if self._tree_view:
                    self._tree_view().set_expanded(variant_item, True, True)

    # Show Variant Sets that exist on target prim
    def _populate_variant_set_list(self):
        # Load all existing variant
        for child in self._children:
            self.record_expand_state(child)
        real_variant_set_names = self._editor_core._collect_variant_sets()
        self._children.clear()

        root_path = self._editor_core._get_root_prim_path()

        # Load variant sets
        for variant_set_name in real_variant_set_names:
            set_path: Sdf.Path = root_path.AppendVariantSelection(variant_set_name, "")
            vset_card = VariantSetCard.create(
                name=variant_set_name,
                type=VariantSetCard.VARIANTSET,
                path=set_path.pathString,
            )
            vset_item = VariantSetCardItem(vset_card, 0)
            self._children.append(vset_item)
            self._populate_variant_list(vset_item)

        self._item_changed(None)
        for vset_item in self._children:
            self._item_changed(vset_item)

    def _populate_variant_list(self, vset_item: VariantSetCardItem):
        # Load variants

        vset_item.children.clear()

        root_path = self._editor_core._get_root_prim_path()

        variant_set_name = vset_item.data.name
        v_set = self._editor_core._get_variant_set_by_name(variant_set_name)
        active_variant_in_set = v_set.GetVariantSelection()

        variants = self._editor_core._get_variants_from_set(variant_set_name)
        for variant in variants:
            vpath: Sdf.Path = root_path.AppendVariantSelection(variant_set_name, variant)
            is_activated = active_variant_in_set == variant
            vcard = VariantCard.create(
                VariantCard.VARIANT,
                name=variant,
                path=vpath.pathString,
                activated=is_activated,
            )
            vcard_item = VariantCardItem(vcard, 0)
            vset_item.add_child_item(vcard_item)

            self._populate_prim_list(vcard_item)

    def _populate_prim_list(self, variant_item: VariantCardItem, new_prims: list = None):
        # Load prims
        variant_item.children.clear()

        vpath = variant_item.data.path

        prim_paths = self._editor_core._check_specs_for_properties(vpath)
        if prim_paths:
            if new_prims:
                prim_paths.update(new_prims)
            prim_paths = sorted(prim_paths)
            for path in prim_paths:
                asyncio.ensure_future(self._editor_core.process_prim(path))
                highlight = False
                if new_prims:
                    if path in new_prims:
                        highlight = True
                prim_name = Sdf.Path(path).StripAllVariantSelections().pathString
                if isinstance(path, str):
                    path = Sdf.Path(path)
                prim_card = PrimCard.create(
                    name=prim_name,
                    type=PrimCard.PRIM,
                    path=path.pathString,
                    highlight=highlight,
                )
                prim_card_item = PrimCardItem(prim_card, 0)
                variant_item.add_child_item(prim_card_item)

                self._populate_property_list(prim_card_item)

    def _populate_property_list(self, prim_item: PrimCardItem):
        # Load properties
        prim_item._children = prim_item._children[:1]  # First item is VariantHelperItem

        prim_path = Sdf.Path(prim_item.data.path)

        edit_target_layer = self._editor_core._get_edit_target_layer()
        existing_card_paths = []

        # Make a fresh empty set of properties/payloads/references
        vproperty_set = set()
        vpayload_set = set()
        vreference_set = set()
        vvariant_selection_set = set()
        vspec = self._editor_core.find_spec_in_variant(prim_path)
        if isinstance(vspec, Sdf.VariantSpec):
            # Collect all the properties, payloads, and references from the prim spec.
            vproperty_set.update(vspec.primSpec.properties)
            vpayload_set.update(vspec.primSpec.payloadList.GetAddedOrExplicitItems())
            vreference_set.update(vspec.primSpec.referenceList.GetAddedOrExplicitItems())
            vvariant_selection_set.update(vspec.primSpec.variantSelections)
        if isinstance(vspec, Sdf.PrimSpec):
            vproperty_set.update(vspec.properties)
            vpayload_set.update(vspec.payloadList.GetAddedOrExplicitItems())
            vreference_set.update(vspec.referenceList.GetAddedOrExplicitItems())
            vvariant_selection_set.update(vspec.variantSelections)

        for prop in vproperty_set:
            prop_path = prop.path.ReplacePrefix(vspec.path, prim_path)
            usd_path = prop_path.StripAllVariantSelections()

            # Collect information about each relationship
            if isinstance(prop, Sdf.RelationshipSpec):
                prop_name = prop.name
                usd_prop = self._editor_core._stage.GetPropertyAtPath(usd_path)
                if isinstance(usd_prop, Usd.Object):
                    prop_metadata = {}
                else:
                    prop_metadata = usd_prop.GetAllMetadata()

            # Collect information about each attribute
            if isinstance(prop, Sdf.AttributeSpec):
                prop_name = prop.name
                prop_metadata = {}
                usd_prop = self._editor_core._stage.GetAttributeAtPath(usd_path)
                try:
                    usd_prop_metadata = usd_prop.GetAllMetadata()
                    prop_metadata.update(usd_prop_metadata)
                except:
                    pass

                if prop_name == "info:mdl:sourceAsset:subIdentifier":
                    try:
                        source_asset_attr = usd_prop.GetPrim().GetAttribute("info:mdl:sourceAsset")
                        if source_asset_attr:
                            sub_id_attr = usd_prop.GetPrim().GetAttribute("info:mdl:sourceAsset:subIdentifier")
                            if has_local_opinion(self._editor_core._stage, sub_id_attr.GetPath()):
                                mdl_path = source_asset_attr.Get().resolvedPath
                            else:
                                mdl_path = vspec.attributes["info:mdl:sourceAsset"].default.path

                            if mdl_path:
                                prop_metadata["allowedTokens"] = get_mdl_subids(mdl_path)
                    except:
                        carb.log_warn(f"Failed to retrieve subids for {prop_name}")

                mdKeys = prop.GetMetaDataInfoKeys()
                for key in mdKeys:
                    if prop.GetInfo(key):
                        info = prop.GetInfo(key)
                        prop_metadata.update({key: info})

                cpp_type_name = prop.typeName.cppTypeName
                # Skip properties that aren't currently supported for direct editing
                if "VtArray" in str(cpp_type_name):
                    continue
            # Skip properties that already have property cards
            if prop_path in existing_card_paths:
                continue

            existing_card_paths.append(prop_path)
            # Make property cards for any actual property (Attributes and Relationships)
            card = PropertyCard.create(
                type=PropertyCard.PROPERTY,
                name=prop_name,
                path=prop_path.pathString,
                prop=prop,
                metadata=prop_metadata,
                layer=edit_target_layer,
                prim_path=prim_path.StripAllVariantSelections(),
            )
            card_item = PropertyCardItem(card, 0)
            prim_item.add_child_item(card_item)

        # Collect information about payloads
        if len(vpayload_set):
            prop_name = "Payloads"
            prop_metadata = {}
            # Create a card for the payloadS
            card = PropertyCard.create(
                type=PropertyCard.PAYLOADS,
                name=prop_name,
                path="",
                prop="",
                metadata=prop_metadata,
                layer=edit_target_layer,
                prim_path=prim_path.pathString,
                payloads=[payload for payload in vpayload_set],
            )
            card_item = PropertyCardItem(card, 0)
            prim_item.add_child_item(card_item)

        # Collect information about references
        if len(vreference_set):
            prop_name = "References"
            prop_metadata = {}
            # Create a card for the referenceS
            card = PropertyCard.create(
                type=PropertyCard.REFERENCES,
                name=prop_name,
                path="",
                prop="",
                metadata=prop_metadata,
                layer=edit_target_layer,
                prim_path=prim_path.pathString,
                references=[reference for reference in vreference_set],
            )
            card_item = PropertyCardItem(card, 0)
            prim_item.add_child_item(card_item)

        for variant_selection in vvariant_selection_set:
            prop_name = variant_selection
            prop_path = prim_path
            vset = self._editor_core._get_variant_set_by_name(prop_name)
            prop_metadata = {}
            card = PropertyCard.create(
                type=PropertyCard.PROPERTY,
                name=prop_name,
                path=prop_path.pathString,
                prop=vset,
                metadata=prop_metadata,
                layer=edit_target_layer,
                prim_path=prim_path.pathString,
            )
            card_item = PropertyCardItem(card, 0)
            prim_item.add_child_item(card_item)

    def add_variant_set(self):
        # Only create new variant set if:
        # Existing variant sets are authored in current layer
        # Or there is no existing variant sets
        if len(self._children) > 0:
            test_variant_set = self._children[0]
            test_variant_set_path = test_variant_set.data.path
            vspec = self._editor_core._get_prim_spec_from_path(test_variant_set_path)
            if not vspec:
                variant_layer_name = "another layer."
                authored_layer = self._editor_core._get_variant_authored_layer(Sdf.Path(test_variant_set_path))
                if authored_layer is not None:
                    authored_layer_name = authored_layer.GetDisplayName()
                    variant_layer_name = (
                        f'layer: "{authored_layer_name}".\nPlease switch to that layer to add new variant.'
                    )

                nm.post_notification(
                    f"Couldn't create new variant set because current sets were authored in {variant_layer_name}",
                    status=nm.NotificationStatus.WARNING,
                )

                return None

        variant_set_name = self._editor_core._create_variant_set(e_c.DEFAULT_VARIANT_SET_NAME)
        root_path = self._editor_core._get_root_prim_path()
        vset_path = root_path.AppendVariantSelection(variant_set_name, "")
        card = VariantSetCard.create(
            name=variant_set_name,
            type=VariantSetCard.VARIANTSET,
            path=vset_path.pathString,
        )
        card_item = VariantSetCardItem(card, 0)

        self._children.append(card_item)

        self._item_changed(None)

        return variant_set_name

    def add_variant(self, variant_set_item: VariantSetCardItem):
        # Check if current layer is the authoring layer
        vset_path = variant_set_item.data.path
        vspec = self._editor_core._get_prim_spec_from_path(vset_path)

        if vspec:
            vset_name = variant_set_item.name_model.as_string

            vname = self._editor_core._create_variant(vset_name, e_c.DEFAULT_VARIANT_NAME)

            root_path = self._editor_core._get_root_prim_path()
            vpath = root_path.AppendVariantSelection(vset_name, vname)
            vcard = VariantCard.create(type=VariantCard.VARIANT, name=vname, path=vpath.pathString)
            vcard_item = VariantCardItem(vcard, 0)
            variant_set_item.add_child_item(vcard_item)

            self._item_changed(variant_set_item)
            self._item_changed(vcard_item)
            self._populate_prim_list(vcard_item)
        else:
            variant_layer_name = "another layer."
            authored_layer = self._editor_core._get_variant_authored_layer(Sdf.Path(vset_path))
            if authored_layer is not None:
                authored_layer_name = authored_layer.GetDisplayName()
                variant_layer_name = f'layer: "{authored_layer_name}".\nPlease switch to that layer to add new variant.'

            nm.post_notification(
                f"Couldn't create new variant because current set was authored in {variant_layer_name}",
                status=nm.NotificationStatus.WARNING,
            )

    def ensure_add_prims_to_variant(self, paths: list[str]):
        asyncio.ensure_future(self.add_prims_to_variant_async(paths))

    async def add_prims_to_variant_async(self, paths: list[str]):
        if not self._editor_core.validate_variant_edit():
            return

        for prim_path in paths:
            await self._editor_core.process_prim(prim_path)

        await omni.kit.app.get_app().next_update_async()

        add_to_all = self._editor_core.add_props_to_all_variants
        target_and_children = []
        target_prim = self._editor_core._stage.GetPrimAtPath(self._editor_core._target_prim_path)
        target_children = self.get_all_children(target_prim)
        target_and_children.append(self._editor_core._target_prim_path)
        for child in target_children:
            target_and_children.append(child)

        variant_path = self._editor_core.active_variant

        def add_prim_card_to_variant_card(variant_path):
            variant_item: VariantCardItem = self.get_active_variant_card_item_by_path(variant_path)
            if variant_item is not None:
                prim_items_to_refresh = []
                for path in paths:
                    if path in target_and_children and bool(self._editor_core.active_variant):
                        name = Sdf.Path(path).name
                        stem = Sdf.Path(path).pathString.split(self._editor_core._target_prim_path + "/")[-1]
                        if path == self._editor_core._target_prim_path:
                            vPath = Sdf.Path(variant_path)
                        else:
                            vPath = Sdf.Path(variant_path).AppendPath(stem)

                        # Check if this prim exists in current variant to avoid prim card duplicates
                        prim_exists_in_variant = False
                        for child_prim in variant_item.children:
                            if child_prim.data.path == vPath:
                                prim_exists_in_variant = True
                                break

                        if prim_exists_in_variant:
                            if variant_path == self._editor_core.active_variant:
                                nm.post_notification(
                                    f"{vPath.StripAllVariantSelections()} exists in this variant",
                                    duration=3,
                                    status=nm.NotificationStatus.INFO,
                                )

                            continue

                        prim_card = PrimCard.create(name=path, type=PrimCard.PRIM, path=vPath, highlight=True)
                        prim_card_item = PrimCardItem(prim_card, 0)

                        relative_path = Sdf.Path(path).MakeRelativePath(
                            Sdf.Path(self._editor_core._get_root_prim_path())
                        )
                        self._editor_core._add_target_prim_metadata(variant_path, relative_path)

                        variant_item.add_child_item(prim_card_item)

                        prim_items_to_refresh.append(prim_card_item)

                    else:
                        nm.post_notification(
                            f"Only {target_prim} or its descendents can be modified by this variant",
                            duration=3,
                            status=nm.NotificationStatus.INFO,
                        )

                self._item_changed(variant_item)
                for item_to_refresh in prim_items_to_refresh:
                    self._item_changed(item_to_refresh)

            prim_paths_to_highlight = []
            for item in prim_items_to_refresh:
                prim_paths_to_highlight.append(item.data.path)

        def add_prims_to_all_variants_in_set():
            active_set_name = Sdf.Path(self._editor_core.active_variant).GetVariantSelection()[0]
            variant_names = self._editor_core._get_variants_from_active_set()
            for name in variant_names:
                variant_path = (
                    Sdf.Path(self._editor_core.active_variant)
                    .GetParentPath()
                    .AppendVariantSelection(active_set_name, name)
                )
                add_prim_card_to_variant_card(variant_path)

        if add_to_all:
            add_prims_to_all_variants_in_set()
        else:
            add_prim_card_to_variant_card(variant_path)

    def add_ref_or_payload_variant_to_prim(
        self,
        prim_item: PrimCardItem,
        prim_path,
        asset_path,
        ref_or_payload_type_name: str,
    ):
        if isinstance(asset_path, list):
            asset_path = asset_path[0]
            # Create the actual reference via Core
            self._editor_core._add_ref_or_payload(prim_path, ref_or_payload_type_name, asset_path)

            # Collect information about the payrefs
            edit_target_layer = self._editor_core._get_edit_target_layer()
            vset_name = self._editor_core._get_active_variant_set()
            vset = self._editor_core._get_variant_set_by_name(vset_name)
            prim_spec = vset.GetVariantEditTarget().GetPrimSpecForScenePath(prim_path)

            if ref_or_payload_type_name == "Reference":
                type = PropertyCard.REFERENCES

                # Create a card for the referenceS
                card = PropertyCard.create(
                    type=type,
                    name="References",
                    path="",
                    prop="",
                    metadata={},
                    layer=edit_target_layer,
                    prim_path=str(prim_path),
                    references=prim_spec.referenceList.GetAddedOrExplicitItems(),
                )
            else:
                type = PropertyCard.PAYLOADS

                # Create a card for the payloadS
                card = PropertyCard.create(
                    type=type,
                    name="Payloads",
                    path="",
                    prop="",
                    metadata={},
                    layer=edit_target_layer,
                    prim_path=str(prim_path),
                    payloads=prim_spec.payloadList.GetAddedOrExplicitItems(),
                )

            # remove the old payrefs ui widget, if exist
            properties = prim_item.children[1:]
            for index, pr in enumerate(properties):
                if pr.data.type == type:
                    prim_item.children.pop(index + 1)
                    break

            # add the new payrefs ui widget
            prop_card_item = PropertyCardItem(card, 0)
            prim_item.add_child_item(prop_card_item)

            self._item_changed(prim_item)

    def add_property_variant_to_prim(
        self,
        prim_item: PrimCardItem,
        prop_card: PropertySelectionCard,
        override_prop_name="",
    ):

        def create_property_card(prop, prop_name, prim_item):
            if prop is not None:
                if type(prop) == Usd.VariantSet:
                    prop_name = prop_name
                    prop_path = Sdf.Path(prim_item.data.path).pathString
                    prop_metadata = {}
                    layer = self._editor_core._get_edit_target_layer()
                    # Create the property card
                    pcard = PropertyCard.create(
                        type=PropertyCard.PROPERTY,
                        name=prop_name,
                        path=prop_path,
                        prop=prop,
                        metadata=prop_metadata,
                        layer=layer,
                        prim_path=prim_item.data.path,
                    )
                    pcard_item = PropertyCardItem(pcard, 0)
                    prim_item.add_child_item(pcard_item)

                    self._item_changed(prim_item)
                    return pcard_item

                else:
                    prop_path = prop.GetPath().pathString
                    prop_metadata = prop.GetAllMetadata()
                    if prop_name == "info:mdl:sourceAsset:subIdentifier":
                        try:
                            prop_metadata["allowedTokens"] = get_mdl_subids(
                                prop.GetPrim().GetAttribute("info:mdl:sourceAsset").Get().resolvedPath
                            )
                        except:
                            carb.log_error(f"Unable to retrieve allowed tokens for {prop_name}")

                    layer = self._editor_core._get_edit_target_layer()
                    # Create the property card
                    pcard = PropertyCard.create(
                        type=PropertyCard.PROPERTY,
                        name=prop_name,
                        path=prop_path,
                        prop=prop,
                        metadata=prop_metadata,
                        layer=layer,
                        prim_path=prim_item.data.path,
                    )
                    pcard_item = PropertyCardItem(pcard, 0)
                    prim_item.add_child_item(pcard_item)

                    self._item_changed(prim_item)
                    return pcard_item

        # Create the actual property
        pre_prop = prop_card.data.prop
        prop_name = pre_prop.GetName() if override_prop_name == "" else override_prop_name
        prim_path = Sdf.Path(prim_item.data.path).StripAllVariantSelections().pathString
        new_props = self._editor_core._add_variant_property(
            prim_path, type(pre_prop), prop_name, prop_card.data.prop_type
        )

        for new_prop in new_props:
            if isinstance(new_prop, (Usd.Property, Usd.Attribute, Usd.VariantSet)):
                prop = new_prop
                create_property_card(prop, prop.GetName(), prim_item)

    def remove_item(self, item, payref=None):
        if isinstance(item, VariantSetCardItem):
            vset_path = item.path_model.as_string
            removed = self._editor_core._remove_variant_set(vset_path)
            self._expanded_state.pop(item.data.name)
            for variant_card in item.children:
                if isinstance(variant_card, VariantCardItem):
                    for prim_card in variant_card.children:
                        if isinstance(prim_card, PrimCardItem):
                            relative_path = Sdf.Path(prim_card.data.path).MakeRelativePath(
                                Sdf.Path(variant_card.data.path)
                            )
                            self._editor_core._remove_prim_path_from_metadata(
                                variant_path=variant_card.data.path,
                                removed_prim_path=prim_card.data.path,
                            )
                        else:
                            pass
                else:
                    pass

            if not removed:
                return

            self._children.pop(self._children.index(item))
            self._item_changed(None)

        else:
            if isinstance(item, VariantCardItem):
                variant_path = item.path_model.as_string
                removed = self._editor_core._remove_variant(variant_path)
                if not removed:
                    return
                for prim_card in item.children:
                    if isinstance(prim_card, PrimCardItem):
                        relative_path = Sdf.Path(prim_card.data.path).MakeRelativePath(Sdf.Path(item.data.path))
                        self._editor_core._remove_prim_path_from_metadata(
                            variant_path=item.data.path, removed_prim_path=relative_path
                        )
                    else:
                        pass

            elif isinstance(item, PrimCardItem):
                # remove all property child items

                with omni.kit.undo.group():
                    for prop_item in item.children:
                        if isinstance(prop_item, PropertyCardItem):
                            self.remove_property_variant(prop_item)
                    parent_item = self.get_parent_item(item)

                    relative_path = Sdf.Path(item.data.name).MakeRelativePath(
                        Sdf.Path(self._editor_core._get_root_prim_path())
                    )
                    self._editor_core._remove_prim_path_from_metadata(
                        variant_path=parent_item.data.path,
                        removed_prim_path=relative_path,
                    )

            elif isinstance(item, PropertyCardItem):
                all_removed = self.remove_property_variant(item, payref)
                if not all_removed:
                    self._item_changed(item)
                    return

            parent_item = self.get_parent_item(item)
            parent_item.children.pop(parent_item.children.index(item))
            self._item_changed(parent_item)

    def remove_property_variant(self, item: PropertyCardItem, payref=None) -> bool:
        all_removed = True

        # Remove property variant from target prim
        prim_path = item.data.prim_path
        if item.data.type == PropertyCard.PROPERTY:
            prop = item.data.prop
            self._editor_core._remove_variant_property(prim_path, prop)
        else:
            if payref in item.data.properties:
                if len(item.data.properties) > 1:
                    all_removed = False

            if item.data.type == PropertyCard.PAYLOADS:
                if all_removed:
                    self._editor_core._clear_variant_payloads(prim_path, item.data.properties)
                else:
                    self._editor_core._remove_variant_payload(prim_path, payref)
            elif item.data.type == PropertyCard.REFERENCES:
                if all_removed:
                    self._editor_core._clear_variant_references(prim_path, item.data.properties)
                else:
                    self._editor_core._remove_variant_reference(prim_path, payref)
            else:
                carb.log_error("Unexpected code path in VariantTreeModel.remove_property_variant()")

            if all_removed == False:
                i = item.data.properties.index(payref)
                item.data.properties.pop(i)
                item.data.asset_paths.pop(i)

        return all_removed

    def select_variant(self, item: VariantCardItem):
        vset_item = self.get_parent_item(item)
        vset_name = vset_item.data.name

        new_variant_selection_path = item.path_model.as_string

        variant_selection_strongest_layer = self.get_layer_with_strongest_opinion_on_variant_selection(vset_name)

        can_set_variant_selection = True
        is_root_layer = False
        if variant_selection_strongest_layer is not None:
            layer_stack: list = self._editor_core._stage.GetLayerStack()
            editing_layer = self._editor_core._get_edit_target_layer()
            variant_selection_strongest_layer_index = layer_stack.index(variant_selection_strongest_layer)

            if variant_selection_strongest_layer_index == 1:
                is_root_layer = True

            editing_layer_index = layer_stack.index(editing_layer)

            # The lower layer_index is, the higher it is in layer stack
            if editing_layer_index > variant_selection_strongest_layer_index:
                can_set_variant_selection = False

        if not can_set_variant_selection:
            # Current authoring layer is not the layer holding strongest opinion of variant selection
            variant_selection_strongest_layer_name = variant_selection_strongest_layer.GetDisplayName()
            if is_root_layer:
                variant_selection_strongest_layer_name += "(Root Layer)"

            nm.post_notification(
                f'Variant selection is overridden in layer "{variant_selection_strongest_layer_name}". \nPlease switch to that layer to clear variant selection first.',
                duration=3,
                status=nm.NotificationStatus.WARNING,
            )
            return False

        with omni.kit.undo.group(), VariantEditorCore.AuthorVariant():
            self._editor_core._select_variant_by_path(new_variant_selection_path)
            # Set editor_core's active variant for display prim/prop details only
            omni.kit.commands.execute(
                "SetVariantEditorActiveVariant",
                variant_path=new_variant_selection_path,
            )

        return True

    def clear_variant_selection(self, item: Union[VariantSetCardItem, VariantCardItem]):
        if isinstance(item, VariantSetCardItem):
            vset_name = item.data.name
            self._item_changed(item)

            for child_v_item in item.children:
                child_v_item.data.activated = False
                self._item_changed(child_v_item)
                for prim_item in child_v_item.children:
                    self._item_changed(prim_item)
                    for prop_item in prim_item.children:
                        self._item_changed(prop_item)

        elif isinstance(item, VariantCardItem):
            vset_item = self.get_parent_item(item)
            vset_name = vset_item.data.name
            item.data.activated = False

            self._item_changed(item)
            for prim_item in item.children:
                self._item_changed(prim_item)
                for prop_item in prim_item.children:
                    self._item_changed(prop_item)

        self._editor_core._clear_variant_selection(vset_name)

        # After clearing variant selection from upper, there may be variant selection in lower layers
        v_set = self._editor_core._get_variant_set_by_name(vset_name)
        active_variant_in_set = v_set.GetVariantSelection()

        if active_variant_in_set:
            active_variant_item = self.get_active_variant_card_item_by_name(vset_name, active_variant_in_set)
            active_variant_item.data.activated = True

            self._item_changed(active_variant_item)
            for prim_item in active_variant_item.children:
                self._item_changed(prim_item)
                for prop_item in prim_item.children:
                    self._item_changed(prop_item)

            curr_strongest_opinion_layer = self.get_layer_with_strongest_opinion_on_variant_selection(vset_name)

            if curr_strongest_opinion_layer is not None:
                curr_strongest_opinion_layer_name = curr_strongest_opinion_layer.GetDisplayName()
                curr_strongest_opinion_layer_index = self._editor_core._stage.GetLayerStack().index(
                    curr_strongest_opinion_layer
                )

                if curr_strongest_opinion_layer_index == 1:
                    curr_strongest_opinion_layer_name += "(Root Layer)"

                nm.post_notification(
                    f'Variant selection still exists in layer: "{curr_strongest_opinion_layer_name}".',
                    duration=3,
                    status=nm.NotificationStatus.WARNING,
                )

    def rename_variant_set(self, item: VariantSetCardItem, old_name: str, new_name: str):
        # Find out variant selection of this set in each layer and restore them after renaming
        prim_variant_selections_has_target_variant = []
        for layer in self._editor_core._stage.GetLayerStack():
            prim_spec: Sdf.PrimSpec = layer.GetPrimAtPath(self._editor_core._get_root_prim_path())
            if prim_spec is not None:
                prim_variant_selections: dict = prim_spec.variantSelections
                if old_name in prim_variant_selections:
                    prim_variant_selections_has_target_variant.append(prim_variant_selections)

        new_path = self._editor_core._rename_variant_set(old_name, new_name)
        if new_path is None:
            return False

        item.data.name = new_name
        item.data.path = new_path

        # Restore variant selection in this set before populating children
        for prim_variant_selections in prim_variant_selections_has_target_variant:
            prev_selected_variant_name = prim_variant_selections.pop(old_name)
            prim_variant_selections[new_name] = prev_selected_variant_name

        # The paths of this variant set item's children are all outdated,
        # Remove all of them and rebuild from scratch
        self._populate_variant_list(item)

        self._item_changed(item)

        return True

    def rename_variant(self, item: VariantCardItem, old_name: str, new_name: str):
        is_active = False
        if self._editor_core.active_variant == item.data.path:
            is_active = True

        vset = self._editor_core._get_variant_set_by_name(Sdf.Path(item.data.path).GetVariantSelection()[0])
        vset_name = vset.GetName()

        # If variant to rename is selected in its variant set in any layers, we need to keep it selected in these layers after renaming
        prim_variant_selections_has_target_variant = []
        for layer in self._editor_core._stage.GetLayerStack():
            prim_spec: Sdf.PrimSpec = layer.GetPrimAtPath(self._editor_core._get_root_prim_path())
            if prim_spec is not None:
                prim_variant_selections: dict = prim_spec.variantSelections
                if vset_name in prim_variant_selections:
                    if prim_variant_selections[vset_name] == old_name:
                        prim_variant_selections_has_target_variant.append(prim_variant_selections)

        new_path = self._editor_core._rename_variant(vset, old_name, new_name)
        if new_path is None:
            return False

        item.data.name = new_name
        item.data.path = new_path.pathString

        # The paths of this variant item's children are all outdated,
        # Remove all of them and rebuild from scratch
        item.children.clear()
        self._populate_prim_list(item)

        # Re-assign variant selection for each layer which has renamed variant selected before
        for prim_variant_selections in prim_variant_selections_has_target_variant:
            prim_variant_selections[vset_name] = new_name

        self._item_changed(item)
        return True

    def duplicate_variant(self, item: VariantCardItem):
        new_variant_path, new_variant_name = self._editor_core._duplicate_variant(item.data.path)
        if new_variant_path is None:
            return

        new_variant_card = VariantCard.create(
            VariantCard.VARIANT, name=new_variant_name, path=new_variant_path.pathString
        )
        new_vcard_item = VariantCardItem(new_variant_card, 0)

        vset_item: VariantSetCardItem = self.get_parent_item(item)
        vset_item.add_child_item(new_vcard_item)

        # Populate variant prim / properties
        self._populate_prim_list(new_vcard_item)

        self._item_changed(vset_item)

    def copy_variant_prop(self, item: PropertyCardItem):
        self._clipboard = {}
        prop_path = Sdf.Path(item.data.path).StripAllVariantSelections()
        value = self.get_item_value(item)
        if value:
            self._clipboard = {prop_path: value}

    def copy_variant_prim(self, item: PrimCardItem) -> Dict:
        self._clipboard = {}
        for prop in item._children:
            if isinstance(prop, PropertyCardItem):
                prop_path = Sdf.Path(prop.data.path).StripAllVariantSelections()
                value = self.get_item_value(prop)
                if value:
                    self._clipboard[prop_path] = value
        return self._clipboard

    def paste_to_variant_prop(self, item: PropertyCardItem):
        for value in self._clipboard.values():
            source_value = str(value)
        if source_value:
            vset_item: VariantSetCardItem = self.get_parent_item(self.get_parent_item(self.get_parent_item(item)))
            vset_name = vset_item.data.name
            vset = self._editor_core._get_variant_set_by_name(vset_name)
            prim_path = vset.GetPrim().GetPath()
            prop_path = Sdf.Path(item.data.path).StripAllVariantSelections()
            target_value = self._editor_core._stage.GetAttributeAtPath(prop_path).Get()
            typed_value = self.convert_type(type(target_value), source_value)
            omni.kit.commands.execute(
                "EditVariant",
                prim_path=prim_path,
                variant_set_name=vset_name,
                cmd_name="ChangeProperty",
                cmd_args={"prop_path": prop_path, "value": typed_value, "prev": None},
            )
            self._item_changed(item)

    def paste_to_variant_prim(self, item: PrimCardItem):
        target_path = Sdf.Path(item.data.path).StripAllVariantSelections()
        variant_item = self.get_parent_item(item)
        vset_item: VariantSetCardItem = self.get_parent_item(variant_item)
        vset_name = vset_item.data.name
        vset = self._editor_core._get_variant_set_by_name(vset_name)
        vset_prim_path = vset.GetPrim().GetPath().pathString
        omni.kit.commands.execute(
            "PasteVariant",
            prim_path=vset_prim_path,
            variant_set_name=vset_name,
            clipboard=self._clipboard,
            target_path=target_path,
        )

    def copy_props_to_all(self, item: VariantCardItem):
        self._clipboard = {}
        vset_item: VariantSetCardItem = self.get_parent_item(item)
        vset_name = vset_item.data.name
        vset = self._editor_core._get_variant_set_by_name(vset_name)
        vset_prim_path = vset.GetPrim().GetPath().pathString

        for prim in item._children:
            if isinstance(prim, PrimCardItem):
                for prop in prim._children:
                    if isinstance(prop, PropertyCardItem):
                        prop_path = Sdf.Path(prop.data.path).StripAllVariantSelections()
                        value = self.get_item_value(prop)
                        if value:
                            self._clipboard[prop_path] = value

        omni.kit.commands.execute(
            "PasteVariant",
            prim_path=vset_prim_path,
            variant_set_name=vset_name,
            clipboard=self._clipboard,
        )

    def get_item_value(self, item: PropertyCardItem):
        models = item.attr_model
        try:
            models = models[0]
        except:
            pass
        if not models:
            return None
        if not isinstance(models, list):
            models = [models]
        value = None
        for model in models:
            try:
                if (
                    isinstance(model, UsdAttributeModelVariant)
                    or isinstance(model, TfTokenAttributeModelVariant)
                    or isinstance(model, MdlEnumAttributeModelVariant)
                    or isinstance(model, GfVecAttributeModelVariant)
                ):
                    value = model.get_value()
            except:
                carb.log_warn("Unsupported type")

        return value

    def convert_type(self, value_type, value_str: str):
        import ast

        if value_type == str or value_type == Sdf.AssetPath or value_type == Sdf.Path:
            return value_str
        if value_type == Sdf.AssetPathArray:
            # Copied AssetPathArray is in this format:
            # [@E:/USD/foo.usd@, @E:/USD/bar.usd@]
            # parse it manually
            value_str = value_str.strip("[] ")
            paths = value_str.split(", ")
            paths = [path.strip("@") for path in paths]
            return paths
        else:
            retval = ""
            try:
                retval = value_type(ast.literal_eval(value_str))
            except:
                pass

            return retval

    def can_paste_to_prop(self, item: PropertyCardItem):
        if not self._clipboard:
            return False
        models = item.attr_model
        try:
            models = models[0]
        except:
            pass
        if not isinstance(models, list):
            models = [models]

        for value in self._clipboard.values():
            source_value = str(value)

        if not models:
            return False

        ret = False
        if source_value:
            for model in models:
                try:
                    if isinstance(model, UsdAttributeModelVariant):
                        value = model.get_value()
                        if self.convert_type(type(value), source_value):
                            ret = True
                    elif isinstance(model, TfTokenAttributeModelVariant):
                        if model.is_allowed_token(source_value):
                            ret = True
                    elif isinstance(model, MdlEnumAttributeModelVariant):
                        if model.is_allowed_enum_string(source_value):
                            ret = True
                    elif isinstance(model, GfVecAttributeModelVariant):
                        value = model.get_value()
                        if self.convert_type(type(value), source_value):
                            ret = True
                    else:
                        carb.log_warn("Unsupported type to paste to")
                        ret = False
                    return ret
                except Exception as e:
                    carb.log_error(f"can_paste: error {e}")
        return ret

    def can_paste_to_prim(self, item: PrimCardItem):
        if self._clipboard:
            if len(self._clipboard) == 1:
                return True
        return False

    def can_paste_all_to_prim(self, item: PrimCardItem):
        if self._clipboard:
            if len(self._clipboard) > 1:
                return True
        return False

    def is_active_variant(self, item: VariantCardItem):
        variant = item.data.name
        vset_item: VariantSetCardItem = self.get_parent_item(item)
        vset_name = vset_item.data.name
        vset = self._editor_core._get_variant_set_by_name(vset_name)
        return variant == vset.GetVariantSelection()

    def get_all_children(self, prim):
        children_list = set([])
        queue = [prim]
        while len(queue) > 0:
            child_prim = queue.pop()
            for child in child_prim.GetAllChildren():
                children_list.add(child.GetPath())
                queue.append(child)

        return children_list


class VariantTreeView(ListView):
    """
    View for VariantTreeModel
    """

    def __init__(
        self,
        model: VariantTreeModel,
        delegate: VariantTreeDelegate,
        on_item_selected_fn=None,
        keep_expanded=False,
    ):
        super().__init__(
            model=model,
            column_widths=[ui.Fraction(1)],
            delegate=delegate,
            drop_between_items=True,
            vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
            scrolling_frame=True,
            on_item_selected_fn=on_item_selected_fn,
            keep_expanded=keep_expanded,
        )

    def _on_selection_changed(self, selections):
        super()._on_selection_changed(selections)

        if len(selections) > 0:
            # Set active variant
            item = selections[0]

            if isinstance(item, VariantCardItem):
                model: VariantTreeModel = self._tree_view.model
                model.select_variant(item)
            elif isinstance(item, VariantSetCardItem):
                vset = VariantEditorCore.get_instance()._get_variant_set_by_name(item.data.name)
                v_name = vset.GetVariantSelection()
                if v_name:
                    variant_card_item = self._tree_view.model.get_active_variant_card_item_by_name(
                        item.data.name, v_name
                    )
                    omni.kit.commands.execute(
                        "SetVariantEditorActiveVariant",
                        variant_path=variant_card_item.path_model.as_string,
                    )

            # Clear selection immediately, otherwise selecting the same item won't have any effect
            self._tree_view.clear_selection()

    def _on_accept_drop(self, item):
        if item.endswith((".usd", ".usda", ".usdc", ".usdz")):
            return True
        elif item.endswith(".mdl"):
            return True
        else:
            return False

    # TODO: Drop under variant set
    def _on_drop(self, item):
        # File is dropped onto tree view
        model: VariantTreeModel = self._tree_view.model
        with omni.kit.undo.group(), self.model._editor_core.AuthorVariant():
            vset_name = model.add_variant_set()

            if vset_name is not None:
                file_list = item.mime_data.split("\n")
                usd_list = []
                mdl_list = []
                ref_type = carb.settings.get_settings().get("/persistent/app/stage/dragDropImport")
                for file in file_list:
                    if file.endswith((".usd", ".usda", ".usdc", ".usdz")):
                        usd_list.append(file)
                    elif file.endswith(".mdl"):
                        mdl_list.append(file)

                if model._editor_core.create_visibility_by_default:
                    model._editor_core._create_visibility_variant_from_files(vset_name, usd_list, ref_type)
                else:
                    model._editor_core._create_geom_variant_from_files(vset_name, usd_list, ref_type)

                model._editor_core._create_material_variant_from_files(vset_name, mdl_list)
            model._populate_variant_set_list()


class VariantTreeDelegate(ui.AbstractItemDelegate):
    """
    Delegate for rendering VariantTreeView
    """

    def __init__(self, selection_changed_fn=None):
        super().__init__()
        self._context_menu = ui.Menu("VariantSet List context menu", menu_compatibility=False, tearable=False)

    def _build_border(self, left, top, right, bottom):
        width = 1
        color = 0xFFCA9C46
        with ui.ZStack():
            if left:
                ui.Line(
                    alignment=ui.Alignment.LEFT,
                    style={"color": color, "border_width": width},
                )
            if top:
                ui.Line(
                    alignment=ui.Alignment.TOP,
                    style={"color": color, "border_width": width},
                )
            if right:
                ui.Line(
                    alignment=ui.Alignment.RIGHT,
                    style={"color": color, "border_width": width + 2},
                )
            if bottom:
                ui.Line(
                    alignment=ui.Alignment.BOTTOM,
                    style={"color": color, "border_width": width + 1},
                )

    def build_branch(self, model, item, column_id, level, expanded):
        """Create a branch widget that opens or closes subtree"""
        if isinstance(item, VariantSetCardItem):
            # Triangle icon to expand variant set
            with ui.VStack():
                ui.Spacer(height=5)
                with ui.HStack():
                    ui.Spacer(width=5)
                    with ui.ZStack(height=30):
                        ui.Rectangle(style={"background_color": ui_c.COLORS.CLR_3})
                        with ui.HStack():
                            ui.Spacer(width=10)
                            with ui.VStack():
                                ui.Spacer()
                                ui.Image(
                                    width=14,
                                    height=14,
                                    style=(ui_c.STYLE_EXPAND_BUTTON if expanded else ui_c.STYLE_COLLAPSE_BUTTON),
                                )
                                ui.Spacer()
                        active_variant = VariantEditorCore.get_instance().active_variant
                        if active_variant is not None:
                            vs_name, v_name = Sdf.Path(active_variant).GetVariantSelection()
                            if vs_name == item.data.name:
                                self._build_border(True, True, False, not expanded)

    def build_widget(
        self,
        model: VariantTreeModel,
        item: Union[VariantSetCardItem, VariantCardItem],
        column_id,
        level,
        expanded,
    ):
        """Create a widget per column per item"""
        if column_id == 0:

            # Double click call back to trigger renaming
            def on_mouse_double_clicked(label, field, end_edit_fn):
                label.visible = False
                field.visible = True
                self.end_edit_subscription = field.model.subscribe_end_edit_fn(
                    lambda field_model, variant_model=model, label=label, rename_field=field, item=item: end_edit_fn(
                        field_model, variant_model, label, rename_field, item
                    )
                )

                async def focus(field):
                    await omni.kit.app.get_app().next_update_async()
                    field.focus_keyboard()

                asyncio.ensure_future(focus(field))

            if isinstance(item, VariantSetCardItem):
                # Build widgets for VariantSetCarItem
                with ui.VStack():
                    ui.Spacer(height=5)
                    vset_widget = ui.HStack(
                        height=30,
                        style=ui_c.STYLE_VARIANT_SET_LIST,
                    )
                    vset_widget.set_mouse_pressed_fn(
                        lambda x, y, btn, flag, model=model, item=item: self._on_variant_set_clicked(btn, model, item)
                    )

                    with vset_widget:
                        with ui.ZStack():
                            ui.Rectangle(style={"background_color": ui_c.COLORS.CLR_3})
                            # NAME
                            with ui.HStack():
                                name_model = model.get_item_value_model(item, Column.NAME)
                                vset_name = name_model.as_string

                                ui.Spacer(width=10)

                                vset_rename_stack = ui.ZStack()
                                with vset_rename_stack:
                                    ui.Spacer(height=1)
                                    vset_label = ui.Label(
                                        vset_name,
                                        name=vset_name,
                                        elided_text=True,
                                        tooltip_fn=lambda: self._create_tooltip(vset_name),
                                        style=ui_c.STYLE_TEXT_LABEL,
                                    )
                                    rename_field = ui.StringField(
                                        name_model,
                                        height=12,
                                        visible=False,
                                        style=ui_c.STYLE_STRING_FIELD,
                                    )

                                    vset_rename_stack.set_mouse_double_clicked_fn(
                                        lambda x, y, b, _: on_mouse_double_clicked(
                                            vset_label,
                                            rename_field,
                                            self.on_end_rename_variant_or_set,
                                        )
                                    )

                                if item:
                                    item._ui_widget = vset_rename_stack

                                ui.Spacer(width=5)
                                with ui.VStack(width=0):
                                    # Add Button
                                    ui.Spacer()
                                    ui.Button(
                                        clicked_fn=lambda model=model, item=item: self._on_add_variant(model, item),
                                        image_url=f"{ui_c.PATH_EXTENSION}{ui_c.PATH_ICON_ADD_DARK}",
                                        # Declaring image width and height necessary for nice antialiasing
                                        image_height=18,
                                        image_width=18,
                                        width=24,
                                        height=24,
                                        style=ui_c.STYLE_ADD_BUTTON,
                                    )
                                    ui.Spacer()

                                ui.Spacer(width=2)

                            active_variant = VariantEditorCore.get_instance().active_variant
                            if active_variant is not None:
                                vs_name, v_name = Sdf.Path(active_variant).GetVariantSelection()
                                if vs_name == item.data.name:
                                    self._build_border(False, True, True, not expanded)

            elif isinstance(item, VariantCardItem):
                # build widgets for VariantCarItem
                variant_widget = ui.HStack(height=24, style=ui_c.STYLE_VARIANT_LIST)
                variant_widget.set_mouse_pressed_fn(
                    lambda x, y, btn, flag, model=model, item=item: self._on_variant_clicked(btn, model, item)
                )

                with variant_widget:
                    ui.Spacer(width=5)
                    with ui.ZStack():
                        ui.Rectangle(style=ui_c.STYLE_VARIANT_LIST)

                        with ui.HStack():
                            blue_bar_style = (
                                ui_c.STYLE_ACTIVE_VARIANT_RECT if item.data.activated else ui_c.STYLE_VARIANT_RECT
                            )

                            ui.Rectangle(width=3, style=blue_bar_style)
                            ui.Spacer(width=3)
                            with ui.VStack(width=20):
                                ui.Spacer()
                                # Vertical lines/Grab Lines
                                ui.Image(height=18, width=18, style=ui_c.STYLE_VERTICAL_LINES)
                                ui.Spacer()

                            ui.Spacer(width=4)
                            with ui.VStack(width=20):
                                ui.Spacer()
                                # Thumbnail placeholder image
                                ui.Image(height=20, width=20, style=ui_c.STYLE_THUMBNAIL)
                                ui.Spacer()

                            ui.Spacer(width=10)
                            with ui.HStack():
                                # Label and Field draw in the same position and allow the user to rename the card
                                variant_rename_stack = ui.ZStack()
                                name_model = model.get_item_value_model(item, Column.NAME)
                                active_style = (
                                    ui_c.STYLE_VARIANT_CARD_ACTIVATED
                                    if item.data.activated
                                    else ui_c.STYLE_VARIANT_CARD
                                )

                                with variant_rename_stack:
                                    variant_label = ui.Label(
                                        name_model.as_string,
                                        height=24,
                                        elided_text=True,
                                        name=name_model.as_string,
                                        tooltip_fn=lambda: self._create_tooltip(name_model.as_string),
                                        style=active_style,
                                    )
                                    variant_rename_field = ui.StringField(
                                        name_model,
                                        height=12,
                                        visible=False,
                                        style=ui_c.STYLE_STRING_FIELD,
                                    )
                                    variant_rename_stack.set_mouse_double_clicked_fn(
                                        lambda x, y, b, _: on_mouse_double_clicked(
                                            variant_label,
                                            variant_rename_field,
                                            self.on_end_rename_variant_or_set,
                                        )
                                    )

                                if item:
                                    item._ui_widget = variant_rename_stack

                            ui.Spacer(width=5)
                            # "X" buttons for removing a variant
                            with ui.VStack(width=24, content_clipping=True):
                                ui.Spacer()
                                variant_remove_button = ui.Button(
                                    identifier="Remove Variant Button",  # for unit test
                                    clicked_fn=lambda model=model, item=item: self._on_delete_variant(model, item),
                                    image_url=f"{ui_c.PATH_EXTENSION}{ui_c.PATH_ICON_REMOVE_DARK}",
                                    # Declaring image width and height necessary for nice antialiasing
                                    image_height=18,
                                    image_width=18,
                                    width=20,
                                    height=20,
                                    style=ui_c.STYLE_REMOVE_BUTTON,
                                    visible=False,
                                )

                                def on_variant_mouse_hovered(hovered):
                                    if hovered:
                                        variant_remove_button.visible = True
                                    else:
                                        variant_remove_button.visible = False

                                variant_widget.set_mouse_hovered_fn(on_variant_mouse_hovered)

                                ui.Spacer()

                        active_variant = VariantEditorCore.get_instance().active_variant
                        if active_variant is not None:
                            active_vs_name, active_v_name = Sdf.Path(active_variant).GetVariantSelection()
                            card_vs_name, card_v_name = Sdf.Path(item.data.path).GetVariantSelection()
                            if card_vs_name == active_vs_name:
                                vset = VariantEditorCore.get_instance()._get_variant_set_by_name(card_vs_name)
                                v_names = vset.GetVariantNames()

                                self._build_border(True, False, True, card_v_name == v_names[-1])

    def _create_tooltip(self, text: str):
        with ui.ZStack(style=ui_c.STYLE_TOOLTIP):
            ui.Rectangle()
            ui.Label(text, style=ui_c.STYLE_TOOLTIP_TEXT)

    def _on_variant_set_clicked(self, btn: int, model: VariantTreeModel, item: VariantSetCardItem) -> None:
        for child in model.get_item_children(None):
            model.record_expand_state(child)
        if btn != 1:
            return True

        self._context_menu.clear()
        with self._context_menu:
            ui.MenuItem("Delete Variant Set", triggered_fn=lambda: model.remove_item(item))
            ui.MenuItem(
                "Rename Variant Set",
                triggered_fn=lambda: item._ui_widget.call_mouse_double_clicked_fn(0, 0, 0, 0),
            )
            ui.MenuItem(
                "Clear Variant Selection",
                triggered_fn=lambda: model.clear_variant_selection(item),
            )

        self._context_menu.show()

        return True

    def _on_variant_clicked(self, btn: int, model: VariantTreeModel, item: VariantCardItem) -> None:
        for child in model.get_item_children(None):
            model.record_expand_state(child)
        if btn != 1:
            return True

        self._context_menu = ui.Menu("Variant List context menu", menu_compatibility=False, tearable=False)
        self._context_menu.clear()
        with self._context_menu:
            ui.MenuItem(
                "Remove Variant",
                triggered_fn=lambda: self._on_delete_variant(model, item),
            )
            ui.MenuItem(
                "Rename Variant",
                triggered_fn=lambda: item._ui_widget.call_mouse_double_clicked_fn(0, 0, 0, 0),
            )
            ui.MenuItem("Duplicate Variant", triggered_fn=lambda: model.duplicate_variant(item))
            ui.MenuItem(
                "Clear Selection",
                triggered_fn=lambda: model.clear_variant_selection(item),
            )
            if model.is_active_variant(item):
                ui.MenuItem(
                    "Copy Properties to All in Set",
                    triggered_fn=lambda: model.copy_props_to_all(item),
                )

        self._context_menu.show()

        return True

    def _on_add_variant(self, model: VariantTreeModel, item: VariantSetCardItem) -> None:
        # Creating a new variant actually duplicates the last variant
        if len(model.get_item_children(item)) > 0:
            last_variant = model.get_item_children(item)[-1]
            model.duplicate_variant(last_variant)
        # Unless there aren't any variants, in which case we should make a new one
        else:
            model.add_variant(item)

    def _on_delete_variant(self, model: VariantTreeModel, item: VariantCardItem) -> None:
        model.remove_item(item)

    def on_end_rename_variant_or_set(
        self,
        field_model,
        variant_model: VariantTreeModel,
        label,
        field,
        item: Union[VariantSetCardItem, VariantCardItem],
    ):
        old_text = label.text
        new_name = omni.usd.make_valid_identifier(field.model.as_string)

        # Always reset the field model to the correct name (either old or new)
        # Do this BEFORE hiding the field to ensure it's in the correct state
        field.model.set_value(old_text)

        if new_name != old_text:
            if isinstance(item, VariantSetCardItem):
                if variant_model.rename_variant_set(item, old_text, new_name):
                    # Update the field model to reflect the successful rename
                    field.model.set_value(new_name)
            elif isinstance(item, VariantCardItem):
                if variant_model.rename_variant(item, old_text, new_name):
                    # Update the field model to reflect the successful rename
                    field.model.set_value(new_name)

        # Always hide the field and show the label
        label.visible = True
        field.visible = False

        self.end_edit_subscription = None
