from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pxr import Sdf, UsdShade

from ...scripts.models.graph.ports.proxy import ProxyAttribute
from ...scripts.plugins.impl.usd.plugin import UsdPlugin
from ...scripts.validation.validator import MaterialValidator
from ..base import MaterialGraphTestBase


class TestMaterialValidator(MaterialGraphTestBase):
    """Reliability contracts for validator caching and event subscribers."""

    async def test_subscriber_failure_does_not_block_later_subscribers(self) -> None:
        validator = MaterialValidator()
        healthy = MagicMock()
        validator.subscribe("started", MagicMock(side_effect=RuntimeError("broken subscriber")))
        validator.subscribe("started", healthy)

        with patch("omni.kit.window.material_graph.scripts.validation.validator.logger.exception") as log_exception:
            validator._emit("started", "universal")

        healthy.assert_called_once_with("universal")
        log_exception.assert_called_once()

    async def test_interactive_can_connect_does_not_serve_stale_path_result(self) -> None:
        validator = MaterialValidator()
        plugin = MagicMock()
        plugin.can_connect.side_effect = [True, False]
        source = SimpleNamespace(
            path="/Source.outputs:out", proxy_attribute=SimpleNamespace(polymorphic_unresolved=False)
        )
        target = SimpleNamespace(
            path="/Target.inputs:in", proxy_attribute=SimpleNamespace(polymorphic_unresolved=False)
        )

        with patch.object(validator, "would_create_cycle", return_value=False):
            self.assertTrue(validator.can_connect("universal", plugin, source, target))
            self.assertFalse(validator.can_connect("universal", plugin, source, target))

        self.assertEqual(plugin.can_connect.call_count, 2)

    async def test_proxy_validation_preserves_interface_owner_identity(self) -> None:
        """Interface-only compatibility sees material/nodegraph ownership from USD proxies."""
        material = UsdShade.Material.Define(self._stage, Sdf.Path("/World/Looks/InterfaceMaterial"))
        shader = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/InterfaceMaterial/Shader"))
        source = material.CreateInput("interface", Sdf.ValueTypeNames.Float)
        target = shader.CreateInput("target", Sdf.ValueTypeNames.Float)
        target.SetConnectability(UsdShade.Tokens.interfaceOnly)
        source_proxy = ProxyAttribute(source.GetFullName(), True, attribute=source.GetAttr())
        target_proxy = ProxyAttribute(target.GetFullName(), False, attribute=target.GetAttr())

        validator = MaterialValidator()
        plugin = UsdPlugin(load_catalog=False)
        self.assertTrue(validator._can_connect_proxy("universal", plugin, source_proxy, target_proxy))
