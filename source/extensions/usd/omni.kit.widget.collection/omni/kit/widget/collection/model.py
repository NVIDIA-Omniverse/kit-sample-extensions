# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from pathlib import Path
from typing import List, Union

import carb
import omni.client
import omni.kit.commands
import omni.ui as ui
import omni.usd
import usdrt
from omni.kit.async_engine import run_coroutine
from omni.kit.core.collection import usd
from omni.kit.widget.stage.stage_model import AssetType, StageItem, handle_exception
from pxr import Sdf, Tf, Trace, Usd


class BaseItem(ui.AbstractItem):
    """
    shared code
    """

    is_flat_collection_content = False
    item_type = "Base"

    def __init__(self, path: Sdf.Path, stage: Usd.Stage, root_identifier=None):
        super().__init__()

        self.path = path
        self.name = path.name
        self.root_identifier = root_identifier
        self.stage = stage

        self._label = self.name

        class NameModel(ui.AbstractValueModel):
            """
            just used to store the label of the item
            """

            def __init__(self, label: str):
                super().__init__()
                self._label = label or ""

            def get_value_as_string(self):
                return self._label

        self.name_model = NameModel(self._label)

        self.children = []
        # Speed up access by name. We still need self.children because we need the order.
        self.children_search_index = {}
        # True when it's necessary to repopulate its children
        self.populated = False
        # True when the prim has authored references
        # It's for the item flags like instanceable, references, etc...
        self.dirty_flags = True

        # Filtering
        self.filtered = None
        # True if it has a child that is filtered
        self.child_filtered = None

    def prefilter(self, filter_name_text, lambda_filters, stage):
        """Recursively mark items that meet the filtering rule"""
        # Is the search string in the name?
        filtered_with_string = not filter_name_text or filter_name_text in self.name.lower()

        # Has the given type
        if lambda_filters:
            filtered_with_lambda = False
            object = stage.GetObjectAtPath(self.path)

            # For some reason, a USDProperty is NOT a valid object so we need to special case
            if type(object) == Usd.Property or object.IsValid():
                for _, fn in lambda_filters.items():
                    if fn(object, self.is_flat_collection_content):
                        filtered_with_lambda = True
                        break

        else:
            filtered_with_lambda = True

        # The result filter
        self.filtered = filtered_with_string and filtered_with_lambda

        # We need to expand all when filtering. It's  expensive but it's the only way to get filtered result.
        self.populate_children(stage)

        # Here we set child_filtered = True if ANY of the kids (recursively) have the filter
        self.child_filtered = False
        for child in self.children:
            child.prefilter(filter_name_text, lambda_filters, stage)
            if not self.child_filtered:
                self.child_filtered = child.child_filtered or child.filtered

    def find(self, paths):
        """Finds the child node with given name."""

        if isinstance(paths, Sdf.Path):
            return self.find([pref.name for pref in paths.GetPrefixes()])

        # We are here because paths is list of tokens like this ["World", "Cube"]
        if len(paths) == 0:
            return self

        # Remove first item, find a child with this item, repeat
        # ["World", "Cube"] -> child(name="World").find(["Cube"])
        name = paths.pop(0)
        # name = name.replace("collection:","") #TODO do this at source
        found = self.children_search_index.get(name, None)
        # print ("looking for...", name, "found", repr(found), "searchd under", repr(self))
        # print ("children_search_index", self.children_search_index )
        if found:
            return found.find(paths)

    def find_full_chain(self, tokens, stage):
        """
        Find the child node with given name and return the list of all the
        parent nodes and the found node. It populates the children during
        search.
        """
        result = [self]

        self.populate_children(stage)

        if tokens:
            name = tokens.pop(0)
            found = self.children_search_index.get(name, None)
            if found:
                if tokens:
                    result += found.find_full_chain(tokens, stage)
                else:
                    result += [found]

        return result

    def needs_repopulate(self, flags_dirty=False, recursive=False, erase_kids=False):
        """
        Makes the item repopulated the next time the widget is asking
        children. `flags_dirty` indicates that `update_flags` will also be
        called.
        """
        self.populated = False
        if flags_dirty:
            self.dirty_flags = True
        if erase_kids:
            self.children = []  # throwing away the "cache" is necessary when we switch expansion states in a collection

        if recursive:
            for c in self.children:
                c.needs_repopulate(flags_dirty, recursive)

    def __str__(self):
        return f"{self.path}"

    def get_node_type(self):
        return ""

    def __repr__(self):
        return f"<{self.item_type} '{self.path}'>"

    def is_usd_prim(self):
        return False

    def is_explicit_collection_item(self):
        """
        we want to hightlight things that are explicitly in the collection rather than added
        via expansion
        """
        return False


