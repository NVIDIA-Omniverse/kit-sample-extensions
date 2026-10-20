"""Stage-backed graph model package for USD/UsdShade editing.

Graph models map live USD entities to graph-widget concepts:
- prim models represent material/shader/nodegraph/backdrop prims,
- attribute models represent input/output properties and their connections,
- isolation models project focused subgraphs for local editing workflows.

This package is necessary because graph UI components expect rich item models
(name/type/ports/style/interaction hooks), while USD provides low-level schema
objects that are not directly suitable as widget items.

Typical consumers: graph widget/view/delegate layers plus controllers that read
or mutate graph state through model APIs instead of direct USD calls.
"""

from .isolation import MaterialGraphIsolationModel
from .nodes import MaterialModel, PrimModel
from .ports import OutputAttributeModel
