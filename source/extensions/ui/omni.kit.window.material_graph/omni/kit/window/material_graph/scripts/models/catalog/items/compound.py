"""Catalog compound item model representing importable nodegraph asset entries."""

import json
from typing import List, Optional

from .droppable import DroppableItem


class CompoundItem(DroppableItem):
    """Catalog item representing an imported compound nodegraph."""

    def __init__(
        self,
        name: str,
        info: str,
        icon: str,
        tooltip: str,
        source_asset: str,
        identifier: str,
        context_visibility: Optional[List[str]] = None,
        group: str = "",
    ) -> None:
        """Initialize instance state for this material graph component."""

        super().__init__(name, info, icon, tooltip)
        self.source_asset = source_asset
        self.identifier = identifier
        self.context_visibility = context_visibility or []
        self.context = ",".join(self.context_visibility) if self.context_visibility else None
        self.group = group
        self.is_compound = True

    def is_visible_in_context(self, context_name: Optional[str]) -> bool:
        """Execute is visible in context behavior for material graph workflows."""

        if not context_name or not self.context_visibility:
            return True
        return context_name in self.context_visibility

    def get_drag_mime_data(self) -> str:
        """Execute get drag mime data behavior for material graph workflows."""

        data = {
            "type": "ImportNodeGraph",
            "origin": "catalog",
            "source_asset": self.source_asset,
            "identifier": self.identifier,
            "name": self.name,
        }
        return json.dumps(data)