class PrimItem(BaseItem):
    """
    Represents a single prim at the root of the scene hierarchy or the child of a prim which is..
    TODO: Do we need to keep both this and CollectionPrimContentItem?

    It can have other PrimItem or CollectionItems as Children, and PrimItems as parents
    """

    def __init__(self, path: Sdf.Path, stage: Usd.Stage, root_identifier=None):
        """
        Args:
            path: all of our Model Items take a valid Sdf.Path. In the case of a prim item, we should
            verify it's also a valid Prim path
        """
        super().__init__(path, stage, root_identifier)
        self.item_type = "Prim"

        # Get type
        self.prim = stage.GetPrimAtPath(self.path)
        self.type_model = ui.SimpleStringModel(self.prim.GetTypeName())

    def is_usd_prim(self):
        return True

    def get_node_type(self):
        return self.type_model.get_value_as_string()

    def populate_children(self, stage):
        """
        Add children using the USD context if necessary.
        Returns True if children should also be repopulated.
        """
        if self.populated or not stage or not self.prim:
            return False

        # Reset dirty flags if set
        if self.dirty_flags:
            self.dirty_flags = False

        # Cache old children by path for O(1) lookup
        old_children_map = {child.path: child for child in self.children}
        self.children.clear()
        self.children_search_index.clear()

        # USD predicate to filter children
        display_predicate = Usd.TraverseInstanceProxies(Usd.PrimDefaultPredicate)
        children_iterator = self.prim.GetFilteredChildren(display_predicate)

        # Process prim children
        for child_prim in children_iterator:
            if child_prim == self.prim:
                continue

            if child_prim.GetMetadata("hide_in_stage_window"):
                continue

            child_path = child_prim.GetPath()
            child_name = child_path.name

            # Reuse existing child if possible
            child_item = old_children_map.pop(child_path, None)
            if not child_item:
                child_item = PrimItem(child_path, stage, self.root_identifier)

            self.children.append(child_item)
            self.children_search_index[child_name] = child_item

        # Process collections alongside prims
        collections = Usd.CollectionAPI.GetAllCollections(self.prim)
        for coll in collections:

            coll_path = coll.GetCollectionPath()
            child_item = old_children_map.pop(coll_path, None)
            if not child_item:
                child_item = CollectionItem(coll_path, coll, stage, self.root_identifier)

            bare_name = child_item.name
            self.children.append(child_item)
            self.children_search_index[bare_name] = child_item

        self.populated = True

        # Return True to indicate children repopulation happened
        return True

    # return True if any children is not PrimItem, else return False
    def has_collection_children(self):
        for child in self.children:
            if not isinstance(child, PrimItem):
                return True
            else:
                if child.has_collection_children():
                    return True
        return False

    def add_child(self, item):
        if item:
            name = item.name
            if not self.children_search_index.get(name, None):
                self.children.append(item)
                self.children_search_index[name] = item

    def remove_child(self, item):
        if item:
            name = item.name
            if self.children_search_index.get(name, None):
                self.children.remove(item)
                self.children_search_index.pop(name, None)


