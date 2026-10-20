# pylint: disable=relative-beyond-top-level,no-member
import pickle
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pxr import Sdf, UsdShade, Vt

from ...scripts.models.graph.nodes.prim.model import PrimModel
from ...scripts.models.graph.nodes.prim.ports import PrimPortSync
from ...scripts.models.graph.nodes.shader import ShaderModel
from ...scripts.models.graph.ports.attribute.input import InputAttributeModel
from ...scripts.models.graph.ports.internal.metadata import AttributeMetadata
from ...scripts.models.graph.ports.proxy import ProxyAttribute
from ...scripts.plugins.core.polymorphic_state import PolymorphicState
from ...scripts.plugins.impl.materialx.plugin import MaterialXPlugin
from ...scripts.settings.settings import Settings
from ..base import MaterialGraphTestBase


class _Collector:
    """Collector stub for prim port sync tests."""

    def __init__(self) -> None:
        self.calls = []

    def add_or_update_proxy_attribute(self, is_output, attribute, proxy_attributes):
        self.calls.append((is_output, attribute.GetName()))
        proxy_attributes.append(attribute.GetName())


class TestPrimPorts(MaterialGraphTestBase):
    """Tests for prim port synchronization."""

    async def test_collect_inputs_outputs(self) -> None:
        """Inputs and outputs should be collected from connectable prims."""
        shader = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/Shader"))
        shader.CreateInput("in", Sdf.ValueTypeNames.Float)
        shader.CreateOutput("out", Sdf.ValueTypeNames.Float)

        collector = _Collector()
        sync = PrimPortSync(shader.GetPrim(), None, None, collector)

        inputs = []
        outputs = []
        sync.collect_inputs(inputs)
        sync.collect_outputs(outputs)

        self.assertIn((False, "inputs:in"), collector.calls)
        self.assertIn((True, "outputs:out"), collector.calls)

    async def test_create_port_copies_polymorphic_unresolved_flag(self) -> None:
        """Interface ports created from unresolved polymorphic ports should render as unresolved."""

        class InputPortDouble(InputAttributeModel):
            """InputAttributeModel-shaped test double for create_port."""

            def __init__(self) -> None:
                """Bypass InputAttributeModel construction for this focused test double."""

            @property
            def attribute_name(self) -> str:
                return "inputs:a"

            @property
            def type(self):
                return Sdf.ValueTypeNames.Float

            @property
            def proxy_attribute(self):
                return SimpleNamespace(
                    variability=Sdf.VariabilityVarying,
                    polymorphic_unresolved=True,
                )

        source_port = InputPortDouble()

        created_proxy = SimpleNamespace(polymorphic_unresolved=False)
        created_port = SimpleNamespace(proxy_attribute=created_proxy, update_proxy_attribute=MagicMock())
        prim_model = PrimModel.__new__(PrimModel)
        prim_model.create_input_port = MagicMock(return_value=created_port)

        result = PrimModel.create_port(prim_model, source_port)

        self.assertIs(result, created_port)
        self.assertTrue(created_proxy.polymorphic_unresolved)
        created_port.update_proxy_attribute.assert_called_once_with(created_proxy)

    async def test_proxy_attribute_variability_metadata_is_pickle_safe(self) -> None:
        """Proxy metadata should not store raw Sdf.Variability objects."""
        proxy = ProxyAttribute("inputs:a", False)
        proxy._metadata["variability"] = Sdf.VariabilityUniform
        proxy._normalize_metadata_values()

        pickle.dumps(proxy._metadata)
        self.assertEqual(proxy.variability, Sdf.VariabilityUniform)

    async def test_semantic_terminal_type_uses_token_for_usd_authoring(self) -> None:
        """MaterialX terminal semantics remain authorable as valid USD token ports."""
        proxy = ProxyAttribute("inputs:edf", False)
        proxy.type_name = "EDF"

        metadata = AttributeMetadata(proxy, SimpleNamespace(path=Sdf.Path("/World/Looks/Material/Volume")))

        self.assertEqual(proxy.type_name, "EDF")
        self.assertEqual(metadata.type_name, Sdf.ValueTypeNames.Token)

    async def test_real_materialx_volume_terminal_inputs_are_authored_as_tokens(self) -> None:
        """The ND_volume EDF/VDF lazy-input path must only send valid types to USD."""
        plugin = MaterialXPlugin(load_catalog=False)
        shader = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/VolumeTerminalType"))
        shader.CreateIdAttr("ND_volume")
        model = ShaderModel(shader.GetPrim(), "mtlx", self._usd_context, plugin, None)
        try:
            self.assertTrue(model.valid, "ND_volume must resolve from the runtime MaterialX SDR registry")
            for terminal_name in ("edf", "vdf"):
                with self.subTest(terminal_name=terminal_name):
                    path = shader.GetPath().AppendProperty(f"{UsdShade.Tokens.inputs}{terminal_name}")
                    port = model._inputs.get_child_by_path(path)
                    self.assertIsNotNone(port)
                    self.assertEqual(port.proxy_attribute.type_name.lower(), terminal_name)
                    self.assertEqual(port.type, Sdf.ValueTypeNames.Token)
                    self.assertTrue(port.create_port())
                    self.assertEqual(self._stage.GetAttributeAtPath(path).GetTypeName(), Sdf.ValueTypeNames.Token)
        finally:
            model.destroy()
            plugin.destroy()

    async def test_proxy_attribute_token_array_metadata_is_pickle_safe(self) -> None:
        """USD token-array metadata should be converted to Python values."""
        attr = self._stage.DefinePrim("/World/Looks/TokenArraySource").CreateAttribute(
            "inputs:mode", Sdf.ValueTypeNames.Token
        )
        attr.SetMetadata("allowedTokens", Vt.TokenArray(["a", "b"]))

        proxy = ProxyAttribute("inputs:mode", False, attribute=attr)

        pickle.dumps(proxy._metadata)
        self.assertEqual(proxy._metadata.get("allowedTokens"), ["a", "b"])

    async def test_proxy_attribute_update_keeps_metadata_pickle_safe(self) -> None:
        """Merged USD metadata should be normalized too."""
        attr = self._stage.DefinePrim("/World/Looks/TokenArrayUpdate").CreateAttribute(
            "inputs:mode", Sdf.ValueTypeNames.Token
        )
        attr.SetMetadata("allowedTokens", Vt.TokenArray(["a", "b"]))
        proxy = ProxyAttribute("inputs:mode", False)

        proxy.update(attr)

        pickle.dumps(proxy._metadata)
        self.assertEqual(proxy._metadata.get("allowedTokens"), ["a", "b"])

    async def test_proxy_attribute_bytes_display_group_is_safe(self) -> None:
        """Byte metadata should not break display group normalization."""
        proxy = ProxyAttribute("inputs:a", False)
        proxy._metadata[Sdf.AttributeSpec.DisplayGroupKey] = b"Advanced"
        proxy._normalize_metadata_values()

        self.assertEqual(proxy.display_group, "Inputs:Advanced")

    async def test_proxy_attribute_update_reprefixes_input_display_group(self) -> None:
        """USD-authored bare ``displayGroup`` must keep the ``Inputs:`` prefix after update().

        Seeds ``display_group`` to a *wrong* value so a no-op ``update()``
        cannot pass this test; only metadata-merge + reprefix produces the
        expected ``Inputs:Albedo``.
        """
        shader = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/UpdateInput"))
        usd_attr = shader.CreateInput("diffuse_reflection_color", Sdf.ValueTypeNames.Color3f).GetAttr()
        usd_attr.SetMetadata(Sdf.AttributeSpec.DisplayGroupKey, "Albedo")

        proxy = ProxyAttribute("inputs:diffuse_reflection_color", False)
        proxy.display_group = "Inputs:StaleSeed"

        proxy.update(usd_attr)

        self.assertEqual(proxy.display_group, "Inputs:Albedo")

    async def test_proxy_attribute_update_reprefixes_output_display_group(self) -> None:
        """USD-authored bare ``displayGroup`` on outputs must keep the ``Outputs:`` prefix."""
        shader = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/UpdateOutput"))
        usd_attr = shader.CreateOutput("out", Sdf.ValueTypeNames.Color3f).GetAttr()
        usd_attr.SetMetadata(Sdf.AttributeSpec.DisplayGroupKey, "Result")

        proxy = ProxyAttribute("outputs:out", True)
        proxy.display_group = "Outputs:StaleSeed"

        proxy.update(usd_attr)

        self.assertEqual(proxy.display_group, "Outputs:Result")

    async def test_proxy_attribute_init_prefixes_bare_usd_display_group(self) -> None:
        """Bare USD ``displayGroup`` must be prefixed on first construction too."""
        shader = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/InitInput"))
        usd_attr = shader.CreateInput("metalness", Sdf.ValueTypeNames.Float).GetAttr()
        usd_attr.SetMetadata(Sdf.AttributeSpec.DisplayGroupKey, "Reflectivity")

        proxy = ProxyAttribute("inputs:metalness", False, attribute=usd_attr)

        self.assertEqual(proxy.display_group, "Inputs:Reflectivity")

    async def test_shader_candidate_port_type_cache_reuses_sdr_nodes(self) -> None:
        """Repeated polymorphic port checks should not refetch candidate SDR nodes."""

        class _DummySdrNode:
            def __init__(self, input_type: str) -> None:
                self._input_type = input_type

            def GetShaderInput(self, name: str) -> object:
                return SimpleNamespace(type=self._input_type) if name == "a" else None

            def GetShaderOutput(self, _name: str) -> None:
                return None

            def GetShaderInputNames(self) -> list[str]:
                return ["a"]

        shader = ShaderModel.__new__(ShaderModel)
        shader._is_polymorphic = True
        shader._is_polymorphic_concrete = False
        shader._polymorphic_candidates = ("fn(float)", "fn(int)")
        shader._polymorphic_source_asset = Sdf.AssetPath("test.mdl")
        shader._candidate_sdr_nodes = {}
        shader._candidate_port_type_cache = {}

        nodes = {
            "fn(float)": _DummySdrNode("float"),
            "fn(int)": _DummySdrNode("int"),
        }
        shader._get_candidate_sdr_node = MagicMock(side_effect=lambda subidentifier: nodes[subidentifier])

        self.assertTrue(shader._is_port_type_ambiguous("a", True))
        self.assertTrue(shader._is_port_type_ambiguous("a", True))
        self.assertEqual(shader._get_candidate_port_types("a", True), ["float", "int"])

        self.assertEqual(shader._get_candidate_sdr_node.call_count, 2)

    async def test_shader_candidate_cache_clears_on_source_asset_change(self) -> None:
        """Candidate metadata cache should follow source asset changes even when candidates match."""
        shader = ShaderModel.__new__(ShaderModel)
        shader._plugin = None
        shader._prim = object()
        shader._is_polymorphic = False
        shader._is_polymorphic_concrete = True
        shader._polymorphic_candidates = ("fn(float)",)
        shader._polymorphic_source_asset = Sdf.AssetPath("old.mdl")
        shader._candidate_sdr_nodes = {"fn(float)": object()}
        shader._candidate_port_type_cache = {("fn(float)", "a", True): "float"}
        shader._resolve_polymorphic_source_asset = MagicMock(return_value=Sdf.AssetPath("new.mdl"))

        shader._sync_polymorphic_state()

        self.assertEqual(str(shader._polymorphic_source_asset), str(Sdf.AssetPath("new.mdl")))
        self.assertEqual(shader._candidate_sdr_nodes, {})
        self.assertEqual(shader._candidate_port_type_cache, {})

    async def test_shader_candidate_cache_survives_unchanged_state(self) -> None:
        """Unchanged polymorphic candidates should not drop expensive per-port metadata caches."""
        shader = ShaderModel.__new__(ShaderModel)
        shader._plugin = MagicMock()
        shader._plugin.get_polymorphic_state_for_prim.return_value = PolymorphicState(
            is_polymorphic=True,
            is_concrete=False,
            base_name="fn",
            current_subidentifier="fn(float)",
            candidates=("fn(float)", "fn(int)"),
        )
        shader._prim = object()
        shader._is_polymorphic = True
        shader._is_polymorphic_concrete = False
        shader._polymorphic_candidates = ("fn(float)", "fn(int)")
        shader._polymorphic_source_asset = Sdf.AssetPath("test.mdl")
        cached_sdr = {"fn(float)": object()}
        cached_types = {("fn(float)", "a", True): "float"}
        shader._candidate_sdr_nodes = cached_sdr.copy()
        shader._candidate_port_type_cache = cached_types.copy()
        shader._resolve_polymorphic_source_asset = MagicMock(return_value=Sdf.AssetPath("test.mdl"))

        shader._sync_polymorphic_state()

        self.assertEqual(shader._candidate_sdr_nodes, cached_sdr)
        self.assertEqual(shader._candidate_port_type_cache, cached_types)

    async def test_shader_candidate_sdr_node_failures_are_not_pinned(self) -> None:
        """Transient candidate lookup failures should be retried later in the model lifetime."""

        class _DummySdrNode:
            def GetShaderInputNames(self) -> list[str]:
                return []

            def GetShaderOutputNames(self) -> list[str]:
                return []

        shader = ShaderModel.__new__(ShaderModel)
        shader._polymorphic_source_asset = SimpleNamespace(path="test.mdl")
        shader._candidate_sdr_nodes = {}
        calls = {"count": 0}

        def _get_node(_source_asset, subidentifier: str):
            calls["count"] += 1
            return None if calls["count"] == 1 else _DummySdrNode()

        with (
            patch("omni.UsdMdl.RegistryUtils.GetShaderNode", side_effect=_get_node),
            patch(
                "omni.kit.window.material_graph.scripts.models.graph.nodes.shader.wrap_shader_node", lambda node: node
            ),
        ):
            self.assertIsNone(shader._get_candidate_sdr_node("fn(float)"))
            self.assertIsNotNone(shader._get_candidate_sdr_node("fn(float)"))

        self.assertEqual(calls["count"], 2)

    async def test_shader_preview_handles_missing_and_connected_asset_inputs(self) -> None:
        """Missing asset files remain renderable while connected assets are not previews."""

        class _AssetSdrNode:
            @staticmethod
            def GetShaderInputNames() -> list[str]:
                return ["connected", "missing"]

            @staticmethod
            def GetShaderInput(_name: str) -> object:
                return SimpleNamespace(GetType=lambda: Sdf.ValueTypeNames.Asset)

        source = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/PreviewSource"))
        source.CreateOutput("out", Sdf.ValueTypeNames.Asset)
        shader = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/Looks/PreviewTarget"))
        connected = shader.CreateInput("connected", Sdf.ValueTypeNames.Asset)
        connected.ConnectToSource(source.ConnectableAPI(), "out")
        shader.CreateInput("missing", Sdf.ValueTypeNames.Asset).Set(Sdf.AssetPath("missing-preview.png"))

        model = ShaderModel.__new__(ShaderModel)
        model._prim = shader.GetPrim()
        model._sdr_node = _AssetSdrNode()

        # An unresolved asset has no resolved path, but must not invalidate or hide the node.
        self.assertEqual(model._get_preview_texture_path(), "")

    async def test_shader_preview_and_tooltip_delegation(self) -> None:
        """Preview settings, delegated items, and unresolved overloads have stable presentation."""
        model = ShaderModel.__new__(ShaderModel)
        model._prim_path = Sdf.Path("/World/Looks/Shader")
        model._type = UsdShade.Shader
        model._description = "test shader"
        model._is_polymorphic = True
        model._is_polymorphic_concrete = False
        model._polymorphic_candidates = ("fn(float)", "fn(color3f)")
        model._get_preview_texture_path = MagicMock(return_value="preview.png")
        item = SimpleNamespace(preview="item.png", tooltip_text="item tooltip")

        with patch.object(Settings, "preview_texture_input", return_value=False):
            self.assertIsNone(ShaderModel.preview.fget(model))
        with patch.object(Settings, "preview_texture_input", return_value=True):
            self.assertEqual(ShaderModel.preview.fget(model), "preview.png")
            self.assertEqual(ShaderModel.preview.fget(model, item), "item.png")

        tooltip = ShaderModel.tooltip_text.fget(model)
        self.assertIn("Polymorphic State:\tunresolved", tooltip)
        self.assertIn("fn(float)", tooltip)
        self.assertEqual(ShaderModel.tooltip_text.fget(model, item), "item tooltip")

    async def test_shader_candidate_ambiguity_boundaries(self) -> None:
        """Candidate ambiguity fails safe when metadata is absent or inconsistent."""
        model = ShaderModel.__new__(ShaderModel)
        model._is_polymorphic = False
        model._is_polymorphic_concrete = False
        model._polymorphic_candidates = ()
        self.assertFalse(model._is_port_type_ambiguous("a", True))

        model._is_polymorphic = True
        self.assertTrue(model._is_port_type_ambiguous("a", True))
        model._polymorphic_candidates = ("one",)
        self.assertFalse(model._is_port_type_ambiguous("a", True))
        model._polymorphic_candidates = ("one", "two")
        model._has_polymorphic_source_asset = MagicMock(return_value=False)
        self.assertTrue(model._is_port_type_ambiguous("a", True))

        model._has_polymorphic_source_asset.return_value = True
        model._get_candidate_port_type = MagicMock(side_effect=["float", None])
        self.assertTrue(model._is_port_type_ambiguous("a", True))
