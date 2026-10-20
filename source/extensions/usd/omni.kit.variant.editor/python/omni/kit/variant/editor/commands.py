import re
from typing import Any, Dict, Union

import carb
import omni.kit.commands
import omni.kit.usd_undo
from pxr import Sdf, Usd, Vt

from .core import VariantEditorCore


def _get_new_name(variant_sets: Usd.VariantSets, variant_set_name: str, variant_name: str | None):
    name = None
    is_used_name = None

    if variant_name is None:
        if not variant_sets.HasVariantSet(variant_set_name):
            return variant_set_name

        name = variant_set_name

        def _is_used_name(name):
            return variant_sets.HasVariantSet(name)

        is_used_name = _is_used_name
    else:
        variant_set = variant_sets.GetVariantSet(variant_set_name)
        if not variant_set.HasAuthoredVariant(variant_name):
            return variant_name

        name = variant_name

        def _is_used_name(name):
            return variant_set.HasAuthoredVariant(name)

        is_used_name = _is_used_name

    strs = re.split(r"(\d*$)", name, 1)

    name = strs[0]
    postfix = strs[1]

    if postfix == "":
        name += "_"
        postfix = 1
    else:
        postfix = int(postfix)

    while is_used_name(name + str(postfix)):
        postfix += 1

    name = name + str(postfix)

    return name


def _check_variant_exist(prim_path, variant_set_name, variant_name):
    stage = omni.usd.get_context().get_stage()
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        carb.log_error(f"Prim {prim_path} doesn't exist. ")
        return

    variant_sets = prim.GetVariantSets()
    if not variant_sets.HasVariantSet(variant_set_name):
        carb.log_error(f"Prim {prim_path} doesn't contain variant set {variant_set_name}.")
        return

    if variant_name is None:
        return prim

    variant_set = variant_sets.GetVariantSet(variant_set_name)

    if not variant_set.HasAuthoredVariant(variant_name):
        carb.log_error(f"Prim {prim_path} doesn't contain variant {variant_name} in variant set {variant_set_name}.")
        return

    return prim


class AddVariantSetCommand(omni.kit.commands.Command):
    def __init__(self, prim_path: str, variant_set_name: str, auto_postfix: bool):
        self._prim_path = prim_path
        self._variant_set_name = variant_set_name
        self._auto_postfix = auto_postfix
        self._usd_undo = None

    def do(self):
        # Select a right name
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath(self._prim_path)
        if not prim:
            carb.log_error(f"Prim {self._prim_path} doesn't exist.")
            return

        variant_set_name = self._variant_set_name

        variant_sets = prim.GetVariantSets()
        if variant_sets.HasVariantSet(self._variant_set_name):
            if self._auto_postfix:
                variant_set_name = _get_new_name(variant_sets, self._variant_set_name, None)
            else:
                carb.log_error(f"Variant set {variant_set_name} already exists in prim {self._prim_path}.")
                return

        # Handle undo
        self._usd_undo = omni.kit.usd_undo.UsdLayerUndo(stage.GetEditTarget().GetLayer())
        self._usd_undo.reserve(prim.GetPath(), Sdf.PrimSpec.VariantSetNamesKey)

        # Add variant set
        variant_sets.AddVariantSet(variant_set_name)

        # Check result
        if variant_sets.HasVariantSet(variant_set_name):
            return variant_set_name

        path = Sdf.Path(self._prim_path).AppendVariantSelection(self._variant_set_name, "")
        variant_set_spec = stage.GetEditTarget().GetLayer().GetObjectAtPath(path)
        if variant_set_spec:
            carb.log_error(f"Variant set {path} could be in a remove list in stronger layers. ")

        self._usd_undo.undo()
        self._usd_undo = None

        return

    def undo(self):
        if self._usd_undo is not None:
            self._usd_undo.undo()


