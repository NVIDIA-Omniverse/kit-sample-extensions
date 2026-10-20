"""Attribute/property command wrappers used by node and port editing flows."""

from typing import Optional

from pxr import Sdf, Usd, UsdUI

from ..execution import execute_command_checked
from ..result import CommandResult

# pylint: disable=no-member


def LockAttribute(attribute_path: Sdf.Path) -> CommandResult:
    """Lock a USD attribute spec."""
    if not attribute_path:
        return CommandResult(False, None, message="Missing attribute path", error_code="invalid_args")
    return execute_command_checked("LockSpecs", spec_paths=[attribute_path], undo_group=True)


def UnlockAttribute(attribute_path: Sdf.Path) -> CommandResult:
    """Unlock a USD attribute spec."""
    if not attribute_path:
        return CommandResult(False, None, message="Missing attribute path", error_code="invalid_args")
    return execute_command_checked("UnlockSpecs", spec_paths=[attribute_path], undo_group=True)


def SetDisplayName(prop_path: Sdf.Path, value: str) -> CommandResult:
    """Set the display name metadata for a property."""
    if not prop_path:
        return CommandResult(False, None, message="Missing property path", error_code="invalid_args")
    return execute_command_checked(
        "ChangeMetadataCommand",
        object_paths=[str(prop_path)],
        value=value,
        key=Sdf.AttributeSpec.DisplayNameKey,
        undo_group=True,
    )


def SetDescription(
    prim_path: Sdf.Path,
    value: str,
    prev: Optional[object],
    stage: Optional[Usd.Stage] = None,
) -> CommandResult:
    """Set the description metadata for a prim."""
    if not prim_path:
        return CommandResult(False, None, message="Missing prim path", error_code="invalid_args")
    prop_path = prim_path.AppendProperty(UsdUI.Tokens.uiDescription)
    command_args = {
        "prop_path": prop_path,
        "value": value,
        "prev": prev,
        "type_to_create_if_not_exist": Sdf.ValueTypeNames.Token,
        "undo_group": True,
    }
    if stage:
        command_args["target_layer"] = stage.GetEditTarget().GetLayer()
    return execute_command_checked(
        "ChangePropertyCommand",
        **command_args,
    )


def RemoveProperty(prop_path: Sdf.Path) -> CommandResult:
    """Remove a property from a prim."""
    if not prop_path:
        return CommandResult(False, None, message="Missing property path", error_code="invalid_args")
    return execute_command_checked("RemovePropertyCommand", prop_path=prop_path, undo_group=True)


def RenameProperty(
    prim_path: Sdf.Path,
    property_name: str,
    new_name: str,
    stage: Optional[Usd.Stage] = None,
) -> CommandResult:
    """Rename a property on a prim."""
    if not prim_path or not property_name or not new_name:
        return CommandResult(False, None, message="Invalid arguments", error_code="invalid_args")
    return execute_command_checked(
        "MaterialGraph_RenamePropertyCommand",
        prim_path=prim_path,
        property_name=property_name,
        new_name=new_name,
        stage=stage,
        undo_group=True,
    )


def SetPrimCustomData(prim: Usd.Prim, value: dict) -> CommandResult:
    """Replace a prim's customData using its owning stage and an undoable command."""
    if not prim or not prim.IsValid():
        return CommandResult(False, None, message="Missing prim", error_code="invalid_args")
    return execute_command_checked(
        "MaterialGraph_SetPrimCustomDataCommand",
        prim_path=prim.GetPath(),
        custom_data=dict(value or {}),
        stage=prim.GetStage(),
        error_message="set prim custom data failed",
    )
