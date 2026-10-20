"""Tests for the data and graph models used by the material graph window.

This module tests the model layer: attribute connections and undo (TestAttributeConnectionsUndo),
attribute group caching (TestAttributeGroupCaching), catalog items and trees for textures and
nodegraphs (TestCatalogItems, TestCatalogTreeTextures, TestCatalogTreeNodeGraphs), compound
registry and compound source (TestCompoundRegistry, TestCompoundSource), connection traversal
(TestConnectionTraversal), expansion state (TestExpansionState),
isolation model for input/output nodes (TestIsolationModel), model helpers and validity
(TestModelHelpers, TestModelValidity), nodegraph backdrop cache and sync helpers (TestNodeGraphBackdropCache,
TestNodegraphSyncHelpers), selection helper (TestSelectionHelper), stage listener (TestStageListener),
texture registry (TestTextureRegistry), schema attributes and prim ports/UI state (TestSchemaAttributes,
TestPrimPorts, TestPrimUiState), group item (TestGroupItem), backdrop stacking calculator
(TestBackdropStackingCalculator), and nodegraph child resolver (TestNodeGraphChildResolver). We
test these because the models are the source of truth for what is shown in the graph and catalog;
broken models would show wrong nodes, wrong connections, or fail to sync with USD."""

from .test_attribute_connections_rejection_logic import TestAttributeConnectionsRejectionLogic  # noqa: F401
from .test_attribute_connections_undo import TestAttributeConnectionsUndo  # noqa: F401
from .test_attribute_group_caching import TestAttributeGroupCaching  # noqa: F401
from .test_backdrop_stacking_calculator import TestBackdropStackingCalculator  # noqa: F401
from .test_catalog_items import TestCatalogItems  # noqa: F401
from .test_catalog_tree_nodegraphs import TestCatalogTreeNodeGraphs  # noqa: F401
from .test_catalog_tree_textures import TestCatalogTreeTextures  # noqa: F401
from .test_compound_registry import TestCompoundRegistry  # noqa: F401
from .test_compound_source import TestCompoundSource  # noqa: F401
from .test_connection_traversal import TestConnectionTraversal  # noqa: F401
from .test_expansion_state import TestExpansionState  # noqa: F401
from .test_group_item import TestGroupItem  # noqa: F401
from .test_input_node_view import TestInputNodeViewModel  # noqa: F401
from .test_isolation_model import TestIsolationModel  # noqa: F401
from .test_model_helpers import TestModelHelpers  # noqa: F401
from .test_model_validity import TestModelValidity  # noqa: F401
from .test_nodegraph_backdrop_cache import TestNodeGraphBackdropCache  # noqa: F401
from .test_nodegraph_child_resolver import TestNodeGraphChildResolver  # noqa: F401
from .test_nodegraph_model_position import TestNodeGraphModelPosition  # noqa: F401
from .test_nodegraph_move_transaction import TestNodeGraphMoveTransaction  # noqa: F401
from .test_nodegraph_sync_helpers import TestNodegraphSyncHelpers  # noqa: F401
from .test_output_attribute_model import TestOutputAttributeModel  # noqa: F401
from .test_prim_ports import TestPrimPorts  # noqa: F401
from .test_prim_ui_state import TestPrimUiState  # noqa: F401
from .test_quicksearch_model import TestQuickSearchModel  # noqa: F401
from .test_schema_attributes import TestSchemaAttributes  # noqa: F401
from .test_selection_helper import TestSelectionHelper  # noqa: F401
from .test_stage_listener import TestStageListener  # noqa: F401
from .test_texture_registry import TestTextureRegistry  # noqa: F401

__all__ = [
    "TestAttributeConnectionsUndo",
    "TestAttributeConnectionsRejectionLogic",
    "TestAttributeGroupCaching",
    "TestCatalogItems",
    "TestCatalogTreeTextures",
    "TestCatalogTreeNodeGraphs",
    "TestCompoundRegistry",
    "TestConnectionTraversal",
    "TestExpansionState",
    "TestIsolationModel",
    "TestModelHelpers",
    "TestModelValidity",
    "TestNodeGraphBackdropCache",
    "TestNodeGraphMoveTransaction",
    "TestNodegraphSyncHelpers",
    "TestSelectionHelper",
    "TestStageListener",
    "TestTextureRegistry",
    "TestSchemaAttributes",
    "TestPrimPorts",
    "TestPrimUiState",
    "TestQuickSearchModel",
    "TestCompoundSource",
    "TestGroupItem",
    "TestInputNodeViewModel",
    "TestBackdropStackingCalculator",
    "TestNodeGraphChildResolver",
    "TestNodeGraphModelPosition",
    "TestOutputAttributeModel",
]
