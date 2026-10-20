"""Implement material graph extension logic for `models/catalog/items/misc.py`."""

import os

from ....config.paths import Paths
from .droppable import DroppableItem


class MiscellaneousItem(DroppableItem):
    """Catalog item for non-shader primitives."""

    def __init__(self, prim_type: str, info: str) -> None:
        """Initialize instance state for this material graph component."""

        prefix = "".join(prim_type.split())
        thumbnail = Paths.ICON_PATH.joinpath(f"{prefix}.svg")
        if not os.path.exists(thumbnail):
            thumbnail = ""
        tooltip = info
        super().__init__(prim_type, info, f"{thumbnail}", tooltip)
