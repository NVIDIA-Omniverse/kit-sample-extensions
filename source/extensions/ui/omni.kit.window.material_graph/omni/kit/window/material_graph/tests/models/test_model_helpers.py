# pylint: disable=relative-beyond-top-level,no-member,protected-access
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pxr import Gf, Sdf, UsdGeom, UsdShade

from ...scripts.commands.result import CommandResult
from ...scripts.config.paths import Paths
from ...scripts.models.graph.core.base import GraphModelBase
from ...scripts.models.graph.core.proxy_item_mixin import ProxyItemMixin
from ...scripts.models.graph.core.state import ModelState
from ...scripts.models.graph.nodes.prim.position_mixin import PositionMixin
from ...scripts.models.graph.ports.attribute.model import AttributeModel
from ...scripts.models.graph.ports.proxy import ProxyAttribute
from ...scripts.validation.validator import MaterialValidator
from ..base import MaterialGraphTestBase
from .helpers import DummyPlugin


class _TogglePlugin(DummyPlugin):
    """Plugin stub that allows toggling connection validation."""

    def __init__(self, allowed: bool) -> None:
        super().__init__()
        self._allowed = allowed

    def can_connect(self, _source_placeholder, _target_placeholder) -> bool:
        """Return a configured connection verdict."""
        return self._allowed


class _DummyPositionBase:
    """Base class that records sync calls."""

    def __init__(self) -> None:
        self.sync_called = False

    def sync_position(self) -> None:
        """Record sync calls."""
        self.sync_called = True


class _DummyPosition(PositionMixin, _DummyPositionBase):
    """Position mixin test harness."""

    def __init__(self, prim) -> None:
        super().__init__()
        self.prim = prim
        self.context_name = "universal"
        self._ui_state = SimpleNamespace(position=None)


