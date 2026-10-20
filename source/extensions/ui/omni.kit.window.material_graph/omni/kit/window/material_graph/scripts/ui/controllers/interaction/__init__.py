"""Interaction controllers for graph events and node creation.

This package provides controllers that handle graph interaction events
(InteractionController: double-click, right-click, context menus) and
node creation from catalog items (NodeCreationController). These
controllers translate user input into model updates and command calls.

Architectural role: Interaction controllers sit between the graph widget
event handlers and the catalog/model/command layers. They centralize
interaction logic for testability and reuse.

Typical consumers: GraphWidget composition, graph section setup, and
tests that verify double-click navigation and context-menu behavior.
"""

from .events import InteractionController
from .node_creation import NodeCreationController

__all__ = [
    "InteractionController",
    "NodeCreationController",
]
