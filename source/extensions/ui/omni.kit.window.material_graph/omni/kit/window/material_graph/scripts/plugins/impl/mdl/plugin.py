"""Implement material graph extension logic for `plugins/impl/mdl/plugin.py`."""

from itertools import product
from typing import Any, Dict, List, Mapping, Optional

import carb.settings
import omni.UsdMdl
from pxr import Ar, Sdf, Usd, UsdShade

from ....config.logging import logger
from ....models.catalog.registries.icon_registry import register as cache_catalog_icon
from ....settings.settings import Settings
from ....utils.sdr_wrappers import (
    mdl_polymorphic_family_key,
    mdl_type_matches_polymorphic_constraint,
    mdl_value_types_are_compatible,
    parse_mdl_subidentifier_argument_types,
    resolve_property_display_type_name,
    wrap_shader_node,
)
from ...core.base import Plugin
from ...core.polymorphic_state import PolymorphicState
from . import settings as mdl_settings
from .polymorphic import MdlPolymorphicResolver
from .properties import MdlProperties

# pylint: disable=no-member,broad-exception-caught


class MdlPlugin(Plugin):
    """Material graph plugin for MDL contexts."""

    _DEFAULT_CATALOG_EXCLUDED_ANNOTATIONS = ("deprecated", "unused", "hidden")
    _CONSTRUCT_PREFIX = "construct_"

    def __init__(self, load_catalog: bool = True) -> None:
        """Initialize instance state for this material graph component."""

        super().__init__("mdl", "MDL", MdlProperties(), load_catalog=load_catalog)
        self._settings_sub: Optional[Any] = None
        self._polymorphic_settings_sub: Optional[Any] = None
        self._catalog_filter_settings_sub: Optional[Any] = None
        self._registered_modules_signature: Optional[tuple[tuple[str, str], ...]] = None
        self._polymorphic = MdlPolymorphicResolver(self.get_shader_source_type())
        if load_catalog:
            settings = carb.settings.get_settings()
            key = Settings.get_plugin_property_key(mdl_settings.MDL_PLUGIN_NAME, mdl_settings.MDL_CATALOG_MODULES_KEY)
            if key:
                self._settings_sub = settings.subscribe_to_tree_change_events(key, self._on_module_paths_changed)
                self._lifecycle.add_unsubscribe(self._settings_sub, "unsubscribe_to_tree_change_events")
            polymorphic_key = Settings.get_plugin_property_key(mdl_settings.MDL_PLUGIN_NAME, "enablePolymorphic")
            if polymorphic_key:
                self._polymorphic_settings_sub = settings.subscribe_to_tree_change_events(
                    polymorphic_key, self._on_polymorphic_setting_changed
                )
                self._lifecycle.add_unsubscribe(self._polymorphic_settings_sub, "unsubscribe_to_tree_change_events")
            catalog_filter_key = Settings.get_plugin_property_key(
                mdl_settings.MDL_PLUGIN_NAME, mdl_settings.MDL_CATALOG_EXCLUDED_ANNOTATIONS_KEY
            )
            if catalog_filter_key:
                self._catalog_filter_settings_sub = settings.subscribe_to_tree_change_events(
                    catalog_filter_key, self._on_module_paths_changed
                )
                self._lifecycle.add_unsubscribe(self._catalog_filter_settings_sub, "unsubscribe_to_tree_change_events")

    def _on_module_paths_changed(
        self, _tree_item: Optional[Any] = None, _changed_item: Optional[Any] = None, _event_type: Optional[Any] = None
    ) -> None:
        """Execute on module paths changed behavior for material graph workflows."""

        if self._destroyed or self._lifecycle is None:
            return
        self.reload()

    def _on_polymorphic_setting_changed(
        self, _tree_item: Optional[Any] = None, _changed_item: Optional[Any] = None, _event_type: Optional[Any] = None
    ) -> None:
        """Reload catalog and refresh active MDL graph when toggle changes."""
        if self._destroyed or self._lifecycle is None:
            return
        self.reload()
        self._refresh_active_mdl_graph()

    def _refresh_active_mdl_graph(self) -> None:
        """Refresh the visible graph immediately when MDL setting changes."""
        try:
            from ....extension import get_graph_window

            graph_window = get_graph_window()
            graph_widget = graph_window.graph_widget if graph_window else None
            if not graph_widget or graph_widget.current_context != self.name:
                return
            graph_widget.request_model_refresh()
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.debug("active MDL graph refresh skipped: %s", exc)

    def _is_polymorphic_enabled(self) -> bool:
        """Return whether polymorphic MDL behavior is enabled."""
        return bool(self.get_plugin_property("enablePolymorphic", True))

    def is_supported_prim(self, prim: Any) -> bool:
        """Return whether a shader carries an MDL source-asset reference.

        Keep incomplete or unresolved references visible so the graph can
        render their authored fallback ports and validation can explain the
        missing asset or subidentifier.
        """

        usdshade_shader = UsdShade.Shader(prim)
        if not usdshade_shader or (usdshade_shader.GetImplementationSource() != UsdShade.Tokens.sourceAsset):
            return False
        return prim.HasAttribute("info:mdl:sourceAsset") or prim.HasAttribute("info:mdl:sourceAsset:subIdentifier")

    def destroy(self) -> None:
        """Execute destroy behavior for material graph workflows."""

        self._settings_sub = None
        self._polymorphic_settings_sub = None
        self._catalog_filter_settings_sub = None
        self._polymorphic.unregister_all_overloads()
        super().destroy()

    def _get_catalog_excluded_annotations(self) -> tuple[str, ...]:
        """Return MDL catalog exclusion annotations from plugin settings."""
        raw = self.get_plugin_property(
            mdl_settings.MDL_CATALOG_EXCLUDED_ANNOTATIONS_KEY,
            list(self._DEFAULT_CATALOG_EXCLUDED_ANNOTATIONS),
        )
        if isinstance(raw, str):
            values = [raw]
        elif isinstance(raw, list):
            values = raw
        elif isinstance(raw, tuple):
            values = list(raw)
        else:
            values = []

        sanitized: list[str] = []
        for value in values:
            if not isinstance(value, str):
                continue
            token = value.strip().lower()
            if token and token not in sanitized:
                sanitized.append(token)
        if sanitized:
            return tuple(sanitized)
        return self._DEFAULT_CATALOG_EXCLUDED_ANNOTATIONS

    def _get_custom_paths(self) -> List[str]:
        """Execute get custom paths behavior for material graph workflows."""

        return []

    def get_polymorphic_state_for_prim(self, prim: Optional[Usd.Prim]) -> PolymorphicState:
        """Execute get polymorphic state for prim behavior for material graph workflows."""

        if not self._is_polymorphic_enabled():
            return PolymorphicState()
        return self._polymorphic.get_state_for_prim(prim)

    def get_polymorphic_source_asset_for_prim(self, prim: Optional[Usd.Prim]) -> Sdf.AssetPath:
        """Return the source asset used by polymorphic analysis for a prim."""
        return self._polymorphic.get_source_asset_for_prim(prim) if self._polymorphic else Sdf.AssetPath()

    def invalidate_polymorphic_runtime_cache(self) -> None:
        """Invalidate sync-time polymorphic analysis caches."""
        if self._polymorphic:
            self._polymorphic.invalidate_runtime_cache()

    def cache_polymorphic_graph_connection_index(self, nodegraph_prim: Optional[Usd.Prim]) -> None:
        """Precompute graph connection state used by polymorphic sync-time analysis."""
        if self._polymorphic and self._is_polymorphic_enabled():
            self._polymorphic.cache_graph_connection_index(nodegraph_prim)

    def can_connect_polymorphic_models(self, source_model: object, target_model: object) -> bool:
        """Execute can connect polymorphic models behavior for material graph workflows."""

        if not self._is_polymorphic_enabled():
            return False
        return self._polymorphic.can_connect_models(source_model, target_model)

    @classmethod
    def _are_mdl_value_types_compatible(cls, source_type_name: Any, target_type_name: Any) -> bool:
        """Return True for MDL backend-supported builtin auto conversions."""
        return mdl_value_types_are_compatible(source_type_name, target_type_name)

    def compare_render_types(self, source_model: Any, target_model: Any) -> Plugin.RenderTypeMatch:
        match = super().compare_render_types(source_model, target_model)
        source = source_model.proxy_attribute
        target = target_model.proxy_attribute

        if match == self.RenderTypeMatch.NO_MATCH:
            if self._are_mdl_value_types_compatible(source.type_name, target.type_name):
                return self.RenderTypeMatch.UNKNOWN
            return match
        if match == self.RenderTypeMatch.UNKNOWN:
            return match

        res = True

        if source.render_type == omni.UsdMdl.Types.Struct:
            res = source.mdl_struct_type == target.mdl_struct_type and source.mdl_symbol == target.mdl_symbol

        elif source.render_type == omni.UsdMdl.Types.Enum:
            res = source.mdl_symbol == target.mdl_symbol

        elif source.render_type == omni.UsdMdl.Types.Array:
            source_array_type = source.mdl_array_element_type
            target_array_type = target.mdl_array_element_type
            if source_array_type is None or target_array_type is None:
                res = False
            elif source_array_type != target_array_type:
                res = False
            elif source_array_type == omni.UsdMdl.Types.Struct:
                res = source.mdl_struct_type == target.mdl_struct_type and source.mdl_symbol == target.mdl_symbol
            elif source_array_type == omni.UsdMdl.Types.Enum:
                res = source.mdl_symbol == target.mdl_symbol

        return self.RenderTypeMatch.MATCH if res else self.RenderTypeMatch.NO_MATCH

    def compare_types(self, source_model: Any, target_model: Any) -> bool:
        """Return True when port types are equal or MDL can auto-convert them."""
        if super().compare_types(source_model, target_model):
            return True

        source = source_model.proxy_attribute
        target = target_model.proxy_attribute
        return self._are_mdl_value_types_compatible(source.type_name, target.type_name)

    def can_connect(self, source_model: Any, target_model: Any) -> bool:
        """Return True if a connection can be created between the two models"""
        if self._is_polymorphic_source_to_uniform_input(source_model, target_model):
            return False

        source_proxy = getattr(source_model, "proxy_attribute", None)
        target_proxy = getattr(target_model, "proxy_attribute", None)
        if bool(getattr(source_proxy, "polymorphic_unresolved", False)) or bool(
            getattr(target_proxy, "polymorphic_unresolved", False)
        ):
            return self._can_connect_unresolved_interface_models(
                source_model,
                target_model,
            )

        if super().can_connect(source_model, target_model):
            return True

        if self._can_connect_unresolved_interface_models(source_model, target_model):
            return True

        return self.can_connect_polymorphic_models(source_model, target_model)

    @staticmethod
    def _is_polymorphic_source_to_uniform_input(source_model: Any, target_model: Any) -> bool:
        """Return True when an unresolved polymorphic source targets a uniform input."""
        target_proxy = getattr(target_model, "proxy_attribute", None)
        target_name = getattr(target_proxy, "name", "")
        if not str(target_name).startswith(UsdShade.Tokens.inputs):
            return False
        if getattr(target_proxy, "variability", None) != Sdf.VariabilityUniform:
            return False

        source_proxy = getattr(source_model, "proxy_attribute", None)
        if bool(getattr(source_proxy, "polymorphic_unresolved", False)):
            return True
        try:
            prim_model = source_model.prim_model
        except (RuntimeError, ValueError, TypeError, AttributeError):
            prim_model = None
        return bool(getattr(prim_model, "polymorphic_unresolved", False))

    def _can_connect_unresolved_interface_models(self, source_model: Any, target_model: Any) -> bool:
        """Allow unresolved interface ports when any concrete candidate pair is compatible."""

        def _candidate_types(model: Any) -> List[str]:
            proxy = getattr(model, "proxy_attribute", None)
            if not getattr(proxy, "polymorphic_unresolved", False):
                return self._get_mdl_types(proxy)
            get_types = getattr(model, "_get_candidate_port_types", None)
            if not callable(get_types):
                return []
            return [str(type_name) for type_name in get_types() if type_name]

        source_proxy = getattr(source_model, "proxy_attribute", None)
        target_proxy = getattr(target_model, "proxy_attribute", None)
        source_unresolved = bool(getattr(source_proxy, "polymorphic_unresolved", False))
        target_unresolved = bool(getattr(target_proxy, "polymorphic_unresolved", False))
        if not (source_unresolved or target_unresolved):
            return False

        source_types = _candidate_types(source_model)
        target_types = _candidate_types(target_model)
        if not source_types or not target_types:
            return False
        if target_unresolved:
            for source_type, target_type in product(source_types, target_types):
                if mdl_type_matches_polymorphic_constraint(target_type, source_type, True):
                    return True
            return False
        for source_type, target_type in product(source_types, target_types):
            if mdl_type_matches_polymorphic_constraint(source_type, target_type, False):
                return True
        return False

    @staticmethod
    def _get_mdl_types(proxy: Any) -> List[str]:
        """Return concrete MDL type spellings for a proxy, preserving priority."""
        if not proxy:
            return []
        mdl_types = [
            str(type_name)
            for type_name in (
                getattr(proxy, "mdl_struct_type", None),
                getattr(proxy, "mdl_symbol", None),
            )
            if type_name
        ]
        if mdl_types:
            return list(dict.fromkeys(mdl_types))
        return [str(proxy.type_name)] if getattr(proxy, "type_name", None) else []

    def resolve_polymorphic_overload_for_prim(self, prim: Optional[Usd.Prim]) -> bool:
        # Connect-time overload mutation is handled by the polymorphic connect command.
        """Execute resolve polymorphic overload for prim behavior for material graph workflows."""

        return False

    def resolve_polymorphic_overload_for_connection(self, source_model: object, target_model: object) -> bool:
        # Connect-time overload mutation is handled by the polymorphic connect command.
        """Execute resolve polymorphic overload for connection behavior for material graph workflows."""

        return False

    def _resolve_source_assets(self, context_id: int) -> List[Sdf.AssetPath]:
        """Resolve configured MDL module paths to source asset entries."""
        asset_paths = Settings.get_mdl_catalog_modules() + self._get_custom_paths()
        source_assets: List[Sdf.AssetPath] = []
        for asset_path in asset_paths:
            try:
                resolved = Ar.GetResolver().Resolve(asset_path)
            except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
                logger.debug("MDL asset resolve failed path=%s: %s", asset_path, exc)
                resolved = ""
            if not resolved:
                logger.warning(
                    "plugin %s MDL module path cannot be resolved: %s ctx=%s", self.name, asset_path, context_id
                )
                continue
            source_assets.append(Sdf.AssetPath(asset_path, resolved))
        return source_assets

    def _ensure_modules_registered(self, source_assets: List[Sdf.AssetPath], context_id: int) -> bool:
        """Ensure MDL modules are registered when module signature changes."""
        signature = tuple((asset.path, asset.resolvedPath) for asset in source_assets)
        if signature == self._registered_modules_signature:
            return True
        try:
            omni.UsdMdl.RegistryUtils.AddModulesToRegistry(source_assets)
            self._registered_modules_signature = signature
            return True
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.warning("plugin %s failed to register MDL modules: %s ctx=%s", self.name, exc, context_id)
            return False

    def _add_texture_shader_hint(self, shader_item: object) -> None:
        """Record known texture shader item variants for texture-drop integration."""
        texture_name = shader_item.name.strip().lower()
        texture_3_texture = {
            "bitmap texture",
            "bitmap texture, bump",
            "hextilng bitmap texture",
            "hextilng normalmap texture",
        }
        texture_3_tex = {"texture lookup color", "texture lookup float3", "texture lookup float4"}
        texture_1_tex = {"texture lookup float"}
        if texture_name in texture_3_texture:
            self._texture_shaders.setdefault(3, []).append((shader_item, "texture"))
        elif texture_name in texture_3_tex:
            self._texture_shaders.setdefault(3, []).append((shader_item, "tex"))
        elif texture_name in texture_1_tex:
            self._texture_shaders.setdefault(1, []).append((shader_item, "tex"))

    def _add_shader_item_to_groups(self, groups: Dict[str, object], shader_item: object) -> None:
        """Add a shader item to category groups and texture-hint registry."""
        family = shader_item.family
        category = family.split(":")[0]
        if category not in groups:
            groups[category] = self.GroupItem(category)
        groups[category].add_child(shader_item)
        self._add_texture_shader_hint(shader_item)

    def _iter_source_asset_subidentifiers(self, source_asset: Sdf.AssetPath, context_id: int) -> List[str]:
        """Return sorted subidentifiers for one source asset."""
        try:
            subidentifiers = omni.UsdMdl.RegistryUtils.GetSubIdentifiersForAsset(source_asset)
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.warning("plugin %s failed to read MDL subidentifiers: %s ctx=%s", self.name, exc, context_id)
            return []
        subidentifiers.sort()
        return subidentifiers

    def _collect_catalog_nodes(
        self, source_assets: List[Sdf.AssetPath], polymorphic_enabled: bool, groups: Dict[str, object], context_id: int
    ) -> Dict[tuple[str, str], list[tuple[object, Sdf.AssetPath, str]]]:
        """Collect SDR nodes grouped by base label and populate non-polymorphic catalog immediately."""
        sdr_nodes: Dict[tuple[str, str], list[tuple[object, Sdf.AssetPath, str]]] = {}
        for source_asset in source_assets:
            for subidentifier in self._iter_source_asset_subidentifiers(source_asset, context_id):
                sdr_node = wrap_shader_node(omni.UsdMdl.RegistryUtils.GetShaderNode(source_asset, subidentifier))
                if not sdr_node:
                    continue
                base_name = sdr_node.GetLabel() or subidentifier.split("(")[0]
                if base_name in ["gamma_mode", "coordinate_space", "wrap_mode"]:
                    continue
                if not polymorphic_enabled:
                    shader_item = self._create_shader_item(subidentifier, sdr_node)
                    if not shader_item:
                        continue
                    shader_item.extra_mime_data = {
                        "source_asset_path": source_asset.path,
                        "source_asset_resolved_path": source_asset.resolvedPath,
                        "subidentifier": subidentifier,
                    }
                    self._add_shader_item_to_groups(groups, shader_item)
                    continue
                base_name = self._polymorphic_catalog_group_name(sdr_node, subidentifier)
                sdr_nodes.setdefault((base_name, source_asset.path), []).append((sdr_node, source_asset, subidentifier))
        return sdr_nodes

    def _register_polymorphic_icons(
        self, shader_item: object, sdr_nodes_list: List[tuple[object, Sdf.AssetPath, str]]
    ) -> None:
        """Register icon aliases for all polymorphic overload identifiers."""
        if not shader_item.icon:
            return
        for overload_sdr_node, _overload_source_asset, _overload_subidentifier in sdr_nodes_list:
            overload_identifier = overload_sdr_node.GetIdentifier()
            if overload_identifier:
                cache_catalog_icon(self.name, overload_identifier, shader_item.icon, shader_item.icon_color)

    @classmethod
    def _get_sdr_output_type_suffix(cls, sdr_node: object) -> str:
        """Return formatted output type suffix like '-> color3f' for one SDR node."""
        output_types: list[str] = []
        for name in sdr_node.GetShaderOutputNames():
            shader_output = sdr_node.GetShaderOutput(name)
            output_type = resolve_property_display_type_name(shader_output)
            if output_type:
                output_type = output_type.replace("color3f", "color")
                output_types.append(output_type)
        if not output_types:
            return ""
        return f"-> {','.join(output_types)}"

    @classmethod
    def _polymorphic_catalog_group_name(cls, sdr_node: object, subidentifier: str) -> str:
        """Return the catalog grouping name for a potential polymorphic MDL entry."""
        return mdl_polymorphic_family_key(sdr_node, subidentifier)

    @staticmethod
    def _subidentifier_arity(subidentifier: str) -> Optional[int]:
        """Return the top-level argument count encoded in an MDL subidentifier."""
        if "(" not in subidentifier:
            return None
        try:
            return len(parse_mdl_subidentifier_argument_types(subidentifier))
        except (TypeError, ValueError):
            return None

    def _build_polymorphic_entries(
        self,
        sdr_nodes: Mapping[tuple[str, str], list[tuple[object, Sdf.AssetPath, str]]],
        groups: Dict[str, object],
        polymorphic_enabled: bool,
    ) -> None:
        """Build one catalog entry per polymorphic family and cache overload metadata."""
        for group_key, sdr_nodes_list in sdr_nodes.items():
            name = group_key[0]
            sdr_nodes_list = sorted(sdr_nodes_list, key=lambda item: (item[1].path, item[2]))
            primary_sdr_node, primary_source_asset, primary_subidentifier = sdr_nodes_list[0]
            family_subidentifiers = [
                subidentifier
                for _, source_asset, subidentifier in sdr_nodes_list
                if source_asset.path == primary_source_asset.path
            ]
            if polymorphic_enabled and len(sdr_nodes_list) > 1:
                family_sdr_nodes = {
                    subidentifier: overload_sdr_node
                    for overload_sdr_node, source_asset, subidentifier in sdr_nodes_list
                    if source_asset.path == primary_source_asset.path
                }
                polymorphic_subidentifiers = self._polymorphic.cache_family_overloads(
                    primary_source_asset.path, name, family_subidentifiers, family_sdr_nodes
                )
                if polymorphic_subidentifiers:
                    shader_item = self._create_shader_item(name, primary_sdr_node)
                    if not shader_item:
                        continue
                    shader_item.extra_mime_data = {
                        "source_asset_path": primary_source_asset.path,
                        "source_asset_resolved_path": primary_source_asset.resolvedPath,
                        "subidentifier": primary_subidentifier,
                    }
                    shader_item.extra_mime_data.update(
                        {
                            "is_polymorphic": True,
                            "polymorphic_base_name": primary_subidentifier.split("(")[0],
                            "polymorphic_subidentifiers": list(polymorphic_subidentifiers),
                        }
                    )
                    self._register_polymorphic_icons(shader_item, sdr_nodes_list)
                    self._add_shader_item_to_groups(groups, shader_item)
                    continue

            # Family is not polymorphic: keep one catalog entry, but carry
            # explicit variants for drop-time user selection.
            shader_item = self._create_shader_item(name, primary_sdr_node)
            if not shader_item:
                continue
            variant_identifiers = {
                subidentifier: overload_sdr_node.GetIdentifier()
                for overload_sdr_node, source_asset, subidentifier in sdr_nodes_list
                if source_asset.path == primary_source_asset.path
                and overload_sdr_node
                and overload_sdr_node.GetIdentifier()
            }
            variant_output_types = {
                subidentifier: self._get_sdr_output_type_suffix(overload_sdr_node)
                for overload_sdr_node, source_asset, subidentifier in sdr_nodes_list
                if source_asset.path == primary_source_asset.path and overload_sdr_node
            }
            shader_item.extra_mime_data = {
                "source_asset_path": primary_source_asset.path,
                "source_asset_resolved_path": primary_source_asset.resolvedPath,
                "subidentifier": primary_subidentifier,
                "variant_subidentifiers": list(family_subidentifiers),
                "variant_identifiers": variant_identifiers,
                "variant_output_types": variant_output_types,
                "requires_variant_selection": len(family_subidentifiers) > 1,
            }
            self._add_shader_item_to_groups(groups, shader_item)

    def _append_sorted_groups(self, groups: Dict[str, object]) -> None:
        """Append catalog groups in deterministic name order."""
        group_names = sorted(groups.keys())
        for group_name in group_names:
            self._catalog_items.append(groups[group_name])

    def build_catalog_items(self) -> None:
        """Execute build catalog items behavior for material graph workflows."""

        context_id = self._next_catalog_context_id()
        logger.info("plugin %s catalog build start ctx=%s", self.name, context_id)
        self._catalog_items.clear()
        self._polymorphic.clear_catalog_cache()
        polymorphic_enabled = self._is_polymorphic_enabled()
        groups = {}
        source_assets = self._resolve_source_assets(context_id)

        if not source_assets:
            logger.info("plugin %s catalog build skipped: no modules ctx=%s", self.name, context_id)
            return

        if not self._ensure_modules_registered(source_assets, context_id):
            return
        sdr_nodes = self._collect_catalog_nodes(source_assets, polymorphic_enabled, groups, context_id)
        self._build_polymorphic_entries(sdr_nodes, groups, polymorphic_enabled)
        self._append_sorted_groups(groups)

        item_count = 0
        for group in self._catalog_items:
            children = group.children
            item_count += len(children) if children is not None else 1
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
            "Graph.Node.Icon": {"image_url": f"{self.Paths.ICON_PATH}/mdl_logo.png"},
        }
