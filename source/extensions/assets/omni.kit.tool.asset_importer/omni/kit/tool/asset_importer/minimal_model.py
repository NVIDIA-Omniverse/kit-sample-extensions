from typing import List

from omni import ui

__all__ = ["MinimalItem", "MinimalModal"]


class MinimalItem(ui.AbstractItem):
    """
    Helper class for ui.AbstractItem implementations to create items for modal item model.
    """

    def __init__(self, text):
        super().__init__()
        self.model = ui.SimpleStringModel(text)


class MinimalModal(ui.AbstractItemModel):
    """
    Helper class for ui.AbstractItemModel implementations to store indexed items for use in Omniverse UI widgets.
    """

    def __init__(self, default_index, item_labels: list[str]):
        super().__init__()
        self._default_index = default_index
        self._current_index = ui.SimpleIntModel(default_index)
        self._current_index.add_value_changed_fn(lambda _: self._item_changed(None))
        self._items = [MinimalItem(label) for label in item_labels]

    @property
    def current_index(self) -> int:
        return self._current_index.as_int

    def get_item_children(self, _: ui.AbstractItem = None) -> List[ui.AbstractItem]:
        return self._items

    def get_item_value_model(self, item: MinimalItem, _):
        if item is None:
            return self._current_index
        return item.model
