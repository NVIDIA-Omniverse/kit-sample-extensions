"""Toolbar section components for actions and menus.

This package provides the toolbar controller (ToolbarController), action
registry (ToolbarActionRegistry), and menu builder (ToolbarMenuBuilder)
used by the Material Graph window toolbar. The toolbar hosts window-level
actions (new material, export, etc.) and submenus.

Architectural role: Toolbar components sit between the window and
action/command layers. They register actions with Kit and build
menu structures from the action registry.

Typical consumers: GraphWindow composition, extension startup, and
tests that verify toolbar actions.
"""

from .actions import ToolbarActionRegistry
from .controller import ToolbarController
from .menus import ToolbarMenuBuilder

__all__ = [
    "ToolbarActionRegistry",
    "ToolbarController",
    "ToolbarMenuBuilder",
]
