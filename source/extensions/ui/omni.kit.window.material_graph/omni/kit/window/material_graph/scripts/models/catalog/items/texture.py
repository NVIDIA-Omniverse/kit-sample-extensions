"""Catalog texture item model carrying drag/drop metadata for texture nodes."""

import json

from .droppable import DroppableItem


class TextureItem(DroppableItem):
    """Catalog item representing a texture asset."""

    def __init__(
        self,
        name: str,
        source_path: str,
        icon_path: str,
        *,
        valid: bool = True,
        group: str = "",
    ) -> None:
        """Initialize instance state for this material graph component."""

        tooltip = source_path or ""
        info = source_path or ""
        super().__init__(name=name, info=info, icon=icon_path, tooltip=tooltip)
        self._source_path = source_path
        self._icon_path = icon_path
        self._valid = bool(valid)
        self.group = group or ""

    @property
    def source_path(self) -> str:
        """Execute source path behavior for material graph workflows."""

        return self._source_path

    @property
    def icon_path(self) -> str:
        """Execute icon path behavior for material graph workflows."""

        return self._icon_path

    @property
    def is_valid(self) -> bool:
        """Execute is valid behavior for material graph workflows."""

        return self._valid

    def set_valid(self, value: bool) -> None:
        """Execute set valid behavior for material graph workflows."""

        self._valid = bool(value)

    def rename(self, new_name: str) -> None:
        """Execute rename behavior for material graph workflows."""

        if not new_name:
            return
        self.name_model.set_value(new_name)

    def get_drag_mime_data(self) -> str:
        """Execute get drag mime data behavior for material graph workflows."""

        data = {
            "type": "Texture",
            "origin": "catalog",
            "source": self._source_path,
            "identifier": self.name_model.get_value_as_string(),
        }
        return json.dumps(data)