class CollectionItem(BaseItem):
    """Represents a USDCollection"""

    def __init__(self, path: Sdf.Path, collection: Usd.CollectionAPI, stage: Usd.Stage, root_identifier=None):
        """
        Args:
            path e.g "/CollectionTest.collection:allGeomProperties"
        """
        super().__init__(path, stage, root_identifier)

        self.collection = collection
        self.item_type = "Collection"

    def is_usd_prim(self):
        return False

    def get_node_type(self):
        return "Collection"

    def populate_children(self, stage):
        """
        We expand the Collection and see what's inside..
        """
        if self.populated:
            return False
        # Move item.children to old_children
        old_children = self.children[:]
        self.children = []
        self.children_search_index = {}

        immediate_children = usd.CollectionHelper(self.path).get_members()  # returns list of sdf_paths
        for item in immediate_children:
            # If it existed item, use it, don't recreate it.
            found_old = next((c for c in old_children if c.path == item), None)
            child_item = None
            if found_old:
                child_item = found_old
                old_children.remove(found_old)
            else:
                if item.IsPropertyPath():
                    if not usd.CollectionHelper.is_collection_property_path(item):
                        child_item = CollectionPrimPropertyContentItem(
                            item, self.collection, self.stage, self.root_identifier
                        )
                else:
                    child_item = CollectionPrimContentItem(item, self.collection, self.stage, self.root_identifier)
            if child_item:
                self.children.append(child_item)
                self.children_search_index[item] = child_item
        self.populated = True
        return True

    def add_child(self, child_item):
        if child_item:
            path = child_item.path
            if not self.children_search_index.get(path, None):
                self.children.append(child_item)
                self.children_search_index[path] = child_item

    def remove_child(self, item):
        if item:
            path = item.path
            if self.children_search_index.get(path, None):
                self.children.remove(item)
                self.children_search_index.pop(path, None)


class CollectionPrimContentItem(BaseItem):
    """
    represents a Prim inside a collection
    """

    is_flat_collection_content = True

    # todo make sure path is an Sdf Path path we can parse.. doesn't matter about anythign else..
    def __init__(self, path: Sdf.Path, collection: Usd.Object, stage: Usd.Stage, root_identifier=None):
        """
        Args
            contents the list of immediate children (props or prims)
        """

        super().__init__(path, stage, root_identifier)
        # print ("init: CollectionPrimContentItem ", path, "part of", collection, "contents", contents)

        self.owning_collection = collection
        self.item_type = "CollectionPrimContentItem"

        prim = stage.GetPrimAtPath(self.path)
        self.type_model = ui.SimpleStringModel(prim.GetTypeName())

    def is_usd_prim(self):
        return True

    def get_node_type(self):
        return self.type_model.get_value_as_string()

    def populate_children(self, stage):
        """
        Add children using the USD context if it's necessary. Returns True
        if children should also be repopulated.
        """
        if self.populated:
            return False
        # Move item.children to old_children
        old_children = self.children[:]
        self.children = []
        self.children_search_index = {}

        # we need to calculate this inside populate_children, as otherwise it won't get updated when expansionstate changes
        children = usd.CollectionHelper(self.owning_collection.GetCollectionPath()).get_members(filter=self.path)
        for item in children:
            # If it existed item, use it, don't recreate it.
            found_old = next((c for c in old_children if c.path == item), None)
            child_item = None
            if found_old:
                child_item = found_old
                old_children.remove(found_old)
            else:
                if item.IsPropertyPath():
                    if not usd.CollectionHelper.is_collection_property_path(item):
                        child_item = CollectionPrimPropertyContentItem(
                            item, self.owning_collection, self.stage, self.root_identifier
                        )
                else:
                    child_item = CollectionPrimContentItem(
                        item, self.owning_collection, self.stage, self.root_identifier
                    )
            if child_item:
                self.children.append(child_item)
                self.children_search_index[item] = child_item
        self.populated = True
        return True

    def add_child(self, child_item):
        if child_item:
            path = child_item.path
            if not self.children_search_index.get(path, None):
                self.children.append(child_item)
                self.children_search_index[path] = child_item

    def remove_child(self, item):
        if item:
            path = item.path
            if self.children_search_index.get(path, None):
                self.children.remove(item)
                self.children_search_index.pop(path, None)

    def is_explicit_collection_item(self):

        # TODO: Check performance of this
        return self.path in self.owning_collection.GetIncludesRel().GetTargets()


