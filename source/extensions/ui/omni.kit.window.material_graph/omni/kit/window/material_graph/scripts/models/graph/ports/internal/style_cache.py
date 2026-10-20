"""Style cache for computing and reusing graph-port visual style dictionaries."""

import hashlib
from collections import OrderedDict
from typing import Any

from omni.kit.graph.delegate.modern import GraphNodeDelegate
from omni.ui import color

from ..proxy import ProxyAttribute


class AttributeStyleCache:
    """LRU cache for port styles derived from ProxyAttribute metadata."""

    PORT_STYLE_CACHE_LIMIT = 256
    PORT_STYLES: "OrderedDict[str, Any]" = OrderedDict()

    @classmethod
    def get_style(cls, value_type_name: Any, proxy_attribute: ProxyAttribute) -> Any:
        """Return a cached style for the port value type."""
        hash_str = str(value_type_name)
        for value in [
            proxy_attribute.render_type,
            proxy_attribute.mdl_struct_type,
            proxy_attribute.mdl_symbol,
            proxy_attribute.mdl_array_element_type,
        ]:
            if value:
                hash_str += value

        if hash_str in cls.PORT_STYLES:
            cls.PORT_STYLES.move_to_end(hash_str)
            return cls.PORT_STYLES[hash_str]

        hash_object = hashlib.sha256(hash_str.encode())
        hex_digest = hash_object.hexdigest()
        port_color = color(hex_digest[:6])
        _ = GraphNodeDelegate.specialized_port_style(str(value_type_name), port_color)
        cls.PORT_STYLES[hash_str] = GraphNodeDelegate.specialized_port_style(str(value_type_name), port_color)
        if len(cls.PORT_STYLES) > cls.PORT_STYLE_CACHE_LIMIT:
            cls.PORT_STYLES.popitem(last=False)
        return cls.PORT_STYLES[hash_str]
