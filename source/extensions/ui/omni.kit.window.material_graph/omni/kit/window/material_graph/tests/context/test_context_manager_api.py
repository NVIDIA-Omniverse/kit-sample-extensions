from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pxr import Sdf, UsdShade

from ...scripts.config.paths import Paths
from ...scripts.context_manager.context_manager import ContextManager
from .base import ContextManagerTestBase


class TestContextManagerApi(ContextManagerTestBase):
    """ContextManager loads a material, adds/removes contexts (plugins), and exposes get_context etc.
    We test add_context (requires root material, missing plugin, non-material root), clear, load
    (binding resolution, same-path noop), and get_context/set_current behavior."""

    async def setUp(self) -> None:
        """Load the test scene and set common paths."""
        await super().setUp()
        await self._load_scene("cube.usda")
        self._material_path = Sdf.Path("/World/Looks/PreviewSurfaceTexture")
        self._cube_prim_path = Sdf.Path("/World/Cube")

    async def test_add_context_requires_root_material(self) -> None:
        """add_context fails until material loaded."""
        plugins = list(self._manager.get_plugins())
        self.assertTrue(plugins)
        context_name = plugins[0].name

        self.assertFalse(self._manager.add_context(context_name))
        self.assertEqual(self._manager.get_last_error(), "No root prim")

        self.assertTrue(self._manager.load(self._material_path))
        self.assertTrue(self._manager.add_context(context_name))
        self.assertIn(context_name, self._manager.get_context_names())

    async def test_add_context_missing_plugin(self) -> None:
        """add_context fails for missing plugin."""
        self.assertTrue(self._manager.load(self._material_path))
        self.assertFalse(self._manager.add_context("missing"))
        self.assertEqual(self._manager.get_last_error(), "Missing plugin 'missing'")

    async def test_add_context_root_not_material(self) -> None:
        """add_context fails when root prim is not Material."""
        # Set _root_prim to cube to cover non-material branch.
        self._manager._root_prim = self._get_prim_at_path(self._cube_prim_path)
        self.assertFalse(self._manager.add_context("missing"))
        self.assertEqual(self._manager.get_last_error(), "Root prim is not a Material")
        self._manager._root_prim = None

    async def test_clear_resets_contexts(self) -> None:
        """clear removes contexts and root prim."""
        plugins = list(self._manager.get_plugins())
        self.assertTrue(plugins)
        context_name = plugins[0].name

        self.assertTrue(self._manager.load(self._material_path))
        self.assertTrue(self._manager.add_context(context_name))
        self.assertIn(context_name, self._manager.get_context_names())

        self._manager.clear()
        self.assertEqual(self._manager.get_context_names(), [])
        handle = self._manager.get_context(context_name)
        self.assertIsNone(handle.context)
        self.assertIsNotNone(handle.plugin)

    async def test_load_uses_material_binding(self) -> None:
        """load resolves material from bound prim."""
        self.assertTrue(self._manager.load(self._cube_prim_path))
        self.assertTrue(self._manager.load(self._material_path))

    async def test_load_same_path_noop(self) -> None:
        """Loading same path does not drop contexts."""
        plugins = list(self._manager.get_plugins())
        self.assertTrue(plugins)
        context_name = plugins[0].name

        self.assertTrue(self._manager.load(self._material_path))
        handle_before = self._manager.get_context(context_name)
        self.assertIsNotNone(handle_before.context)

        self.assertTrue(self._manager.load(self._material_path))
        self.assertTrue(self._manager.load(self._material_path))
        handle_after = self._manager.get_context(context_name)
        self.assertIs(handle_before.context, handle_after.context)

    async def test_get_node(self) -> None:
        """get_node returns plugin result or None."""
        node = object()
        plugin = SimpleNamespace(get_node=lambda identifier: node)
        # Patch the plugin access to avoid needing a real plugin module.
        self._manager._plugin_access.get_plugin = lambda _name: plugin
        self.assertIs(self._manager.get_node("mdl", "something"), node)

        self._manager._plugin_access.get_plugin = lambda _name: None
        self.assertIsNone(self._manager.get_node("mdl", "missing"))
        self.assertEqual(self._manager.get_last_error(), "Missing plugin 'mdl'")

    async def test_get_context_invalid_root(self) -> None:
        """get_context reports error when root/stage invalid."""
        plugins = list(self._manager.get_plugins())
        self.assertTrue(plugins)
        context_name = plugins[0].name
        self.assertTrue(self._manager.load(self._material_path))

        class DummyContext:
            """Context returning no stage."""

            def get_stage(self) -> None:
                """Return no stage."""
                return None

        original_context = self._manager._usd_context
        self._manager._usd_context = DummyContext()
        handle = self._manager.get_context(context_name)
        self._manager._usd_context = original_context

        self.assertIsNone(handle.context)
        self.assertIsNotNone(handle.error)
        self.assertEqual(self._manager.get_last_error(), "No USD stage")

    async def test_destroy_is_safe(self) -> None:
        """destroy makes API safe after teardown."""
        self.assertTrue(self._manager.load(self._material_path))
        plugins = list(self._manager.get_plugins())
        self.assertTrue(plugins)
        context_name = plugins[0].name
        handle_before = self._manager.get_context(context_name)
        self.assertIsNotNone(handle_before.context)

        self._manager.destroy()
        self.assertEqual(list(self._manager.get_plugins()), [])
        handle_after = self._manager.get_context(context_name)
        self.assertIsNone(handle_after.context)
        self.assertIsNotNone(handle_after.error)
        self._manager.destroy()

    async def test_destroy_is_idempotent(self) -> None:
        """destroy is safe to call multiple times."""
        self._manager.destroy()
        self._manager.destroy()
        handle = self._manager.get_context("missing")
        self.assertIsNone(handle.context)

    async def test_root_prim_replacement_recreates_contexts(self) -> None:
        """Root prim replacement invalidates and recreates contexts."""
        plugins = list(self._manager.get_plugins())
        self.assertTrue(plugins)
        context_name = plugins[0].name

        self.assertTrue(self._manager.load(self._material_path))
        handle_before = self._manager.get_context(context_name)
        self.assertIsNotNone(handle_before.context)

        # Replace prim by deleting and re-defining it at the same path.
        stage = self._stage
        self.assertTrue(stage.RemovePrim(self._material_path))
        self.assertTrue(UsdShade.Material.Define(self._stage, str(self._material_path)))

        self.assertTrue(self._manager.load(self._material_path))
        handle_after = self._manager.get_context(context_name)
        self.assertIsNotNone(handle_after.context)
        self.assertIsNot(handle_before.context, handle_after.context)

    async def test_invalid_usd_context(self) -> None:
        """Invalid USD context prevents load and sets error."""
        manager = ContextManager(object())
        self.assertFalse(manager.load(self._material_path))
        self.assertEqual(manager.get_last_error(), "Invalid USD context")
        manager.destroy()

    async def test_remove_context_failure_sets_error(self) -> None:
        """remove_context surfaces error when output removal fails."""
        plugins = list(self._manager.get_plugins())
        self.assertTrue(plugins)
        context_name = plugins[0].name

        self.assertTrue(self._manager.load(self._material_path))
        self.assertTrue(self._manager.add_context(context_name))
        context = self._manager.get_context(context_name).context
        self._manager._root_prim.CreateAttribute("outputs:surface", Sdf.ValueTypeNames.Token)

        with patch.object(self._manager, "_remove_context_output", return_value=False):
            context.plugin.get_material_output_names = lambda: ["outputs:surface"]
            self.assertFalse(self._manager.remove_context(context_name))
            self.assertIn("Failed to remove material output", self._manager.get_last_error() or "")

    async def test_validation_subscription_and_context_destruction_boundaries(self) -> None:
        """Optional validation callbacks and cached context teardown remain safe and idempotent."""
        self.assertIsNone(self._manager.subscribe_validation("changed", None))
        self._manager._validator.subscribe = MagicMock(return_value=42)
        self._manager._validator.unsubscribe = MagicMock()
        callback = MagicMock()
        self.assertEqual(self._manager.subscribe_validation("changed", callback), 42)
        self._manager.unsubscribe_validation(42)
        self._manager._validator.unsubscribe.assert_called_once_with(42)

        plugins = list(self._manager.get_plugins())
        context_name = plugins[0].name
        self.assertTrue(self._manager.load(self._material_path))
        handle = self._manager.get_context(context_name)
        self.assertTrue(handle.is_valid)
        handle.context.destroy = MagicMock()
        self.assertTrue(self._manager.destroy_context(context_name))
        handle.context.destroy.assert_called_once_with()
        self.assertFalse(self._manager.destroy_context(context_name))

        self._manager._validator = None
        self.assertIsNone(self._manager.subscribe_validation("changed", callback))
        self._manager.unsubscribe_validation(42)

    async def test_validation_defaults_and_context_creation_failure(self) -> None:
        """Validation fails open when no graph is available and creation errors stay actionable."""
        result = self._manager.validate_context("missing")
        self.assertTrue(result.is_valid)

        plugins = list(self._manager.get_plugins())
        plugin = plugins[0]
        self.assertTrue(self._manager.load(self._material_path))
        self._manager.destroy_context(plugin.name)
        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.context_manager.context_manager.Context.create_context",
                return_value=None,
            ),
            patch(f"{Paths.MODULE_ID}.scripts.context_manager.context_manager.logger.error"),
        ):
            self.assertFalse(self._manager.add_context(plugin.name))
        self.assertEqual(self._manager.get_last_error(), f"Context create failed '{plugin.name}'")

        context = SimpleNamespace(
            model=SimpleNamespace(skip_next_activation_sync=MagicMock()),
            destroy=MagicMock(),
        )
        with patch(
            f"{Paths.MODULE_ID}.scripts.context_manager.context_manager.Context.create_context",
            return_value=context,
        ):
            self.assertIs(self._manager._create_context(plugin.name, plugin), context)
        context.model.skip_next_activation_sync.assert_called_once_with()

        self._manager._validator = None
        result = self._manager.validate_context(plugin.name)
        self.assertTrue(result.is_valid)
