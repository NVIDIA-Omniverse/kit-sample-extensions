"""Destroy/cleanup behavior mixin for GraphWidget."""

from .....config.logging import logger


class GraphWidgetDestroyMixin:
    """Cleanup logic for GraphWidget."""

    @staticmethod
    def _safe_call(label: str, func) -> None:
        """Run cleanup callback and convert failures into warnings."""
        try:
            func()
        except (
            RuntimeError,
            ValueError,
            TypeError,
            AttributeError,
        ) as exc:  # pylint: disable=broad-exception-caught
            logger.warning("destroy failed for %s: %s", label, exc)

    def _destroy_controllers(self) -> None:
        """Destroy controller objects and clear references."""
        if self._context_switcher:
            self._safe_call("context switcher", self._context_switcher.destroy)
            self._context_switcher = None
        if self._catalog_controller:
            self._safe_call("catalog controller", self._catalog_controller.destroy)
            self._catalog_controller = None
        if self._interaction_controller:
            self._safe_call("interaction controller", self._interaction_controller.destroy)
            self._interaction_controller = None
        if self._node_creation_controller:
            self._safe_call("node creation controller", self._node_creation_controller.destroy)
            self._node_creation_controller = None
        if self._stage_lifecycle_controller:
            self._safe_call("stage lifecycle controller", self._stage_lifecycle_controller.destroy)
            self._stage_lifecycle_controller = None
        if self._context_model_controller:
            self._safe_call("context model controller", self._context_model_controller.destroy)
            self._context_model_controller = None
        if self._graph_settings_controller:
            self._safe_call("graph settings controller", self._graph_settings_controller.destroy)
            self._graph_settings_controller = None
        if self._startup_controller:
            self._safe_call("startup controller", self._startup_controller.destroy)
            self._startup_controller = None
        if self._context_visibility_controller:
            self._safe_call("context visibility menu", self._context_visibility_controller.unregister_menu_items)
            self._safe_call("context visibility controller", self._context_visibility_controller.destroy)
            self._context_visibility_controller = None
        if self._nodegraph_export_controller:
            self._safe_call("nodegraph export menu", self._nodegraph_export_controller.unregister_menu_items)
            self._safe_call("nodegraph export controller", self._nodegraph_export_controller.destroy)
            self._nodegraph_export_controller = None
        if self._catalog_context_menu_controller:
            self._safe_call("catalog context menu controller", self._catalog_context_menu_controller.destroy)
            self._catalog_context_menu_controller = None
        if self._toolbar_controller:
            self._safe_call("toolbar actions", self._toolbar_controller.clear_actions_and_hotkeys)
            self._safe_call("toolbar controller", self._toolbar_controller.destroy)
            self._toolbar_controller = None

    def _destroy_view_resources(self) -> None:
        """Destroy transient UI resources and overlays."""
        if self._graph_drop_overlay:
            self._safe_call("graph drop overlay", self._graph_drop_overlay.destroy)
            self._graph_drop_overlay = None
        self._graph_background_color = None
        self._usd_context = None
        self._context_manager = None
        if self._catalog_model:
            self._catalog_model.destroy()
            self._catalog_model = None
        if self._open_graph_lifecycle:
            self._open_graph_lifecycle.cleanup()
            self._open_graph_lifecycle = None
        if self._upgrade_refresh_lifecycle:
            self._upgrade_refresh_lifecycle.cleanup()
            self._upgrade_refresh_lifecycle = None

    def destroy(self) -> None:
        """Destroy controllers and release resources."""
        self._destroy_controllers()
        self._destroy_view_resources()

        self.model = None
        super().destroy()
