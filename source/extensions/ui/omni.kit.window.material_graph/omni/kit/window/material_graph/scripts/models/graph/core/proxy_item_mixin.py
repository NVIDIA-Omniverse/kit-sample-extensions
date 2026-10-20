"""Implement material graph extension logic for `models/graph/core/proxy_item_mixin.py`."""

from typing import Any, Optional


class ProxyItemMixin:
    """Mixin for proxy-item property access.

    Graph widgets often pass a proxy `item` to property accessors. These helpers
    allow subclasses to read/write attributes from the proxy when present,
    falling back to the model instance.
    """

    @staticmethod
    def _proxy_value(item: Optional[Any], attr: str, fallback: Any) -> Any:
        """Read `attr` from proxy item when present, else return fallback."""
        return getattr(item, attr) if item else fallback

    @staticmethod
    def _proxy_set(item: Optional[Any], attr: str, value: Any) -> bool:
        """Set `attr` on proxy item when present and report success."""
        if item is None:
            return False
        setattr(item, attr, value)
        return True


__all__ = ["ProxyItemMixin"]
