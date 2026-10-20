"""Core UI controllers for Material Graph window behavior.

This package hosts controllers that manage the graph window's core lifecycle
and state: context switching, stage events, graph settings, startup wiring,
and nodegraph export. These controllers are composed into the main GraphWidget
and coordinate with the USD stage, catalog model, and toolbar.

Architectural role: Core controllers sit between the window/widget layer and
domain services (commands, models, settings). They translate user actions and
stage events into model updates and command invocations.

Typical consumers: GraphWidget composition, extension startup, and tests that
exercise context switching, stage lifecycle, or export flows.
"""

from .context_model import ContextModelController
from .context_solo import ContextSoloController
from .context_switcher import ContextSwitcherController
from .context_visibility import ContextVisibilityController
from .graph_settings import GraphSettingsController
from .nodegraph_export import NodeGraphExportController
from .stage_lifecycle import StageLifecycleController
from .startup import StartupController

__all__ = [
    "ContextModelController",
    "ContextSoloController",
    "ContextSwitcherController",
    "ContextVisibilityController",
    "GraphSettingsController",
    "NodeGraphExportController",
    "StageLifecycleController",
    "StartupController",
]
