"""Wrapper for SDR shader-node-like APIs."""

from typing import Any, Iterable, Optional

from pxr import Sdr


class SdrShaderNodeWrapper:
    """Stable wrapper around an SDR shader node-like object."""

    def __init__(self, sdr_node: object) -> None:
        self._sdr_node = sdr_node

    def __bool__(self) -> bool:
        return bool(self._sdr_node)

    def __getattr__(self, name: str) -> Any:
        # Delegate all API calls/attributes to the wrapped node unless overridden.
        return getattr(self._sdr_node, name)

    def GetShaderInputNames(self) -> list[str]:
        if hasattr(self._sdr_node, "GetShaderInputNames"):
            return self._sdr_node.GetShaderInputNames()
        return self._sdr_node.GetInputNames()

    def GetShaderOutputNames(self) -> list[str]:
        if hasattr(self._sdr_node, "GetShaderOutputNames"):
            return self._sdr_node.GetShaderOutputNames()
        return self._sdr_node.GetOutputNames()


def wrap_shader_node(shader_node: Sdr.ShaderNode) -> Optional[SdrShaderNodeWrapper]:
    """Normalize arbitrary shader-node-like objects into wrapper instances."""
    if not shader_node:
        return None
    if isinstance(shader_node, SdrShaderNodeWrapper):
        return shader_node
    return SdrShaderNodeWrapper(shader_node)


def wrap_shader_nodes(shader_nodes: Iterable[Sdr.ShaderNode]) -> list[SdrShaderNodeWrapper]:
    """Bulk-wrap node-like objects, dropping invalid entries."""
    return [wrap_shader_node(n) for n in shader_nodes]
