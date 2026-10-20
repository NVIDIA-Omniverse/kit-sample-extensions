from unittest.mock import MagicMock, patch

from ...scripts.commands.impl.isolation import MaterialGraph_IsolationModelRemoveCommand
from ...scripts.models.graph.isolation import MaterialGraphIsolationModel
from .base import CommandsTestBase

# pylint: disable=relative-beyond-top-level


class TestIsolationCommand(CommandsTestBase):
    """MaterialGraph_IsolationModelRemoveCommand removes input/output nodes from the isolation model
    and supports undo (re-add placeholder). We test both input and output removal and that undo
    calls add_input_or_output and refresh."""

    async def test_remove_input_branch(self) -> None:
        """Remove input branch; undo re-adds and refreshes."""

        # Patch MaterialGraphIsolationModel.InputNode so we use a dummy with removable input.
        class DummyInputNode:
            """Dummy input node with a removable input."""

            def __init__(self) -> None:
                """Initialize with a test position."""
                self.position = (1, 2)
                self.removed = False

            def remove_input(self) -> None:
                """Record removal of the input node."""
                self.removed = True

        class DummyIsolationModel:
            """Dummy isolation model for input removal."""

            def __init__(self) -> None:
                """Initialize tracking fields."""
                self.added = None
                self.refreshed = False

            def remove_input(self) -> None:
                """Placeholder for input removal."""
                pass

            def add_input_or_output(self, position: tuple[int, int], is_input: bool) -> None:
                """Record a re-added input/output placeholder."""
                self.added = (position, is_input)

            def refresh(self) -> None:
                """Record a refresh request."""
                self.refreshed = True

        node = DummyInputNode()
        isolation_model = DummyIsolationModel()

        with patch.object(MaterialGraphIsolationModel, "InputNode", DummyInputNode):
            cmd = MaterialGraph_IsolationModelRemoveCommand(isolation_model, node, graph_model=None)
            self.assertTrue(cmd.do())
            self.assertTrue(node.removed)
            cmd.undo()
            self.assertEqual(isolation_model.added, ((1, 2), True))
            self.assertTrue(isolation_model.refreshed)

    async def test_remove_output_branch(self) -> None:
        """Remove output branch; undo re-adds and refreshes."""

        class DummyNode:
            """Dummy output node with a removable output."""

            def __init__(self) -> None:
                """Initialize with a test position."""
                self.position = (3, 4)
                self.removed = False

            def remove_output(self) -> None:
                """Record removal of the output node."""
                self.removed = True

        class DummyIsolationModel:
            """Dummy isolation model for output removal."""

            def __init__(self) -> None:
                """Initialize tracking fields."""
                self.added = None
                self.refreshed = False

            def remove_output(self) -> None:
                """Placeholder for output removal."""
                pass

            def add_input_or_output(self, position: tuple[int, int], is_input: bool) -> None:
                """Record a re-added input/output placeholder."""
                self.added = (position, is_input)

            def refresh(self) -> None:
                """Record a refresh request."""
                self.refreshed = True

        node = DummyNode()
        isolation_model = DummyIsolationModel()
        cmd = MaterialGraph_IsolationModelRemoveCommand(isolation_model, node, graph_model=None)
        cmd.do()
        self.assertTrue(node.removed)
        cmd.undo()
        self.assertEqual(isolation_model.added, ((3, 4), False))
        self.assertTrue(isolation_model.refreshed)

    async def test_node_failure_does_not_remove_isolation_cache(self) -> None:
        """A failed persisted-position removal must leave the visible isolation node intact."""
        node = MagicMock(position=(5, 6), remove_input=MagicMock(return_value=False))
        isolation_model = MagicMock()

        class DummyInputNode:
            pass

        with patch.object(MaterialGraphIsolationModel, "InputNode", DummyInputNode):
            cmd = MaterialGraph_IsolationModelRemoveCommand(isolation_model, node, graph_model=None)
            cmd._is_input = True
            self.assertFalse(cmd.do())

        isolation_model.remove_input.assert_not_called()