class CollectionPrimPropertyContentItem(BaseItem):
    """
    represents a Property in collection. It's always under a prim

    Args:
        path: a valid Sdf Path for a Prim or Property on a prim
    """

    is_flat_collection_content = True

    # todo make sure path is an Sdf Path path we can parse.. doesn't matter about anythign else..
    def __init__(self, path: Sdf.Path, collection: Usd.Object, stage: Usd.Stage, root_identifier=None):

        super().__init__(path, stage, root_identifier)
        # print ("init: CollectionContentItem ", path, "part of", collection)
        self.owning_collection = collection
        self.item_type = "CollectionPrimPropertyContentItem"

        # Get type
        self.type_model = ui.SimpleStringModel("CollectionPrimPropertyContentItem")

    def is_usd_prim(self):
        return False

    def get_node_type(self):
        return "Property"

    def populate_children(self, stage):
        """
        Add children using the USD context if it's necessary. Returns True
        if children should also be repopulated.
        """
        return False

    def __repr__(self):
        return f"<Omni::UI CollectionPrimPropertyContentItem Item '{self.path}'>"

    def is_explicit_collection_item(self):

        # TODO: Check performance of this
        return self.path in self.owning_collection.GetIncludesRel().GetTargets()


class CollectionModel(ui.AbstractItemModel):
    """The item model that watches the stage"""

    def __init__(self, stage: Usd.Stage, collection_watch=None):

        super().__init__()

        self._stage = stage
        self._collection_watch = collection_watch
        if self._stage:
            self._root = PrimItem(Sdf.Path.absoluteRootPath, self._stage, self._stage.GetRootLayer().identifier)
            self._defaultPrim = self._stage.GetRootLayer().defaultPrim
            stage_id = omni.usd.get_context().get_stage_id()
            try:
                self._usdrt_stage = usdrt.Usd.Stage.Attach(stage_id)
            except Exception as e:
                carb.log_warn(f"Failed to attach usdrt stage: {e}")
                self._usdrt_stage = None
            if self._usdrt_stage:
                self._build_from_leaf_to_root(stage)
        else:
            self._root = None
            self._defaultPrim = None

        # Stage watching
        if self._stage:
            self.__stage_listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_objects_changed, self._stage)

        self.__dirty_prim_paths = set()
        self.__prim_changed_task = None

        # The string that the shown objects should have.
        self._filter_name_text = None
        # The dict of form {"type_name_string", lambda prim: True}. When lambda is True, the prim will be shown.
        self._filters = {}
        self.__prim_filter_task = None

    def _build_from_leaf_to_root(self, stage):
        if not stage or not self._root or not self._usdrt_stage:
            return False
        if self._collection_watch and len(self._collection_watch.current_collection) > 0:
            collection_prims = self._collection_watch.current_collection
        elif not getattr(usdrt, "OVSTAGE_BACKED", False) and hasattr(self._usdrt_stage, "GetPrimsWithAppliedAPIName"):
            collection_prims = self._usdrt_stage.GetPrimsWithAppliedAPIName("CollectionAPI")
        else:
            # Kit 111's OVStage-backed USDRT (what production apps load; usdrt.OVSTAGE_BACKED) finds no multi-apply
            # schema by base name, if it has GetPrimsWithAppliedAPIName at all: read the composed USD stage.
            # CollectionAPI is multi-apply, so its applied schemas read "CollectionAPI:<name>".
            collection_prims = [
                prim.GetPath()
                for prim in stage.Traverse()
                if any(schema.split(":")[0] == "CollectionAPI" for schema in prim.GetAppliedSchemas())
            ]
        for p in collection_prims:
            current_path = Sdf.Path(str(p))
            self.add_item_by_path(current_path, stage)
        self._root.populated = True
        return True

    def update_item_by_path(self, path, stage):
        current_prim = stage.GetPrimAtPath(path)
        collections = Usd.CollectionAPI.GetAllCollections(current_prim)
        if not collections:
            item = self.find(path)
            if isinstance(item, PrimItem):
                if item.has_collection_children():
                    self._reload_all_collection(path, stage)
                    if not item.has_collection_children():
                        self._on_prim_removed(path)
                else:
                    self._on_prim_removed(path)
        else:
            self.add_item_by_path(path, stage)

    def add_item_by_path(self, path, stage):
        if not stage or not path:
            return
        if not stage.GetPrimAtPath(path) and not self.find(path):
            return
        current_path = path
        previous_item = None
        find_parent_item = None

        while not (find_parent_item := self.find(current_path)):
            current_prim = stage.GetPrimAtPath(current_path)
            current_item = PrimItem(current_path, stage, stage.GetRootLayer().identifier)

            if previous_item:
                current_item.add_child(previous_item)
            collections = Usd.CollectionAPI.GetAllCollections(current_prim)
            if len(collections) > 0 and self._collection_watch:
                self._collection_watch.add_collection(current_path)
            for coll in collections:
                coll_path = coll.GetCollectionPath()
                child_item = CollectionItem(coll_path, coll, stage)
                current_item.add_child(child_item)

            current_item.populated = True
            previous_item = current_item
            current_path = current_path.GetParentPath()

        if previous_item:
            find_parent_item.add_child(previous_item)
        self._reload_all_collection(path, stage)

    # update all collection again here for update this prim may update by delete it's collection child
    # TODO: it not correct for the on_prim_create, it may trigger by delete some collection
    def _reload_all_collection(self, path, stage):
        find_item = self.find(path)
        if find_item:
            prim = stage.GetPrimAtPath(path)
            if prim:
                collections = Usd.CollectionAPI.GetAllCollections(prim)
                item_to_remove = []
                for item in find_item.children:
                    if isinstance(item, CollectionItem):
                        item_to_remove.append(item)
                for item in item_to_remove:
                    find_item.remove_child(item)
                for coll in collections:
                    coll_path = coll.GetCollectionPath()
                    child_item = CollectionItem(coll_path, coll, stage)
                    find_item.add_child(child_item)
            else:
                # it's not a prim, so it's a collection
                find_item.populated = False
                find_item.needs_repopulate(True, True)

    def find(self, path: Sdf.Path) -> ui.AbstractItem:
        """Return item with the given path"""
        if not self._root:
            return None

        if path == Sdf.Path.absoluteRootPath:
            return self._root

        return self._root.find(path)

    def find_full_chain(self, path):
        """Return the list of all the parent nodes and the node representing the given path"""
        if not self._root:
            return None

        if not path or path == "/":
            return None

        if path[-1] == "/":
            path = path[:-1]

        prefixes = path.split("/")[1:]
        return self._root.find_full_chain(prefixes, self._stage)

    def update_dirty(self):
        """
        Create/remove dirty items that was collected from TfNotice. Can be
        called any time to pump changes.
        """
        dirty_prim_paths = self.__dirty_prim_paths.copy()  # Copy to be on the safe side.
        self.__dirty_prim_paths = set()
        for path in dirty_prim_paths:
            # If the path is a prim path, we need to update the collection state
            if path.IsPrimPath():
                prim = self._stage.GetPrimAtPath(path)
                if prim:
                    self._on_prim_created(path)
                else:
                    self._on_prim_removed(path)

            elif usd.CollectionHelper.is_collection_property_path(path):
                coll_path = usd.CollectionHelper.strip_property_from_path(path)
                # Check to see if the prim has a valid collection attribute.
                # If not, The collection does not exist and needs to be removed.
                if not self._stage.GetPropertyAtPath(path):
                    self._on_prim_removed(coll_path)
                else:
                    self._on_prim_created(coll_path)

    @Trace.TraceFunction
    def _on_objects_changed(self, notice, sender):
        """Called by Usd.Notice.ObjectsChanged"""
        if not (self.__prim_changed_task is None or self.__prim_changed_task.done()):
            return

        prims_resynced = []

        # We want to handle:
        # Prim Updates - these happen when we add/delete/rename a Collection
        # Collection Updates - when we change one of the 4 properties of a collection
        #
        # At the moment, we don't really treat them differently. Maybe we should for efficiency

        coll_attribs = usd.CollectionHelper.get_collection_properties()

        for sdf_path in notice.GetChangedInfoOnlyPaths():
            # We ignore any property updates other than the collection ones
            if sdf_path.IsPropertyPath():
                for a in coll_attribs:
                    if sdf_path.pathString.endswith(":" + a):
                        prims_resynced.append(sdf_path)
                        break
            else:
                # it's a prim path
                # OMPE-65187: Filter out prototype prim paths to avoid unnecessary updates
                if Usd.Prim.IsPrototypePath(sdf_path) or Usd.Prim.IsPathInPrototype(sdf_path):
                    continue
                prims_resynced.append(sdf_path)

        # Used for created prims
        for p in notice.GetResyncedPaths():
            # We ignore any property updates other than the collection ones
            if p.IsPropertyPath():
                for a in coll_attribs:
                    if p.pathString.endswith(":" + a):
                        prims_resynced.append(p)
                        break
            else:
                # OMPE-65187: Filter out prototype prim paths to avoid unnecessary updates
                if Usd.Prim.IsPrototypePath(p) or Usd.Prim.IsPathInPrototype(p):
                    continue
                prims_resynced.append(p)
        if not prims_resynced:
            return

        self.__dirty_prim_paths.update(prims_resynced)
        # Update in the next frame. We need it because we want to accumulate the affected prims
        if self.__prim_changed_task is None or self.__prim_changed_task.done():
            self.__prim_changed_task = run_coroutine(self.__delayed_prim_changed())

    @handle_exception
    @Trace.TraceFunction
    async def __delayed_prim_changed(self):
        await omni.kit.app.get_app().next_update_async()

        # Pump the changes to the model.
        self.update_dirty()

        self.__prim_changed_task = None

    @handle_exception
    @Trace.TraceFunction
    async def __delayed_prim_filter(self):
        await omni.kit.app.get_app().next_update_async()

        # Pump the changes to the model.
        filter_name_text = self._filter_name_text and self._filter_name_text.lower()
        if self._root:
            self._root.prefilter(filter_name_text, self._filters, self._stage)
            self._item_changed(None)

        self.__prim_filter_task = None

    def _on_prim_created(self, path: Sdf.Path):
        """
        this is called via update_dirty whenever something
        changes in the scene.
        It's not really on_prim_created, it's also when collection expansion state changes..

        Attrs
            path is a prim path to a newly created prim, or a collection that needs to be updated
        """
        if not self._root:
            return
        if path == Sdf.Path.absoluteRootPath:
            # It happens when recomposition of stage
            if not self._build_from_leaf_to_root(self._stage):
                self._root.needs_repopulate(True, True)
                self._on_prim_updated(Sdf.Path.absoluteRootPath)
        elif path.IsPrimPath():
            # print("elif path.IsPrimPath():", path)
            self.update_item_by_path(path, self._stage)
            self._item_changed(None)
        elif Usd.CollectionAPI.IsCollectionAPIPath(path):
            # print("elif Usd.CollectionAPI.IsCollectionAPIPath(path):", path)
            # It's a Collection
            self.add_item_by_path(path, self._stage)
            self._item_changed(None)
        else:
            carb.log_warn(f"_on_prim_created: unknown type for path {path}")

        if not self._root:
            carb.log_warn(f"root item is None")
            return

        if self._filter_name_text or self._filters:
            # If it's filtering mode, we need to refilter everything to make the new object appear
            filter_name_text = self._filter_name_text and self._filter_name_text.lower()
            self._root.prefilter(filter_name_text, self._filters, self._stage)

    def _on_prim_removed(self, path):
        if not self._root:
            return

        # Update parent
        # self._on_prim_updated(path.GetParentPath())
        def remove(path):
            found_parent = self.find(path.GetParentPath())
            if found_parent:
                item_to_remove = self.find(path)
                if self._collection_watch:
                    self._collection_watch.remove_collection(path)
                if item_to_remove:
                    found_parent.remove_child(item_to_remove)
                    # TODO: in current workflow, filter always works, so don't need to check this for now
                    if (
                        not found_parent.children
                        and found_parent.path != Sdf.Path.absoluteRootPath
                        and found_parent != self._root
                    ):
                        remove(found_parent.path)
                    return True
            else:
                return False

        if remove(path):
            self._item_changed(None)

    def _on_prim_updated(self, path, update_flags=False, force_rebuild_tree=False):
        found = self.find(path)
        if found:
            found.needs_repopulate(update_flags)
            if found.path == Sdf.Path.absoluteRootPath:
                # Pass None to the widget if root is changed
                found = None
            # If found==None the entire tree will be rebuilt
            self._item_changed(found if not force_rebuild_tree else None)
        else:
            pass

    def get_item_children(self, item: ui.AbstractItem) -> List[ui.AbstractItem]:
        """Reimplemented from AbstractItemModel"""

        if item is None:
            item = self._root

        if not item:
            return []
        # When running tests, it's possible that usd_context doesn't have a stage
        if self._stage:
            need_repopulate_children = item.populate_children(self._stage)
            if need_repopulate_children:
                for child in item.children:
                    child.needs_repopulate(True)
                    self._item_changed(child)

        if not self._filter_name_text and not self._filters:
            # If _filter_name_text is empty, then user didn't request filtered result and we can just return children.
            return item.children
        else:
            return [child for child in item.children if (child.filtered or child.child_filtered)]

    def get_item_value_model_count(self, item):
        """Reimplemented from AbstractItemModel"""
        return 1

    def get_item_value_model(self, item, column_id):
        """Reimplemented from AbstractItemModel"""

        if item is None:
            item = self._root

        if not item:
            return None

        if column_id == 0:
            return item.name_model

    def drop_accepted(self, target_item, source):
        """Reimplemented from AbstractItemModel. Called to highlight target when drag and drop."""

        # TODO: try/except so we don't have to have a hard dep on stage?
        from omni.kit.widget.stage.stage_model import StageItem

        droppable_sources = [StageItem, PrimItem, CollectionItem, CollectionPrimContentItem]
        for source_class in droppable_sources:
            if isinstance(source, source_class) and source != target_item:
                # print("drop_accepted from ", source_class, target_item, source, type(source))
                return True
        if isinstance(source, str):
            # Drag and drop from the content browser, material browser
            return True

        # print("drop_not accepted", target_item, source, type(source))
        return False

    def _add_prim(self, source_path: str, target_item):
        if isinstance(target_item, CollectionPrimContentItem) or isinstance(
            target_item, CollectionPrimPropertyContentItem
        ):
            collection_path = target_item.owning_collection.GetCollectionPath().pathString
            omni.kit.commands.execute(
                "AddItemToCollection", path_to_add=str(source_path), collection_path=collection_path
            )
        elif isinstance(target_item, CollectionItem):
            collection_path = target_item.path.pathString
            omni.kit.commands.execute(
                "AddItemToCollection", path_to_add=str(source_path), collection_path=collection_path
            )

    def drop(self, target_item: BaseItem, source: Union[BaseItem, StageItem, str]):
        """This supports dropping onto the Collection widget"""

        if not self._root:
            return

        if not target_item:
            target_item = self._root

        # adding a prim to a collection
        if (
            isinstance(source, StageItem)
            or isinstance(source, CollectionPrimContentItem)
            or isinstance(source, PrimItem)
        ):
            if source.root_identifier == target_item.root_identifier:
                # if we drop onto a prim, we want the target to be it's parent
                self._add_prim(source.path, target_item)

        elif isinstance(source, str):
            # NOTE: need to check if the string has multiple elements separated by newline, `\n`.
            source_list = source.split("\n")
            for source_path in source_list:
                # Drag and drop from the content browser
                if AssetType().is_usd(source_path):
                    stem = Path(source_path).stem
                    path = target_item.path.AppendChild(Tf.MakeValidIdentifier(stem))
                    omni.kit.commands.execute(
                        "CreateReference", path_to=path, asset_path=source_path, usd_context=omni.usd.get_context()
                    )
                elif AssetType().is_mdl(source_path):
                    AssetType().add_future(self.__apply_mdl(source_path, target_item.path))
                else:
                    prim = self._stage.GetPrimAtPath(source_path)
                    if prim:
                        self._add_prim(prim.GetPath(), target_item)

        # Add a Collection to a Collection
        elif isinstance(source, CollectionItem):
            if source.root_identifier == target_item.root_identifier:
                collection_path = str(target_item)
                if isinstance(target_item, CollectionPrimContentItem) or isinstance(
                    target_item, CollectionPrimPropertyContentItem
                ):
                    collection_path = target_item.owning_collection.GetCollectionPath().pathString
                omni.kit.commands.execute(
                    "AddItemToCollection", path_to_add=str(source.path), collection_path=collection_path
                )
        else:
            carb.log_warn(f"didn't drop.. source is of type {type(source)}")
        # TODO: A load of other permutations to add

    def get_drag_mime_data(self, item):
        """Returns Multipurpose Internet Mail Extensions (MIME) data for be able to drop this item somewhere"""
        # As we don't do Drag and Drop to the operating system, we return the string.
        return str(item.path) if item else "/"

    @handle_exception
    async def __apply_mdl(self, mdl_name, target_path):
        """Import and apply MDL asset to the specified prim"""
        mtl_name = await AssetType().get_first_material_name(mdl_name)
        if not mtl_name:
            carb.log_error(f"[Stage Widget] the MDL Asset '{mdl_name}' doesn't have any material")
            return

        omni.kit.undo.begin_group()

        # Create material. Despite the name, it only can bind to selection.
        mtl_created_list = []
        omni.kit.commands.execute(
            "CreateAndBindMdlMaterialFromLibrary",
            mdl_name=mdl_name,
            mtl_name=mtl_name,
            mtl_created_list=mtl_created_list,
            select_new_prim=False,
        )

        # Bind created material to the target prim
        # Special case: don't bind it to /World and to /World/Looks
        if target_path and target_path not in ["/World", "/World/Looks"]:
            omni.kit.commands.execute(
                "BindMaterialCommand", prim_path=target_path, material_path=mtl_created_list[0], strength=None
            )

        omni.kit.undo.end_group()

    def filter_by_text(self, filter_name_text):
        if not self._root:
            return

        """Specify the filter string that is used to reduce the model"""
        if self._filter_name_text == filter_name_text:
            return

        self._filter_name_text = filter_name_text
        if filter_name_text and self._root:
            self._root.prefilter(filter_name_text.lower(), self._filters, self._stage)

        self._item_changed(None)

    def filter(self, add=None, remove=None, clear=None):
        """
        Set filtering by type. In most cases we need to filter with several types, so this method allows to add, remove
        and set list of types and update the items if it's necessary.

        Args:
            add: The dictionary of this form: {"type_name_string", lambda prim: True}. When lambda is True, the prim
                 will be shown.
            remove: Can be str, dict, list, set. Removes filter by name.
            clear: Removes all the filters. When using with `add`, it will remove the filters first and then will add
                   the given ones.

        Returns:
            True if the model has filters. False otherwise.
        """

        if not self._root:
            return

        changed = False

        if clear:
            if self._filters:
                self._filters.clear()
                changed = True

        if remove:
            if isinstance(remove, str):
                remove = [remove]

            for key in remove:
                if key in self._filters:
                    del self._filters[key]
                    changed = True

        if add:
            self._filters.update(add)
            changed = True

        if changed:
            if self.__prim_filter_task is None or self.__prim_filter_task.done():
                self.__prim_filter_task = run_coroutine(self.__delayed_prim_filter())

        return not not self._filters

    def get_filters(self):
        """Return dict of filters"""
        return self._filters

    def reset(self):
        """Force full re-update"""
        if self._root:
            self._root.children = []
            self._root.children_search_index = {}
            self._root.populated = False
        self._item_changed(None)

    def destroy(self):
        self._stage = None
        self._root = None
        self._defaultPrim = None

        self.__stage_listener = None

        self.__dirty_prim_paths = set()
        self.__prim_changed_task = None
        self.__prim_filter_task = None
