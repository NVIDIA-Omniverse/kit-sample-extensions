# pylint: disable=relative-beyond-top-level,no-member,protected-access,attribute-defined-outside-init
import asyncio
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pxr import Sdf, UsdShade

from ...scripts.plugins.core import Plugin, PluginPropertiesBase, PluginProperty
from ..base import MaterialGraphTestBase


class _Props(PluginPropertiesBase):
    """Properties stub for plugin base tests."""

    def list(self) -> list:
        return [PluginProperty("p", "Prop", "string", default="x")]


class _Plugin(Plugin):
    """Minimal plugin implementation for tests."""

    def __init__(self, load_catalog: bool = True) -> None:
        super().__init__("test", "Test", _Props(), load_catalog=load_catalog)

    def build_catalog_items(self) -> None:
        self._catalog_items.clear()

    def is_supported_prim(self, _prim) -> bool:
        return False


class TestPluginBase(MaterialGraphTestBase):
    """Plugin base behaviors."""

    async def test_properties_and_names(self) -> None:
        """Plugin should expose names and properties."""
        plugin = _Plugin(load_catalog=False)
        self.assertEqual(plugin.name, "test")
        self.assertEqual(plugin.display_name, "Test")
        props = plugin.properties
        self.assertEqual(len(props), 1)
        self.assertEqual(props[0].key, "p")
        plugin.destroy()

    async def test_reload_marks_pending(self) -> None:
        """Reload should queue when a build is in progress."""
        plugin = _Plugin(load_catalog=False)

        class _DummyTask:
            def done(self) -> bool:
                return False

            def cancel(self) -> None:
                return None

        plugin._catalog_task = _DummyTask()
        plugin._catalog_reload_pending = False
        plugin.reload()
        self.assertTrue(plugin._catalog_reload_pending)
        plugin.destroy()

    async def test_can_connect_covers_render_type_value_type_and_interface_rules(self) -> None:
        """Base connection policy should honor force, render, value, and interface-only constraints."""
        plugin = _Plugin(load_catalog=False)

        def _model(
            type_name="float",
            *,
            render_type=None,
            connectability=None,
            owner_is_interface=False,
            parent=None,
            prim=None,
        ):
            return SimpleNamespace(
                proxy_attribute=SimpleNamespace(
                    type_name=type_name,
                    render_type=render_type,
                    connectability=connectability,
                    owner_is_interface=owner_is_interface,
                ),
                parent=parent,
                prim=prim,
            )

        source = _model(render_type="color")
        target = _model(render_type="color")
        with patch(f"{Plugin.__module__}.Settings.get_force_connect", return_value=False):
            self.assertTrue(plugin.can_connect(source, target))
            target.proxy_attribute.render_type = "normal"
            self.assertFalse(plugin.can_connect(source, target))

            source = _model(Sdf.ValueTypeNames.Color3f)
            target = _model(Sdf.ValueTypeNames.Point3f)
            self.assertTrue(plugin.compare_types(source, target))
            self.assertTrue(plugin.can_connect(source, target))
            target.proxy_attribute.type_name = "not-a-usd-type"
            self.assertFalse(plugin.can_connect(source, target))

            source = _model(connectability=UsdShade.Tokens.interfaceOnly)
            target = _model()
            self.assertFalse(plugin.can_connect(source, target))
            target.proxy_attribute.owner_is_interface = True
            self.assertTrue(plugin.can_connect(source, target))

            source = _model(parent=SimpleNamespace(source=object()))
            target = _model(connectability=UsdShade.Tokens.interfaceOnly)
            self.assertTrue(plugin.can_connect(source, target))

            graph_prim = SimpleNamespace(IsA=lambda schema: schema is UsdShade.NodeGraph)
            source = _model(prim=graph_prim)
            self.assertTrue(plugin.can_connect(source, target))

        with patch(f"{Plugin.__module__}.Settings.get_force_connect", return_value=True):
            self.assertTrue(plugin.can_connect(_model("bad"), _model("worse")))
        plugin.destroy()

    async def test_texture_selection_and_icon_resolution(self) -> None:
        """Texture arity selection and both catalog icon annotation formats should be deterministic."""
        plugin = _Plugin(load_catalog=False)
        plugin._texture_shaders = {1: ["one"], 4: ["four"]}
        self.assertEqual(plugin.create_texture(2), ["four"])
        self.assertEqual(plugin.create_texture(8), ["four"])
        plugin._texture_shaders.clear()
        self.assertEqual(plugin.create_texture(1), [])

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "thumbnail.png").write_bytes(b"thumbnail")
            (root / "icon.svg").write_text("<svg/>", encoding="utf-8")
            with patch(f"{Plugin.__module__}.cache_catalog_icon") as cache_icon:
                thumbnail = plugin._get_icon("shader", {"thumbnail": {"name": "thumbnail.png"}}, root, "family:sub")
                icon = plugin._get_icon("shader", {"icon": {"path": "icon.svg"}}, root, "family:sub")
                missing = plugin._get_icon(
                    "shader", {"thumbnail": "bad", "icon": {"path": "missing.svg"}}, root, "family"
                )
            self.assertEqual(thumbnail[0], str(root / "thumbnail.png"))
            self.assertEqual(icon[0], str(root / "icon.svg"))
            self.assertEqual(missing, ("", 0x00000000))
            self.assertEqual(cache_icon.call_count, 2)
        plugin.destroy()

    async def test_catalog_completion_handles_cancel_failure_and_queued_reload(self) -> None:
        """Catalog completion callbacks should contain task failures and service one queued reload."""
        plugin = _Plugin(load_catalog=False)
        cancelled = SimpleNamespace(result=MagicMock(side_effect=asyncio.CancelledError()))
        plugin._on_catalog_task_done(cancelled)

        failed = SimpleNamespace(result=MagicMock(side_effect=RuntimeError("catalog")))
        plugin._catalog_task = failed
        plugin._catalog_reload_pending = True
        plugin._load_catalog = MagicMock()
        plugin._on_catalog_task_done(failed)
        self.assertIsNone(plugin._catalog_task)
        self.assertFalse(plugin._catalog_reload_pending)
        plugin._load_catalog.assert_called_once_with()

        plugin._destroyed = True
        plugin._load_catalog.reset_mock()
        plugin._on_catalog_task_done(failed)
        plugin._load_catalog.assert_not_called()
        plugin.destroy()
