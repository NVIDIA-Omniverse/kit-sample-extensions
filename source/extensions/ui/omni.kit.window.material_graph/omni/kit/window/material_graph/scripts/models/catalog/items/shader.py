"""Catalog shader item model carrying node-creation metadata and payload hints."""

import json
from typing import Dict, List, Optional

from pxr import UsdShade

from .droppable import DroppableItem


class ShaderItem(DroppableItem):
    """Catalog item representing an SDR shader node."""

    def __init__(
        self,
        name: str,
        context: str,
        identifier: str,
        info: str = "",
        icon: str = "",
        icon_color: int = 0x00000000,
        tooltip: str = "",
        sub_menu: str = "",
        family: Optional[str] = None,
        ui_order: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> None:
        """Initialize instance state for this material graph component."""

        super().__init__(name, info, icon, tooltip)
        self.context = context
        self.identifier = identifier
        self.family = family
        self.ui_order = ui_order
        self.tags = tags
        self.extra_mime_data: Dict[str, object] = {}
        self.sub_menu = sub_menu
        self.icon = icon
        self.icon_color = icon_color

    def get_drag_mime_data(self) -> str:
        """Execute get drag mime data behavior for material graph workflows."""

        data = {
            "type": UsdShade.Tokens.Shader,
            "origin": "catalog",
            "identifier": self.identifier,
            "context": self.context,
        }
        data.update(self.extra_mime_data)
        return json.dumps(data)