class RemoveVariantSetCommand(omni.kit.commands.Command):
    def __init__(self, prim_path: str, variant_set_name: str):
        self._prim_path = prim_path
        self._variant_set_name = variant_set_name
        self._usd_undo = None

    def do(self):
        # Check path and name
        prim = _check_variant_exist(self._prim_path, self._variant_set_name, None)
        if prim is None:
            return False

        # Check if the variant set exists in current layer
        layer = prim.GetStage().GetEditTarget().GetLayer()

        path = Sdf.Path(self._prim_path).AppendVariantSelection(self._variant_set_name, "")

        variant_set_spec = layer.GetObjectAtPath(path)
        if variant_set_spec is None:
            carb.log_error(f"Variant set {path} doesn't exist in current layer.")
            return False

        # Check if any variant is selected.
        variant_set = prim.GetVariantSet(self._variant_set_name)
        selected_variant = variant_set.GetVariantSelection()

        # Handle undo
        parent_spec = variant_set_spec.owner

        self._usd_undo = omni.kit.usd_undo.UsdLayerUndo(layer)
        self._usd_undo.reserve(parent_spec.path, Sdf.PrimSpec.VariantSetNamesKey)
        self._usd_undo.reserve(variant_set_spec.path)
        if selected_variant != "":
            self._usd_undo.reserve(parent_spec.path, Sdf.PrimSpec.VariantSelectionKey)

        # Remove the variant set
        with Sdf.ChangeBlock():
            if selected_variant != "":
                variant_set.ClearVariantSelection()
            parent_spec.variantSetNameList.RemoveItemEdits(variant_set_spec.name)
            del parent_spec.variantSets[variant_set_spec.name]

        # Check result
        if selected_variant != "":
            selected_variant = variant_set.GetVariantSelection()
            if selected_variant != "":
                carb.log_warn(
                    f"Variant selection of variant set {self._variant_set_name} of prim {self._prim_path} can not be cleared. It could exist in stronger layers. "
                )

        if not prim.GetVariantSets().HasVariantSet(self._variant_set_name):
            return True

        if not variant_set_spec:
            carb.log_error(f"Variant set {path} could exist in stronger layers. ")

        self._usd_undo.undo()
        self._usd_undo = None

        return False

    def undo(self):
        if self._usd_undo is not None:
            self._usd_undo.undo()


class RenameVariantSetCommand(omni.kit.commands.Command):
    def __init__(self, prim_path: str, variant_set_name: str, new_name: str):
        self._prim_path = prim_path
        self._variant_set_name = variant_set_name
        self._new_name = new_name
        self._usd_undo = None

    def do(self):
        # Check path and name
        prim = _check_variant_exist(self._prim_path, self._variant_set_name, None)
        if prim is None:
            return False

        if prim.GetVariantSets().HasVariantSet(self._new_name):
            carb.log_error(f"Variant set {self._new_name} already exists in prim {self._prim_path}. ")
            return False

        layer = prim.GetStage().GetEditTarget().GetLayer()

        old_path = Sdf.Path(self._prim_path).AppendVariantSelection(self._variant_set_name, "")
        old_spec = layer.GetObjectAtPath(old_path)
        if old_spec is None:
            carb.log_error(f"Variant set {old_path} doesn't exist in current layer.")
            return False

        # Check if any variant is selected
        variant_set = prim.GetVariantSet(self._variant_set_name)
        selected_variant = variant_set.GetVariantSelection()

        # Handle undo
        new_path = Sdf.Path(self._prim_path).AppendVariantSelection(self._new_name, "")

        self._usd_undo = omni.kit.usd_undo.UsdLayerUndo(layer)
        self._usd_undo.reserve(old_path.GetParentPath(), Sdf.PrimSpec.VariantSetNamesKey)
        self._usd_undo.reserve(old_path)
        self._usd_undo.reserve(new_path.GetParentPath(), Sdf.PrimSpec.VariantSetNamesKey)
        self._usd_undo.reserve(new_path)

        if selected_variant != "":
            self._usd_undo.reserve(old_path.GetParentPath(), Sdf.PrimSpec.VariantSelectionKey)

        # Copy and remove
        with Sdf.ChangeBlock():
            if selected_variant != "":
                variant_set.ClearVariantSelection()
            Sdf.CopySpec(layer, old_path, layer, new_path)
            parent_spec = layer.GetObjectAtPath(old_path.GetParentPath())
            parent_spec.variantSetNameList.ReplaceItemEdits(old_spec.name, self._new_name)
            del parent_spec.variantSets[old_spec.name]
            if selected_variant != "":
                variant_set = prim.GetVariantSet(self._new_name)
                variant_set.SetVariantSelection(selected_variant)

        # Check result
        if selected_variant != "":
            if variant_set.GetVariantSelection() != selected_variant:
                carb.log_warn(f"Another variant in variant set {self._new_name} is selected in stronger layers.")

        variant_sets = prim.GetVariantSets()
        if not variant_sets.HasVariantSet(self._variant_set_name) and variant_sets.HasVariantSet(self._new_name):
            return True

        if not old_spec and variant_sets.HasVariantSet(self._variant_set_name):
            carb.log_error(f"Variant set {old_path} could exist in stronger layers. ")

        if layer.GetObjectAtPath(new_path) and not variant_sets.HasVariant(self._new_name):
            carb.log_error(f"Variant set {new_path} could exist in a remove list in stronger layers.")

        self._usd_undo.undo()
        self._usd_undo = None

        return False

    def undo(self):
        if self._usd_undo is not None:
            self._usd_undo.undo()


