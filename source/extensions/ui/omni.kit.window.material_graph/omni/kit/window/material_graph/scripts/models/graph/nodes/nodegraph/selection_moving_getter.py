"""Selection moving-item adapter for nodegraph batch positioning."""

from typing import Any, List, Optional

from omni.kit.widget.graph import AbstractBatchPositionGetter


class SelectionMovingGetter(AbstractBatchPositionGetter):
    """Return peer selection items that should move with a dragged item."""

    def __call__(self, drive_item: Any) -> Optional[List[Any]]:
        """Return currently selected items that should move with the drive item."""
        model = self.model
        if not model:
            return []
        return model._get_selected_moving_items(drive_item)
