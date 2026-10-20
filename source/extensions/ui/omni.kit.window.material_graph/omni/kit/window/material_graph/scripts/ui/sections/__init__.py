"""Major UI sections that compose the Material Graph window.

This package exports the primary visual sections: the graph canvas (GraphWidget)
and breadcrumb navigation (MaterialGraphBreadcrumbs). These sections are
assembled by the window and receive controllers for interaction and state.

Architectural role: Sections are the main UI building blocks; they host
delegates, controllers, and sub-widgets. The graph section is the central
canvas; toolbar and catalog are composed alongside it.

Typical consumers: GraphWindow assembly, layout tests, and integration tests
that verify section visibility and composition.
"""

from .graph import GraphWidget, MaterialGraphBreadcrumbs

__all__ = ["GraphWidget", "MaterialGraphBreadcrumbs"]
