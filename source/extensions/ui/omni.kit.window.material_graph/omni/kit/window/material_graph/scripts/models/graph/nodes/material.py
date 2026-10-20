"""Material graph model specialization for UsdShade.Material root node behavior."""

from typing import Any, List

import omni.UsdMdl
from pxr import Sdf, Usd, UsdShade

from ....commands.wrappers.material import PauseMaterial
from ....config.logging import logger
from ..ports.proxy import ProxyAttribute
from .nodegraph import NodeGraphModel


class MaterialModel(NodeGraphModel):
    """Nodegraph model specialized for materials."""

    def __init__(
        self,
        prim: Usd.Prim,
        context_name: str,
        usd_context: Any,
        plugin: Any,
        validator: object,
    ) -> None:
        """Initialize material-root graph model bound to UsdShade.Material schema type."""
        super().__init__(prim, context_name, usd_context, plugin, None, UsdShade.Material)
        self.validator = validator

    def destroy(self) -> None:
        """Execute destroy behavior for material graph workflows."""

        if self._pause:
            result = PauseMaterial(self._prim_path, False, stage=self._stage)
            if not result.success:
                logger.warning(
                    "material cleanup could not unpause '%s': %s; the session-layer paused state may remain authored",
                    self._prim_path,
                    result.error_code or result.message or "command returned no reason",
                )
        super().destroy()

    def set_valid(self) -> None:
        """Set validity according to whether the underlying material prim still exists."""
        self._valid = self.prim_exists()

    def get_output_attributes(self, output_proxy_attributes: List[ProxyAttribute]) -> None:
        """Populate material output proxy attributes."""
        output_names = self._plugin.get_material_output_names()

        for name in output_names:
            attribute = self.prim.GetAttribute(name)
            proxy_attribute = ProxyAttribute(name, True, attribute=attribute)
            proxy_attribute.display_group = "Outputs"
            proxy_attribute.type_name = attribute.GetTypeName() or Sdf.ValueTypeNames.Token
            if self._context_name == "mdl":
                proxy_attribute.render_type = omni.UsdMdl.Types.Struct
                proxy_attribute.mdl_struct_type = omni.UsdMdl.StructTypes.Material
                proxy_attribute.mdl_symbol = "::material"
            output_proxy_attributes.append(proxy_attribute)

    def get_child_prims(self) -> List[Usd.Prim]:
        """Return child prims connected to outputs and descendants."""
        child_prims = []
        seen_paths = set()

        for prim in self._outputs.get_connected_prims(False):
            if not prim or prim == self._prim:
                continue

            prim_path = prim.GetPath()
            if prim_path in seen_paths:
                continue

            seen_paths.add(prim_path)
            child_prims.append(prim)

        for prim in super().get_child_prims():
            prim_path = prim.GetPath()
            if prim_path in seen_paths:
                continue
            seen_paths.add(prim_path)
            child_prims.append(prim)
        return child_prims

    def set_pause(self, enabled: bool) -> bool:
        """Toggle material evaluation pause state and propagate pause to child models."""
        if self._pause == enabled:
            return True
        result = PauseMaterial(self._prim_path, enabled, stage=self._stage)
        if not result.success:
            logger.warning(
                "set material pause=%s failed for '%s': %s; pause state was not changed",
                enabled,
                self._prim_path,
                result.error_code or result.message or "command returned no reason",
            )
            return False
        self._pause = enabled
        super().set_pause(enabled)
        return True
