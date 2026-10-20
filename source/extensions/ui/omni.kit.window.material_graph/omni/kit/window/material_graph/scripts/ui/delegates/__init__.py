"""Graph delegate package providing style and menu coordination hooks.

The C++ GraphCanvasWidget handles all node rendering natively. This package
provides a minimal delegate that satisfies the GraphEditorCoreWidget constructor
requirement and supplies get_style() for UI styling.
"""

from .node import MaterialGraphNodeDelegate
