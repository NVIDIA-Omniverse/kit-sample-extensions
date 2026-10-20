from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import omni.kit.test
from pxr import Sdf

from ...scripts.config.paths import Paths
from ...scripts.models.graph.nodes.nodegraph import NodeGraphModel
from ...scripts.models.graph.nodes.nodegraph.position import PositionItemResolver, PositionMoveTransaction
from ...scripts.models.graph.nodes.nodegraph.position import resolver as position_resolver_module
from ...scripts.models.graph.nodes.nodegraph.position import transaction as position_transaction_module
from ...scripts.models.graph.nodes.prim.model import PrimModel
from ...scripts.models.graph.ports import (
    AttributeModel,
    InputAttributeGroupModel,
    InputAttributeModel,
    OutputAttributeGroupModel,
    OutputAttributeModel,
)


class _FakePrim(PrimModel):
    pass


class TestNodeGraphMoveTransaction(omni.kit.test.AsyncTestCase):
    """Coverage for staged move lifecycle and commit routing in NodeGraphModel.

    These tests protect the drag-transaction behavior introduced for node moves:
    - begin/end lifecycle must correctly open/close staged transactions,
    - staged values must commit in one undo group,
    - PrimModel and IO AttributeModel items must route through the correct
      serialization path (attribute vs context metadata).

    The suite is intentionally narrow and mocks external graph/runtime services,
    so regressions in transaction ownership, routing, or undo grouping are
    caught quickly without full UI interaction.
    """

    @staticmethod
    def _make_txn(**overrides):
        """Create a transaction stub aligned with PositionMoveTransaction API."""
        txn = SimpleNamespace(
            is_staging=False,
            is_committing=False,
            has_any_io_entries=MagicMock(return_value=False),
            begin=MagicMock(),
            commit=MagicMock(),
            force_commit=MagicMock(return_value=False),
        )
        for key, value in overrides.items():
            setattr(txn, key, value)
        return txn

    @staticmethod
    def _make_model() -> NodeGraphModel:
        """Create a minimal NodeGraphModel fixture for isolated unit tests."""
        # Keep fixture small and deterministic; tests focus on transaction logic
        # instead of full graph wiring or USD stage behavior.
        model = NodeGraphModel.__new__(NodeGraphModel)
        model.INPUT = "input"
        model.OUTPUT = "output"
        model._prim_path = "/World/NodeGraph"
        model._input_output_position = [None, None]
        model._position_txn = TestNodeGraphMoveTransaction._make_txn()
        model._selected_items = []
        model._suppress_next_none_item_changed = False
        model._position_only_sync_skip_items = {}
        model._position_only_view_items = {}
        model._position_only_validation_items = {}
        model._connection_only_sync_skip_items = {}
        model._skip_next_activation_sync = False
        model._synced_once = False
        model._parent = SimpleNamespace(model_root=MagicMock())
        model.set_position_cmd = MagicMock()
        model.remove_position_cmd = MagicMock()
        model._position_item_resolver = SimpleNamespace(
            normalize_moving_item=lambda item: item,
            resolve_io_attribute_item=lambda item: item,
            resolve_concrete_position_item=lambda item: item,
        )
        model._normalize_moving_item = lambda item: item
        model._get_selected_moving_items = lambda _drive: []
        model.batch_position_begin_edit = MagicMock()
        model.batch_position_end_edit = MagicMock()
        return model

    @staticmethod
    def _make_io_item(item_cls):
        """Create a lightweight IO attribute model with a fixed prim path."""
        item = item_cls.__new__(item_cls)
        item._prim_path = "/World/NodeGraph"
        return item

    @staticmethod
    def _make_fake_prim() -> _FakePrim:
        """Create a lightweight PrimModel-like object for staged apply tests."""
        # This fake item is enough to exercise PrimModel position serialization
        # via the staged apply path without requiring a real prim.
        item = _FakePrim.__new__(_FakePrim)
        item._ui_state = SimpleNamespace(position=(0.0, 0.0))
        item._prim_path = "/World/Fake"
        item._parent = SimpleNamespace(model_root=MagicMock())
        item.set_position_cmd = MagicMock()
        item.remove_position_cmd = MagicMock()
        return item

    async def test_begin_edit_commits_stale_transaction_first(self) -> None:
        """Begin-edit should force-commit stale staged transaction before reentry."""
        # Drag reentry can happen when a prior end-edit callback is missed.
        # We require a best-effort commit before opening a new transaction.
        model = self._make_model()
        model._position_txn = self._make_txn(is_staging=True, begin=MagicMock())
        model._force_commit_staged_positions = MagicMock()

        model.position_begin_edit("drive")

        model._force_commit_staged_positions.assert_called_once_with()
        model._position_txn.begin.assert_called_once()
        model.batch_position_begin_edit.assert_called_once_with("drive")
        self.assertTrue(model._position_txn.begin.called)

    async def test_end_edit_commits_staged_positions_and_clears_txn(self) -> None:
        """End-edit should commit staged values and clear active transaction state."""
        # End-edit is the transaction boundary where staged values become
        # serialized; active state must be reset afterward.
        model = self._make_model()
        model._position_txn = self._make_txn(is_staging=True)
        model._commit_staged_positions = MagicMock()

        model.position_end_edit("drive")

        model._commit_staged_positions.assert_called_once()
        model.batch_position_end_edit.assert_called_once_with("drive")
        self.assertTrue(model._commit_staged_positions.called)

    async def test_force_commit_resets_state_when_enabled(self) -> None:
        """Force-commit should flush pending staged values and reset txn state."""
        # Lifecycle boundaries (destroy/deactivate/pause) call force-commit;
        # this guard ensures no staged positions leak past those boundaries.
        model = self._make_model()
        model._position_txn = self._make_txn(force_commit=MagicMock(return_value=True))

        model._force_commit_staged_positions()

        model._position_txn.force_commit.assert_called_once_with(model._apply_staged_position)

    async def test_apply_staged_position_uses_prim_serializer_path(self) -> None:
        """Staged prim positions should route through PrimModel serialization."""
        # Prim-backed nodes must use the PrimModel position path so USD attrs and
        # model notifications stay consistent with non-staged writes.
        model = self._make_model()
        item = self._make_fake_prim()

        model._apply_staged_position(item, (3.0, 4.0))

        item.set_position_cmd.assert_called_once()
        self.assertEqual(item._ui_state.position, (3.0, 4.0))
        item._parent.model_root.notify_position_changed.assert_called_once_with(item)
        item._parent.model_root._item_changed.assert_not_called()

    async def test_apply_staged_position_for_input_routes_context_suffix(self) -> None:
        """Input AttributeModel staged writes should use input context suffix."""
        # Input/output nodes persist position in context customData, so staged
        # commit must select the correct suffix for metadata keys.
        model = self._make_model()
        input_item = InputAttributeModel.__new__(InputAttributeModel)
        model._input_output_position = [None, None]

        model._apply_staged_position(input_item, (10.0, 20.0))

        self.assertEqual(model._input_output_position[0], (10.0, 20.0))
        model.set_position_cmd.assert_called_once_with((10.0, 20.0), model.INPUT)
        model._parent.model_root._item_changed.assert_not_called()

    async def test_apply_staged_position_for_output_routes_context_suffix(self) -> None:
        """Output AttributeModel staged writes should use output context suffix."""
        # Mirrors input-branch routing to prevent output-node regressions.
        model = self._make_model()
        output_item = OutputAttributeModel.__new__(OutputAttributeModel)
        model._input_output_position = [None, None]

        model._apply_staged_position(output_item, (30.0, 40.0))

        self.assertEqual(model._input_output_position[1], (30.0, 40.0))
        model.set_position_cmd.assert_called_once_with((30.0, 40.0), model.OUTPUT)
        model._parent.model_root._item_changed.assert_not_called()

    async def test_commit_staged_positions_wraps_undo_group_once(self) -> None:
        """Commit should apply staged values inside one undo group."""
        # One drag operation must be undoable in a single step.
        model = self._make_model()
        model._position_txn = self._make_txn(commit=MagicMock())
        ctx = MagicMock()
        ctx.__enter__.return_value = None
        ctx.__exit__.return_value = False

        with patch(
            f"{Paths.MODULE_ID}.scripts.models.graph.nodes.nodegraph.model.omni.kit.undo.group",
            return_value=ctx,
        ) as undo_group:
            model._commit_staged_positions()

        undo_group.assert_called_once()
        model._position_txn.commit.assert_called_once_with(model._apply_staged_position)

    async def test_staging_io_item_change_skips_base_self_sync(self) -> None:
        """Staged root IO updates should bypass expensive base self-sync callback."""
        model = self._make_model()
        model._position_txn.is_staging = True
        io_item = self._make_io_item(InputAttributeModel)

        with patch.object(PrimModel, "_on_item_changed_cb", autospec=True) as base_callback:
            model._on_item_changed_cb(io_item)

        base_callback.assert_not_called()

    async def test_non_staging_or_non_io_item_change_calls_base_callback(self) -> None:
        """Non-IO or non-staging updates should continue using base callback routing."""
        model = self._make_model()
        non_io_item = object()

        with patch.object(PrimModel, "_on_item_changed_cb", autospec=True) as base_callback:
            model._on_item_changed_cb(non_io_item)

        base_callback.assert_called_once_with(model, non_io_item)

    async def test_position_only_item_change_skips_base_callback_once(self) -> None:
        """Position-only notifications should update observers without full self-sync."""
        model = self._make_model()
        item = object()
        model._position_only_sync_skip_items[id(item)] = item

        with patch.object(PrimModel, "_on_item_changed_cb", autospec=True) as base_callback:
            model._on_item_changed_cb(item)
            model._on_item_changed_cb(item)

        base_callback.assert_called_once_with(model, item)

    async def test_position_only_notification_has_independent_view_and_validation_consumers(self) -> None:
        """Canvas and validation should each consume a position marker without racing."""
        model = self._make_model()
        model._item_changed = MagicMock()
        item = object()

        model.notify_position_changed(item)

        model._item_changed.assert_called_once_with(item)
        self.assertTrue(model.consume_position_only_changed(item))
        self.assertFalse(model.consume_position_only_changed(item))
        self.assertTrue(model.consume_position_only_validation_changed(item))
        self.assertFalse(model.consume_position_only_validation_changed(item))

    async def test_connection_only_item_change_skips_base_callback_once(self) -> None:
        """Connection-only notifications should avoid full graph self-sync."""
        model = self._make_model()
        item = object()
        model._connection_only_sync_skip_items[id(item)] = item

        with patch.object(PrimModel, "_on_item_changed_cb", autospec=True) as base_callback:
            model._on_item_changed_cb(item)
            model._on_item_changed_cb(item)

        base_callback.assert_called_once_with(model, item)

    async def test_connection_only_notification_marks_and_notifies_item(self) -> None:
        """Connection-only notification should fan out item-specific changes."""
        model = self._make_model()
        model._item_changed = MagicMock()
        item = object()

        model.notify_connection_changed(item)

        model._item_changed.assert_called_once_with(item)
        self.assertIs(model._connection_only_sync_skip_items[id(item)], item)

    async def test_one_shot_none_item_change_after_io_commit_is_suppressed(self) -> None:
        """One immediate None callback after IO commit should skip base sync once."""
        model = self._make_model()
        model._suppress_next_none_item_changed = True

        with patch.object(PrimModel, "_on_item_changed_cb", autospec=True) as base_callback:
            model._on_item_changed_cb(None)
            model._on_item_changed_cb(None)

        base_callback.assert_called_once_with(model, None)

    async def test_staging_io_group_item_change_skips_base_self_sync(self) -> None:
        """Staged grouped-IO updates should bypass expensive base self-sync callback."""
        model = self._make_model()
        model._position_txn.is_staging = True
        group_item = InputAttributeGroupModel.__new__(InputAttributeGroupModel)
        group_item._prim_path = "/World/NodeGraph"

        with patch.object(PrimModel, "_on_item_changed_cb", autospec=True) as base_callback:
            model._on_item_changed_cb(group_item)

        base_callback.assert_not_called()

    async def test_staging_output_io_group_item_change_skips_base_self_sync(self) -> None:
        """Staged grouped output-IO updates should bypass expensive base callback."""
        model = self._make_model()
        model._position_txn.is_staging = True
        group_item = OutputAttributeGroupModel.__new__(OutputAttributeGroupModel)
        group_item._prim_path = "/World/NodeGraph"

        with patch.object(PrimModel, "_on_item_changed_cb", autospec=True) as base_callback:
            model._on_item_changed_cb(group_item)

        base_callback.assert_not_called()

    async def test_staging_io_group_with_different_prim_path_calls_base_callback(self) -> None:
        """Staged grouped-IO updates for another prim must keep base callback routing."""
        model = self._make_model()
        model._position_txn.is_staging = True
        group_item = InputAttributeGroupModel.__new__(InputAttributeGroupModel)
        group_item._prim_path = "/World/OtherNodeGraph"

        with patch.object(PrimModel, "_on_item_changed_cb", autospec=True) as base_callback:
            model._on_item_changed_cb(group_item)

        base_callback.assert_called_once_with(model, group_item)

    async def test_non_staging_io_group_item_change_calls_base_callback(self) -> None:
        """Non-staging grouped-IO updates should continue base callback routing."""
        model = self._make_model()
        model._position_txn.is_staging = False
        group_item = InputAttributeGroupModel.__new__(InputAttributeGroupModel)
        group_item._prim_path = "/World/NodeGraph"

        with patch.object(PrimModel, "_on_item_changed_cb", autospec=True) as base_callback:
            model._on_item_changed_cb(group_item)

        base_callback.assert_called_once_with(model, group_item)

    async def test_get_selected_nodes_ignores_transient_when_prim_selection_exists(self) -> None:
        """Transient IO-style selections should not persist when a prim is selected."""
        model = self._make_model()
        prim_selected = _FakePrim.__new__(_FakePrim)
        transient_selected = object()
        model._selection_adapter = SimpleNamespace(get_selected_nodes=MagicMock(return_value=[prim_selected]))
        model._stage = object()
        model.get_item_model = MagicMock()
        model._selected_items = [transient_selected]

        selected = model._get_selected_nodes()

        self.assertEqual(selected, [prim_selected])

    async def test_get_selected_nodes_uses_transient_when_no_prim_selection_exists(self) -> None:
        """Transient selections remain available when USD selection is empty."""
        model = self._make_model()
        transient_selected = object()
        stale_prim = _FakePrim.__new__(_FakePrim)
        model._selection_adapter = SimpleNamespace(get_selected_nodes=MagicMock(return_value=[]))
        model._stage = object()
        model.get_item_model = MagicMock()
        model._selected_items = [stale_prim, transient_selected]

        selected = model._get_selected_nodes()

        self.assertEqual(selected, [transient_selected])

    async def test_position_transaction_keys_and_io_detection(self) -> None:
        """Transaction keys distinguish prims, IO wrappers, typed proxies, and anonymous items."""

        class DummyPrim:
            def __init__(self, path="/Prim", position=(1, 2)):
                self.prim_path = path
                self.position = position

        class DummyInput:
            def __init__(self, path="/Prim", position=(1, 2)):
                self.prim_path = path
                self.position = position

        class DummyOutput:
            def __init__(self, path="/Prim", position=(1, 2)):
                self.prim_path = path
                self.position = position

        class TypedProxy(DummyPrim):
            @staticmethod
            def get_type_name():
                return "TypedProxy"

        with patch.multiple(
            position_transaction_module,
            PrimModel=DummyPrim,
            InputAttributeModel=DummyInput,
            OutputAttributeModel=DummyOutput,
        ):
            transaction = PositionMoveTransaction()
            self.assertEqual(transaction._get_item_path(None), "__none__")
            self.assertTrue(transaction._get_item_path(object()).startswith("__item__:"))
            self.assertEqual(transaction._get_item_path(DummyPrim()), "/Prim")
            self.assertEqual(transaction._get_item_path(DummyInput()), "/Prim:InputNode")
            self.assertEqual(transaction._get_item_path(DummyOutput()), "/Prim:OutputNode")
            self.assertEqual(transaction._get_item_path(TypedProxy()), "/Prim")

            transaction.begin([DummyInput(), DummyOutput()])
            self.assertTrue(transaction.is_staging)
            self.assertTrue(transaction.has_any_io_entries())
            self.assertIsNone(transaction._get_io_entry_key_for_prim_path("/Prim"))
            self.assertEqual(transaction._io_key("/Prim", False), "/Prim:InputNode")
            self.assertEqual(transaction._io_key("/Prim", True), "/Prim:OutputNode")

    async def test_position_transaction_stages_remaps_and_applies_changes(self) -> None:
        """Staged positions support lazy insertion, IO-owner remapping, and callable/direct apply paths."""

        class DummyPrim:
            def __init__(self, path, position):
                self.prim_path = path
                self.position = position

        class DummyInput:
            def __init__(self, path, position):
                self.prim_path = path
                self.position = position

        class DummyOutput:
            def __init__(self, path, position):
                self.prim_path = path
                self.position = position

        with patch.multiple(
            position_transaction_module,
            PrimModel=DummyPrim,
            InputAttributeModel=DummyInput,
            OutputAttributeModel=DummyOutput,
        ):
            io_item = DummyInput("/Graph", None)
            prim_proxy = DummyPrim("/Graph", (3, 4))
            unchanged = DummyPrim("/Still", (5, 6))
            transaction = PositionMoveTransaction()
            transaction.begin([io_item, unchanged, None])

            self.assertIsNone(transaction.get_position(None))
            self.assertIsNone(transaction.get_position(io_item))
            self.assertEqual(transaction.get_position(prim_proxy), (3, 4))
            transaction.set_position(prim_proxy, (10, 20))
            self.assertEqual(transaction.get_position(io_item), (10, 20))
            self.assertIs(transaction._cache["/Graph:InputNode"]["item"], io_item)

            inserted = DummyPrim("/Inserted", None)
            transaction.set_position(inserted, (7, 8))
            self.assertEqual(transaction._cache["/Inserted"]["start"], (7, 8))
            self.assertEqual(transaction.get_position(inserted), (7, 8))

            applied = []
            transaction.apply(lambda item, value: applied.append((item, value)))
            self.assertFalse(transaction.is_staging)
            self.assertEqual(applied, [(io_item, (10, 20))])
            self.assertEqual(transaction._cache, {})

            inserted.position = (7, 8)
            transaction.begin([inserted])
            transaction.set_position(inserted, (9, 10))
            transaction.apply()
            self.assertEqual(inserted.position, (9, 10))

    async def test_position_transaction_commit_and_force_commit_are_exception_safe(self) -> None:
        """Commit flags clear after callback errors and force_commit reports whether work ran."""
        item = SimpleNamespace(prim_path="/Item", position=(0, 0))
        transaction = PositionMoveTransaction()
        self.assertFalse(transaction.force_commit())
        transaction.commit()

        transaction.begin([item])
        transaction.set_position(item, (1, 1))

        def fail_apply(_item, _position):
            raise RuntimeError("injected")

        with self.assertRaises(RuntimeError):
            transaction.commit(fail_apply)
        self.assertFalse(transaction.is_committing)
        self.assertFalse(transaction.is_staging)

        transaction.begin([item])
        transaction.set_position(item, (2, 2))
        self.assertTrue(transaction.force_commit())
        self.assertEqual(item.position, (2, 2))

    async def test_position_resolver_identifies_io_wrappers_and_contains_type_errors(self) -> None:
        """IO identification accepts known wrappers and contains broken type-name providers."""

        class InputNode:
            @staticmethod
            def get_type_name():
                return "InputNode"

        class OutputNode:
            @staticmethod
            def get_type_name():
                return "OutputNode"

        class BrokenNode:
            @staticmethod
            def get_type_name():
                raise RuntimeError("broken")

        self.assertFalse(PositionItemResolver.is_input_output_node_item(None))
        self.assertFalse(PositionItemResolver.is_input_output_node_item(object()))
        self.assertTrue(PositionItemResolver.is_input_output_node_item(InputNode()))
        self.assertTrue(PositionItemResolver.is_input_output_node_item(OutputNode()))
        self.assertFalse(PositionItemResolver.is_input_output_node_item(BrokenNode()))

    async def test_position_resolver_walks_proxy_graphs_and_breaks_cycles(self) -> None:
        """Attribute resolution traverses source/model/path/port wrappers without looping."""

        class DummyAttribute:
            pass

        class DummyInput(DummyAttribute):
            pass

        class DummyOutput(DummyAttribute):
            pass

        class DummyPrim:
            pass

        class DummyEmpty:
            pass

        class InputNode:
            @staticmethod
            def get_type_name():
                return "InputNode"

            def __init__(self, ports=None):
                self.ports = ports or []

        leaf = DummyInput()
        path = Sdf.Path("/Graph.inputs:test")
        by_path = SimpleNamespace(path=path)
        by_get_path = SimpleNamespace(GetPath=lambda: path)
        nested = SimpleNamespace(source=SimpleNamespace(ports=[by_path]))
        cyclic = SimpleNamespace()
        cyclic.source = cyclic

        class Model:
            def __getitem__(self, item):
                if isinstance(item, InputNode):
                    return SimpleNamespace(ports=[nested, by_get_path, cyclic])
                raise KeyError(item)

            @staticmethod
            def get_item_model(candidate):
                return leaf if candidate == path else None

        with patch.multiple(
            position_resolver_module,
            AttributeModel=DummyAttribute,
            InputAttributeModel=DummyInput,
            OutputAttributeModel=DummyOutput,
            PrimModel=DummyPrim,
            IsolationGraphModel=SimpleNamespace(EmptyPort=DummyEmpty),
        ):
            resolver = PositionItemResolver(Model())
            self.assertIsNone(resolver.resolve_io_attribute_item(object()))
            self.assertIs(resolver.resolve_io_attribute_item(InputNode()), leaf)
            self.assertIsNone(resolver._resolve_attribute_candidate(None, DummyInput, set()))
            self.assertIsNone(resolver._resolve_attribute_candidate(DummyEmpty(), DummyInput, set()))
            self.assertIsNone(resolver._resolve_attribute_candidate(cyclic, DummyInput, set()))
            self.assertIs(
                resolver._resolve_attribute_candidate(SimpleNamespace(prim_model=leaf), DummyInput, set()), leaf
            )

    async def test_position_resolver_contains_model_and_get_path_failures(self) -> None:
        """Broken wrapper lookups are contained and the remaining candidates are still evaluated."""

        class DummyInput:
            pass

        class InputNode:
            ports = []

            @staticmethod
            def get_type_name():
                return "InputNode"

        class BrokenCandidate:
            @staticmethod
            def GetPath():
                raise ValueError("bad path")

        class Model:
            def __getitem__(self, _item):
                raise RuntimeError("bad lookup")

            @staticmethod
            def get_item_model(_item):
                return None

        with patch.multiple(
            position_resolver_module,
            InputAttributeModel=DummyInput,
            OutputAttributeModel=type("DummyOutput", (), {}),
            IsolationGraphModel=SimpleNamespace(EmptyPort=type("DummyEmpty", (), {})),
        ):
            resolver = PositionItemResolver(Model())
            self.assertIsNone(resolver.resolve_io_attribute_item(InputNode()))
            self.assertIsNone(resolver._resolve_attribute_candidate(BrokenCandidate(), DummyInput, set()))

    async def test_position_resolver_normalizes_all_supported_wrapper_shapes(self) -> None:
        """Move normalization resolves direct, proxy, source, prim/path, and fallback model shapes."""

        class DummyAttribute:
            pass

        class DummyPrim:
            pass

        class InputNode:
            @staticmethod
            def get_type_name():
                return "InputNode"

        direct = DummyPrim()
        from_proxy = DummyAttribute()
        from_prim_path = DummyPrim()
        from_path = DummyAttribute()
        from_item = DummyPrim()

        class Model:
            def __getitem__(self, item):
                if getattr(item, "use_proxy", False):
                    return SimpleNamespace(source=from_proxy)
                raise RuntimeError("no proxy")

            @staticmethod
            def get_item_model(item):
                return {
                    "/PrimPath": from_prim_path,
                    "/Path": from_path,
                    "item-key": from_item,
                }.get(str(item))

        with patch.multiple(
            position_resolver_module,
            AttributeModel=DummyAttribute,
            InputAttributeModel=type("DummyInput", (DummyAttribute,), {}),
            OutputAttributeModel=type("DummyOutput", (DummyAttribute,), {}),
            PrimModel=DummyPrim,
        ):
            resolver = PositionItemResolver(Model())
            self.assertIsNone(resolver.normalize_moving_item(None))
            self.assertIs(resolver.normalize_moving_item(direct), direct)
            io_wrapper = InputNode()
            self.assertIs(resolver.normalize_moving_item(io_wrapper), io_wrapper)
            self.assertIs(resolver.normalize_moving_item(SimpleNamespace(prim_model=direct)), direct)
            self.assertIs(resolver.normalize_moving_item(SimpleNamespace(source=from_proxy)), from_proxy)
            self.assertIs(resolver.normalize_moving_item(SimpleNamespace(use_proxy=True)), from_proxy)
            self.assertIs(resolver.normalize_moving_item(SimpleNamespace(prim_path="/PrimPath")), from_prim_path)
            self.assertIs(resolver.normalize_moving_item(SimpleNamespace(path="/Path")), from_path)
            self.assertIs(resolver.normalize_moving_item("item-key"), from_item)
            unknown = object()
            self.assertIs(resolver.normalize_moving_item(unknown), unknown)
            self.assertIs(resolver.resolve_concrete_position_item(direct), direct)
            self.assertIs(resolver.resolve_concrete_position_item(io_wrapper), io_wrapper)
            self.assertIsNone(resolver.resolve_concrete_position_item(unknown))

    async def test_nodegraph_position_routes_staged_io_and_regular_items(self) -> None:
        """Position access should route every graph item shape without a rendered canvas."""

        class InputNode:
            @staticmethod
            def get_type_name():
                return "InputNode"

        class OutputNode:
            @staticmethod
            def get_type_name():
                return "OutputNode"

        model = self._make_model()
        model._ui_state = SimpleNamespace(position=(1.0, 2.0))
        model._input_output_position = [(3.0, 4.0), (5.0, 6.0)]
        staged = self._make_txn(
            is_staging=True,
            get_position=MagicMock(return_value=(7.0, 8.0)),
            set_position=MagicMock(),
        )
        model._position_txn = staged

        self.assertEqual(NodeGraphModel.position.fget(model), (1.0, 2.0))
        self.assertEqual(NodeGraphModel.position.fget(model, InputNode()), (7.0, 8.0))
        staged.get_position.assert_called_once()

        staged.is_staging = False
        self.assertEqual(NodeGraphModel.position.fget(model, InputNode()), (3.0, 4.0))
        self.assertEqual(NodeGraphModel.position.fget(model, OutputNode()), (5.0, 6.0))

        input_group = self._make_io_item(InputAttributeGroupModel)
        output_group = self._make_io_item(OutputAttributeGroupModel)
        self.assertEqual(NodeGraphModel.position.fget(model, input_group), (3.0, 4.0))
        self.assertEqual(NodeGraphModel.position.fget(model, output_group), (5.0, 6.0))

        persist = MagicMock()
        model._persist_concrete_position = persist
        NodeGraphModel.position.fset(model, (9.0, 10.0), InputNode())
        persist.assert_called_once()

        staged.is_staging = True
        staged.set_position.reset_mock()
        NodeGraphModel.position.fset(model, (11.0, 12.0), OutputNode())
        staged.set_position.assert_called_once()

        staged.is_committing = True
        NodeGraphModel.position.fset(model, (13.0, 14.0), object())
        staged.set_position.assert_called_once()

        staged.is_committing = False
        staged.is_staging = False
        persist.reset_mock()
        NodeGraphModel.position.fset(model, (15.0, 16.0), input_group)
        persist.assert_not_called()

        staged.is_staging = True
        model.batch_set_position = MagicMock()
        regular_item = object()
        NodeGraphModel.position.fset(model, (17.0, 18.0), regular_item)
        model.batch_set_position.assert_called_once_with((17.0, 18.0), regular_item)
        staged.set_position.assert_called_with(regular_item, (17.0, 18.0))
        model.model_root.notify_position_changed.assert_called_with(regular_item)
        model.model_root._item_changed.assert_not_called()

    async def test_selected_moving_items_normalize_filter_and_deduplicate(self) -> None:
        """Move transactions should use USD prim selection and only safe transient fallbacks."""
        model = self._make_model()
        prim = self._make_fake_prim()
        transient = object()
        duplicate = object()
        model._selection_adapter = SimpleNamespace(get_selected_nodes=MagicMock(return_value=[]))
        model._stage = object()
        model.get_item_model = MagicMock()
        model._selected_items = [prim, transient, duplicate]
        model._normalize_moving_item = lambda item: duplicate if item is transient else item

        selected = NodeGraphModel._get_selected_moving_items(model)

        self.assertEqual(selected, [duplicate])
        model._selection_adapter.get_selected_nodes.assert_called_once_with(
            model._stage, model._prim_path, model.get_item_model
        )

        model._selection_adapter.get_selected_nodes.return_value = [duplicate]
        model._selected_items = [transient]
        self.assertEqual(NodeGraphModel._get_selected_moving_items(model), [duplicate])

    async def test_persist_io_positions_and_remove_commands_report_results(self) -> None:
        """IO position changes should deduplicate writes, clear correctly, and surface command failure."""

        class InputNode:
            @staticmethod
            def get_type_name():
                return "InputNode"

        model = self._make_model()
        model._suppress_next_selection_run_select = False
        model._parent = SimpleNamespace(model_root=MagicMock())
        model._input_output_position = [None, None]

        model._persist_concrete_position(InputNode(), None, notify_root=True)
        model._persist_concrete_position(InputNode(), (10.0, 20.0), notify_root=True)
        model.set_position_cmd.assert_called_once_with((10.0, 20.0), model.INPUT)
        self.assertTrue(model._suppress_next_none_item_changed)
        self.assertTrue(model._suppress_next_selection_run_select)
        model.model_root._item_changed.assert_called_once_with(model)

        model._persist_concrete_position(InputNode(), None)
        model.remove_position_cmd.assert_called_once_with(model.INPUT)

        attribute = InputAttributeModel.__new__(InputAttributeModel)
        model._persist_concrete_position(attribute, (30.0, 40.0))
        model.set_position_cmd.assert_called_with((30.0, 40.0), model.INPUT)

        model.remove_position_cmd = MagicMock(return_value=SimpleNamespace(success=False))
        self.assertFalse(model.remove_input())
        model.remove_position_cmd.return_value = SimpleNamespace(success=True)
        self.assertTrue(model.remove_input())
        self.assertIsNone(model._input_output_position[0])

        model.remove_position_cmd.return_value = SimpleNamespace(success=False)
        self.assertFalse(model.remove_output())
        model.remove_position_cmd.return_value = SimpleNamespace(success=True)
        self.assertTrue(model.remove_output())
        self.assertIsNone(model._input_output_position[1])

    async def test_io_position_authoring_failure_preserves_cache(self) -> None:
        """IO add and drag commits must not expose positions that failed to author."""

        class InputNode:
            @staticmethod
            def get_type_name():
                return "InputNode"

        model = self._make_model()
        model.set_position_cmd.return_value = SimpleNamespace(success=False)

        self.assertFalse(model.add_input_or_output((10.0, 20.0), True))
        self.assertIsNone(model._input_output_position[0])
        self.assertFalse(model._persist_concrete_position(InputNode(), (30.0, 40.0)))
        self.assertIsNone(model._input_output_position[0])
        self.assertFalse(model._suppress_next_none_item_changed)

        model.set_position_cmd.return_value = SimpleNamespace(success=True)
        self.assertTrue(model.add_input_or_output((10.0, 20.0), True))
        self.assertEqual(model._input_output_position[0], (10.0, 20.0))
        self.assertTrue(model._persist_concrete_position(InputNode(), (30.0, 40.0)))
        self.assertEqual(model._input_output_position[0], (30.0, 40.0))

    async def test_selection_routes_suppression_application_and_local_change(self) -> None:
        """Selection setter callbacks should handle command feedback without UI interaction."""
        model = self._make_model()
        model._selection_changed = MagicMock()
        model._suppress_next_selection_run_select = True
        model._selection_adapter = SimpleNamespace(sync_selection=MagicMock(), clear=MagicMock())
        prim = self._make_fake_prim()
        transient = object()

        with patch(
            f"{Paths.MODULE_ID}.scripts.models.graph.nodes.nodegraph.model.SelectionAdapter.apply_selection"
        ) as apply_selection:
            NodeGraphModel.selection.fset(model, [prim, transient])
            prim_items, callback = model._selection_adapter.sync_selection.call_args.args
            self.assertEqual(prim_items, [prim])
            callback("kit-selection", prim_items, True)
            self.assertFalse(model._suppress_next_selection_run_select)
            model._selection_changed.assert_called_once_with()
            apply_selection.assert_not_called()

            callback("kit-selection", prim_items, True)
            apply_selection.assert_called_once_with("kit-selection", prim_items, True)
            callback("kit-selection", prim_items, False)
            self.assertEqual(model._selection_changed.call_count, 2)

            apply_selection.return_value = False
            callback("old-selection", prim_items, True)
            model._selection_adapter.clear.assert_called_once_with()
            self.assertEqual(model._selection_changed.call_count, 3)

        child_selection = [object()]
        self.assertIs(NodeGraphModel.selection.fget(model, SimpleNamespace(selection=child_selection)), child_selection)

    async def test_stage_listener_path_suppression_is_bounded_and_restored(self) -> None:
        """Transient notice suppression should normalize paths and always schedule restoration."""
        model = self._make_model()
        listener = SimpleNamespace(add_ignored_paths=MagicMock(), remove_ignored_paths=MagicMock())
        model._stage_listener_manager = SimpleNamespace(_stage_listener=listener)
        tasks = []
        model._lifecycle = SimpleNamespace(add_task=lambda task, label: tasks.append((task, label)))

        app = SimpleNamespace(next_update_async=AsyncMock())
        with patch(
            f"{Paths.MODULE_ID}.scripts.models.graph.nodes.nodegraph.model.omni.kit.app.get_app",
            return_value=app,
        ):
            model.suppress_stage_listener_property_paths_for_frames(["/World/A.inputs:x"], frames=2)
            self.assertEqual(len(tasks), 1)
            await tasks[0][0]

        normalized = [Sdf.Path("/World/A.inputs:x")]
        listener.add_ignored_paths.assert_called_once_with(normalized)
        listener.remove_ignored_paths.assert_called_once_with(normalized)
        self.assertEqual(app.next_update_async.await_count, 2)
        self.assertEqual(tasks[0][1], "restore stage listener ignore paths")