class AddVariantCommand(omni.kit.commands.Command):
    def __init__(
        self,
        prim_path: str,
        variant_set_name: str,
        variant_name: str,
        auto_postfix: bool,
    ):
        self._prim_path = prim_path
        self._variant_set_name = variant_set_name
        self._variant_name = variant_name
        self._auto_postfix = auto_postfix
        self._usd_undo = None

    def do(self):
        # Validate path and name
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath(self._prim_path)
        if not prim:
            carb.log_error(f"Prim {self._prim_path} doesn't exist. ")
            return

        variant_sets = prim.GetVariantSets()
        if not variant_sets.HasVariantSet(self._variant_set_name):
            carb.log_error(f"Prim {self._prim_path} doesn't contain variant set {self._variant_set_name}.")
            return

        layer = stage.GetEditTarget().GetLayer()

        variant_set_path = Sdf.Path(self._prim_path).AppendVariantSelection(self._variant_set_name, "")
        variant_set_spec = layer.GetObjectAtPath(variant_set_path)
        if variant_set_spec is None:
            carb.log_error(f"Variant set {variant_set_path} doesn't exist in current layer. ")
            return

        variant_name = self._variant_name

        variant_set = variant_sets.GetVariantSet(self._variant_set_name)
        if variant_set.HasAuthoredVariant(self._variant_name):
            if self._auto_postfix:
                variant_name = _get_new_name(variant_sets, self._variant_set_name, self._variant_name)
            else:
                carb.log_error(
                    f"Variant {self._variant_name} already exists in variant set {self._variant_set_name} of prim {self._prim_path}"
                )
                return

        # Handle undo
        self._usd_undo = omni.kit.usd_undo.UsdLayerUndo(layer)
        path = Sdf.Path(self._prim_path).AppendVariantSelection(self._variant_set_name, variant_name)
        self._usd_undo.reserve(path)

        # Add variant
        added = variant_set.AddVariant(variant_name)

        # Check result
        if variant_set.HasAuthoredVariant(variant_name):
            return variant_name

        if added:
            carb.log_error(f"Variant {path} could exist in a remove list in stronger layrs.")

        self._usd_undo.undo()
        self._usd_undo = None

    def undo(self):
        if self._usd_undo is not None:
            self._usd_undo.undo()


class RemoveVariantCommand(omni.kit.commands.Command):
    def __init__(self, prim_path: str, variant_set_name: str, variant_name: str):
        self._prim_path = prim_path
        self._variant_set_name = variant_set_name
        self._variant_name = variant_name
        self._usd_undo = None

    def do(self):
        # Check path and name
        prim = _check_variant_exist(self._prim_path, self._variant_set_name, None)
        if prim is None:
            return False

        layer = prim.GetStage().GetEditTarget().GetLayer()

        path = Sdf.Path(self._prim_path).AppendVariantSelection(self._variant_set_name, self._variant_name)
        variant_spec = layer.GetObjectAtPath(path)
        if variant_spec is None:
            carb.log_error(f"Variant {path} doesn't exist in current layer. ")
            return False

        variant_set = prim.GetVariantSet(self._variant_set_name)
        selected_variant = variant_set.GetVariantSelection()

        # Handle undo
        self._usd_undo = omni.kit.usd_undo.UsdLayerUndo(layer)
        self._usd_undo.reserve(path)
        if selected_variant == self._variant_name:
            self._usd_undo.reserve(prim.GetPath(), Sdf.PrimSpec.VariantSelectionKey)

        # Remove variant
        with Sdf.ChangeBlock():
            if selected_variant == self._variant_name:
                variant_set.ClearVariantSelection()

            variant_spec.owner.RemoveVariant(variant_spec)

        # Check result
        if selected_variant == self._variant_name:
            if variant_set.GetVariantSelection() != "":
                carb.log_warn(f"Variant selection {selected_variant}")

        if not variant_set.HasAuthoredVariant(self._variant_name):
            return True

        if not variant_set:
            carb.log_error(f"Variant {path} would exist in stronger layers. ")

        self._usd_undo.undo()
        self._usd_undo = None

        return False

    def undo(self):
        if self._usd_undo is not None:
            self._usd_undo.undo()


