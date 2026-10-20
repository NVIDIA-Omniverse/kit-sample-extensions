"""Shader-node graph model with polymorphic MDL state and proxy attribute handling."""

from typing import Any, List, Optional

from pxr import Sdf, Usd, UsdShade

from ....plugins.core.polymorphic_state import PolymorphicState
from ....settings.settings import Settings
from ....utils.sdr_wrappers import (
    parse_mdl_subidentifier_argument_types,
    resolve_property_display_type_name,
    wrap_shader_node,
)
from ..ports.proxy import ProxyAttribute
from .prim.model import PrimModel


class ShaderModel(PrimModel):
    """Shader prim model with SDR-driven ports and polymorphic state metadata."""

    def __init__(
        self, prim: Usd.Prim, context_name: str, usd_context: Any, plugin: Any, parent: Any, sync: bool = True
    ) -> None:
        """Initialize shader model caches and bind to the UsdShade.Shader schema type."""
        self._is_polymorphic = False
        self._is_polymorphic_concrete = True
        self._polymorphic_candidates = tuple()
        self._sdr_node = None
        self._polymorphic_source_asset = None
        self._candidate_sdr_nodes = {}
        self._candidate_port_type_cache = {}
        super().__init__(prim, context_name, usd_context, plugin, parent, UsdShade.Shader, sync)
        # ``set_valid`` runs from ``PrimModel.sync()``; ``NodeGraphModel.create_child`` uses
        # ``sync=False`` then calls ``sync()`` immediately — avoid resolving SDR twice per shader.

    def set_valid(self) -> None:
        """Update validity by resolving SDR node metadata and prim existence state."""
        old_sdr = self._sdr_node
        self._sdr_node = self._plugin.get_shader_node_for_prim(self._prim) if self._plugin else None
        self._valid = bool(self._sdr_node and self.prim_exists())
        if old_sdr and self._sdr_node is not old_sdr:
            self._input_port_sig = None
            self._output_port_sig = None
        self._sync_polymorphic_state()

    def _sync_polymorphic_state(self) -> None:
        """Execute sync polymorphic state behavior for material graph workflows."""

        state = self._plugin.get_polymorphic_state_for_prim(self._prim) if self._plugin else PolymorphicState()
        old_candidates = self._polymorphic_candidates
        old_source_asset = self._polymorphic_source_asset
        self._is_polymorphic = state.is_polymorphic
        self._is_polymorphic_concrete = state.is_concrete
        self._polymorphic_candidates = tuple(state.candidates)
        current_source_asset = self._resolve_polymorphic_source_asset()
        self._polymorphic_source_asset = current_source_asset
        if self._polymorphic_candidates != old_candidates or str(current_source_asset) != str(old_source_asset):
            self._clear_polymorphic_candidate_cache()
            # Candidate set changed — per-port polymorphic flags need
            # refreshing even if port names/types haven't changed.
            self._input_port_sig = None
            self._output_port_sig = None

    def _clear_polymorphic_candidate_cache(self) -> None:
        """Drop cached polymorphic overload metadata for this shader."""
        self._candidate_sdr_nodes = {}
        self._candidate_port_type_cache = {}

    def _resolve_polymorphic_source_asset(self):
        """Read the current polymorphic source asset from USD."""
        get_source_asset = (
            getattr(self._plugin, "get_polymorphic_source_asset_for_prim", None) if self._plugin else None
        )
        if not callable(get_source_asset):
            return None
        return get_source_asset(self._prim)

    def sync_description(self) -> None:
        """Populate description from SDR help text for tooltip and inspector display."""
        if self._sdr_node:
            self._description = self._sdr_node.GetHelp()

    @staticmethod
    def _resolve_subidentifier_type(sdr_node: object, subidentifier: str, is_input: bool, port_name: str, prop: object):
        """Resolve a candidate port type from subidentifier signature or SDR metadata."""
        type_name = ""
        if is_input:
            input_names = sdr_node.GetShaderInputNames()
            try:
                candidate_types = parse_mdl_subidentifier_argument_types(subidentifier)
            except (TypeError, ValueError):
                candidate_types = []
            if port_name in input_names:
                port_index = input_names.index(port_name)
                if port_index < len(candidate_types):
                    type_name = candidate_types[port_index]
        return type_name or resolve_property_display_type_name(prop)

    def _get_candidate_port_types(self, port_name: str, is_input: bool) -> list:
        """Return the set of types for *port_name* across remaining polymorphic candidates."""
        if not self._should_scan_polymorphic_candidates():
            return []
        if not self._has_polymorphic_source_asset():
            return []

        types: list[str] = []
        for sub in self._polymorphic_candidates:
            type_name = self._get_candidate_port_type(sub, port_name, is_input)
            if type_name:
                types.append(type_name)
        return types

    def _is_port_type_ambiguous(self, port_name: str, is_input: bool) -> bool:
        """Return True if *port_name*'s type varies across remaining polymorphic candidates."""
        if not self._is_polymorphic or self._is_polymorphic_concrete:
            return False
        if len(self._polymorphic_candidates) == 0:
            return True
        if len(self._polymorphic_candidates) == 1:
            return False
        if not self._has_polymorphic_source_asset():
            return True

        seen_types: set = set()
        for sub in self._polymorphic_candidates:
            type_name = self._get_candidate_port_type(sub, port_name, is_input)
            if not type_name:
                return True
            seen_types.add(type_name)
            if len(seen_types) > 1:
                return True
        return False

    def _should_scan_polymorphic_candidates(self) -> bool:
        """Return whether candidate metadata scanning can affect the result."""
        return self._is_polymorphic and not self._is_polymorphic_concrete and len(self._polymorphic_candidates) > 1

    def _has_polymorphic_source_asset(self) -> bool:
        """Return whether a current source asset is available for candidate metadata."""
        return bool(self._get_polymorphic_source_asset())

    def _get_polymorphic_source_asset(self):
        """Return cached polymorphic source asset for this shader."""
        if self._polymorphic_source_asset is not None:
            return self._polymorphic_source_asset
        self._polymorphic_source_asset = self._resolve_polymorphic_source_asset()
        return self._polymorphic_source_asset

    def _get_candidate_sdr_node(self, subidentifier: str):
        """Return cached SDR node for a polymorphic candidate."""
        if subidentifier in self._candidate_sdr_nodes:
            return self._candidate_sdr_nodes[subidentifier]
        source_asset = self._get_polymorphic_source_asset()
        if not source_asset:
            return None
        import omni.UsdMdl

        try:
            sdr_node = wrap_shader_node(omni.UsdMdl.RegistryUtils.GetShaderNode(source_asset, subidentifier))
        except (RuntimeError, ValueError, TypeError, AttributeError):
            return None
        if not sdr_node:
            return None
        self._candidate_sdr_nodes[subidentifier] = sdr_node
        return sdr_node

    def _get_candidate_port_type(self, subidentifier: str, port_name: str, is_input: bool) -> Optional[str]:
        """Return cached resolved type for one candidate port."""
        cache_key = (subidentifier, port_name, bool(is_input))
        if cache_key in self._candidate_port_type_cache:
            return self._candidate_port_type_cache[cache_key]
        sdr_node = self._get_candidate_sdr_node(subidentifier)
        if not sdr_node:
            return None
        prop = sdr_node.GetShaderInput(port_name) if is_input else sdr_node.GetShaderOutput(port_name)
        if not prop:
            return None
        type_name = self._resolve_subidentifier_type(sdr_node, subidentifier, is_input, port_name, prop)
        self._candidate_port_type_cache[cache_key] = type_name
        return type_name

    def get_input_attributes(self, input_proxy_attributes: List[Any]) -> None:
        """Build shader input proxy attributes from SDR definitions and USD prim inputs."""
        api = UsdShade.ConnectableAPI(self._prim)
        if not (api and self._sdr_node):
            return

        for name in self._sdr_node.GetShaderInputNames():
            proxy = ProxyAttribute(f"{UsdShade.Tokens.inputs}{name}", False, self._sdr_node.GetShaderInput(name))
            proxy.polymorphic_unresolved = self._is_port_type_ambiguous(name, True)
            input_proxy_attributes.append(proxy)

        super().get_input_attributes(input_proxy_attributes)

    def get_output_attributes(self, output_proxy_attributes: List[Any]) -> None:
        """Build shader output proxy attributes from SDR definitions and USD prim outputs."""
        api = UsdShade.ConnectableAPI(self._prim)
        if not (api and self._sdr_node):
            return

        for name in self._sdr_node.GetShaderOutputNames():
            proxy = ProxyAttribute(f"{UsdShade.Tokens.outputs}{name}", True, self._sdr_node.GetShaderOutput(name))
            proxy.polymorphic_unresolved = self._is_port_type_ambiguous(name, False)
            output_proxy_attributes.append(proxy)

        super().get_output_attributes(output_proxy_attributes)

    @property
    def preview(self, item: Optional[Any] = None) -> Optional[str]:
        """Return a preview texture path if available."""
        if not Settings.preview_texture_input():
            return

        if item:
            return item.preview

        return self._get_preview_texture_path()

    def _get_preview_texture_path(self) -> Optional[str]:
        """Resolve preview texture from asset inputs."""
        if not self._sdr_node:
            return None
        connectable = UsdShade.ConnectableAPI(self._prim)
        if not connectable:
            return None
        for name in self._sdr_node.GetShaderInputNames():
            sdr_shader_property = self._sdr_node.GetShaderInput(name)
            if sdr_shader_property.GetType() != Sdf.ValueTypeNames.Asset:
                continue

            shader_input = connectable.GetInput(name)
            if not shader_input or shader_input.HasConnectedSource():
                continue

            asset_path = shader_input.GetAttr().Get()
            return asset_path.resolvedPath if asset_path else None
        return None

    @property
    def polymorphic_unresolved(self) -> bool:
        """Execute polymorphic unresolved behavior for material graph workflows."""

        return self._is_polymorphic and not self._is_polymorphic_concrete

    @property
    def tooltip_text(self, item: Optional[Any] = None) -> str:
        """Execute tooltip text behavior for material graph workflows."""

        text = super().tooltip_text if item is None else item.tooltip_text
        if item is not None:
            return text
        if self._is_polymorphic and not self._is_polymorphic_concrete:
            text += f"\n\nPolymorphic State:\tunresolved"
            if self._polymorphic_candidates:
                text += f"\n\tcandidates:\n\t\t{'\n\t\t'.join(self._polymorphic_candidates)}"
        return text
