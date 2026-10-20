"""Implement material graph extension logic for `plugins/impl/usd/properties.py`."""

from typing import List

from pxr import UsdShade

from ...core.properties_base import PluginPropertiesBase
from ...core.property import PluginProperty


class UsdProperties(PluginPropertiesBase):
    """Defines universal (USD) plugin settings."""

    def list(self) -> List[PluginProperty]:
        """Execute list behavior for material graph workflows."""

        return [
            PluginProperty(
                "outputPorts",
                "Material Output Ports",
                "string_list",
                default=[UsdShade.Tokens.displacement, UsdShade.Tokens.surface, UsdShade.Tokens.volume],
                description="Outputs created on Material prims for this context.",
            )
        ]
