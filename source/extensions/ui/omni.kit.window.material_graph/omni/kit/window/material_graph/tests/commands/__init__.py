"""Tests for material graph commands and their wrapper layer.

This module tests all Material Graph commands and the wrappers that call them: connections (connect/
disconnect/remove), ports, compound import and compound commands, group/ungroup nodegraph,
material and shader node creation, nodegraph creation, rename property, isolation model remove,
command registry (register/unregister with omni.kit.commands), command utilities, and edge cases
(undo with missing dest, rename no-op). We test these because commands drive USD mutations and
undo/redo; broken commands would corrupt the stage or break the graph UX. Wrappers are tested
so that callers can rely on a stable, result-typed API."""

from .test_command_edge_cases import TestCommandEdgeCases  # noqa: F401
from .test_command_registry import TestCommandRegistry  # noqa: F401
from .test_command_utils import TestCommandUtils  # noqa: F401
from .test_compound_commands import TestCompoundCommands  # noqa: F401
from .test_compound_import_position import TestCompoundImportPosition  # noqa: F401
from .test_connect_polymorphic_command import TestPolymorphicConnectCommand  # noqa: F401
from .test_connections_command import TestConnectionsCommand  # noqa: F401
from .test_group_nodegraph_command import TestGroupNodeGraphCommand  # noqa: F401
from .test_isolation_command import TestIsolationCommand  # noqa: F401
from .test_material_command import TestMaterialCommand  # noqa: F401
from .test_node_commands import TestNodeCommands  # noqa: F401
from .test_nodegraph_command import TestNodeGraphCommand  # noqa: F401
from .test_ports_command import TestPortsCommand  # noqa: F401
from .test_rename_property_command import TestRenamePropertyCommand  # noqa: F401
from .test_solo_command import TestSoloCommand  # noqa: F401
from .test_wrappers import TestCommandWrappers  # noqa: F401
