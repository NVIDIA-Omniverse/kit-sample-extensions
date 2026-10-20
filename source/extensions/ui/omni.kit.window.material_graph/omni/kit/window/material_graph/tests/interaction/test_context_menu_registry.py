# pylint: disable=relative-beyond-top-level,invalid-overridden-method
import functools
import gc
import weakref
from unittest.mock import patch

from ...scripts import api as api_module
from ...scripts.api import context_menu
from ...scripts.api.context_menu import registry as registry_module
from ..base import MaterialGraphTestBase


class TestContextMenuRegistry(MaterialGraphTestBase):
    """Registry behavior for the public context-menu API."""

    async def setUp(self) -> None:
        """Clear registry before each test."""
        await super().setUp()
        context_menu.clear_node_menu_items()
        context_menu.clear_background_menu_items()

    async def tearDown(self) -> None:
        """Clear registry after each test."""
        context_menu.clear_node_menu_items()
        context_menu.clear_background_menu_items()
        await super().tearDown()

    async def test_node_add_remove_cycle(self) -> None:
        """A removed node menu entry can be re-registered."""

        def _callback(_node_type: str, _prim_path: str) -> None:
            return None

        self.assertTrue(api_module.add_node_menu_item("ItemA", _callback, node_types="NodeGraph"))
        self.assertFalse(api_module.add_node_menu_item("ItemA", _callback, node_types="NodeGraph"))
        api_module.remove_node_menu_item("ItemA", _callback)
        self.assertTrue(api_module.add_node_menu_item("ItemA", _callback, node_types="NodeGraph"))

    async def test_background_add_remove_cycle(self) -> None:
        """A removed background menu entry can be re-registered."""

        def _callback(_items: list, _mouse_position: object) -> None:
            return None

        self.assertTrue(api_module.add_background_menu_item("ItemA", _callback))
        self.assertFalse(api_module.add_background_menu_item("ItemA", _callback))
        api_module.remove_background_menu_item("ItemA", _callback)
        self.assertTrue(api_module.add_background_menu_item("ItemA", _callback))

    async def test_remove_by_label_removes_all_callbacks(self) -> None:
        """Removing by label clears all callbacks under that label."""

        def _callback_a(_node_type: str, _prim_path: str) -> None:
            return None

        def _callback_b(_node_type: str, _prim_path: str) -> None:
            return None

        self.assertTrue(api_module.add_node_menu_item("ItemA", _callback_a, node_types="NodeGraph"))
        self.assertTrue(api_module.add_node_menu_item("ItemA", _callback_b, node_types="NodeGraph"))
        api_module.remove_node_menu_item("ItemA")
        self.assertTrue(api_module.add_node_menu_item("ItemA", _callback_a, node_types="NodeGraph"))

    async def test_keyword_only_callback_is_rejected(self) -> None:
        """Menu arguments are positional; keyword-only slots are not compatible."""

        def _callback(*, node_type: str, prim_path: str) -> None:
            del node_type, prim_path

        self.assertFalse(api_module.add_node_menu_item("KeywordOnly", _callback))

    async def test_equivalent_bound_partial_can_unregister(self) -> None:
        """A reconstructed partial with the same owner/args removes the entry."""

        class Owner:
            def callback(self, prefix: str, node_type: str, prim_path: str) -> None:
                del prefix, node_type, prim_path

        owner = Owner()
        self.assertTrue(
            api_module.add_node_menu_item(
                "Partial",
                functools.partial(owner.callback, "prefix"),
                node_types="NodeGraph",
            )
        )
        api_module.remove_node_menu_item("Partial", functools.partial(owner.callback, "prefix"))
        self.assertEqual(context_menu.get_node_menu_items("NodeGraph"), [])

    async def test_invalid_callbacks_and_node_type_inputs_are_contained(self) -> None:
        """Malformed public registrations should fail predictably and emit actionable warnings."""
        registry = registry_module.ContextMenuRegistry()
        with (
            patch.object(registry_module, "_should_log_warnings", return_value=True),
            patch.object(registry_module.logger, "warning") as warning,
        ):
            self.assertFalse(registry.add_node_menu_item("NotCallable", object()))
            self.assertFalse(registry.add_node_menu_item("TooFew", lambda _node_type: None))
            self.assertFalse(registry.add_background_menu_item("TooFew", lambda _items: None))

            callback = lambda _node_type, _prim_path: None
            self.assertTrue(registry.add_node_menu_item("InvalidTypes", callback, node_types=object()))
            self.assertTrue(warning.called)

        self.assertEqual(registry.get_node_menu_items(None), [])
        self.assertEqual([item.label for item in registry.get_node_menu_items("Anything")], ["InvalidTypes"])

    async def test_bound_callbacks_are_weak_and_pruned_after_owner_destruction(self) -> None:
        """Registry entries must not retain extension owners beyond their lifecycle."""
        calls = []

        class Owner:
            def node_callback(self, node_type, prim_path):
                calls.append((node_type, prim_path))

            def background_callback(self, prefix, items, mouse_position):
                calls.append((prefix, items, mouse_position))

        registry = registry_module.ContextMenuRegistry()
        owner = Owner()
        owner_ref = weakref.ref(owner)
        node_callback = owner.node_callback
        background_callback = functools.partial(owner.background_callback, "prefix")
        self.assertTrue(registry.add_node_menu_item("WeakNode", node_callback))
        self.assertTrue(registry.add_background_menu_item("WeakBackground", background_callback))

        registry.get_node_menu_items("Shader")[0].callback("Shader", "/Node")
        registry.get_background_menu_items()[0].callback([], (10, 20))
        self.assertEqual(calls[0], ("Shader", "/Node"))
        self.assertEqual(calls[1], ("prefix", [], (10, 20)))

        del node_callback
        del background_callback
        del owner
        gc.collect()
        self.assertIsNone(owner_ref())
        with (
            patch.object(registry_module, "_should_log_info", return_value=True),
            patch.object(registry_module.logger, "info") as info,
        ):
            self.assertEqual(registry.get_node_menu_items("Shader"), [])
            self.assertEqual(registry.get_background_menu_items(), [])
            self.assertTrue(info.called)

    async def test_registry_snapshots_filters_and_clear_operations_are_independent(self) -> None:
        """Node filters and returned lists should not expose mutable registry internals."""
        registry = registry_module.ContextMenuRegistry()
        callback = lambda *_args: None
        self.assertTrue(registry.add_node_menu_item("All", callback))
        self.assertTrue(registry.add_node_menu_item("ShaderOnly", callback, {"Shader"}))
        self.assertTrue(registry.add_background_menu_item("Background", callback))

        shader_items = registry.get_node_menu_items("Shader")
        material_items = registry.get_node_menu_items("Material")
        self.assertEqual([item.label for item in shader_items], ["All", "ShaderOnly"])
        self.assertEqual([item.label for item in material_items], ["All"])
        shader_items.clear()
        self.assertEqual(len(registry.get_node_menu_items("Shader")), 2)

        registry.clear_node_menu_items()
        registry.clear_background_menu_items()
        self.assertEqual(registry.get_node_menu_items("Shader"), [])
        self.assertEqual(registry.get_background_menu_items(), [])
