"""Tests for the material graph UI: window, controllers, catalog, toolbar, and drop handling.

This module tests the UI layer that users see and interact with: graph window (TestGraphWindowUi),
graph settings controller (TestGraphSettingsController), startup controller (TestStartupController),
nodegraph export controller (TestNodeGraphExportController), drop handlers and payload drop
(TestDropHandlers, TestPayloadDropHandler), graph coordinates (TestGraphCoords), canvas port menu
(TestGraphCanvasPortMenu), catalog widget and catalog context menu controller
(TestCatalogWidget, TestCatalogContextMenuController), and toolbar controller and menu builder
(TestToolbarControllerUi, TestToolbarMenuBuilder). We test
these because the UI is the surface for all graph and catalog actions; broken controllers or
widgets would make the window unusable or show incorrect state, and drop handling must correctly
route drag/drop into the graph and catalog."""

from .test_catalog_context_menu_controller import TestCatalogContextMenuController  # noqa: F401
from .test_catalog_drop_overlay import TestCatalogDropOverlayController  # noqa: F401
from .test_catalog_widget import TestCatalogWidget  # noqa: F401
from .test_context_solo_controller import TestContextSoloController  # noqa: F401
from .test_drop_handlers import TestDropHandlers  # noqa: F401
from .test_graph_canvas_headless import TestGraphCanvasHeadless  # noqa: F401
from .test_graph_canvas_port_menu import TestGraphCanvasPortMenu  # noqa: F401
from .test_graph_coords import TestGraphCoords  # noqa: F401
from .test_graph_settings_controller import TestGraphSettingsController  # noqa: F401
from .test_graph_widget_controller import TestGraphWidgetController  # noqa: F401
from .test_graph_window import TestGraphWindowUi  # noqa: F401
from .test_nodegraph_export_controller import TestNodeGraphExportController  # noqa: F401
from .test_payload_drop_handler import TestPayloadDropHandler  # noqa: F401
from .test_startup_controller import TestStartupController  # noqa: F401
from .test_toolbar_controller import TestToolbarControllerUi  # noqa: F401
from .test_toolbar_menus import TestToolbarMenuBuilder  # noqa: F401
from .test_ui_smoke_workflows import TestUiSmokeWorkflows  # noqa: F401

__all__ = [
    "TestCatalogContextMenuController",
    "TestCatalogDropOverlayController",
    "TestCatalogWidget",
    "TestContextSoloController",
    "TestDropHandlers",
    "TestGraphCanvasPortMenu",
    "TestGraphCanvasHeadless",
    "TestGraphCoords",
    "TestGraphSettingsController",
    "TestGraphWindowUi",
    "TestGraphWidgetController",
    "TestNodeGraphExportController",
    "TestPayloadDropHandler",
    "TestStartupController",
    "TestToolbarControllerUi",
    "TestToolbarMenuBuilder",
    "TestUiSmokeWorkflows",
]
