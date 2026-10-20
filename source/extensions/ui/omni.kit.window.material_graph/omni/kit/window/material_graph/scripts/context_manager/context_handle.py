"""Implement material graph extension logic for `context_manager/context_handle.py`."""

from dataclasses import dataclass
from typing import Optional

from ..plugins.core import Plugin as PluginBase
from .context import Context


@dataclass(frozen=True)
class ContextHandle:
    """Typed handle for a context and its plugin.

    Valid handles have both context and plugin set with no error. When error is
    set, callers should not use the context and should fall back to error
    handling.
    """

    context: Optional[Context]
    plugin: Optional[PluginBase]
    name: str
    error: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """Return True when context and plugin are available."""
        return self.context is not None and self.plugin is not None and self.error is None