class TestModelHelpers(MaterialGraphTestBase):
    """Coverage for model helper utilities."""

    def _create_model(self) -> GraphModelBase:
        prim = UsdGeom.Xform.Define(self._stage, "/World/TestNode").GetPrim()
        model = GraphModelBase(
            "TestNode",
            "TestType",
            prim.GetPath(),
            None,
            prim,
            "universal",
            self._usd_context,
            DummyPlugin(),
            False,
        )
        model.validator = MaterialValidator()
        return model

    def _create_attribute_model(self, parent, shader, port_cls, is_output, plugin):
        attr = (
            shader.CreateOutput("out", Sdf.ValueTypeNames.Float)
            if is_output
            else shader.CreateInput("in", Sdf.ValueTypeNames.Float)
        )
        usd_attr = attr.GetAttr()
        proxy_attribute = ProxyAttribute(usd_attr.GetName(), is_output, attribute=usd_attr)
        return AttributeModel(
            parent,
            shader.GetPrim(),
            "universal",
            self._usd_context,
            plugin,
            False,
            proxy_attribute,
            port_cls,
        )

    async def test_graph_model_get_item_model_selection_paths(self) -> None:
        """Selection path resolution should map to model instances."""
        model = self._create_model()
        self.assertIs(model.get_item_model(model.prim_path), model)

        sentinel = object()

        def _get_property_model(_path):
            return sentinel

        model.get_property_model = _get_property_model
        property_path = model.prim_path.AppendProperty("inputs:in")
        self.assertIs(model.get_item_model(property_path), sentinel)
        self.assertIsNone(model.get_item_model(Sdf.Path("/World/Other")))

        class _ProxyItem:
            def GetPath(self):
                return model.prim_path

        self.assertIs(model.get_item_model(_ProxyItem()), model)

        class _ProxyModelItem:
            prim_model = model

        self.assertIs(model.get_item_model(_ProxyModelItem()), model)

    async def test_graph_model_can_connect(self) -> None:
        """Connection validation should return explicit booleans."""
        model = self._create_model()
        self.assertFalse(model.can_connect(object(), object()))

        shader = UsdShade.Shader.Define(self._stage, "/World/TestNode/Shader")
        source = self._create_attribute_model(model, shader, UsdShade.Input, False, _TogglePlugin(True))
        target = self._create_attribute_model(model, shader, UsdShade.Output, True, _TogglePlugin(True))
        self.assertTrue(model.can_connect(source, target))

        source_blocked = self._create_attribute_model(model, shader, UsdShade.Input, False, _TogglePlugin(False))
        self.assertFalse(model.can_connect(source_blocked, target))

    async def test_graph_model_can_connect_force_modifier_override(self) -> None:
        """Ctrl+Shift should bypass non-cyclical compatibility checks for attribute ports."""
        model = self._create_model()
        source_shader = UsdShade.Shader.Define(self._stage, "/World/TestNode/ForceShaderSource")
        target_shader = UsdShade.Shader.Define(self._stage, "/World/TestNode/ForceShaderTarget")
        source = self._create_attribute_model(model, source_shader, UsdShade.Output, True, _TogglePlugin(False))
        target = self._create_attribute_model(model, target_shader, UsdShade.Input, False, _TogglePlugin(False))
        self.assertFalse(model.can_connect(source, target))
        modifier_module = source.__class__.__module__
        with patch(
            f"{modifier_module}.is_force_connection_modifier_pressed",
            autospec=True,
            return_value=True,
        ):
            self.assertTrue(model.can_connect(source, target))

    async def test_graph_model_can_connect_force_modifier_still_blocks_cycles(self) -> None:
        """Ctrl+Shift must not allow cyclical source->target connections."""
        model = self._create_model()
        shader = UsdShade.Shader.Define(self._stage, "/World/TestNode/CycleShader")
        source = self._create_attribute_model(model, shader, UsdShade.Output, True, _TogglePlugin(True))
        target = self._create_attribute_model(model, shader, UsdShade.Input, False, _TogglePlugin(True))
        modifier_module = source.__class__.__module__
        with patch(
            f"{modifier_module}.is_force_connection_modifier_pressed",
            autospec=True,
            return_value=True,
        ):
            self.assertFalse(model.can_connect(source, target))

    async def test_failed_unlock_preserves_attribute_lock_state(self) -> None:
        """Resuming a port must not clear the lock cache when unlocking its USD spec fails."""
        parent = self._create_model()
        shader = UsdShade.Shader.Define(self._stage, "/World/TestNode/LockedShader")
        attribute = self._create_attribute_model(parent, shader, UsdShade.Input, False, DummyPlugin())
        attribute._locked = True
        with patch(
            f"{Paths.MODULE_ID}.scripts.models.graph.ports.attribute.model.UnlockAttribute",
            return_value=CommandResult(False, error_code="injected"),
        ):
            attribute.set_pause(False)
        self.assertTrue(attribute._locked)

        with patch(
            f"{Paths.MODULE_ID}.scripts.models.graph.ports.attribute.model.UnlockAttribute",
            return_value=CommandResult(True),
        ):
            attribute.set_pause(False)
        self.assertFalse(attribute._locked)

    async def test_failed_attribute_rename_is_reported(self) -> None:
        """Attribute-model rename should propagate its structured command failure."""
        parent = self._create_model()
        shader = UsdShade.Shader.Define(self._stage, "/World/TestNode/RenameShader")
        attribute = self._create_attribute_model(parent, shader, UsdShade.Input, False, DummyPlugin())
        with patch(
            f"{Paths.MODULE_ID}.scripts.models.graph.ports.attribute.model.RenameProperty",
            return_value=CommandResult(False, error_code="injected"),
        ):
            self.assertFalse(attribute.set_name(f"{UsdShade.Tokens.inputs}renamed"))

    async def test_proxy_item_mixin_helpers(self) -> None:
        """Proxy helpers should fall back and set attributes."""

        class _Proxy:
            value = 3

        self.assertEqual(ProxyItemMixin._proxy_value(_Proxy(), "value", 10), 3)
        self.assertEqual(ProxyItemMixin._proxy_value(None, "value", 10), 10)

        proxy = _Proxy()
        self.assertTrue(ProxyItemMixin._proxy_set(proxy, "value", 5))
        self.assertEqual(proxy.value, 5)
        self.assertFalse(ProxyItemMixin._proxy_set(None, "value", 5))

    async def test_model_state_values(self) -> None:
        """ModelState values should remain stable."""
        self.assertEqual(ModelState.ACTIVE.value, "active")
        self.assertEqual(ModelState.CLEARED.value, "cleared")
        self.assertEqual(ModelState.DESTROYED.value, "destroyed")

    async def test_position_mixin_custom_data(self) -> None:
        """Position mixin should read/write per-context custom data."""
        # Validate wrapper-level command routing instead of raw metadata writes,
        # so tests remain aligned with command-based persistence behavior.
        prim = UsdGeom.Xform.Define(self._stage, "/World/PosNode").GetPrim()
        position = _DummyPosition(prim)
        key = position._get_context_position_key()
        with patch(
            f"{Paths.MODULE_ID}.scripts.models.graph.nodes.prim.position_mixin.SetContextPosition",
            autospec=True,
        ) as set_ctx:
            self.assertIs(position.set_position_cmd((1.0, 2.0)), set_ctx.return_value)
            set_ctx.assert_called_once()

        prim.SetCustomDataByKey(key, Gf.Vec2f(1.0, 2.0))

        position.sync_position()
        self.assertEqual(position._ui_state.position, Gf.Vec2f(1.0, 2.0))
        self.assertFalse(position.sync_called)

        with patch(
            f"{Paths.MODULE_ID}.scripts.models.graph.nodes.prim.position_mixin.RemoveContextPosition",
            autospec=True,
        ) as remove_ctx:
            position.remove_position_cmd()
            remove_ctx.assert_called_once()

        prim.ClearCustomDataByKey(key)
        self.assertFalse(prim.HasAuthoredCustomDataKey(key))

        position.sync_position()
        self.assertTrue(position.sync_called)

    async def test_attribute_tooltips_cover_unresolved_and_mdl_metadata(self) -> None:
        """Port tooltips should explain candidate, struct, enum, and array metadata headlessly."""
        import omni.UsdMdl

        parent = self._create_model()
        shader = UsdShade.Shader.Define(self._stage, "/World/TestNode/TooltipShader")
        attribute = self._create_attribute_model(parent, shader, UsdShade.Input, False, DummyPlugin())
        proxy = attribute.proxy_attribute
        proxy._metadata["documentation"] = "Useful port"
        attribute._parent = SimpleNamespace(
            prim_model=SimpleNamespace(
                _get_candidate_port_types=lambda _name, _is_input: ["float", "color3f", "float"]
            ),
            display_group="Inputs",
            model_root=MagicMock(),
        )

        proxy.polymorphic_unresolved = True
        unresolved = attribute.tooltip_text
        self.assertIn("Candidate types", unresolved)
        self.assertIn("color3f, float", unresolved)
        self.assertIn("Useful port", unresolved)

        proxy.polymorphic_unresolved = False
        proxy._metadata["variability"] = "uniform"
        proxy.render_type = omni.UsdMdl.Types.Struct
        proxy.mdl_struct_type = "::audit::Payload"
        proxy.mdl_symbol = "Payload"
        struct_text = attribute.tooltip_text
        self.assertIn("::audit::Payload", struct_text)
        self.assertIn("Payload", struct_text)

        proxy.render_type = omni.UsdMdl.Types.Enum
        self.assertIn("Payload", attribute.tooltip_text)
        proxy.render_type = omni.UsdMdl.Types.Array
        proxy._metadata[omni.UsdMdl.Metadata.ArrayElementType] = "float"
        self.assertIn("float", attribute.tooltip_text)
        self.assertEqual(
            AttributeModel.tooltip_text.fget(attribute, SimpleNamespace(tooltip_text="delegated")), "delegated"
        )

    async def test_attribute_style_and_delegated_state_paths(self) -> None:
        """Uniform style overrides and delegated property access should preserve model state."""
        parent = self._create_model()
        shader = UsdShade.Shader.Define(self._stage, "/World/TestNode/StyleShader")
        attribute = self._create_attribute_model(parent, shader, UsdShade.Input, False, DummyPlugin())
        proxy = attribute.proxy_attribute
        proxy._metadata["variability"] = "uniform"
        port_type = str(attribute.type)
        style = {
            f"Graph.Node.Port.Input.Icon::{port_type}": {"image_url": "old.svg"},
            f"Graph.Node.Port.Output.CustomColor::{port_type}": {"border_color": 0xFF336699},
        }
        with patch(
            f"{Paths.MODULE_ID}.scripts.models.graph.ports.attribute.model.AttributeStyleCache.get_style",
            return_value=style,
        ):
            result = AttributeModel.get_style(attribute.type, proxy)
        self.assertIn("uniform.svg", result[f"Graph.Node.Port.Input.Icon::{port_type}"]["image_url"])
        self.assertNotEqual(
            result[f"Graph.Node.Port.Output.CustomColor::{port_type}"]["background_color"],
            style[f"Graph.Node.Port.Output.CustomColor::{port_type}"]["border_color"],
        )

        delegated = SimpleNamespace(
            prim_model="prim",
            usdshade_port="port",
            style="style",
            proxy_attribute="proxy",
            display_group="group",
            inputs=["input"],
            outputs=["output"],
        )
        self.assertEqual(AttributeModel.prim_model.fget(attribute, delegated), "prim")
        self.assertEqual(AttributeModel.usdshade_port.fget(attribute, delegated), "port")
        self.assertEqual(AttributeModel.style.fget(attribute, delegated), "style")
        self.assertEqual(AttributeModel.proxy_attribute.fget(attribute, delegated), "proxy")
        self.assertEqual(AttributeModel.display_group.fget(attribute, delegated), "group")
        self.assertEqual(AttributeModel.inputs.fget(attribute, delegated), ["input"])
        self.assertEqual(AttributeModel.outputs.fget(attribute, delegated), ["output"])
        AttributeModel.usdshade_port.fset(attribute, "updated", delegated)
        AttributeModel.inputs.fset(attribute, ["updated"], delegated)
        self.assertEqual(delegated.usdshade_port, "updated")
        self.assertEqual(delegated.inputs, ["updated"])
