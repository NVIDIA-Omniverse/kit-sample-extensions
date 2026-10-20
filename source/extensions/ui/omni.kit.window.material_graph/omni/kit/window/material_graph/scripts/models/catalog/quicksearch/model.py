"""QuickSearch model that proxies grouped Material Graph catalog entries."""

from typing import Any, List, Optional

import omni.ui as ui

from ....config.logging import get_logger, log_exception
from ..items import GroupItem
from ..items.compound import CompoundItem
from ..items.texture import TextureItem
from .section_item import QuickSearchSectionItem

logger = get_logger()


class MaterialGraphQuickSearchModel(ui.AbstractItemModel):
    """Expose catalog entries to omni.kit.window.quicksearch with groups."""

    def __init__(self, *args: Any) -> None:
        """Initialize instance state for this material graph component."""
        super().__init__(*args)
        self._filter_text = ""
        self._sections = [
            QuickSearchSectionItem("nodes", "Nodes"),
            QuickSearchSectionItem("nodegraphs", "NodeGraphs"),
            QuickSearchSectionItem("textures", "Textures"),
        ]

    def destroy(self) -> None:
        """Release cached item references."""
        self._filter_text = ""
        self._sections.clear()

    def get_item_children(self, item: Optional[Any]) -> List[Any]:
        """Return grouped, filtered children for the current tree node."""
        catalog_model = self._get_catalog_model()
        if not catalog_model:
            return []

        if item is None:
            visible_sections = []
            for section in self._sections:
                if self._section_children(section, catalog_model):
                    visible_sections.append(section)
            return visible_sections
        if isinstance(item, QuickSearchSectionItem):
            return self._section_children(item, catalog_model)
        if isinstance(item, GroupItem):
            return self._filter_children(item.children, catalog_model.current_context)
        return []

    def can_item_have_children(self, item: Optional[Any]) -> bool:
        """Tell quicksearch which items should be expandable."""
        if item is None:
            return True
        if isinstance(item, QuickSearchSectionItem):
            catalog_model = self._get_catalog_model()
            if not catalog_model:
                return False
            return bool(self._section_children(item, catalog_model))
        if isinstance(item, GroupItem):
            catalog_model = self._get_catalog_model()
            if not catalog_model:
                return False
            return bool(self._filter_children(item.children, catalog_model.current_context))
        return False

    def get_item_value_model_count(self, item: Any) -> int:
        """Return number of columns displayed in quicksearch."""
        return 1

    def get_item_value_model(self, item: Any, column_id: int) -> Optional[Any]:
        """Return value models used by quicksearch delegates."""
        if item is None:
            return None
        if column_id == 0:
            return item.name_model
        if column_id == 1:
            return item.info_model
        if column_id == 2:
            return item.icon_model
        if column_id == 3:
            return item.tooltip_model
        return None

    def filter_by_text(self, filter_name_text: str) -> None:
        """Apply case-insensitive text filtering while preserving groups."""
        self._filter_text = (filter_name_text or "").strip().lower()
        self._item_changed(None)

    def execute(self, item: Any) -> None:
        """Create a node when quicksearch entry is accepted."""
        from ....extension import GraphExtension

        if self._is_leaf_item(item):
            mime_data = item.get_drag_mime_data()
            if mime_data:
                try:
                    GraphExtension.add_node(mime_data)
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    log_exception(
                        logger,
                        "quicksearch execute failed",
                        action="quicksearch_execute",
                        exc=exc,
                    )
                    from ....extension import get_graph_window

                    graph_window = get_graph_window()
                    graph_widget = graph_window.graph_widget if graph_window else None
                    if graph_widget:
                        graph_widget.show_error(
                            "Quick Search could not create the selected node; see the preceding Material Graph log "
                            "entry for the item and exception details",
                            log_message=False,
                        )

    @staticmethod
    def _matches(item: Any, text: str) -> bool:
        """Return True when the item name/info/tags contains the query text."""
        lc_text = text.lower()
        name = item.name_model.as_string.lower()
        if lc_text in name:
            return True
        info = item.info_model.as_string.lower() if item.info_model else ""
        if info and lc_text in info:
            return True
        if item.tags:
            return any(lc_text in str(tag).lower() for tag in item.tags)
        return False

    def _filter_children(self, items: List[Any], current_context: Optional[str]) -> List[Any]:
        """Filter children by context visibility and the active query text."""
        result = []
        for child in items:
            if isinstance(child, GroupItem):
                if self._group_has_match(child, current_context):
                    result.append(child)
                continue
            if not self._is_leaf_item(child):
                continue
            if not child.is_visible_in_context(current_context):
                continue
            if self._filter_text and not self._matches(child, self._filter_text):
                continue
            result.append(child)
        return result

    def _section_children(self, section: QuickSearchSectionItem, catalog_model: Any) -> List[Any]:
        """Return filtered children for a synthetic top-level tab section."""
        current_context = catalog_model.current_context
        roots = self._partition_root_children(catalog_model.children).get(section.key, [])
        return self._filter_children(roots, current_context)

    @staticmethod
    def _partition_root_children(items: List[Any]) -> dict:
        """Partition catalog root entries by tab-equivalent buckets."""
        buckets = {"nodes": [], "nodegraphs": [], "textures": []}
        for child in items:
            if getattr(child, "is_texture_group", False) or isinstance(child, TextureItem):
                buckets["textures"].append(child)
            elif getattr(child, "is_compound_group", False) or isinstance(child, CompoundItem):
                buckets["nodegraphs"].append(child)
            else:
                buckets["nodes"].append(child)
        return buckets

    def _group_has_match(self, group: GroupItem, current_context: Optional[str]) -> bool:
        """Return True when any descendant item is visible and matches query."""
        for child in group.children:
            if isinstance(child, GroupItem):
                if self._group_has_match(child, current_context):
                    return True
                continue
            if not self._is_leaf_item(child):
                continue
            if not child.is_visible_in_context(current_context):
                continue
            if self._filter_text and not self._matches(child, self._filter_text):
                continue
            return True
        return False

    @staticmethod
    def _is_leaf_item(item: Any) -> bool:
        """Return True when item behaves like a droppable catalog leaf."""
        return callable(getattr(item, "get_drag_mime_data", None)) and hasattr(item, "is_visible_in_context")

    @staticmethod
    def _get_catalog_model() -> Optional[Any]:
        """Return the active GraphWidget catalog model."""
        from ....extension import get_graph_window

        graph_window = get_graph_window()
        if not graph_window or not graph_window.graph_widget:
            return None
        return graph_window.graph_widget.catalog_model
