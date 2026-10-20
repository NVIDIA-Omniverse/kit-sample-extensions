"""Controller package that orchestrates Material Graph UI behavior.

Controllers in this package separate interaction logic from widget rendering.
They coordinate context switching, node creation/drop flows, stage lifecycle
events, toolbar actions, startup wiring, visibility rules, and menu systems.

This architecture keeps `GraphWidget` composition-oriented and testable while
placing mutable behavior/state machines in focused controller classes.

Typical consumers: `GraphWidget` composition/bootstrap code and startup flows
that instantiate coordinated controller sets.
"""

from ..sections.toolbar.controller import ToolbarController
from .catalog.context_menu import CatalogContextMenuController
from .catalog.visibility import CatalogController
from .core.context_model import ContextModelController
from .core.context_solo import ContextSoloController
from .core.context_switcher import ContextSwitcherController
from .core.context_visibility import ContextVisibilityController
from .core.graph_settings import GraphSettingsController
from .core.nodegraph_export import NodeGraphExportController
from .core.stage_lifecycle import StageLifecycleController
from .core.startup import StartupController
from .interaction.events import InteractionController
from .interaction.node_creation import NodeCreationController
from .overlay import (
    CatalogDropOverlayController,
    GraphBackgroundDropIndicatorController,
)

__all__ = [
    "CatalogController",
    "CatalogContextMenuController",
    "CatalogDropOverlayController",
    "ContextModelController",
    "ContextSoloController",
    "ContextSwitcherController",
    "ContextVisibilityController",
    "GraphBackgroundDropIndicatorController",
    "GraphSettingsController",
    "InteractionController",
    "NodeCreationController",
    "NodeGraphExportController",
    "StageLifecycleController",
    "StartupController",
    "ToolbarController",
]
