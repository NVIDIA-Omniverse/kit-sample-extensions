"""UI-node command wrappers for position, color, size, and backdrop creation."""

from typing import Iterable, Optional, Tuple, Union

import omni.usd
from pxr import Sdf, Usd, UsdShade, UsdUI

from ...config.logging import logger
from ...config.nodes import Nodes
from ...settings.settings import Settings
from ..execution import execute_command_checked
from ..result import CommandResult

# pylint: disable=no-member


def RemovePosition(prim_path: Sdf.Path, stage: Optional[Usd.Stage] = None) -> CommandResult:
    """Remove a UI position attribute from a prim."""
    if not prim_path:
        return CommandResult(False, None, message="Missing prim path", error_code="invalid_args")
    return execute_command_checked("UsdUIRemovePositionCommand", prim_path=prim_path, stage=stage)


Position = Tuple[float, float]
Color = Tuple[float, float, float]
ContextVisibility = Union[str, Iterable[str]]


def SetPosition(
    prim_path: Sdf.Path,
    value: Position,
    prev: Optional[Position],
    is_material: bool,
    context_name: str,
    stage: Optional[Usd.Stage] = None,
) -> CommandResult:
    """Set a node position or material custom data position."""
    if not prim_path:
        return CommandResult(False, None, message="Missing prim path", error_code="invalid_args")
    stage = stage or omni.usd.get_context().get_stage()
    if is_material:
        key = f"position:{context_name}"
        if not stage:
            logger.warning(
                "set material position failed for prim '%s' context='%s' key='%s': no USD stage is open; "
                "position was not changed",
                prim_path,
                context_name,
                key,
            )
            return CommandResult(False, None, message="No USD stage", error_code="no_stage")
        prim = stage.GetPrimAtPath(prim_path)
        if not prim:
            return CommandResult(False, None, message="Missing prim", error_code="missing_prim")
        return execute_command_checked(
            "MaterialGraph_SetPrimCustomDataKeyCommand",
            prim_path=prim_path,
            key=key,
            value=value,
            stage=stage,
        )
    return execute_command_checked(
        "UsdUINodeGraphNodeSetCommand",
        attribute=UsdUI.Tokens.uiNodegraphNodePos,
        prim_path=prim_path,
        value=value,
        prev=prev,
        stage=stage,
    )


def SetContextPosition(
    prim_path: Sdf.Path,
    key: str,
    value: Optional[Position],
    prev: Optional[Position],
    stage: Optional[Usd.Stage] = None,
) -> CommandResult:
    """Set a context-specific customData position via undoable metadata command."""
    if not prim_path:
        return CommandResult(False, None, message="Missing prim path", error_code="invalid_args")
    if not key:
        return CommandResult(False, None, message="Missing customData key", error_code="invalid_args")

    stage = stage or omni.usd.get_context().get_stage()
    if not stage:
        logger.warning(
            "set context position failed for prim '%s' key='%s': no USD stage is open; position was not changed",
            prim_path,
            key,
        )
        return CommandResult(False, None, message="No USD stage", error_code="no_stage")
    prim = stage.GetPrimAtPath(prim_path)
    if not prim:
        return CommandResult(False, None, message="Missing prim", error_code="missing_prim")

    result = execute_command_checked(
        "MaterialGraph_SetPrimCustomDataKeyCommand",
        prim_path=prim_path,
        key=key,
        value=value,
        clear=value is None,
        stage=stage,
    )

    # Validate the authored key after command execution.  Do not mutate USD
    # outside the command: doing so would make undo/redo report false state.
    if result.success:
        authored = prim.GetCustomDataByKey(key) if prim.HasAuthoredCustomDataKey(key) else None
        expected = value
        authored_ok = (expected is None and not prim.HasAuthoredCustomDataKey(key)) or (authored == expected)
        if not authored_ok:
            return CommandResult(
                False,
                None,
                message="Context position validation failed",
                error_code="validation_position_failed",
                command_name=result.command_name,
                validation={"prim_path": str(prim_path), "key": key, "expected": expected, "authored": authored},
            )
    return result


def RemoveContextPosition(
    prim_path: Sdf.Path,
    key: str,
    prev: Optional[Position],
    stage: Optional[Usd.Stage] = None,
) -> CommandResult:
    """Remove a context-specific customData position via undoable metadata command."""
    return SetContextPosition(prim_path, key, None, prev, stage=stage)


def SetDisplayColor(
    prim_path: Sdf.Path,
    value: Color,
    prev: Optional[Color],
    stage: Optional[Usd.Stage] = None,
) -> CommandResult:
    """Set the display color for a UI node."""
    if not prim_path:
        return CommandResult(False, None, message="Missing prim path", error_code="invalid_args")
    return execute_command_checked(
        "UsdUINodeGraphNodeSetCommand",
        attribute=UsdUI.Tokens.uiNodegraphNodeDisplayColor,
        prim_path=prim_path,
        value=value,
        prev=prev,
        stage=stage,
    )


def SetSize(
    prim_path: Sdf.Path,
    value: Position,
    prev: Optional[Position],
    stage: Optional[Usd.Stage] = None,
) -> CommandResult:
    """Set the size for a UI node."""
    if not prim_path:
        return CommandResult(False, None, message="Missing prim path", error_code="invalid_args")
    return execute_command_checked(
        "UsdUINodeGraphNodeSetCommand",
        attribute=UsdUI.Tokens.uiNodegraphNodeSize,
        prim_path=prim_path,
        value=value,
        prev=prev,
        stage=stage,
    )


def CreateBackdrop(
    parent_path: Sdf.Path,
    position: Position,
    position_key: Optional[str] = None,
    context_visibility: Optional[ContextVisibility] = None,
    stage: Optional[Usd.Stage] = None,
) -> CommandResult:
    """Create a backdrop prim and return structured result."""
    if not parent_path:
        return CommandResult(False, None, message="Missing parent path", error_code="invalid_args")

    result = execute_command_checked(
        "MaterialGraph_CreatePrimCommand",
        parent_path=parent_path,
        prim_type=UsdUI.Tokens.Backdrop,
        prim_name=UsdUI.Tokens.Backdrop,
        position=position,
        position_key=position_key,
        context_visibility=context_visibility,
        display_color=Settings.get_backdrop_default_color(),
        size=Nodes.Backdrop.DEFAULT_SIZE,
        stage=stage,
        error_message="create backdrop failed",
    )
    return result


def CreateNodeGraph(
    parent_path: Sdf.Path,
    position: Position,
    position_key: Optional[str] = None,
    context_visibility: Optional[ContextVisibility] = None,
    stage: Optional[Usd.Stage] = None,
) -> CommandResult:
    """Create a nodegraph prim and return structured result."""
    if not parent_path:
        return CommandResult(False, None, message="Missing parent path", error_code="invalid_args")

    result = execute_command_checked(
        "MaterialGraph_CreatePrimCommand",
        parent_path=parent_path,
        prim_type=UsdShade.Tokens.NodeGraph,
        prim_name=UsdShade.Tokens.NodeGraph,
        position=position,
        position_key=position_key,
        context_visibility=context_visibility,
        stage=stage,
        error_message="create nodegraph failed",
    )
    return result
