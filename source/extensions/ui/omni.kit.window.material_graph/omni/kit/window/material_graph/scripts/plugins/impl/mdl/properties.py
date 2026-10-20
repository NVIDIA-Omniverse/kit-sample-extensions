"""Implement material graph extension logic for `plugins/impl/mdl/properties.py`."""

from typing import List

from pxr import UsdShade

from ....settings.utils import MDL_CATALOG_MODULES, _get_list
from ...core.properties_base import PluginPropertiesBase
from ...core.property import PluginProperty


class MdlProperties(PluginPropertiesBase):
    """Defines MDL plugin settings."""

    def list(self) -> List[PluginProperty]:
        """Execute list behavior for material graph workflows."""

        return [
            PluginProperty(
                "enablePolymorphic",
                "Enable Polymorphic Nodes",
                "bool",
                default=True,
                description="When enabled, polymorphic MDL nodes are collapsed into a single catalog entry.",
            ),
            PluginProperty(
                "outputPorts",
                "Material Output Ports",
                "string_list",
                default=[UsdShade.Tokens.displacement, UsdShade.Tokens.surface, UsdShade.Tokens.volume],
                description="Outputs created on Material prims for this context.",
            ),
            PluginProperty(
                "modules",
                "Modules",
                "string_list",
                default=_get_list(MDL_CATALOG_MODULES),
                description="MDL modules to populate the catalog for this plugin.",
            ),
            PluginProperty(
                "catalogExcludedAnnotations",
                "Catalog Excluded Annotations",
                "string_list",
                default=["deprecated", "unused", "hidden"],
                description=(
                    "Annotation keys that exclude MDL materials/functions from the catalog when present "
                    "on a shader annotation map."
                ),
            ),
        ]
