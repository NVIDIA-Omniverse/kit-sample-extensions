"""Implement material graph extension logic for `plugins/impl/materialx/properties.py`."""

from typing import List

from pxr import UsdShade

from ...core.properties_base import PluginPropertiesBase
from ...core.property import PluginProperty


class MaterialXProperties(PluginPropertiesBase):
    """Defines MaterialX plugin settings."""

    def list(self) -> List[PluginProperty]:
        """Execute list behavior for material graph workflows."""

        return [
            PluginProperty(
                "autoUpgradeNodes",
                "Auto-Upgrade Outdated Nodes",
                "bool",
                default=True,
                description="Automatically upgrade outdated MaterialX node identifiers when switching to the MaterialX context.",
            ),
            PluginProperty(
                "outputPorts",
                "Material Output Ports",
                "string_list",
                default=[UsdShade.Tokens.displacement, UsdShade.Tokens.surface, UsdShade.Tokens.volume],
                description="Outputs created on Material prims for this context.",
            ),
            PluginProperty(
                "ignoreContexts",
                "Ignored Contexts",
                "string_list",
                default=["light", "volume"],
                description="Context names to exclude from the MaterialX catalog.",
            ),
            PluginProperty(
                "ignoreFamilies",
                "Ignored Families",
                "string_list",
                default=["volumematerial"],
                description="Node families to exclude from the MaterialX catalog.",
            ),
            PluginProperty(
                "ignoreNameRegexes",
                "Ignored Name Patterns",
                "string_list",
                default=[".*lama.*", ".*volumematerial.*", ".*disney.*", ".*surfacematerial.*", ".*edf.*", ".*vdf.*"],
                description="Regex patterns for node names to exclude.",
            ),
        ]
