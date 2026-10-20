"""Helpers to ensure NodeGraphNodeAPI metadata is consistently applied and removed."""

from typing import Callable, Optional, Tuple, Type, TypeVar

import omni.kit.undo
import omni.usd
from pxr import Sdf, Usd, UsdUI

from ..result import CommandResult

# pylint: disable=no-member,protected-access


TCommand = TypeVar("TCommand")


def _get_stage_for_command(command: object) -> Optional[Usd.Stage]:
    """Return a USD stage for a command instance."""
    if "_get_stage" in dir(command):
        return command._get_stage()
    return omni.usd.get_context().get_stage()


def _get_prim_from_path(command: object, path: object) -> Optional[Usd.Prim]:
    """Return a prim from a path for a given command."""
    stage = _get_stage_for_command(command)
    if not stage or not path:
        return None
    if isinstance(path, str):
        path = Sdf.Path(path)
    return stage.GetPrimAtPath(path)


def _get_nodegraph_node_api_name() -> str:
    """Return the NodeGraphNodeAPI schema name."""
    return (
        UsdUI.NodeGraphNodeAPI.GetSchemaTypeName()
        if "GetSchemaTypeName" in dir(UsdUI.NodeGraphNodeAPI)
        else "NodeGraphNodeAPI"
    )


def _unwrap_command_prim(result: object) -> Optional[Usd.Prim]:
    """Normalize command results to a prim object."""
    if result is None:
        return None
    if isinstance(result, CommandResult):
        return result.payload if result.success else None
    return result


def _apply_nodegraph_node_api(prim: object) -> bool:
    """Apply NodeGraphNodeAPI to a prim if possible."""
    prim = _unwrap_command_prim(prim)
    if not prim:
        return False
    if prim.HasAPI(UsdUI.NodeGraphNodeAPI):
        return False
    if not UsdUI.NodeGraphNodeAPI.CanApply(prim):
        return False
    with omni.kit.undo.disabled():
        if not prim.ApplyAPI(UsdUI.NodeGraphNodeAPI):
            return False
    return prim.HasAPI(UsdUI.NodeGraphNodeAPI)


def _remove_nodegraph_node_api(prim: object) -> None:
    """Remove NodeGraphNodeAPI from a prim when present."""
    if not prim or not prim.HasAPI(UsdUI.NodeGraphNodeAPI):
        return
    try:
        with omni.kit.undo.disabled():
            if not prim.RemoveAPI(UsdUI.NodeGraphNodeAPI):
                return
        # Ensure the apiSchemas list is cleaned up for older USD builds.
        schema_name = _get_nodegraph_node_api_name()
        api_schemas = prim.GetMetadata(Usd.Tokens.apiSchemas) or []
        if "GetAddedOrExplicitItems" in dir(api_schemas):
            api_schemas = list(api_schemas.GetAddedOrExplicitItems())
        if schema_name in api_schemas:
            api_schemas = [name for name in api_schemas if name != schema_name]
            prim.SetMetadata(Usd.Tokens.apiSchemas, Sdf.TokenListOp.CreateExplicit(api_schemas))
    except AttributeError as exc:
        # Older USD builds can expose apiSchemas metadata in variants that do
        # not support this cleanup path; skipping is safe and expected.
        from ...config.logging import logger

        logger.debug("skipped apiSchemas cleanup for %s: %s", prim, exc)


def _capture_nodegraph_node_api_state(
    command: object, prim: object
) -> Optional[Tuple[Sdf.Layer, Sdf.Path, bool, object]]:
    """Capture the exact edit-target apiSchemas field before a command mutates it."""
    stage = _get_stage_for_command(command)
    if not stage or not prim:
        return None
    edit_target = stage.GetEditTarget()
    spec_path = edit_target.MapToSpecPath(prim.GetPath())
    prim_spec = edit_target.GetLayer().GetPrimAtPath(spec_path)
    if not prim_spec:
        return edit_target.GetLayer(), spec_path, False, None
    field = Usd.Tokens.apiSchemas
    authored = prim_spec.HasInfo(field)
    return edit_target.GetLayer(), spec_path, authored, prim_spec.GetInfo(field) if authored else None


def _restore_nodegraph_node_api_state(
    snapshot: Optional[Tuple[Sdf.Layer, Sdf.Path, bool, object]], prim: object
) -> None:
    """Restore apiSchemas without leaving an added/deleted list-op behind."""
    if not snapshot:
        _remove_nodegraph_node_api(prim)
        return
    layer, spec_path, authored, value = snapshot
    prim_spec = layer.GetPrimAtPath(spec_path)
    if not prim_spec:
        return
    field = Usd.Tokens.apiSchemas
    if authored:
        prim_spec.SetInfo(field, value)
    elif prim_spec.HasInfo(field):
        prim_spec.ClearInfo(field)


def get_nodegraph_node_api(prim: object) -> Optional[UsdUI.NodeGraphNodeAPI]:
    """Ensure and return NodeGraphNodeAPI for a prim."""
    prim = _unwrap_command_prim(prim)
    if not prim:
        return None
    _apply_nodegraph_node_api(prim)
    if not prim.HasAPI(UsdUI.NodeGraphNodeAPI):
        return None
    return UsdUI.NodeGraphNodeAPI(prim)


def prim_from_attr(attr_name: str) -> Callable[[object], Optional[Usd.Prim]]:
    """Create a prim getter for a command attribute name."""

    def _get_prim(command: object) -> Optional[Usd.Prim]:
        """Fetch a prim from a command's attribute path."""
        return _get_prim_from_path(command, command.__dict__.get(attr_name))

    return _get_prim


def ensure_nodegraph_node_api(
    get_prim: Callable[[object], Optional[Usd.Prim]],
    should_apply: Optional[Callable[[object, object], bool]] = None,
) -> Callable[[Type[TCommand]], Type[TCommand]]:
    """Decorator to apply NodeGraphNodeAPI in do/undo.

    This mutates the command's do/undo methods and stores internal state on the instance.
    """

    def decorator(cls: Type[TCommand]) -> Type[TCommand]:
        """Wrap command class do/undo to maintain NodeGraphNodeAPI state."""
        original_do = cls.do
        original_undo = cls.undo

        def do(self, *args: object, **kwargs: object) -> object:
            """Run command and apply NodeGraphNodeAPI."""
            prim_before = get_prim(self)
            self._nodegraph_node_api_state = _capture_nodegraph_node_api_state(self, prim_before)
            result = original_do(self, *args, **kwargs)
            prim = get_prim(self)
            applied = _apply_nodegraph_node_api(prim) if should_apply is None or should_apply(self, result) else False
            self._nodegraph_node_api_applied = applied
            self._nodegraph_node_api_prim_path = prim.GetPath() if prim else None
            return result

        def undo(self, *args: object, **kwargs: object) -> object:
            """Undo command and remove NodeGraphNodeAPI if applied."""
            result = original_undo(self, *args, **kwargs)
            if self.__dict__.get("_nodegraph_node_api_applied", False):
                prim = get_prim(self)
                if not prim:
                    prim = _get_prim_from_path(self, self.__dict__.get("_nodegraph_node_api_prim_path"))
                _restore_nodegraph_node_api_state(self.__dict__.get("_nodegraph_node_api_state"), prim)
            return result

        cls.do = do
        cls.undo = undo
        return cls

    return decorator
