# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
##
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
##

"""Logic and Data class module

Model - Main class for logic of data translation from stage to the data classes
"""

import asyncio
import typing
from typing import Dict, List, Optional

import carb
import omni.kit.app
import omni.kit.commands
import omni.ui as ui
from pxr import Sdf, Usd, Vt

from .items import Group, Prim, Variant


class Model(ui.AbstractItemModel):
    """Model - this is the class that the tree will get, along with the delegate."""

    group_prefix = "VARIANTGROUP_"
    default_group_name = "NewVariantGroup"

    def __init__(self):
        super(Model, self).__init__()
        self._usd_context = None
        self._stage = None
        self._prims: typing.List[Prim] = []
        self._groups: typing.List[Group] = []
        self._variants: typing.List[Variant] = []
        self._ungrouped_variants = Group("Ungrouped Variants", None)
        self._group_root = None
        self._view_state = 0
        self._is_groups = True
        self._search: Optional[str] = None
        self._variant_prims = []
        self._variant_prims_cache: typing.List[Usd.Prim] = []
        self._variant_prims_cache_valid: bool = False
        self._drop_target = None
        self._selection = []
        self._tree = None
        self._expanded_state: Dict[str, bool] = {}
        self._predicate = Usd.PrimAllPrimsPredicate
        self._hide_locked_variants = False
        self._refresh_pending: bool = False
        self._refresh_select_requested: bool = False
        self._vset_cache: Dict[str, Dict[str, typing.Any]] = {}
        # Multi-frame debouncing to batch rapid variant changes
        self._refresh_debounce_frames: int = 5  # Wait 5 frames to batch rapid variant changes
        self._refresh_debounce_counter: int = 0
        self._refresh_task: Optional[asyncio.Task] = None
        self.load()

    def destroy(self):
        # Cancel any pending debounced refresh task so it cannot fire after the
        # stage has been closed/replaced. _debounced_flush -> _perform_refresh
        # -> load -> stage.Traverse() against a stage in transition raises
        # UsdExpiredPrimAccessError as an unawaited asyncio task. The task's
        # except-CancelledError clause exits cleanly on cancel.
        if self._refresh_task is not None and not self._refresh_task.done():
            self._refresh_task.cancel()
        self._refresh_task = None
        self._refresh_pending = False
        self._refresh_debounce_counter = 0
        self._refresh_select_requested = False

        self._prims: typing.List[Prim] = []
        self._groups: typing.List[Group] = []
        self._variants: typing.List[Variant] = []
        self._group_root = None
        self._search: Optional[str] = None
        self._variant_prims = []
        self._stage = None
        self._drop_target = None
        self._selection = []
        self._tree = None
        self._expanded_state: Dict[str, bool] = {}

    def reload(self, context, stage) -> None:
        self._usd_context = context
        self._stage = stage
        self._group_root = None
        self._search: Optional[str] = None
        self._expanded_state: Dict[str, bool] = {}
        self._variant_prims_cache_valid = False
        self.refresh()

    def refresh(self, select=False) -> None:
        """Refresh the model with multi-frame debouncing to batch rapid variant changes.

        Performance optimization: Wait multiple frames to coalesce variant changes,
        preventing excessive geometry processing requests during rapid variant operations.
        """
        self._refresh_select_requested = self._refresh_select_requested or select

        # Cancel any existing refresh task to restart the debounce timer
        if self._refresh_task and not self._refresh_task.done():
            self._refresh_task.cancel()
            self._refresh_task = None

        # If already pending, just reset the debounce counter
        if self._refresh_pending:
            self._refresh_debounce_counter = self._refresh_debounce_frames
        else:
            self._refresh_pending = True
            self._refresh_debounce_counter = self._refresh_debounce_frames

        self._refresh_task = asyncio.ensure_future(self._debounced_flush())

    async def _debounced_flush(self):
        """Wait for debounce period, resetting on new requests, then perform refresh."""
        try:
            # Wait for the debounce period, counting down each frame
            while self._refresh_debounce_counter > 0:
                await omni.kit.app.get_app().next_update_async()
                self._refresh_debounce_counter -= 1

            # Only refresh if counter reached zero (no new requests came in)
            if self._refresh_debounce_counter == 0:
                select_flag = self._refresh_select_requested
                self._refresh_select_requested = False
                self._refresh_pending = False
                self._refresh_task = None
                self._perform_refresh(select_flag)
        except asyncio.CancelledError:
            # Task was cancelled, this is expected when a new refresh is requested
            pass

    def _perform_refresh(self, select=False) -> None:
        if not select:
            self.get_expanded()
        self._ungrouped_variants = Group("Ungrouped Variants", None)
        self._prims = []
        self._groups = []
        self._variants = []
        # Clear the variant set cache so the next load reads fresh selections from USD.
        # Without this, stale cached variant selections could persist across refreshes.
        self._vset_cache.clear()
        self.load()

    def load(self) -> None:
        """Analyzes the data structure prim and creates all the data needed"""
        if self._stage:
            if self._view_state == 0 or self._is_groups:
                if not self._variant_prims_cache_valid:
                    self._variant_prims_cache = [
                        prim for prim in self._stage.Traverse(self._predicate) if prim.HasVariantSets()
                    ]
                    self._variant_prims_cache_valid = True
                self._variant_prims = self._variant_prims_cache
            else:
                selection = self._usd_context.get_selection().get_selected_prim_paths()
                self._variant_prims = []
                for path in selection:
                    prim = self._stage.GetPrimAtPath(path)
                    if prim.HasVariantSets():
                        self._variant_prims.append(prim)
        else:
            self._variant_prims = []
        if self._is_groups:
            self.load_groups()
        else:
            self.load_prims()
        self._item_changed(None)

    def invalidate_variant_prims_cache(self) -> None:
        self._variant_prims_cache_valid = False

    def load_prims(self) -> None:
        if len(self._variant_prims) > 0:
            for p in self._variant_prims:
                prim_path = p.GetPath().pathString
                prim_item = Prim(prim_path)
                if self._search:
                    # Eagerly populate only for search to preserve existing UX
                    self._populate_variants_for_prim(prim_item, p)
                    if len(prim_item.variants) == 0:
                        continue
                    # Filter by prim path or any variant match
                    if (self._search.lower() in prim_path.lower()) or len(prim_item.variants) > 0:
                        self._prims.append(prim_item)
                else:
                    # Lazy: keep variants empty; populate on expand/children query
                    self._prims.append(prim_item)

    def load_groups(self) -> None:
        self._group_root = self.get_group_root()
        if not self._stage or not self._stage.GetPseudoRoot().IsValid():
            return
        if not self._group_root or not self._group_root.IsValid():
            return
        collections = Usd.CollectionAPI.GetAllCollections(self._group_root)
        for collection in collections:
            if not collection.GetPrim().IsValid():
                continue
            cFlag = False
            vFlag = False
            collection_path = collection.GetCollectionPath().pathString
            if self.group_prefix in collection_path:
                group_name = collection_path.split(self.group_prefix)[1]
                if self._search:
                    if self._search.lower() in group_name.lower():
                        cFlag = True
                group_item = Group(group_name, collection_path)
                members = self._stage.GetPropertyAtPath(collection_path + ":includes").GetTargets()
                for member in members:
                    # Since we cannot prevent users from putting non-variant usd objects into the collection, we try and except
                    try:
                        path = member.pathString
                        prim_path = path.split(".")[0]
                        vset_name = path.split(".")[1]
                        prim = self._stage.GetPrimAtPath(prim_path)
                        vset = prim.GetVariantSet(vset_name)
                        cur_sel = vset.GetVariantSelection()
                        variant_item = Variant(
                            prim=prim,
                            vset=vset,
                            vset_name=vset_name,
                            variant_selection=cur_sel,
                            group=group_item.group_path,
                        )
                        if self._hide_locked_variants:
                            if self.get_variant_lock_metadata(variant_item):
                                continue
                        if self._search and not cFlag:
                            if self._search.lower() in vset_name.lower() or self._search.lower() in cur_sel.lower():
                                vFlag = True
                                group_item.add_variant(variant_item)
                                self._variants.append(variant_item)

                        else:
                            group_item.add_variant(variant_item)
                            self._variants.append(variant_item)
                    except:
                        continue
                if self._search:
                    if cFlag or vFlag:
                        self._groups.append(group_item)
                else:
                    self._groups.append(group_item)
        if len(self._variant_prims) > 0:
            # Precompute grouped keys for O(1) membership checks
            grouped_keys = set()
            for group in self._groups:
                for variant in group.variants:
                    grouped_keys.add((variant._prim, variant._vset_name))
            self._ungrouped_variants = Group("Ungrouped Variants", None)
            for p in self._variant_prims:
                vset_names = p.GetVariantSets().GetNames()
                for v in vset_names:
                    # Skip if already placed in a group
                    if (p, v) in grouped_keys:
                        continue
                    vset = p.GetVariantSet(v)
                    cur_sel = vset.GetVariantSelection()
                    variant_item = Variant(prim=p, vset=vset, vset_name=v, variant_selection=cur_sel)
                    if self._hide_locked_variants:
                        if self.get_variant_lock_metadata(variant_item):
                            continue
                    if self._search:
                        if self._search.lower() in v.lower():
                            self._ungrouped_variants.add_variant(variant_item)
                            self._variants.append(variant_item)
                    else:
                        self._ungrouped_variants.add_variant(variant_item)
                        self._variants.append(variant_item)
            if self._search:
                if self._search.lower() in "Ungrouped Variants" or len(self._ungrouped_variants.variants) > 0:
                    self._groups.append(self._ungrouped_variants)
            else:
                self._groups.append(self._ungrouped_variants)

    def set_selection(self, selection):
        self._selection = selection

    def get_expanded(self):
        if self._is_groups:
            for group in self.groups:
                if self._tree:
                    self._expanded_state[group.group_name] = self._tree().is_expanded(group)
        else:
            for prim in self.prims:
                if self._tree:
                    self._expanded_state[prim.prim_path] = self._tree().is_expanded(prim)

    def get_group_root(self):
        if self._group_root:
            return self._group_root
        else:
            if self._stage:
                children = self._stage.GetPseudoRoot().GetChildren()
                return children[0] if len(children) > 0 else None
            else:
                return None

    def add_group(self):
        self._group_root = self.get_group_root()
        if self._group_root:
            collection_name = self.group_prefix + self.default_group_name
            prim_path = self._group_root.GetPath().pathString
            _, group_path = omni.kit.commands.execute(
                "CreateCollection", prim_path=prim_path, collection_name=collection_name
            )
            group_item = Group(group_path.pathString.split(self.group_prefix)[1], group_path.pathString)
            for item in self._selection:
                if isinstance(item, Variant):
                    for group in self._groups:
                        if item in group.variants:
                            if group.group_path:
                                omni.kit.commands.execute(
                                    "RemoveItemFromCollection",
                                    prim_or_prop_path=self.get_variant_path(item),
                                    collection_path=group.group_path,
                                )
                            omni.kit.commands.execute(
                                "AddItemToCollection",
                                path_to_add=self.get_variant_path(item),
                                collection_path=group_path.pathString,
                            )
                            break
            # Ensure model reflects the new collection immediately
            self.invalidate_variant_prims_cache()
            try:
                self._perform_refresh()
            except Exception:
                self.refresh()

    def remove_group(self, item):
        if isinstance(item, Variant):
            if item.group:
                for group in self._groups:
                    if group.group_path == item.group:
                        self.remove_group(group)
        elif isinstance(item, Group):
            if item is not self._ungrouped_variants:
                omni.kit.commands.execute("DeleteCollection", collection_path=item.group_path)
                # Ensure model reflects removal immediately
                self.invalidate_variant_prims_cache()
                try:
                    self._perform_refresh()
                except Exception:
                    self.refresh()

    def rename_group(self, group: Group, name: str):
        if Sdf.Path.IsValidPathString(name):
            if not name == group.group_name:
                new_name = self.group_prefix + name
                collection = omni.kit.commands.execute(
                    "RenameCollection", old_collection_path=group.group_path, new_collection_name=new_name
                )
                if collection[0]:
                    group._group_path = collection[1].pathString
                    group._group_name = group.group_path.split(self.group_prefix)[1]
                    group._name_model = ui.SimpleStringModel(group._group_name)
        else:
            carb.log_error(f"Cannot rename to {name} as it is not a valid USD path")

    def remove_variant_from_group(self, item):
        for group in self._groups:
            if item in group.variants:
                if group.group_path:
                    item_path = self.get_variant_path(item)
                    omni.kit.commands.execute(
                        "RemoveItemFromCollection", prim_or_prop_path=item_path, collection_path=group.group_path
                    )
                    self.refresh()
                    break

    def get_variant_lock_metadata(self, item):
        prim = self.get_prim(item._prim_path)
        if not prim or not prim.IsValid():
            return False
        metadata = prim.GetMetadata("variant_sets_ui_hints")
        if metadata:
            if item._vset_name in metadata["omni:variants_locked"]:
                return True
        return False

    def set_variant_lock_metadata(self, item):
        prim = self.get_prim(item._prim_path)
        if not prim or not prim.IsValid():
            return
        metadata = prim.GetMetadata("variant_sets_ui_hints")
        if metadata:
            if item._vset_name in metadata["omni:variants_locked"]:
                metadata["omni:variants_locked"] = Vt.StringArray(
                    [vset for vset in metadata["omni:variants_locked"] if vset != item._vset_name]
                )
                prim.SetMetadata("variant_sets_ui_hints", metadata)
            else:
                metadata["omni:variants_locked"] = Vt.StringArray(
                    list(metadata["omni:variants_locked"]) + [item._vset_name]
                )
                prim.SetMetadata("variant_sets_ui_hints", metadata)
        else:
            metadata = Vt._ReturnDictionary({"omni:variants_locked": [item._vset_name]})
            prim.SetMetadata("variant_sets_ui_hints", metadata)
        self.refresh()

    def select_prim(self, item):
        selection = self._usd_context.get_selection()
        selection.set_selected_prim_paths([item.prim_path], True)

    def get_prim(self, prim_path):
        if self._stage:
            return self._stage.GetPrimAtPath(prim_path)
        else:
            return None

    def set_view_mode(self, view_state):
        self._view_state = view_state
        self._perform_refresh()

    def toggle_locked_variants(self, state: bool):
        self._hide_locked_variants = state
        self.refresh()

    def set_tab(self, is_groups):
        self.get_expanded()
        self._is_groups = is_groups
        self._perform_refresh()

    def search(self, search_words: Optional[List[str]]):
        self._search = "".join(search_words) if search_words else None
        self.refresh()

    def check_for_update(self, prim_path: str, props):
        if self._stage:
            prim = self._stage.GetPrimAtPath(prim_path)
            if prim:
                if prim in self._variant_prims:
                    if prim.HasVariantSets():
                        if "set()" in props:
                            vset_items = []
                            for v in self._variants:
                                if v.prim_path == prim_path:
                                    vset_items.append(v)
                            vset_names = prim.GetVariantSets().GetNames()
                            if len(vset_names) == len(vset_items):
                                for item in vset_items:
                                    if not item._vset_name in vset_names:
                                        # A variant set has been renamed
                                        return True
                                    else:
                                        for name in vset_names:
                                            if item._vset_name == name:
                                                vset = prim.GetVariantSet(name)
                                                if item._variant_selection == vset.GetVariantSelection():
                                                    continue
                                                else:
                                                    # A variant has been set or renamed
                                                    return True
                                return self.check_for_collection_updates(prim_path)
                            else:
                                # A variant set has been added or removed
                                return True
                        else:
                            return self.check_for_collection_updates(prim_path)
                    else:
                        # A variant prim no longer has variant sets
                        return True
                else:
                    if prim.HasVariantSets():
                        # New variant prim added
                        return True
                    else:
                        return self.check_for_collection_updates(prim_path)
            else:
                for p in self._variant_prims:
                    if p.GetPath().pathString == prim_path:
                        # A variant prim was deleted
                        return True
                return self.check_for_collection_updates(prim_path)
        else:
            return False

    def check_for_collection_updates(self, prim_path: str):
        if not self._group_root or not self._group_root.IsValid():
            return False
        if prim_path == self._group_root.GetPath().pathString:
            collections = Usd.CollectionAPI.GetAllCollections(self._group_root)
            collection_paths = []
            for c in collections:
                if not c.GetPrim().IsValid():
                    continue
                path_str = c.GetCollectionPath().pathString
                if self.group_prefix in path_str:
                    collection_paths.append(path_str)
            if self._ungrouped_variants in self.groups:
                group_count = len(self.groups) - 1
            else:
                group_count = len(self.groups)
            if len(collection_paths) != group_count:
                # A variant group has been added or removed
                return True
            for cpath in collection_paths:
                match = False
                name = cpath.split(self.group_prefix)[1]
                for group in self.groups:
                    if name == group.group_name:
                        match = True
                        break
                if not match:
                    # A variant group has been renamed
                    return True
            return False
        else:
            return False

    def _get_vset_info(self, prim: Usd.Prim) -> typing.Tuple[typing.List[str], Dict[str, str]]:
        prim_path = prim.GetPath().pathString
        cache = self._vset_cache.get(prim_path)
        if cache is not None:
            return cache["vset_names"], cache["selections"]
        vset_names = prim.GetVariantSets().GetNames()
        selections = {}
        for v in vset_names:
            vset = prim.GetVariantSet(v)
            selections[v] = vset.GetVariantSelection()
        self._vset_cache[prim_path] = {"vset_names": vset_names, "selections": selections}
        return vset_names, selections

    def invalidate_vset_cache_for(self, prim_path):
        # Convert Sdf.Path to string to match the string keys used in _vset_cache.
        # StageChangeHelper provides Sdf.Path objects from USD notices, but the cache
        # stores entries using prim.GetPath().pathString (a Python str).
        key = str(prim_path)
        if key in self._vset_cache:
            del self._vset_cache[key]

    def _populate_variants_for_prim(self, prim_item: Prim, usd_prim: Usd.Prim):
        if not usd_prim or not usd_prim.IsValid():
            return
        vset_names, selections = self._get_vset_info(usd_prim)
        for v in vset_names:
            vset = usd_prim.GetVariantSet(v)
            cur_sel = selections.get(v, vset.GetVariantSelection())
            variant_item = Variant(prim=usd_prim, vset=vset, vset_name=v, variant_selection=cur_sel)
            if self._hide_locked_variants and self.get_variant_lock_metadata(variant_item):
                continue
            if self._search:
                if (self._search.lower() in v.lower()) or (self._search.lower() in cur_sel.lower()):
                    prim_item.add_variant(variant_item)
                    self._variants.append(variant_item)
            else:
                prim_item.add_variant(variant_item)
                self._variants.append(variant_item)

    def get_variant_path(self, item: Variant) -> str:
        return item.prim_path + "." + item._vset_name

    def drop_accepted(self, target_item, source, drop_location=-1):
        """Reimplemented from AbstractItemModel. Called to highlight target when drag and drop."""
        if target_item == source:
            if self._drop_target:
                if self._drop_target._drop:
                    self._drop_target._drop.visible = False
            return False

        if not source:
            return False

        if target_item and isinstance(source, Variant):
            drop_target = None
            if isinstance(target_item, Variant):
                for group in self._groups:
                    if target_item in group.variants:
                        drop_target = group
                        break
            elif isinstance(target_item, Group):
                drop_target = target_item
            if self._drop_target:
                if self._drop_target._drop:
                    self._drop_target._drop.visible = False
            if drop_target:
                if drop_target._drop:
                    self._drop_target = drop_target
                    self._drop_target._drop.visible = True
                return True
        else:
            if self._drop_target:
                if self._drop_target._drop:
                    self._drop_target._drop.visible = False
            return False

    def drop(self, target_item, source, drop_location=-1):
        """Reimplemented from AbstractItemModel. Called when dropping something to the item."""
        if self._drop_target:
            if self._drop_target._drop:
                self._drop_target._drop.visible = False

        def move_variant(target_group, variant):
            for group in self._groups:
                if source in group.variants:
                    if group.group_path:
                        omni.kit.commands.execute(
                            "RemoveItemFromCollection",
                            prim_or_prop_path=self.get_variant_path(variant),
                            collection_path=group.group_path,
                        )
                    if target_group.group_path:
                        omni.kit.commands.execute(
                            "AddItemToCollection",
                            path_to_add=self.get_variant_path(variant),
                            collection_path=target_group.group_path,
                        )
                    break
            self._item_changed(variant)

        if not source:
            return

        if target_item and isinstance(source, Variant):
            if isinstance(target_item, Group):
                move_variant(target_item, source)
            elif isinstance(target_item, Variant):
                for group in self._groups:
                    if target_item in group.variants:
                        move_variant(group, source)
                        break

    def get_drag_mime_data(self, item):
        """Returns Multipurpose Internet Mail Extensions (MIME) data for be able to drop this item somewhere"""
        # As we don't do Drag and Drop to the operating system, we return the string.
        try:
            return item.name_model.as_string
        except Exception:
            return ""

    def get_item_children(self, item: typing.Union[None, Prim, Group, Variant]) -> typing.Union[None, typing.List]:
        """UI tree query for the children

        Args:
            item (typing.Union[None, Prim, Variant]): Top level children, Prim children or variant children

        Returns:
            typing.Union[None, typing.List]: _description_
        """
        if item is None:
            # UI is asking for top level items.
            if self._is_groups:
                return self._groups
            else:
                return self._prims
        if isinstance(item, Prim):
            # Populate lazily when the tree asks for children
            if len(item.variants) == 0:
                usd_prim = self.get_prim(item.prim_path)
                self._populate_variants_for_prim(item, usd_prim)
            return item.variants
        if isinstance(item, Group):
            return item.variants
        # Item is an Variant so we return no children.
        return []

    def get_item_value_model_count(self, item: ui.AbstractItem = None) -> int:
        """Returns the number of columns this model item contains

        Args:
            item (ui.AbstractItem): None

        Returns:
            int: Number of columns
        """
        return 1

    def get_item_value_model(self, item: typing.Union[Prim, Group, Variant], column_id: int) -> ui.AbstractValueModel:
        """Get the value model associated with this item

        Args:
            item (typing.Union[Prim, Variant]): The item to request the value model from.
            column_id (int): The column number to get the value model

        Returns:
            ui.AbstractValueModel: The value model
        """
        try:
            return item.name_model
        except Exception:
            # Fallback for non-presenter items (e.g., framework placeholder/header rows)
            return ui.SimpleStringModel("")

    @property
    def prims(self) -> typing.List[Prim]:
        """List of prim items

        Returns:
            typing.List[Prim]: List of prim items
        """
        return self._prims

    @property
    def groups(self) -> typing.List[Group]:
        """List of group items

        Returns:
            typing.List[Group]: List of group items
        """
        return self._groups