class RenameVariantCommand(omni.kit.commands.Command):
    def __init__(self, prim_path: str, variant_set_name: str, variant_name: str, new_name: str):
        self._prim_path = prim_path
        self._variant_set_name = variant_set_name
        self._variant_name = variant_name
        self._new_name = new_name
        self._usd_undo = None

    def do(self):
        # Check path and name
        prim = _check_variant_exist(self._prim_path, self._variant_set_name, None)
        if prim is None:
            return False

        variant_set = prim.GetVariantSet(self._variant_set_name)
        if variant_set.HasAuthoredVariant(self._new_name):
            carb.log_error(
                f"Variant {self._new_name} already exists in variant set {self._variant_set_name} in prim {self._prim_path}"
            )
            return False

        layer = prim.GetStage().GetEditTarget().GetLayer()

        path = Sdf.Path(self._prim_path).AppendVariantSelection(self._variant_set_name, self._variant_name)
        variant_spec = layer.GetObjectAtPath(path)
        if variant_spec is None:
            carb.log_error(f"Variant {path} doesn't exist in current layer. ")
            return False

        selected_variant = variant_set.GetVariantSelection()

        # Handle undo
        new_path = Sdf.Path(self._prim_path).AppendVariantSelection(self._variant_set_name, self._new_name)

        self._usd_undo = omni.kit.usd_undo.UsdLayerUndo(layer)
        self._usd_undo.reserve(path)
        self._usd_undo.reserve(new_path)

        if selected_variant == self._variant_name:
            self._usd_undo.reserve(self._prim_path, Sdf.PrimSpec.VariantSelectionKey)

        # Move variant
        with Sdf.ChangeBlock():
            Sdf.CopySpec(layer, path, layer, new_path)
            variant_spec.owner.RemoveVariant(variant_spec)
            if selected_variant == self._variant_name:
                variant_set.SetVariantSelection(self._new_name)

        # Check result
        if selected_variant == self._variant_name:
            if variant_set.GetVariantSelection() != self._new_name:
                carb.log_warn(f"Another variant in variant set {self._variant_set_name} is selected in stroger layers.")

        if not variant_set.HasAuthoredVariant(self._variant_name) and variant_set.HasAuthoredVariant(self._new_name):
            return True

        if variant_set.HasAuthoredVariant(self._variant_name) and not variant_spec:
            carb.log_error(f"Variant {path} could exist in stronger layers. ")

        if not variant_set.HasAuthoredVariant(self._new_name) and layer.GetObjectAtPath(new_path):
            carb.log_error(f"Variant {path} could exist in a remove list in stronger layers. ")

        self._usd_undo.undo()
        self._usd_undo = None

        return False

    def undo(self):
        if self._usd_undo is not None:
            self._usd_undo.undo()


