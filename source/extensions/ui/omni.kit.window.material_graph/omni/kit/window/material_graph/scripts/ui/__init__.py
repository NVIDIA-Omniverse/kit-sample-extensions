"""UI entry package for window-level Material Graph presentation.

This package exports the top-level graph window object that hosts the editor
widget tree, docking behavior, and visibility lifecycle integration with Kit.

Lower-level UI concerns (catalog, controllers, delegates, interactions) live in
subpackages; this root serves as the window-facing assembly boundary.

Typical consumers: extension lifecycle code that creates the graph window and
tests that exercise top-level window behaviors.
"""

from .window import GraphWindow
