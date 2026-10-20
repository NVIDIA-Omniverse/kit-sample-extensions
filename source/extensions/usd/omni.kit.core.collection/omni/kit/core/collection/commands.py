# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import contextlib
from typing import List, Optional, Union

import carb
import omni
import omni.kit.commands
from omni.usd.commands import ToggleVisibilitySelectedPrimsCommand
from pxr import Sdf, Usd, UsdGeom

from .usd import CollectionHelper, StageHelper, increment_pathname


@contextlib.contextmanager
def apply_stored_edit_target(stage: Usd.Stage, edit_target: Union[Usd.EditTarget, None] = None):

    # Store the current edit target
    current_edit_target = stage.GetEditTarget()

    # Apply the edit target in use when the command was initially called
    if edit_target:
        stage.SetEditTarget(edit_target)

    try:
        yield
    finally:
        # Restore the "current" edit target
        stage.SetEditTarget(current_edit_target)


class AddItemToCollection(omni.kit.commands.Command):
    def __init__(self, path_to_add: str, collection_path: str, usd_context_name: str = "", **kwargs):
        """
        Args:
            path_to_add: A full path to a prim/property/collection
            collection_path: full path to the collection
        """
        self.path_to_add = path_to_add
        self.collection_path = collection_path
        self.usd_context_name = usd_context_name

        self.stage = StageHelper.get_stage(self.usd_context_name)
        self._edit_target = self.stage.GetEditTarget() if self.stage else None

    def do(self):
        collection = CollectionHelper(self.collection_path, self.stage).get_collection_api()
        if collection.GetIncludeRootAttr().Get():
            carb.log_warn("AddItemToCollection: can't add to a collection that includes Root!")
        else:
            collection.IncludePath(Sdf.Path(self.path_to_add))
            carb.log_warn(f"AddItemToCollection do {self.path_to_add} {self.collection_path}")

    def undo(self):
        with apply_stored_edit_target(self.stage, self._edit_target):
            collection = CollectionHelper(self.collection_path, self.stage).get_collection_api()
            current_includes = collection.GetIncludesRel().RemoveTarget(Sdf.Path(self.path_to_add))
            carb.log_verbose("AddItemToCollection undo %s %s" % (self.path_to_add, self.collection_path))


class RemoveItemFromCollection(omni.kit.commands.Command):
    """
    If the item has been directly included in the collection, we can remove it from the includes list
    """

    def __init__(self, prim_or_prop_path: str, collection_path: str, usd_context_name: str = "", **kwargs):
        self.prim_or_prop_path = prim_or_prop_path
        self.collection_path = collection_path
        self.usd_context_name = usd_context_name

        self.stage = StageHelper.get_stage(self.usd_context_name)
        self._edit_target = self.stage.GetEditTarget() if self.stage else None

    def do(self):
        collection = CollectionHelper(self.collection_path, self.stage).get_collection_api()
        path_to_remove = Sdf.Path(self.prim_or_prop_path)
        collection.CreateIncludesRel().RemoveTarget(path_to_remove)
        carb.log_verbose("RemoveItemFromCollection do %s %s" % (self.prim_or_prop_path, self.collection_path))

    def undo(self):
        with apply_stored_edit_target(self.stage, self._edit_target):
            collection = CollectionHelper(self.collection_path, self.stage).get_collection_api()
            path_to_add = Sdf.Path(self.prim_or_prop_path)
            collection.CreateIncludesRel().AddTarget(path_to_add)
            carb.log_verbose("RemoveItemFromCollection undo %s %s" % (self.prim_or_prop_path, self.collection_path))


class ExcludeItemFromCollection(omni.kit.commands.Command):
    """
    Add the item to the exclude list
    """

    def __init__(self, prim_or_prop_path: str, collection_path: str, usd_context_name: str = "", **kwargs):
        self.prim_or_prop_path = prim_or_prop_path
        self.collection_path = collection_path
        self.usd_context_name = usd_context_name

        self.stage = StageHelper.get_stage(self.usd_context_name)
        self._edit_target = self.stage.GetEditTarget() if self.stage else None

    def do(self):
        collection = CollectionHelper(self.collection_path, self.stage).get_collection_api()
        path_to_remove = Sdf.Path(self.prim_or_prop_path)
        collection.CreateExcludesRel().AddTarget(path_to_remove)
        carb.log_verbose("ExcludeItemFromCollection do %s %s" % (self.prim_or_prop_path, self.collection_path))

    def undo(self):
        with apply_stored_edit_target(self.stage, self._edit_target):
            collection = CollectionHelper(self.collection_path, self.stage).get_collection_api()
            path_to_remove = Sdf.Path(self.prim_or_prop_path)
            collection.CreateExcludesRel().RemoveTarget(path_to_remove)
            carb.log_verbose("ExcludeItemFromCollection undo %s %s" % (self.prim_or_prop_path, self.collection_path))