class DuplicateVariantCommand(omni.kit.commands.Command):
    def __init__(
        self,
        prim_path: str,
        variant_set_name: str,
        variant_name: str,
        new_name: str,
        auto_postfix: bool,
    ):
        self._prim_path = prim_path
        self._variant_set_name = variant_set_name
        self._variant_name = variant_name
        self._new_name = new_name
        self._auto_postfix = auto_postfix
        self._usd_undo = None

    def do(self):
        # Validate names and paths
        prim = _check_variant_exist(self._prim_path, self._variant_set_name, self._variant_name)
        if prim is None:
            return

        layer = prim.GetStage().GetEditTarget().GetLayer()

        path = Sdf.Path(self._prim_path).AppendVariantSelection(self._variant_set_name, self._variant_name)
        variant_spec = layer.GetObjectAtPath(path)
        if variant_spec is None:
            carb.log_error(
                f"Variant {self._variant_name} in variant set {self._variant_set_name} of prim {self._prim_path} doesn't exist in current layer."
            )
            return

        variant_name = self._new_name

        variant_set = prim.GetVariantSet(self._variant_set_name)
        if variant_set.HasAuthoredVariant(self._new_name):
            if self._auto_postfix:
                variant_name = _get_new_name(prim.GetVariantSets(), self._variant_set_name, self._variant_name)
            else:
                carb.log_error(
                    f"Variant {variant_name} already exists in variant set {self._variant_set_name} of prim {self._prim_path}."
                )
                return

        # Handle undo
        new_path = Sdf.Path(self._prim_path).AppendVariantSelection(self._variant_set_name, variant_name)

        self._usd_undo = omni.kit.usd_undo.UsdLayerUndo(layer)
        self._usd_undo.reserve(new_path)

        # Copy variant
        Sdf.CopySpec(layer, path, layer, new_path)

        # Check result
        if variant_set.HasAuthoredVariant(variant_name):
            return variant_name

        new_variant_spec = layer.GetObjectAtPath(path)
        if new_variant_spec is not None:
            carb.log_error(f"Variant {variant_name} could be in a remove list in stronger layers.")

        self._usd_undo.undo()
        self._usd_undo = None

        return

    def undo(self):
        if self._usd_undo is not None:
            self._usd_undo.undo()


class EditVariantCommand(omni.kit.commands.Command):
    def __init__(
        self,
        prim_path: str,
        variant_set_name: str,
        cmd_name: str,
        cmd_args: dict,
        target_variant: str = None,
    ):
        self._prim_path = prim_path
        self._variant_set_name = variant_set_name
        self._edit_cmd = omni.kit.commands.create(cmd_name, **cmd_args)
        self._target_variant = target_variant

    def _get_variant_edit_context(self):
        prim = _check_variant_exist(self._prim_path, self._variant_set_name, None)
        if prim is None:
            return

        variant_set = prim.GetVariantSet(self._variant_set_name)
        variant_name = variant_set.GetVariantSelection()
        if self._target_variant and not self._target_variant == variant_name:
            variant_name = self._target_variant
            variant_set.SetVariantSelection(variant_name)
        if not variant_name:
            carb.log_error(f"No variant is selected for variant set {self._variant_set_name} of prim {self._prim_path}")
            return

        return variant_set.GetVariantEditContext()

    def do(self):
        edit_context = self._get_variant_edit_context()
        if edit_context is None:
            return

        with edit_context:
            self._edit_cmd.do()

    def undo(self):
        edit_context = self._get_variant_edit_context()
        if edit_context is None:
            return

        with edit_context:
            self._edit_cmd.undo()


class PasteVariantCommand(omni.kit.commands.Command):
    def __init__(
        self,
        prim_path: str,
        variant_set_name: str,
        clipboard: Dict[Sdf.Path, Any],
        target_path: Sdf.Path = None,
    ):
        self._prim_path = prim_path
        self._variant_set_name = variant_set_name
        self._clipboard = clipboard
        self._target_path = target_path
        self._edit_cmds = []
        self._variant_set = self._get_variant_set()
        self._variants = [v for v in self._variant_set.GetVariantNames()]
        self._current_variant = self._variant_set.GetVariantSelection()

    def _get_variant_set(self):
        prim = _check_variant_exist(self._prim_path, self._variant_set_name, None)
        if prim is None:
            return

        variant_set = prim.GetVariantSet(self._variant_set_name)
        return variant_set

    def _select_variant(self, variant):
        self._variant_set.SetVariantSelection(variant)

    def do(self):
        if self._target_path:
            stage = omni.usd.get_context().get_stage()
            prim = stage.GetPrimAtPath(self._target_path)
            for prop_path in self._clipboard.keys():
                target_prop = None
                if self._target_path == prop_path.GetPrimPath():
                    target_prop = prop_path
                elif prim.HasAttribute(prop_path.name):
                    target_prop = self._target_path.AppendProperty(prop_path.name)
                if target_prop:
                    self._edit_cmds.append(
                        omni.kit.commands.create(
                            "EditVariant",
                            prim_path=self._prim_path,
                            variant_set_name=self._variant_set_name,
                            cmd_name="ChangeProperty",
                            cmd_args={
                                "prop_path": target_prop,
                                "value": self._clipboard[prop_path],
                                "prev": None,
                            },
                        )
                    )
            for cmd in self._edit_cmds:
                cmd.do()
        else:
            for variant in self._variants:
                for prop_path in self._clipboard.keys():
                    self._edit_cmds.append(
                        omni.kit.commands.create(
                            "EditVariant",
                            prim_path=self._prim_path,
                            variant_set_name=self._variant_set_name,
                            cmd_name="ChangeProperty",
                            cmd_args={
                                "prop_path": prop_path,
                                "value": self._clipboard[prop_path],
                                "prev": None,
                            },
                            target_variant=variant,
                        )
                    )

            for cmd in self._edit_cmds:
                cmd.do()
            self._select_variant(self._current_variant)

    def undo(self):
        if self._target_path:
            for cmd in self._edit_cmds:
                cmd.undo()
        else:
            for cmd in self._edit_cmds:
                cmd.undo()
            self._select_variant(self._current_variant)


