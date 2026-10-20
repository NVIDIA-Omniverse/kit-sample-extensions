"""Base catalog item abstraction and UI model plumbing for catalog entries."""

from typing import Optional

import omni.ui

from .data import CatalogItemData

# pylint: disable=no-member


class BaseItem(omni.ui.AbstractItem):
    """Base catalog item with UI models and metadata."""

    def __init__(self, name: str, info: str, icon: str, tooltip: str) -> None:
        """Initialize instance state for this material graph component."""

        super().__init__()
        self._data = CatalogItemData(name=name, info=info, icon=icon, tooltip=tooltip)
        self.name_model = omni.ui.SimpleStringModel(self._data.name)
        self.info_model = omni.ui.SimpleStringModel(self._data.info)
        self.icon_model = omni.ui.SimpleStringModel(self._data.icon)
        self.tooltip_model = omni.ui.SimpleStringModel(self._data.tooltip)
        # Explicit defaults keep catalog contracts stable across item types.
        self.identifier = None
        self.context = None
        self.family = None
        self.group = ""
        self.tags = None
        self.is_texture_group = False
        self.is_compound_group = False
        self.filtered = True

    def is_visible_in_context(self, _current_context: Optional[str] = None) -> bool:
        """Return True for items that do not constrain visibility by context."""
        return True

    def prefilter(self, filter_name_text: str, current_context: Optional[str] = None) -> None:
        """Execute prefilter behavior for material graph workflows."""
        if not self.is_visible_in_context(current_context):
            self.filtered = False
            return
        if not filter_name_text:
            self.filtered = True
            return
        name = self.name_model.as_string.lower()
        self.filtered = filter_name_text in name

    @property
    def name(self) -> str:
        """Execute name behavior for material graph workflows."""

        return self._data.name

    @property
    def info(self) -> str:
        """Execute info behavior for material graph workflows."""

        return self._data.info

    @property
    def tooltip(self) -> str:
        """Execute tooltip behavior for material graph workflows."""

        return self._data.tooltip

    @property
    def data(self) -> CatalogItemData:
        """Execute data behavior for material graph workflows."""

        return self._data