class ClearCollection(omni.kit.commands.Command):
    def __init__(self, collection_path: str, usd_context_name: str = "", **kwargs):
        self.collection_path = collection_path
        self.usd_context_name = usd_context_name

        self.stage = StageHelper.get_stage(self.usd_context_name)
        self._edit_target = self.stage.GetEditTarget() if self.stage else None

    def do(self):
        collection = CollectionHelper(self.collection_path, self.stage).get_collection_api()

        self.includes = collection.GetIncludesRel().GetTargets()
        self.excludes = collection.GetExcludesRel().GetTargets()
        self.expansion = collection.GetExpansionRuleAttr().Get()

        collection.ResetCollection()
        carb.log_verbose("ClearCollection do %s " % (self.collection_path))

    def undo(self):
        with apply_stored_edit_target(self.stage, self._edit_target):
            collection = CollectionHelper(self.collection_path, self.stage).get_collection_api()
            collection.GetIncludesRel().SetTargets(self.includes)
            collection.GetExcludesRel().SetTargets(self.excludes)
            collection.GetExpansionRuleAttr().Set(self.expansion)
            carb.log_verbose("ClearCollection undo %s" % (self.collection_path))


class BlockCollection(omni.kit.commands.Command):
    def __init__(self, collection_path: str, usd_context_name: str = "", **kwargs):
        self.collection_path = collection_path
        self.usd_context_name = usd_context_name

        self.stage = StageHelper.get_stage(self.usd_context_name)
        self._edit_target = self.stage.GetEditTarget() if self.stage else None

    def do(self):
        collection = CollectionHelper(self.collection_path, self.stage).get_collection_api()

        self.includes = collection.GetIncludesRel().GetTargets()
        self.excludes = collection.GetExcludesRel().GetTargets()

        collection.BlockCollection()
        carb.log_verbose("BlockCollection do %s " % (self.collection_path))

    def undo(self):
        with apply_stored_edit_target(self.stage, self._edit_target):
            collection = CollectionHelper(self.collection_path, self.stage).get_collection_api()
            collection.GetIncludesRel().SetTargets(self.includes)
            collection.GetExcludesRel().SetTargets(self.excludes)
            carb.log_verbose("BlockCollection undo %s" % (self.collection_path))


class SetCollectionExpansionRule(omni.kit.commands.Command):

    string_to_token_mapping = {
        "explicitOnly": Usd.Tokens.explicitOnly,
        "expandPrims": Usd.Tokens.expandPrims,
        "expandPrimsAndProperties": Usd.Tokens.expandPrimsAndProperties,
    }

    def __init__(self, collection_path: str, expansion_rule: str, usd_context_name: str = "", **kwargs):
        self.collection_path = collection_path
        self.expansion_rule = expansion_rule
        self.usd_context_name = usd_context_name
        self.rule_token = None
        self.current_val = None

        self.stage = StageHelper.get_stage(self.usd_context_name)
        self._edit_target = self.stage.GetEditTarget() if self.stage else None

    def do(self):
        if self.expansion_rule in self.string_to_token_mapping:
            self.rule_token = self.string_to_token_mapping[self.expansion_rule]
            collection = CollectionHelper(self.collection_path, self.stage).get_collection_api()
            self.current_val = collection.GetExpansionRuleAttr().Get()
            collection.GetExpansionRuleAttr().Set(self.rule_token)
            carb.log_verbose("SetCollectionExpansionRule do %s %s" % (self.collection_path, self.expansion_rule))
        else:
            carb.log_warn(f"SetCollectionExpansionRule: invalid rule {self.expansion_rule}")

    def undo(self):
        with apply_stored_edit_target(self.stage, self._edit_target):
            if self.current_val:
                collection = CollectionHelper(self.collection_path, self.stage).get_collection_api()
                collection.GetExpansionRuleAttr().Set(self.current_val)
                carb.log_verbose("SetCollectionExpansionRule undo %s %s" % (self.collection_path, self.expansion_rule))


