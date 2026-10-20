"""Implement material graph extension logic for `plugins/impl/materialx/plugin.py`."""

import re
from typing import Any, Dict, List, Optional

from pxr import UsdShade

from ....config.logging import logger
from ....utils.sdr_wrappers import SdrRegistryWrapper
from ...core.base import Plugin
from ...core.property import PluginProperty
from .properties import MaterialXProperties


class MaterialXPlugin(Plugin):
    """Material graph plugin for MaterialX contexts."""

    def __init__(self, load_catalog: bool = True) -> None:
        """Initialize instance state for this material graph component."""

        super().__init__("mtlx", "MaterialX", MaterialXProperties(), load_catalog=load_catalog)
        self._ignore_regex_cache: Optional[tuple[tuple[str, ...], List[re.Pattern]]] = None
        self._pending_upgrade_changes: List[Any] = []

    def _get_property(self, key: str) -> Optional[PluginProperty]:
        """Execute get property behavior for material graph workflows."""

        for prop in self.properties:
            if prop.key == key:
                return prop
        return None

    def _get_list_property(self, key: str) -> List[Any]:
        """Execute get list property behavior for material graph workflows."""

        prop = self._get_property(key)
        default = prop.default if prop else []
        value = self.get_plugin_property(key, default)
        if isinstance(value, list):
            return value
        return default

    def _get_compiled_ignore_regexes(self, patterns: List[str]) -> List[re.Pattern]:
        """Execute get compiled ignore regexes behavior for material graph workflows."""

        if self._ignore_regex_cache and self._ignore_regex_cache[0] == tuple(patterns):
            return self._ignore_regex_cache[1]
        compiled: List[re.Pattern] = []
        for pattern in patterns:
            try:
                compiled.append(re.compile(pattern, re.IGNORECASE))
            except re.error as exc:
                logger.warning(
                    "plugin %s invalid ignore regex '%s': %s",
                    self.name,
                    pattern,
                    exc,
                )
        self._ignore_regex_cache = (tuple(patterns), compiled)
        return compiled

    @staticmethod
    def _get_texture_channels_from_name(shader_name: str) -> Optional[int]:
        """Execute get texture channels from name behavior for material graph workflows."""

        if not shader_name:
            return None
        parts = shader_name.split()
        if not parts:
            return None
        last = parts[-1]
        if last.lower() == "float":
            return 1
        if last.lower().startswith("float") and last[-1].isdigit():
            try:
                return int(last[-1])
            except ValueError:
                return None
        return None

    def is_supported_prim(self, prim: Any) -> bool:
        """Execute is supported prim behavior for material graph workflows."""

        usdshade_shader = UsdShade.Shader(prim)
        if not usdshade_shader:
            return False

        shader_id = usdshade_shader.GetShaderId()
        if shader_id:
            if bool(SdrRegistryWrapper().GetShaderNodeByIdentifierAndType(shader_id, self.name)):
                return True
            if shader_id.startswith("ND_"):
                return True

        return False

    @staticmethod
    def _normalized_role(sdr_node: object, role: str) -> str:
        """Normalize role display name for grouping."""
        if "Usd" in role:
            return "UsdPreviewSurface"
        for name in sdr_node.GetShaderOutputNames():
            sdr_property = sdr_node.GetShaderOutput(name)
            if sdr_property.GetType() == "terminal":
                return "Surface"
        return role[:1].upper() + role[1:]

    @staticmethod
    def _display_name_for_node(sdr_node: object) -> str:
        """Return user-facing display name for shader node."""
        name = sdr_node.GetIdentifier().replace("ND_", "").replace("_", " ")
        name = re.sub(r"(\w)([A-Z])", r"\1 \2", name)
        return name.title()

    def _is_ignored_node(
        self,
        sdr_node_name: str,
        sdr_node: object,
        ignore_name_regexs: List[re.Pattern],
        ignore_contexts: set,
        ignore_families: set,
    ) -> bool:
        """Return True when node should be filtered out by plugin settings."""
        if any(regex.search(sdr_node_name) for regex in ignore_name_regexs):
            return True
        context = sdr_node.GetContext()
        if context in ignore_contexts:
            return True
        role = sdr_node.GetMetadata().get("role", sdr_node.GetFamily())
        return role in ignore_families

    def _add_texture_shader_entry(self, shader_item: object) -> None:
        """Track texture-compatible shader item variants by channel count."""
        if not (shader_item.name.startswith("Tiledimage") or shader_item.name.startswith("Image")):
            return
        channels = self._get_texture_channels_from_name(shader_item.name) or 3
        channels = min(max(channels, 1), 3)
        if channels not in self._texture_shaders:
            self._texture_shaders[channels] = []
        self._texture_shaders[channels].append((shader_item, "file"))

    def _collect_grouped_sdr_nodes(
        self, sdr: SdrRegistryWrapper, ignore_name_regexs: List[re.Pattern], ignore_contexts: set, ignore_families: set
    ) -> tuple[Dict[str, object], Dict[str, Dict[str, List[tuple[str, object]]]]]:
        """Collect catalog groups and role/family grouped SDR nodes."""
        groups: Dict[str, object] = {}
        sdr_nodes: Dict[str, Dict[str, List[tuple[str, object]]]] = {}
        node_names = sdr.GetShaderNodeNames()
        for sdr_node_name in node_names:
            sdr_node = sdr.GetShaderNodeByNameAndType(sdr_node_name, self.name)
            if not sdr_node:
                continue
            if self._is_ignored_node(sdr_node_name, sdr_node, ignore_name_regexs, ignore_contexts, ignore_families):
                continue
            family = sdr_node.GetFamily()
            raw_role = sdr_node.GetMetadata().get("role", family)
            role = self._normalized_role(sdr_node, raw_role)
            if role not in groups:
                groups[role] = self.GroupItem(role)
            sdr_nodes.setdefault(role, {}).setdefault(family, []).append(
                (self._display_name_for_node(sdr_node), sdr_node)
            )
        return groups, sdr_nodes

    def _append_group_items_from_sdr(
        self, groups: Dict[str, object], sdr_nodes: Dict[str, Dict[str, List[tuple[str, object]]]]
    ) -> None:
        """Create shader catalog items from grouped SDR metadata."""
        for role, role_dict in sdr_nodes.items():
            for family, sdr_nodes_list in role_dict.items():
                for name, sdr_node in sdr_nodes_list:
                    shader_item = self._create_shader_item(name, sdr_node)
                    if not shader_item:
                        continue
                    if len(sdr_nodes_list) > 1:
                        shader_item.family = f"{role}:{family}"
                    groups[role].add_child(shader_item)
                    self._add_texture_shader_entry(shader_item)

    def _append_sorted_roles(self, groups: Dict[str, object]) -> None:
        """Append role groups to catalog in deterministic order."""
        roles = sorted(groups.keys())
        for role in roles:
            self._catalog_items.append(groups[role])

    def build_catalog_items(self) -> None:
        """Execute build catalog items behavior for material graph workflows."""

        ignore_contexts = set(self._get_list_property("ignoreContexts"))
        ignore_families = set(self._get_list_property("ignoreFamilies"))
        ignore_regexes = self._get_list_property("ignoreNameRegexes")
        ignore_name_regexs = self._get_compiled_ignore_regexes(ignore_regexes)
        context_id = self._next_catalog_context_id()
        logger.info(
            "plugin %s catalog build start contexts=%s families=%s patterns=%s ctx=%s",
            self.name,
            len(ignore_contexts),
            len(ignore_families),
            len(ignore_regexes),
            context_id,
        )
        try:
            sdr = SdrRegistryWrapper()
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:  # pylint: disable=broad-exception-caught
            self._catalog_items.clear()
            logger.warning("plugin %s registry unavailable: %s ctx=%s", self.name, exc, context_id)
            return

        groups = {}

        try:
            node_names = sdr.GetShaderNodeNames()
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:  # pylint: disable=broad-exception-caught
            self._catalog_items.clear()
            logger.warning("plugin %s node enumeration failed: %s ctx=%s", self.name, exc, context_id)
            return

        groups, sdr_nodes = self._collect_grouped_sdr_nodes(sdr, ignore_name_regexs, ignore_contexts, ignore_families)
        self._append_group_items_from_sdr(groups, sdr_nodes)

        for _, items in self._texture_shaders.items():
            items.sort(key=lambda item: item[0].name)

        self._append_sorted_roles(groups)

        item_count = 0
        for group in self._catalog_items:
            item_count += len(group.children) if group.children else 1
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
            "Graph.Node.Icon": {"image_url": f"{self.Paths.ICON_PATH}/materialx_logo.svg"},
        }
