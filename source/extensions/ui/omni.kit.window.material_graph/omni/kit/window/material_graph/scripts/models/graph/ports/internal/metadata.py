"""Attribute metadata extraction helpers for graph-port model presentation logic."""

from typing import Any

from pxr import Sdf

from .....utils.sdr_wrappers import resolve_sdf_value_type_name
from ..proxy import ProxyAttribute


class AttributeMetadata:
    """Structured attribute metadata derived from a ProxyAttribute."""

    def __init__(self, proxy_attribute: ProxyAttribute, parent: Any) -> None:
        """Initialize instance state for this material graph component."""

        self.proxy_attribute = proxy_attribute
        self.attribute_name = ""
        self.name = ""
        self.type_name = None
        self.path = None
        self.update(proxy_attribute, parent)

    def update(self, proxy_attribute: ProxyAttribute, parent: Any) -> None:
        """Refresh cached metadata fields from proxy attribute and parent model context."""
        self.proxy_attribute = proxy_attribute
        self.attribute_name = proxy_attribute.name
        self.name = proxy_attribute.display_name or self.attribute_name.split(Sdf.Path.namespaceDelimiter)[-1]
        self.type_name = resolve_sdf_value_type_name(proxy_attribute.type_name)
        self.path = parent.path.AppendProperty(self.attribute_name)