class DuplicateCollection(omni.kit.commands.Command):
    """
    Duplicate a collection under the same prim path
    we just want to use the same logic as prim duplicate and add a numeric counter to the end
    """

    def __init__(self, collection_path: str, new_collection_name: str = "", usd_context_name: str = "", **kwargs):
        self.collection_path = collection_path
        self.new_collection_name = new_collection_name
        self.usd_context_name = usd_context_name

        self.stage = StageHelper.get_stage(self.usd_context_name)
        self._edit_target = self.stage.GetEditTarget() if self.stage else None

    def do(self):
        coll_helper = CollectionHelper(self.collection_path, self.stage)
        if not self.new_collection_name:
            self.new_collection_name = coll_helper.get_collection_name()

        self.duplicated_coll_full_path = coll_helper.duplicate_with_name(self.new_collection_name, True)

        carb.log_verbose("DuplicateCollection do %s %s" % (self.collection_path, self.duplicated_coll_full_path))

    def undo(self):
        with apply_stored_edit_target(self.stage, self._edit_target):
            coll_helper = CollectionHelper(self.duplicated_coll_full_path, self.stage)
            coll_helper.delete_collection()
            carb.log_verbose("DuplicateCollection undo %s" % (self.duplicated_coll_full_path))


class RenameCollection(omni.kit.commands.Command):
    """
    Rename a collection under the same prim
    """

    def __init__(self, old_collection_path: str, new_collection_name: str, usd_context_name: str = "", **kwargs):
        self.old_collection_path = old_collection_path
        self.new_collection_name = new_collection_name
        self.usd_context_name = usd_context_name

        self.stage = StageHelper.get_stage(self.usd_context_name)
        self._edit_target = self.stage.GetEditTarget() if self.stage else None

    def do(self):
        coll_helper = CollectionHelper(self.old_collection_path, self.stage)

        self.old_collection_name = coll_helper.collection_name

        stage = self.stage if self.stage else omni.usd.get_context().get_stage()
        prim_path = Sdf.Path(self.old_collection_path).GetPrimPath()
        prim = stage.GetPrimAtPath(prim_path)

        while prim.GetPropertiesInNamespace(CollectionHelper.prop_prefix + self.new_collection_name):
            self.new_collection_name = increment_pathname(self.new_collection_name)

        coll_helper2 = CollectionHelper(
            prim_path.pathString + CollectionHelper.prop_dotted_prefix + self.new_collection_name, self.stage
        )

        self.new_collection_path = coll_helper.duplicate_with_name(coll_helper2.get_collection_name())
        coll_helper.delete_collection()

        carb.log_verbose("RenameCollection do %s %s" % (self.old_collection_path, self.new_collection_name))

        return coll_helper2.get_full_path()

    def undo(self):
        with apply_stored_edit_target(self.stage, self._edit_target):
            coll_helper_new = CollectionHelper(self.new_collection_path, self.stage)
            coll_helper_prev = CollectionHelper(self.old_collection_path, self.stage)

            coll_helper_new.duplicate_with_name(coll_helper_prev.get_collection_name())
            coll_helper_new.delete_collection()
            carb.log_verbose("RenameCollection undo %s %s" % (self.old_collection_path, self.new_collection_name))


class DeleteCollection(omni.kit.commands.Command):
    def __init__(self, collection_path: str, usd_context_name: str = "", **kwargs):
        self.collection_path = collection_path
        self.usd_context_name = usd_context_name

        self.stage = StageHelper.get_stage(self.usd_context_name)
        self._edit_target = self.stage.GetEditTarget() if self.stage else None

    def do(self):
        coll_helper = CollectionHelper(self.collection_path, self.stage)

        api = coll_helper.get_collection_api()

        self.includes = api.GetIncludesRel().GetTargets()
        self.excludes = api.GetExcludesRel().GetTargets()

        expansion_rule_attr = api.GetExpansionRuleAttr()
        self.authored_expansion = False
        if expansion_rule_attr.HasAuthoredValue():
            self.expansion = expansion_rule_attr.Get()
            self.authored_expansion = True

        include_root_attr = api.GetIncludeRootAttr()
        self.authored_include_root = False
        if include_root_attr.HasAuthoredValue():
            self.includesRoot = include_root_attr.Get()
            self.authored_include_root = True

        coll_helper.delete_collection()
        carb.log_verbose("DeleteCollection do %s " % (self.collection_path))

    def undo(self):
        with apply_stored_edit_target(self.stage, self._edit_target):
            prim_path, collection_name = CollectionHelper._get_collection_path_elements(Sdf.Path(self.collection_path))
            api = CreateCollection._do_create(prim_path, collection_name, self.stage)
            api.GetIncludesRel().SetTargets(self.includes)
            api.GetExcludesRel().SetTargets(self.excludes)
            if self.authored_expansion:
                api.GetExpansionRuleAttr().Set(self.expansion)
            if self.authored_include_root:
                api.GetIncludeRootAttr().Set(self.includesRoot)
            carb.log_verbose("DeleteCollection undo %s " % (self.collection_path))


