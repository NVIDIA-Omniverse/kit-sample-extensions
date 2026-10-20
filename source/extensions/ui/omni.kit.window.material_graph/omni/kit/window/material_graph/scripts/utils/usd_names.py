"""USD naming and relationship helpers shared across graph models."""

from typing import Any

from pxr import UsdShade


def strip_usd_namespace(name: Any) -> str:
    """Return a USD input/output property name without its namespace prefix."""
    return str(name).removeprefix(UsdShade.Tokens.inputs).removeprefix(UsdShade.Tokens.outputs)


def is_internal_nodegraph_interface_connection(source_model: Any, target_model: Any) -> bool:
    """Return True for direct child <-> containing NodeGraph interface wiring."""
    source_prim = getattr(source_model, "prim", None)
    target_prim = getattr(target_model, "prim", None)
    if not (source_prim and target_prim):
        return False
    try:
        if target_prim.IsA(UsdShade.NodeGraph) and source_prim.GetParent().GetPath() == target_prim.GetPath():
            return True
        if source_prim.IsA(UsdShade.NodeGraph) and target_prim.GetParent().GetPath() == source_prim.GetPath():
            return True
    except (RuntimeError, ValueError, TypeError, AttributeError):
        return False
    return False
