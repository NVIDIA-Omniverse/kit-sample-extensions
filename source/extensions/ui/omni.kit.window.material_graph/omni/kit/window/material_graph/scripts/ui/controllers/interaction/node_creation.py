"""Node-creation controller for catalog/menu-driven graph node instantiation."""

from typing import Optional, Tuple

import omni.client
import omni.ui

from ....commands.wrappers.nodes import CreateShader
from ....commands.wrappers.ui_nodes import CreateBackdrop, CreateNodeGraph
from ....config.logging import logger
from ..drop.catalog import CatalogCreationHandler
from ..drop.paths import PathDropHandler
from ..drop.payloads import PayloadDropHandler
from ..drop.textures import TextureDropHandler
from .coords import get_graph_mouse_position
from .handler_registry import HandlerRegistry

# pylint: disable=no-member


class NodeCreationController:
    """Handles drag-and-drop creation of nodes."""

    def __init__(
        self,
        widget: object,
        context_visibility_controller: object,
        catalog_model: object,
        context_manager: object,
        usd_context: object,
        graph_settings_controller: object,
    ) -> None:
        """Initialize the node creation controller."""
        self._widget = widget
        self._context_visibility_controller = context_visibility_controller
        self._catalog_model = catalog_model
        self._context_manager = context_manager
        self._usd_context = usd_context
        self._graph_settings_controller = graph_settings_controller
        self._handlers = HandlerRegistry()
        self._catalog_handler = self._handlers.add(CatalogCreationHandler(widget, catalog_model, self.drop))
        self._path_handler = self._handlers.add(PathDropHandler(widget, usd_context))
        self._texture_handler = self._handlers.add(TextureDropHandler(widget, context_manager))
        self._payload_handler = self._handlers.add(
            PayloadDropHandler(
                widget,
                context_manager,
                graph_settings_controller,
                context_visibility_controller,
                create_shader=self._create_shader,
                create_backdrop=self._create_backdrop,
                create_nodegraph=self._create_nodegraph,
                texture_drop_fn=self._texture_handler.handle_drop if self._texture_handler else None,
            )
        )

    @staticmethod
    def _create_shader(*args: object, **kwargs: object) -> object:
        """Create a shader node using the current module reference."""
        return CreateShader(*args, **kwargs)

    @staticmethod
    def _create_backdrop(*args: object, **kwargs: object) -> object:
        """Create a backdrop using the current module reference."""
        return CreateBackdrop(*args, **kwargs)

    @staticmethod
    def _create_nodegraph(*args: object, **kwargs: object) -> object:
        """Create a nodegraph using the current module reference."""
        return CreateNodeGraph(*args, **kwargs)

    def accept_drop(self, drop_data: str) -> bool:
        """Return True if the payload can be dropped."""
        if not isinstance(drop_data, str):
            return False

        if self._path_handler and self._path_handler.can_accept(drop_data):
            logger.debug("drop accept: kind=path accepted=True")
            return True

        if omni.client.is_valid_url(drop_data):
            accepted = self._texture_handler.can_accept(drop_data)
            logger.debug("drop accept: kind=texture accepted=%s", accepted)
            return accepted

        if self._payload_handler:
            accepted = self._payload_handler.can_accept(drop_data)
            logger.debug("drop accept: kind=payload accepted=%s", accepted)
            return accepted
        logger.debug("drop accept: kind=unknown accepted=False")
        return False

    def drop(self, event: omni.ui.WidgetMouseDropEvent) -> None:
        """Handle drop events and create corresponding nodes."""
        if self._path_handler and self._path_handler.handle_drop(event.mime_data):
            logger.debug("drop handled: path")
            return

        if omni.client.is_valid_url(event.mime_data):
            if self._texture_handler:
                self._texture_handler.handle_drop(event.mime_data, event)
                logger.debug("drop handled: texture")
            return

        if self._payload_handler:
            self._payload_handler.handle_drop(event.mime_data, event)
            logger.debug("drop handled: payload")
        return

    def create_from_catalog(self, item: object, mouse_position: Optional[Tuple[float, float]] = None) -> None:
        """Create a node from a catalog item."""
        if self._catalog_handler:
            self._catalog_handler.create_from_catalog(item, mouse_position)

    def get_hovered_position(self) -> Optional[Tuple[float, float]]:
        """Return mouse position in graph coordinates."""
        return get_graph_mouse_position(self._widget.graph_view)

    def destroy(self) -> None:
        """Release subscriptions, callbacks, and cached references owned by this controller."""
        if self._handlers:
            self._handlers.destroy()
            self._handlers = None
        self._catalog_handler = None
        self._path_handler = None
        self._payload_handler = None
        self._texture_handler = None
        self._context_visibility_controller = None
        self._catalog_model = None
        self._context_manager = None
        self._usd_context = None
        self._widget = None