class CreateCollection(omni.kit.commands.Command):
    def __init__(self, prim_path: str, collection_name: str = "", usd_context_name: str = "", **kwargs):
        super().__init__()
        self.prim_path = prim_path
        self.name = collection_name
        self.usd_context_name = usd_context_name
        self.stage = StageHelper.get_stage(self.usd_context_name)
        self._edit_target = self.stage.GetEditTarget() if self.stage else None

    @classmethod
    def _do_create(cls, prim_path: str, collection_name: str = "", stage=None):
        current_stage = stage if stage else omni.usd.get_context().get_stage()
        prim = current_stage.GetPrimAtPath(Sdf.Path(prim_path))

        if not collection_name:
            collection_name = "collection"

        while prim.GetPropertiesInNamespace(CollectionHelper.prop_prefix + collection_name):
            collection_name = increment_pathname(collection_name)

        # USD >=21.02 uses Apply, earlier uses ApplyCollection
        if hasattr(Usd.CollectionAPI, "Apply"):
            return Usd.CollectionAPI.Apply(prim, collection_name)
        return Usd.CollectionAPI.ApplyCollection(prim, collection_name)

    def do(self):
        collection = self._do_create(self.prim_path, self.name, self.stage)
        self.name = collection.GetName()
        carb.log_verbose("CreateCollection do %s %s" % (self.prim_path, self.name))
        return collection.GetCollectionPath()

    def undo(self):
        with apply_stored_edit_target(self.stage, self._edit_target):
            coll_helper = CollectionHelper(self.prim_path + CollectionHelper.prop_dotted_prefix + self.name, self.stage)
            coll_helper.delete_collection()
            carb.log_verbose("CreateCollection undo %s %s" % (self.prim_path, self.name))


class SelectPrimsInCollection(omni.kit.commands.Command):
    def __init__(self, collection_path: str = "", usd_context_name: str = "", **kwargs):
        super().__init__()
        self.collection_path = collection_path
        self.usd_context_name = usd_context_name

        self.stage = StageHelper.get_stage(self.usd_context_name)

    def do(self):
        self._prev_selection = omni.usd.get_context().get_selection().get_selected_prim_paths()

        coll_helper = CollectionHelper(self.collection_path, self.stage)
        prims = coll_helper.get_all_members(prims_only=True)
        prim_list = [p.GetPrimPath().pathString for p in prims]
        omni.usd.get_context().get_selection().set_selected_prim_paths(prim_list, True)
        carb.log_verbose("SelectPrimsInCollection do %s" % (self.collection_path))

    def undo(self):
        omni.usd.get_context().get_selection().set_selected_prim_paths(self._prev_selection, True)
        carb.log_verbose("SelectPrimsInCollection undo %s" % (self.collection_path))


class SetCollectionVisibility(ToggleVisibilitySelectedPrimsCommand):
    def __init__(self, selected_paths: List[str], visible: bool, stage: Optional[Usd.Stage] = None):
        super().__init__(selected_paths, stage)
        self._visible = visible

    def _toggle_visibility(self, visible: bool, undo: bool = False):
        if not undo:
            self._current_time = self._timeline.get_current_time()

        for selected_path in self._selected_paths:
            if not (selected_prim := self._stage.GetPrimAtPath(selected_path)):
                continue

            if not undo:
                # save parent visibility as toggling may influence parents.
                prefixes = selected_path.GetPrefixes()[:-1]
                for path in prefixes:
                    parent = self._stage.GetPrimAtPath(path)
                    if not parent:
                        break

                    visibility = self._get_prim_visibility(parent, self._current_time)
                    if visibility == UsdGeom.Tokens.invisible:
                        self._old_invisible_prims.add(path)

            imageable = UsdGeom.Imageable(selected_prim)
            imageable.MakeVisible() if visible else imageable.MakeInvisible()

        if undo:
            for path in self._old_invisible_prims:
                if not (prim := self._stage.GetPrimAtPath(path)):
                    continue
                UsdGeom.Imageable(prim).MakeInvisible()

    def do(self):
        self._toggle_visibility(self._visible, undo=False)

    def undo(self):
        self._toggle_visibility(not self._visible, undo=True)


omni.kit.commands.register(AddItemToCollection)
omni.kit.commands.register(RemoveItemFromCollection)
omni.kit.commands.register(DuplicateCollection)
omni.kit.commands.register(RenameCollection)
omni.kit.commands.register(DeleteCollection)
omni.kit.commands.register(ClearCollection)
omni.kit.commands.register(CreateCollection)
omni.kit.commands.register(BlockCollection)
omni.kit.commands.register(SetCollectionExpansionRule)
omni.kit.commands.register(ExcludeItemFromCollection)
omni.kit.commands.register(SelectPrimsInCollection)
omni.kit.commands.register(SetCollectionVisibility)
