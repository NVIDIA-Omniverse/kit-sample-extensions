"""Implement material graph extension logic for `plugins/core/properties_base.py`."""

from typing import List

from .property import PluginProperty


class PluginPropertiesBase:
    """Base class for defining plugin property sets."""

    def list(self) -> List[PluginProperty]:
        """Execute list behavior for material graph workflows."""

        return []
