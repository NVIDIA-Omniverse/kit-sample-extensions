"""Synthetic quicksearch section item model for catalog tab-style grouping."""

import omni.ui as ui


class QuickSearchSectionItem(ui.AbstractItem):
    """Top-level section row used to mirror catalog tabs in quicksearch."""

    def __init__(self, key: str, name: str) -> None:
        super().__init__()
        self.key = key
        self.name_model = ui.SimpleStringModel(name)
        self.info_model = ui.SimpleStringModel("")
        self.icon_model = ui.SimpleStringModel("")
        self.tooltip_model = ui.SimpleStringModel("")
        self.tags = []
        # Keep parity with catalog GroupItem fields expected by delegates.
        self.is_texture_group = False
        self.is_compound_group = False
