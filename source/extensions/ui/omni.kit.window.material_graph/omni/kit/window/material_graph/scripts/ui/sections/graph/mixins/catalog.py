"""Catalog behavior mixin for GraphWidget."""

import json
from typing import Optional

import omni.ui
from omni.kit.widget.graph import IsolationGraphModel

from .....config.logging import logger
from .....models.catalog.registries.texture import get_texture_registry
from .....settings.settings import Settings
from .....settings.utils import is_existing_path
from ...catalog import MaterialGraphCatalog, MaterialGraphCatalogDelegate
from ...catalog.constants import CATALOG_TAB_TEXTURES


class GraphWidgetCatalogMixin:
    """Catalog build and catalog drop handling."""

    def on_build_catalog(self) -> None:
        """Create the catalog panel with drop overlay."""
        self._catalog_widget = MaterialGraphCatalog(
            model=self._catalog_model,
            delegate=MaterialGraphCatalogDelegate(
                on_item_double_clicked=self._on_catalog_item_double_clicked,
                on_group_accept_drop=self._on_catalog_group_accept_drop,
                on_group_drop=self._on_catalog_group_drop,
            ),
            on_context_menu_fn=self.on_catalog_context_menu,
            accept_drop_fn=self.on_catalog_accept_drop,
            drop_fn=self.on_catalog_drop,
            search_field_style=self.style,
            height=omni.ui.Percent(100),
        )

    def _on_catalog_group_accept_drop(self, item: object, data: str) -> bool:
        """Delegate group-level drop accept checks to the catalog widget."""
        if not self._catalog_widget:
            return False
        return self._catalog_widget.accept_group_drop(item, data)

    def _on_catalog_group_drop(self, item: object, event: omni.ui.WidgetMouseDropEvent) -> None:
        """Delegate group-level drop handling to the catalog widget."""
        if self._catalog_widget:
            self._catalog_widget.drop_on_group(item, event)

    @staticmethod
    def _parse_catalog_payload(payload: str) -> Optional[dict]:
        """Parse JSON payload for catalog drags."""
        try:
            data = json.loads(payload)
        except (TypeError, ValueError):
            return None
        return data if isinstance(data, dict) else None

    def _is_catalog_payload(self, payload: object) -> bool:
        """Return True if payload looks like a catalog JSON payload."""
        if not isinstance(payload, str):
            return False
        data = self._parse_catalog_payload(payload)
        return bool(data and "type" in data)

    def _should_show_input_output_indicator(self, drop_data: str) -> bool:
        """Return True when dragging input/output over an existing node."""
        payload = self._parse_catalog_payload(drop_data)
        if not payload:
            return False
        item_type = payload.get("type")
        if item_type not in [
            IsolationGraphModel.InputNode.get_type_name(),
            IsolationGraphModel.OutputNode.get_type_name(),
        ]:
            return False
        isolation_model = self.isolation_model
        if not isolation_model:
            return False
        if item_type == IsolationGraphModel.InputNode.get_type_name():
            return bool(isolation_model._input_nodes)
        return bool(isolation_model._output_nodes)

    def on_catalog_accept_drop(self, drop_data: str) -> bool:
        """Return whether a catalog drop is accepted."""
        if not isinstance(drop_data, str):
            return False
        if self._is_catalog_payload(drop_data):
            data = self._parse_catalog_payload(drop_data) or {}
            if data.get("origin") == "catalog":
                logger.debug("catalog drop accept: origin=catalog accepted=False")
                return False
            if data.get("type") == "Texture" and self._catalog_widget:
                result = self._catalog_widget.get_active_tab() == CATALOG_TAB_TEXTURES
                logger.debug("catalog drop accept: type=Texture accepted=%s", result)
                return result
        lower = drop_data.lower()
        if lower.endswith(".mdl"):
            handle = self._context_manager.get_context(self.current_context)
            if handle.plugin and handle.plugin.name != "mdl":
                result = False
            else:
                result = True
            logger.debug("catalog drop accept: type=mdl accepted=%s", result)
            return result

        droppable = Settings.get_droppable_texture_formats()
        ext = lower.rsplit(".", 1)[-1] if "." in lower else ""
        if not ext or ext not in droppable:
            logger.debug("catalog drop accept: extension=%s not in droppable formats, rejected", ext)
            return False

        result = is_existing_path(drop_data)
        logger.debug("catalog drop accept: type=texture_file ext=%s accepted=%s", ext, result)
        return result

    def on_catalog_drop(self, event: omni.ui.WidgetMouseDropEvent) -> None:
        """Handle a drop on the catalog panel."""
        drop_data = event.mime_data if event else None
        if not isinstance(drop_data, str):
            return
        if self._is_catalog_payload(drop_data) and self._catalog_widget:
            payload = self._parse_catalog_payload(drop_data) or {}
            if payload.get("type") == "Texture":
                self._catalog_widget.handle_texture_drop(payload, event)
                logger.debug("catalog drop: handled texture payload")
                return
        if drop_data.lower().endswith(".mdl"):
            Settings.add_mdl_catalog_module(drop_data)
            logger.info("catalog drop: added mdl module")
            return
        registry = get_texture_registry()
        if registry.has_texture(drop_data):
            return
        if not is_existing_path(drop_data):
            return
        registry.add_texture(drop_data)
        self._catalog_drop_cache.clear()
        logger.debug("catalog drop: added texture path")

    def on_catalog_context_menu(self, _items: object) -> None:
        """Show catalog context menu."""
        if self._catalog_context_menu_controller:
            self._catalog_context_menu_controller.show_menu(_items)

    def _on_catalog_item_double_clicked(self, item: object) -> None:
        """Handle catalog item double clicks."""
        if self._catalog_widget:
            self._catalog_widget.handle_item_double_clicked(item)
