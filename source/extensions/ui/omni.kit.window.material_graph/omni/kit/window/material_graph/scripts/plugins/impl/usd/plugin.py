"""Implement material graph extension logic for `plugins/impl/usd/plugin.py`."""

from typing import Any, Dict, List, Optional

import omni.UsdMdl
from pxr import Ar, Sdf, UsdShade

from ....config.logging import logger
from ....utils.sdr_wrappers import wrap_shader_node
from ...core.base import Plugin
from .properties import UsdProperties

# pylint: disable=no-member


class UsdPlugin(Plugin):
    """Material graph plugin for the universal USD context."""

    def __init__(self, load_catalog: bool = True) -> None:
        """Initialize instance state for this material graph component."""

        self._source_asset: Optional[Sdf.AssetPath] = None
        self._source_asset_checked = False
        self._preview_surface_registered = False
        super().__init__("universal", "Universal", UsdProperties(), load_catalog=load_catalog)

    def _ensure_preview_surface(self) -> bool:
        """Execute ensure preview surface behavior for material graph workflows."""

        if self._source_asset_checked:
            return bool(self._source_asset)
        self._source_asset_checked = True
        resolved = Ar.GetResolver().Resolve("UsdPreviewSurface.mdl")
        self._source_asset = None
        if resolved:
            self._source_asset = Sdf.AssetPath("UsdPreviewSurface.mdl", resolved)
            try:
                if not self._preview_surface_registered:
                    omni.UsdMdl.RegistryUtils.AddModuleToRegistry(self._source_asset)
                    self._preview_surface_registered = True
            except (
                RuntimeError,
                ValueError,
                TypeError,
                AttributeError,
            ) as exc:  # pylint: disable=broad-exception-caught
                self._source_asset = None
                self._preview_surface_registered = False
                logger.warning(
                    "plugin %s failed to register UsdPreviewSurface.mdl: %s",
                    self.name,
                    exc,
                )
        else:
            logger.warning("plugin %s UsdPreviewSurface.mdl could not be resolved", self.name)
        return bool(self._source_asset)

    def reload(self) -> None:
        """Execute reload behavior for material graph workflows."""

        self._source_asset_checked = False
        self._source_asset = None
        self._preview_surface_registered = False
        super().reload()

    def build_port_names(self, port_names: List[str]) -> List[str]:
        """Execute build port names behavior for material graph workflows."""

        return [f"{UsdShade.Tokens.outputs}{port_name}" for port_name in port_names]

    def is_supported_prim(self, prim: Any) -> bool:
        """Return whether a shader belongs to the Universal context.

        Keep ID-authored shaders visible when their SDR definition is missing so
        the graph can render its USD-authored fallback ports and report the
        unresolved definition. MaterialX ``ND_`` identifiers remain scoped to
        the MaterialX plugin.
        """

        sdr_shader_node = wrap_shader_node(omni.UsdMdl.RegistryUtils.GetShaderNodeForPrim(prim))
        if not sdr_shader_node:
            try:
                shader_id = UsdShade.Shader(prim).GetShaderId()
            except (RuntimeError, ValueError, TypeError, AttributeError):
                return False
            shader_id = str(shader_id or "").strip()
            return bool(shader_id and not shader_id.startswith("ND_"))
        identifier = sdr_shader_node.GetIdentifier() or sdr_shader_node.GetName()
        if identifier and "usdpreviewsurface" in identifier.lower():
            return True
        uri = sdr_shader_node.GetResolvedImplementationURI() or ""
        return uri.lower().endswith("usdpreviewsurface.mdl")

    def get_shader_source_type(self) -> str:
        """Execute get shader source type behavior for material graph workflows."""

        return "mdl"

    def build_catalog_items(self) -> None:
        """Execute build catalog items behavior for material graph workflows."""

        context_id = self._next_catalog_context_id()
        logger.info("plugin %s catalog build start ctx=%s", self.name, context_id)
        if not self._ensure_preview_surface():
            logger.info(
                "plugin %s catalog build skipped: missing source asset ctx=%s",
                self.name,
                context_id,
            )
            return
        group = self.GroupItem("UsdPreviewSurface")

        for subidentifier in omni.UsdMdl.RegistryUtils.GetSubIdentifiersForAsset(self._source_asset):
            sdr_node = wrap_shader_node(omni.UsdMdl.RegistryUtils.GetShaderNode(self._source_asset, subidentifier))
            if not sdr_node:
                continue

            if sdr_node.GetMetadata().get(omni.UsdMdl.Metadata.Semantic, 0) != "0":
                continue

            name = sdr_node.GetIdentifier().split(">")[0].split("<")[-1]
            shader_item = self._create_shader_item(name, sdr_node)
            if shader_item:
                if name == "UsdUVTexture":
                    self._texture_shaders[4] = [(shader_item, "file")]

                elif name.startswith("UsdPrimvarReader"):
                    shader_item.family = "UsdPreviewSurface:UsdPrimvarReader"
                group.add_child(shader_item)
        if group.children:
            self._catalog_items.append(group)
        item_count = 0
        for item in self._catalog_items:
            item_count += len(item.children) if item.children else 1
        logger.info(
            "plugin %s catalog build end groups=%s items=%s ctx=%s",
            self.name,
            len(self._catalog_items),
            item_count,
            context_id,
        )

    def get_style(self) -> Dict[str, Dict[str, str]]:
        """Execute get style behavior for material graph workflows."""

        return {
            "Graph.Node.Icon": {"image_url": f"{self.Paths.ICON_PATH}/usd_logo.svg"},
        }