class RefreshVariantUiCommand(omni.kit.commands.Command):
    """
    A dummy command to tell variant editor to refresh variant UI.
    """

    def do(self):
        pass

    def undo(self):
        pass


class CreateUsdRelationshipCommand(omni.kit.commands.Command):
    def __init__(
        self,
        prim: Usd.Prim,
        rel_name: str,
        custom: bool = False,
        usd_context_name: str = "",
    ):
        self._stage = prim.GetStage()
        self._prim_path = prim.GetPath()
        self._rel_name = rel_name
        self._custom = custom
        self._usd_context_name = usd_context_name
        self._usd_undo = None

    def do(self):
        stage = omni.usd.get_context(self._usd_context_name).get_stage()
        prim = stage.GetPrimAtPath(self._prim_path)
        if not prim:
            return

        self._usd_undo = omni.kit.usd_undo.UsdEditTargetUndo(stage.GetEditTarget())
        self._usd_undo.reserve(self._prim_path)
        rel = prim.CreateRelationship(self._rel_name, self._custom)
        if not rel.IsValid():
            self._usd_undo.undo()
            self._usd_undo = None

    def undo(self):
        if not self._usd_undo:
            return

        self._usd_undo.undo()


class CollapseSessionPropertyCommand(omni.kit.commands.Command):
    def __init__(
        self,
        prim: Usd.Prim,
        prop_name: str,
        usd_context_name: str = "",
    ):
        self._usd_context_name = usd_context_name
        self._prim_path = prim.GetPath()
        self._prop_name = prop_name
        self._done = False
        self._target_layer_undo = None

    def do(self):
        stage = omni.usd.get_context(self._usd_context_name).get_stage()
        session_layer = stage.GetSessionLayer()
        session_prim = session_layer.GetPrimAtPath(self._prim_path)
        if not session_prim:
            return
        prop_path = session_prim.path.AppendProperty(self._prop_name)
        session_prop = session_layer.GetPropertyAtPath(prop_path)
        if not session_prop:
            return

        edit_layer = stage.GetEditTarget().GetLayer()
        if edit_layer == session_layer:
            return

        Sdf.CopySpec(session_layer, prop_path, edit_layer, prop_path)
        session_prim.RemoveProperty(session_prop)
        self._done = True

    def undo(self):
        if not self._done:
            return
        stage = omni.usd.get_context(self._usd_context_name).get_stage()
        edit_layer = stage.GetEditTarget().GetLayer()
        prim_path = stage.GetEditTarget().MapToSpecPath(self._prim_path)
        edit_prim = edit_layer.GetPrimAtPath(prim_path)
        prop_path = edit_prim.path.AppendProperty(self._prop_name)

        Sdf.CopySpec(edit_layer, prop_path, stage.GetSessionLayer(), prop_path)
        edit_prop = edit_layer.GetPropertyAtPath(prop_path)
        edit_prim.RemoveProperty(edit_prop)


class SetVariantEditorActiveVariantCommand(omni.kit.commands.Command):
    def __init__(self, variant_path: str):
        self._variant_path = variant_path
        self._old_variant_path = None

    def do(self):
        self._old_variant_path = VariantEditorCore.get_instance().active_variant
        VariantEditorCore.get_instance().active_variant = self._variant_path

    def undo(self):
        VariantEditorCore.get_instance().active_variant = self._old_variant_path
