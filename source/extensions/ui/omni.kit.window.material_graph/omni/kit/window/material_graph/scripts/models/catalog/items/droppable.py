"""Base catalog item type that provides drag-and-drop payload serialization."""

import json

from ..core.base import BaseItem


class DroppableItem(BaseItem):
    """Catalog item base that serializes drag payload metadata for graph drops."""

    def get_drag_mime_data(self) -> str:
        """Execute get drag mime data behavior for material graph workflows."""

        data = {"type": self.name_model.get_value_as_string(), "origin": "catalog"}
        return json.dumps(data)
