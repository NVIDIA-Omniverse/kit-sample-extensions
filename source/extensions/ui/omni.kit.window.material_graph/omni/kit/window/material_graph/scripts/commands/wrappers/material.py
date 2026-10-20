"""Material-level command wrappers for create/pause operations with validation."""

# pylint: disable=no-member
from typing import Optional

import omni.usd
from pxr import Sdf, Usd, UsdShade

from ...config.logging import logger
from ..execution import execute_command_checked
from ..result import CommandResult


def PauseMaterial(prim_path: Sdf.Path, value: bool, stage: Optional[Usd.Stage] = None) -> CommandResult:
    """Toggle the paused state on a material prim."""
    if not prim_path:
        return CommandResult(False, None, message="Missing prim path", error_code="invalid_args")

    stage = stage or omni.usd.get_context().get_stage()
    if not stage:
        logger.warning("pause material '%s' failed: no USD stage is open; paused state was not changed", prim_path)
        return CommandResult(False, None, message="No USD stage", error_code="no_stage")

    session_layer = stage.GetSessionLayer()
    if not session_layer:
        logger.warning(
            "pause material '%s' failed: the USD stage has no session layer; paused state was not changed",
            prim_path,
        )
        return CommandResult(False, None, message="no USD stage session layer", error_code="no_stage_session_layer")

    prop_path = prim_path.AppendProperty("paused")

    if not value:
        return execute_command_checked(
            "RemovePropertyCommand",
            prop_path=prim_path.AppendProperty("paused"),
            usd_context_name=stage,
            remove_from_layers=[session_layer],
            error_message="failed to un-pause material",
        )

    else:
        return execute_command_checked(
            "ChangePropertyCommand",
            prop_path=prop_path,
            value=value,
            prev=False,
            target_layer=session_layer,
            is_custom=True,
            type_to_create_if_not_exist=Sdf.ValueTypeNames.Bool,
            error_message="failed to pause material",
        )


def CreateMaterial() -> CommandResult:
    """Create a new material prim and return a structured result."""
    stage = omni.usd.get_context().get_stage()
    if not stage:
        logger.warning("create material failed: no USD stage is open; no material was created")
        return CommandResult(False, None, message="No USD stage", error_code="no_stage")

    if stage.HasDefaultPrim():
        parent_path = stage.GetDefaultPrim().GetPath()
    else:
        parent_path = Sdf.Path.absoluteRootPath

    parent_path = parent_path.AppendChild("Looks")

    result = execute_command_checked(
        "MaterialGraph_CreatePrimCommand",
        parent_path=parent_path,
        prim_type=UsdShade.Tokens.Material,
        prim_name=UsdShade.Tokens.Material,
        stage=stage,
        error_message="create material failed",
    )
    if not result.success:
        return result
    prim = result.payload
    if not prim:
        return CommandResult(
            False,
            None,
            message="Material prim missing after create",
            error_code="validation_missing_prim",
            command_name=result.command_name,
        )
    return CommandResult(
        True,
        prim,
        command_name=result.command_name,
        validation={"prim_path": str(prim.GetPath())},
    )
