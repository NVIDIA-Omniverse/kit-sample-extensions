"""Implement material graph extension logic for `ui/controllers/drop/catalog.py`."""

import json
from typing import Any, Optional, Tuple

import omni.ui

from ....config.logging import logger
from ...interaction.menu_utils import show_menu_at_cursor


class CatalogCreationHandler:
    """Handle node creation from catalog items."""

    def __init__(self, widget: Any, catalog_model: Any, drop_fn: Any) -> None:
        """Initialize catalog creation handler."""
        self._widget = widget
        self._catalog_model = catalog_model
        self._drop_fn = drop_fn
        self._variant_menu: Optional[omni.ui.Menu] = None

    def create_from_catalog(self, item: Any, mouse_position: Optional[Tuple[float, float]] = None) -> None:
        """Create a node from a catalog item."""
        graph_view = self._widget.graph_view
        if not graph_view or not graph_view.model:
            return

        mime_data = self._catalog_model.get_drag_mime_data(item)
        if not mime_data:
            return
        item_name = getattr(item, "name", None) or getattr(item, "identifier", None) or type(item).__name__
        logger.info(
            "catalog create: item=%s context=%s",
            item_name,
            getattr(self._widget, "current_context", None),
        )

        class _DropEvent:
            """Minimal drop event for catalog creation."""

            def __init__(self, data: str, position: Optional[Tuple[float, float]]) -> None:
                """Initialize synthetic drop event."""
                self.mime_data = data
                if position:
                    self.x = position[0]
                    self.y = position[1]
                else:
                    self.x = None
                    self.y = None

        payload = self._parse_payload(mime_data)
        if not payload:
            self._drop_fn(_DropEvent(mime_data, mouse_position))
            return

        variants = payload.get("variant_subidentifiers", None)
        if isinstance(variants, list) and len(variants) > 1:
            self._show_variant_menu(payload, variants, mouse_position, _DropEvent)
            return

        self._drop_fn(_DropEvent(mime_data, mouse_position))

    @staticmethod
    def _parse_payload(mime_data: str) -> Optional[dict]:
        """Parse drag mime data payload if it is JSON."""
        try:
            payload = json.loads(mime_data)
        except (TypeError, ValueError):
            return None
        return payload if isinstance(payload, dict) else None

    def _show_variant_menu(
        self,
        payload: dict,
        variants: list,
        mouse_position: Optional[Tuple[float, float]],
        drop_event_type: type,
    ) -> None:
        """Show variant picker menu and dispatch selected payload via drop callback."""
        variant_identifiers = payload.get("variant_identifiers", {})
        variant_output_types = payload.get("variant_output_types", {})
        menu = omni.ui.Menu("Node variant")
        self._variant_menu = menu

        with menu:
            for variant in variants:
                subidentifier = str(variant)
                output_suffix = (
                    variant_output_types.get(subidentifier, "") if isinstance(variant_output_types, dict) else ""
                )
                label = f"{subidentifier} {output_suffix}".strip() if output_suffix else subidentifier

                def _select(selected_variant: str = subidentifier) -> None:
                    selected_payload = dict(payload)
                    selected_payload["subidentifier"] = selected_variant
                    if isinstance(variant_identifiers, dict):
                        selected_identifier = variant_identifiers.get(selected_variant)
                        if selected_identifier:
                            selected_payload["identifier"] = selected_identifier
                    selected_payload["requires_variant_selection"] = False
                    self._drop_fn(drop_event_type(json.dumps(selected_payload), mouse_position))

                omni.ui.MenuItem(label, triggered_fn=_select)

        show_menu_at_cursor(menu, mouse_position)

    def destroy(self) -> None:
        """Release drop-handler references and callbacks to avoid retaining stale UI state."""
        self._widget = None
        self._catalog_model = None
        self._drop_fn = None
        self._variant_menu = None
