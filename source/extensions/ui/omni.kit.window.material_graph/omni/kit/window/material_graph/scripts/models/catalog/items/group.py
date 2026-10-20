"""Catalog group-item model used to organize nested catalog entries in the UI."""

from typing import List, Optional

from ..core.base import BaseItem


class GroupItem(BaseItem):
    """Catalog container item that owns sorted child entries for nested menus."""

    def __init__(self, item_name: str) -> None:
        """Initialize instance state for this material graph component."""

        super().__init__(item_name, "", "", "")
        self._children: List[BaseItem] = []
        self.is_texture_group = False
        self.is_compound_group = False

    def add_child(self, child: BaseItem) -> None:
        """Execute add child behavior for material graph workflows."""

        self._children.append(child)
        self._children.sort(key=lambda item: item.name_model.as_string)

    @property
    def children(self) -> List[BaseItem]:
        """Execute children behavior for material graph workflows."""

        return self._children

    def prefilter(self, filter_name_text: str, current_context: Optional[str] = None) -> None:
        """Execute prefilter behavior for material graph workflows."""

        group_visible = False
        for child in self._children:
            if not child.is_visible_in_context(current_context):
                child.filtered = False
                group_visible |= child.filtered
                continue
            if not filter_name_text:
                child.filtered = True
            else:
                filter_passed = filter_name_text in child.name_model.as_string.lower()
                if not filter_passed and child.tags:
                    for tag in child.tags:
                        if filter_name_text in tag:
                            filter_passed = True
                            break
                child.filtered = filter_passed
            group_visible |= child.filtered
        self.filtered = group_visible
