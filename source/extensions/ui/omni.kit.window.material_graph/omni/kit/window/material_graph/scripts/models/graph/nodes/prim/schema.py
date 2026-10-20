# pylint: disable=no-member
"""Implement material graph extension logic for `models/graph/nodes/prim/schema.py`."""

import copy
import re
from typing import Any, Dict, List, Tuple

from pxr import Sdf, Usd, UsdShade

from .....config.logging import logger
from ...ports.proxy import ProxyAttribute

# ``insert_schema_attributes`` mutates ``ProxyAttribute`` instances in place; cache only
# canonical trees and return ``deepcopy`` so each ``PrimModel`` gets an independent copy.
_SCHEMA_COLLECT_CACHE: Dict[Tuple[str, ...], Dict[str, Dict[str, List[ProxyAttribute]]]] = {}


class SchemaAttributeCollector:
    """Collects schema-defined attributes for prims."""

    def __init__(self, prim: Usd.Prim) -> None:
        """Initialize the collector for a prim."""
        self._prim = prim

    def collect(self) -> Dict[str, Dict[str, List[ProxyAttribute]]]:
        """Collect schema attributes grouped by port type and instance."""
        if not self._prim:
            logger.debug("schema attribute collection skipped: missing prim")
            return {}
        key = tuple(str(s) for s in self._prim.GetAppliedSchemas())
        cached = _SCHEMA_COLLECT_CACHE.get(key)
        if cached is not None:
            return copy.deepcopy(cached)
        schema_attributes = self._collect_from_registry()
        _SCHEMA_COLLECT_CACHE[key] = schema_attributes
        return copy.deepcopy(schema_attributes)

    def _collect_from_registry(self) -> Dict[str, Dict[str, List[ProxyAttribute]]]:
        """Build schema proxy metadata from ``Usd.SchemaRegistry`` (uncached)."""
        schema_attributes: Dict[str, Dict[str, List[ProxyAttribute]]] = {}
        schema_registry = Usd.SchemaRegistry()

        for applied_schema in self._prim.GetAppliedSchemas():
            schema_type_name, instance_name = schema_registry.GetTypeNameAndInstance(applied_schema)

            if not schema_registry.IsAppliedAPISchema(schema_type_name):
                continue

            prim_def = schema_registry.FindAppliedAPIPrimDefinition(schema_type_name)
            if not prim_def:
                continue

            schema_property_names = prim_def.GetPropertyNames()
            if not schema_property_names:
                continue

            for prop_name in schema_property_names:
                attribute_definition = prim_def.GetAttributeDefinition(prop_name)
                if not (attribute_definition and attribute_definition.IsAttribute()):
                    continue

                attribute_name = schema_registry.MakeMultipleApplyNameInstance(prop_name, instance_name)

                port_type = None
                is_output = False

                if attribute_name.startswith(UsdShade.Tokens.inputs):
                    port_type = UsdShade.Tokens.inputs

                elif attribute_name.startswith(UsdShade.Tokens.outputs):
                    port_type = UsdShade.Tokens.outputs
                    is_output = True

                else:
                    continue

                port_dict = schema_attributes.setdefault(port_type, {})
                port_dict.setdefault(instance_name, []).append(
                    ProxyAttribute(attribute_name, is_output, attribute_definition=attribute_definition)
                )

        return schema_attributes

    @staticmethod
    def clear_collect_cache() -> None:
        """Drop cached schema trees (tests or schema hot-reload)."""
        _SCHEMA_COLLECT_CACHE.clear()

    @staticmethod
    def _split_camel(text: str) -> str:
        """Split CamelCase tokens into space-delimited words for UI display labels."""
        return re.sub(r"(?<!^)(?=[A-Z])", " ", text)

    @staticmethod
    def _cap_first(text: str) -> str:
        """Capitalize the first letter of a string."""
        return text[:1].upper() + text[1:] if text else text

    @staticmethod
    def _remove_prefix_token(text: str, prefix: str) -> str:
        """Remove repeated display-label prefixes from a composed label."""
        if not text or not prefix:
            return text
        value = text.strip()
        prefix = prefix.strip()
        prefix_lower = prefix.casefold()
        while value.casefold().startswith(f"{prefix_lower} "):
            value = value[len(prefix) :].strip()
        return value

    @staticmethod
    def _remove_namespace_prefix(text: str, prefix: str) -> str:
        """Remove an authored namespace prefix from a display group string."""
        if not text or not prefix:
            return text
        separator = Sdf.Path.namespaceDelimiter
        expected = f"{prefix}{separator}"
        if text.casefold().startswith(expected.casefold()):
            return text[len(expected) :]
        return text

    def insert_schema_attributes(
        self,
        is_output: bool,
        proxy_attributes: List[ProxyAttribute],
        schema_attributes: Dict[str, Dict[str, List[ProxyAttribute]]],
    ) -> List[ProxyAttribute]:
        """Insert schema-defined attributes into proxy list.

        Returns a new list to avoid mutating the input list while iterating.
        """
        port_type = UsdShade.Tokens.outputs if is_output else UsdShade.Tokens.inputs

        if not (schema_attributes and port_type in schema_attributes):
            return list(proxy_attributes)

        port_dict = schema_attributes[port_type]
        merged = list(proxy_attributes)

        for instance_name, schema_proxy_attributes in port_dict.items():
            anchor_index = None
            anchor = None
            for idx, proxy_attribute in enumerate(merged):
                if proxy_attribute.name == instance_name:
                    anchor_index = idx
                    anchor = proxy_attribute
                    break

            if anchor_index is None or anchor is None:
                merged.extend(schema_proxy_attributes)
                continue

            src_display_name = anchor.display_name or anchor.name.split(Sdf.Path.namespaceDelimiter)[-1]
            src_display_group = anchor.display_group

            for schema_proxy_attribute in schema_proxy_attributes:
                for idx, proxy_attribute in enumerate(list(merged)):
                    if proxy_attribute.name == schema_proxy_attribute.name:
                        schema_proxy_attribute.update(proxy_attribute)
                        merged.pop(idx)
                        if idx < anchor_index:
                            anchor_index -= 1
                        break

                display_name = self._remove_prefix_token(schema_proxy_attribute.display_name, src_display_name)
                display_group = schema_proxy_attribute.display_group
                display_group = self._remove_namespace_prefix(display_group, port_type.capitalize())
                display_group = self._remove_namespace_prefix(display_group, src_display_group)
                display_group = self._remove_prefix_token(display_group, src_display_name)

                if not display_name:
                    base = schema_proxy_attribute.name.split(Sdf.Path.namespaceDelimiter)[-1]
                    display_name = self._cap_first(self._split_camel(base))

                if display_group:
                    display_group = f"{src_display_name} {self._cap_first(display_group)}"
                else:
                    display_group = src_display_name

                schema_proxy_attribute.display_name = f"{src_display_name} {display_name}"
                schema_proxy_attribute.display_group = (
                    f"{src_display_group}{Sdf.Path.namespaceDelimiter}{display_group}"
                )

            insert_at = min(anchor_index + 1, len(merged))
            merged[insert_at:insert_at] = schema_proxy_attributes

        return merged

    @staticmethod
    def add_or_update_proxy_attribute(is_output: bool, attribute: Any, proxy_attributes: List[ProxyAttribute]) -> None:
        """Add or update a proxy attribute from a USD attribute."""
        if not attribute:
            return

        name = attribute.GetName()
        for proxy_attribute in proxy_attributes:
            if proxy_attribute.name == name:
                proxy_attribute.update(attribute)
                return

        proxy_attributes.append(ProxyAttribute(name, is_output, attribute=attribute))
