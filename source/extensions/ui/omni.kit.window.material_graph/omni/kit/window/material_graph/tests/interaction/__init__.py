"""Tests for graph and catalog interaction: menus, lifecycle, and controllers.

This module tests the interaction layer that sits between the graph model and the UI: catalog
controller (TestCatalogController), context menu registry (TestContextMenuRegistry), context
visibility (TestContextVisibilityController), background menu and double-click
(TestInteractionBackgroundMenu, TestInteractionDoubleClick), safe callback wrapping
(TestInteractionSafeCallback), menu utilities (TestMenuUtils), node creation controller
(TestNodeCreationController), and stage lifecycle controller (TestStageLifecycleController)."""

from .test_catalog_controller import TestCatalogController  # noqa: F401
from .test_context_menu_registry import TestContextMenuRegistry  # noqa: F401
from .test_context_visibility import TestContextVisibilityController  # noqa: F401
from .test_interaction_background_menu import TestInteractionBackgroundMenu  # noqa: F401
from .test_interaction_double_click import TestInteractionDoubleClick  # noqa: F401
from .test_interaction_safe_callback import TestInteractionSafeCallback  # noqa: F401
from .test_menu_utils import TestMenuUtils  # noqa: F401
from .test_node_creation_controller import TestNodeCreationController  # noqa: F401
from .test_stage_lifecycle_controller import TestStageLifecycleController  # noqa: F401

__all__ = [
    "TestCatalogController",
    "TestContextMenuRegistry",
    "TestContextVisibilityController",
    "TestInteractionBackgroundMenu",
    "TestInteractionDoubleClick",
    "TestInteractionSafeCallback",
    "TestMenuUtils",
    "TestNodeCreationController",
    "TestStageLifecycleController",
]
