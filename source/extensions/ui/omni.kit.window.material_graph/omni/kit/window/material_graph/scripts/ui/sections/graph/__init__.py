"""Graph section components: canvas widget and breadcrumb navigation.

This package provides the main graph canvas (GraphWidget) and breadcrumb bar
(MaterialGraphBreadcrumbs) used for compound navigation. The graph section
hosts the nodegraph view, delegates, drop handlers, and context controllers.

Architectural role: The graph section is the central editing surface; it
integrates the Kit graph widget with material-graph-specific delegates,
mixins, and interaction handlers.

Typical consumers: Sections package assembly, GraphWindow, and tests that
exercise graph interaction and compound navigation.
"""

from .breadcrumbs import MaterialGraphBreadcrumbs
from .widget import GraphWidget

__all__ = ["GraphWidget", "MaterialGraphBreadcrumbs"]
