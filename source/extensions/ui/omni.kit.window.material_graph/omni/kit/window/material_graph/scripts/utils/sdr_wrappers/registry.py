"""Wrapper for SDR registry access."""

from typing import Optional

from pxr import Sdr

from .shader_node import SdrShaderNodeWrapper, wrap_shader_node


class SdrRegistryWrapper:
    """Stable wrapper around ``Sdr.Registry()``."""

    def __init__(self) -> None:
        self._registry = Sdr.Registry()

    def GetShaderNodeByIdentifier(self, identifier: str) -> Optional[SdrShaderNodeWrapper]:
        return wrap_shader_node(self._registry.GetShaderNodeByIdentifier(identifier))

    def GetShaderNodeByIdentifierAndType(self, identifier: str, source_type: str) -> Optional[SdrShaderNodeWrapper]:
        return wrap_shader_node(self._registry.GetShaderNodeByIdentifierAndType(identifier, source_type))

    def GetShaderNodeNames(self) -> list[str]:
        if hasattr(self._registry, "GetShaderNodeNames"):
            return self._registry.GetShaderNodeNames()
        return self._registry.GetNodeNames()

    def GetShaderNodeByNameAndType(self, name: str, source_type: str) -> Optional[SdrShaderNodeWrapper]:
        return wrap_shader_node(self._registry.GetShaderNodeByNameAndType(name, source_type))


def get_registry() -> Optional[SdrRegistryWrapper]:
    return SdrRegistryWrapper()
