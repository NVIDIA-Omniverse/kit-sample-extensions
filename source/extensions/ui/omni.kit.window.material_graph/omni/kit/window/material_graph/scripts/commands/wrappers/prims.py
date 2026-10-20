"""Prim command wrappers that enforce post-command validation semantics."""

# pylint: disable=no-member

from typing import Optional

import omni.usd
from pxr import Sdf, Usd, UsdShade

from ..execution import execute_command_checked
from ..result import CommandResult
from .ui_nodes import ContextVisibility


def RenamePrim(prim: Usd.Prim, value: str) -> CommandResult:
    """Rename a prim and return structured command result."""
    if not prim or not value:
        return CommandResult(False, None, message="Invalid arguments", error_code="invalid_args")
    path_from = prim.GetPath()
    if path_from.name == value:
        return CommandResult(True, path_from, validation={"unchanged": True})

    result = execute_command_checked(
        "RenamePrimCommand",
        prim_path=str(path_from),
        new_name=value,
    )
    if not result.success:
        return result
    new_path = path_from.GetParentPath().AppendChild(value)
    return CommandResult(
        True,
        new_path,
        command_name=result.command_name,
        validation={"path_from": str(path_from), "path_to": str(new_path)},
    )


def DeletePrims(paths: list[Sdf.Path], stage: Optional[Usd.Stage] = None) -> CommandResult:
    """Delete prims and validate that they no longer exist."""
    if not paths:
        return CommandResult(False, None, message="Missing paths", error_code="invalid_args")
    normalized = list(dict.fromkeys(Sdf.Path(str(path)) for path in paths if path))
    if not normalized:
        return CommandResult(False, None, message="Missing paths", error_code="invalid_args")
    stage = stage or omni.usd.get_context().get_stage()
    if not stage:
        return CommandResult(False, None, message="No USD stage", error_code="no_stage")

    # DeletePrims can return command-level success while leaving prims behind
    # in edge cases; run an explicit stage existence check for each target path.
    usd_context = omni.usd.get_context_from_stage(stage)
    command_args = {"context_name": usd_context.get_name()} if usd_context else {"stage": stage}
    result = execute_command_checked("MaterialGraph_DeletePrimsCommand", paths=normalized, **command_args)
    if not result.success:
        return result

    remaining = [str(path) for path in normalized if stage.GetPrimAtPath(path)]
    if remaining:
        return CommandResult(
            False,
            None,
            message="Delete validation failed",
            error_code="validation_delete_failed",
            command_name=result.command_name,
            validation={"remaining_paths": tuple(remaining)},
            target_paths=tuple(str(path) for path in normalized),
        )
    return CommandResult(
        True,
        None,
        command_name=result.command_name,
        validation={"deleted_paths": tuple(str(path) for path in normalized)},
        target_paths=tuple(str(path) for path in normalized),
    )


def MovePrims(
    paths_to_move: dict[str, str],
    destructive: bool = False,
    stage_or_context: Optional[object] = None,
) -> CommandResult:
    """Move prims and validate destination/source paths."""
    if not paths_to_move:
        return CommandResult(False, None, message="Missing paths_to_move", error_code="invalid_args")
    if isinstance(stage_or_context, Usd.Stage):
        stage = stage_or_context
        command_context = omni.usd.get_context_from_stage(stage)
        if not command_context:
            return CommandResult(
                False,
                None,
                message="USD stage is not attached to a context",
                error_code="invalid_stage_context",
            )
    elif isinstance(stage_or_context, str):
        command_context = omni.usd.get_context(stage_or_context)
        stage = command_context.get_stage() if command_context else None
    elif stage_or_context is not None:
        try:
            stage = stage_or_context.get_stage()
        except (AttributeError, RuntimeError):
            return CommandResult(False, None, message="Invalid USD context", error_code="invalid_stage_context")
        command_context = stage_or_context
    else:
        command_context = omni.usd.get_context()
        stage = command_context.get_stage()
    if not stage:
        return CommandResult(False, None, message="No USD stage", error_code="no_stage")

    # MovePrims reports command success, but we still validate both:
    # - destinations exist
    # - sources are no longer present
    result = execute_command_checked(
        "MovePrims",
        paths_to_move=paths_to_move,
        destructive=destructive,
        stage_or_context=command_context,
    )
    if not result.success:
        return result

    missing_destinations = [dst for src, dst in paths_to_move.items() if not stage.GetPrimAtPath(dst)]
    lingering_sources = [src for src, dst in paths_to_move.items() if stage.GetPrimAtPath(src)]
    if missing_destinations or lingering_sources:
        return CommandResult(
            False,
            None,
            message="Move validation failed",
            error_code="validation_move_failed",
            command_name=result.command_name,
            validation={
                "missing_destinations": tuple(missing_destinations),
                "lingering_sources": tuple(lingering_sources),
            },
            target_paths=tuple(paths_to_move.values()),
        )
    return CommandResult(
        True,
        None,
        command_name=result.command_name,
        validation={"moved_paths": dict(paths_to_move)},
        target_paths=tuple(paths_to_move.values()),
    )


def GroupNodeGraph(
    parent_path: Sdf.Path,
    selected_paths: list[str],
    position: object,
    position_key: object,
    context_visibility: Optional[ContextVisibility] = None,
    stage: Optional[Usd.Stage] = None,
) -> CommandResult:
    """Group selected nodes into a nodegraph and validate result prim."""
    if not parent_path or not selected_paths:
        return CommandResult(False, None, message="Invalid arguments", error_code="invalid_args")
    # Group command success alone is not enough for callers; validate payload type
    # so callers get deterministic nodegraph semantics.
    result = execute_command_checked(
        "MaterialGraph_GroupNodeGraphCommand",
        parent_path=parent_path,
        selected_paths=selected_paths,
        position=position,
        position_key=position_key,
        context_visibility=context_visibility,
        stage=stage,
    )
    if not result.success:
        return result
    prim = result.payload
    if not prim or not prim.IsValid() or not prim.IsA(UsdShade.NodeGraph):
        return CommandResult(
            False,
            prim,
            message="Grouped nodegraph validation failed",
            error_code="validation_group_failed",
            command_name=result.command_name,
        )
    return CommandResult(
        True,
        prim,
        command_name=result.command_name,
        validation={"nodegraph_path": str(prim.GetPath())},
    )


def UngroupNodeGraph(nodegraph_path: Sdf.Path, stage: Optional[Usd.Stage] = None) -> CommandResult:
    """Ungroup a nodegraph and validate that the nodegraph prim is removed."""
    if not nodegraph_path:
        return CommandResult(False, None, message="Missing nodegraph_path", error_code="invalid_args")
    stage = stage or omni.usd.get_context().get_stage()
    if not stage:
        return CommandResult(False, None, message="No USD stage", error_code="no_stage")

    # Treat ungroup as successful only when the command succeeds *and* the
    # nodegraph prim is actually gone from stage.
    result = execute_command_checked(
        "MaterialGraph_UngroupNodeGraphCommand",
        nodegraph_path=nodegraph_path,
        stage=stage,
    )
    if not result.success:
        return result
    if stage.GetPrimAtPath(nodegraph_path):
        return CommandResult(
            False,
            None,
            message="Ungroup validation failed",
            error_code="validation_ungroup_failed",
            command_name=result.command_name,
            target_paths=(str(nodegraph_path),),
        )
    return CommandResult(
        True,
        None,
        command_name=result.command_name,
        validation={"ungrouped_path": str(nodegraph_path)},
        target_paths=(str(nodegraph_path),),
    )
