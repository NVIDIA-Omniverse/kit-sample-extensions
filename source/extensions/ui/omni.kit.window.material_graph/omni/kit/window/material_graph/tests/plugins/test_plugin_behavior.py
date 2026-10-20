# pylint: disable=relative-beyond-top-level,protected-access
from types import SimpleNamespace
from unittest.mock import patch

import omni.UsdMdl
from pxr import Sdf, Sdr, UsdShade

from ...scripts.config.paths import Paths
from ...scripts.plugins.impl.materialx.plugin import MaterialXPlugin
from ...scripts.plugins.impl.mdl.plugin import MdlPlugin
from ...scripts.plugins.impl.usd.plugin import UsdPlugin
from ...scripts.settings.settings import Settings
from ...scripts.utils.sdr_wrappers import resolve_property_display_type_name
from ..base import MaterialGraphTestBase


class _DummyTypeIndicator:
    """Minimal SDR type indicator test double."""

    def __init__(self, type_name: str = "", ndr_type: str = "", sdr_type: str = "", has_sdf_type: bool = False) -> None:
        self._type_name = type_name
        self._ndr_type = ndr_type
        self._sdr_type = sdr_type or type_name
        self._has_sdf_type = has_sdf_type

    def GetNdrType(self) -> str:
        return self._ndr_type

    def GetSdrType(self) -> str:
        return self._sdr_type

    def HasSdfType(self) -> bool:
        return self._has_sdf_type

    def GetSdfType(self) -> str:
        return self._type_name or self._sdr_type


class _DummyShaderProperty:
    """Minimal SDR shader property test double."""

    def __init__(
        self,
        type_name: str = "",
        *,
        ndr_type: str = "",
        sdr_type: str = "",
        metadata: dict | None = None,
    ) -> None:
        self._indicator = _DummyTypeIndicator(type_name, ndr_type, sdr_type, type_name == "token")
        self._metadata = metadata or {}

    def GetTypeAsSdfType(self) -> _DummyTypeIndicator:
        return self._indicator

    def GetMetadata(self) -> dict:
        return self._metadata


class _DummySdrNode:
    """Minimal SDR node test double."""

    def __init__(
        self,
        identifier: str = "mdl::dummy",
        input_types: list[str] | None = None,
        output_types: list[str] | None = None,
        *,
        label: str = "",
        inputs: list[str] | None = None,
        metadata: dict | None = None,
    ) -> None:
        self._identifier = identifier
        self._label = label
        self._metadata = metadata or {}
        self._input_names = inputs or [f"in_{index}" for index in range(len(input_types or []))]
        self._output_names = [f"out_{index}" for index in range(len(output_types or []))]
        self._inputs = {
            name: _DummyShaderProperty(type_name) for name, type_name in zip(self._input_names, input_types or [])
        }
        self._outputs = {
            name: _DummyShaderProperty(type_name) for name, type_name in zip(self._output_names, output_types or [])
        }

    def GetMetadata(self) -> dict:
        return self._metadata

    def GetIdentifier(self) -> str:
        return self._identifier

    def GetHelp(self) -> str:
        return "dummy"

    def GetResolvedImplementationURI(self) -> str:
        return ""

    def GetLabel(self) -> str:
        return self._label

    def GetShaderInputNames(self) -> list[str]:
        return list(self._input_names)

    def GetShaderOutputNames(self) -> list[str]:
        return list(self._output_names)

    def GetShaderInput(self, name: str) -> _DummyShaderProperty:
        return self._inputs[name]

    def GetShaderOutput(self, name: str) -> _DummyShaderProperty:
        return self._outputs[name]


class _DummyShaderItem:
    """Minimal shader item used by polymorphic catalog build helper tests."""

    def __init__(self, family: str = "math:ops") -> None:
        self.family = family
        self.icon = ""
        self.icon_color = 0
        self.extra_mime_data = {}


class TestPluginBehavior(MaterialGraphTestBase):
    """Plugin helper behaviors and edge cases."""

    def _create_mdl_port_model(
        self,
        type_name: object,
        render_type: object = None,
        variability: object = Sdf.VariabilityVarying,
        name: str = "inputs:in",
    ) -> SimpleNamespace:
        """Create a minimal model carrying MDL proxy-attribute type metadata."""
        return SimpleNamespace(
            prim=None,
            parent=None,
            proxy_attribute=SimpleNamespace(
                name=name,
                type_name=type_name,
                render_type=render_type,
                connectability=UsdShade.Tokens.full,
                variability=variability,
                mdl_struct_type=None,
                mdl_symbol=None,
                mdl_array_element_type=None,
            ),
        )

    @staticmethod
    def _create_unresolved_interface_model(
        type_name: object,
        candidates: list[str],
        *,
        name: str = "inputs:in",
        variability: object = Sdf.VariabilityVarying,
    ) -> SimpleNamespace:
        """Create a minimal unresolved interface model with candidate type names."""
        return SimpleNamespace(
            prim=None,
            parent=None,
            proxy_attribute=SimpleNamespace(
                name=name,
                type_name=type_name,
                render_type=None,
                connectability=UsdShade.Tokens.full,
                variability=variability,
                mdl_struct_type=None,
                mdl_symbol=None,
                mdl_array_element_type=None,
                polymorphic_unresolved=True,
            ),
            _get_candidate_port_types=lambda: candidates,
        )

    async def test_materialx_channel_parsing(self) -> None:
        """MaterialX channel parsing should be robust for non-numeric suffixes."""
        parser = MaterialXPlugin._get_texture_channels_from_name
        self.assertEqual(parser("Image Float"), 1)
        self.assertEqual(parser("Image Float3"), 3)
        self.assertIsNone(parser("Image Color"))
        self.assertIsNone(parser(""))

    async def test_usd_preview_surface_identifier_detection(self) -> None:
        """UsdPlugin should detect UsdPreviewSurface by identifier."""
        plugin = UsdPlugin(load_catalog=False)

        class DummyNode:
            """Minimal SDR node stub."""

            def GetIdentifier(self) -> str:
                """Return the shader identifier."""
                return "UsdPreviewSurface"

            def GetName(self) -> str:
                """Return the node name."""
                return ""

            def GetResolvedImplementationURI(self) -> str:
                """Return the implementation URI."""
                return ""

        with patch("omni.UsdMdl.RegistryUtils.GetShaderNodeForPrim", return_value=DummyNode()):
            self.assertTrue(plugin.is_supported_prim(object()))

    async def test_usd_unresolved_id_shader_remains_supported(self) -> None:
        """Universal should retain unresolved ID-authored shaders for fallback display and validation."""
        plugin = UsdPlugin(load_catalog=False)
        shader = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/MissingUniversalNode"))
        shader.SetShaderId("MissingUniversalNode")

        with patch("omni.UsdMdl.RegistryUtils.GetShaderNodeForPrim", return_value=None):
            self.assertTrue(plugin.is_supported_prim(shader.GetPrim()))

    async def test_usd_unresolved_materialx_shader_stays_out_of_universal(self) -> None:
        """Universal should not claim unresolved MaterialX identifiers."""
        plugin = UsdPlugin(load_catalog=False)
        shader = UsdShade.Shader.Define(self._stage, Sdf.Path("/World/MissingMaterialXNode"))
        shader.SetShaderId("ND_missing_materialx_node")

        with patch("omni.UsdMdl.RegistryUtils.GetShaderNodeForPrim", return_value=None):
            self.assertFalse(plugin.is_supported_prim(shader.GetPrim()))

    async def test_materialx_empty_catalog(self) -> None:
        """MaterialX plugin should handle empty catalogs."""
        plugin = MaterialXPlugin(load_catalog=False)

        class DummyRegistry:
            """Minimal SDR registry stub with no nodes."""

            def GetShaderNodeNames(self):
                return []

        with patch(
            f"{Paths.MODULE_ID}.scripts.plugins.impl.materialx.plugin.SdrRegistryWrapper",
            return_value=DummyRegistry(),
        ):
            plugin.build_catalog_items()
            self.assertEqual(plugin._catalog_items, [])

    async def test_materialx_registry_unavailable_logs_warning(self) -> None:
        """MaterialX plugin should warn when registry is unavailable."""
        plugin = MaterialXPlugin(load_catalog=False)
        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.plugins.impl.materialx.plugin.SdrRegistryWrapper",
                side_effect=RuntimeError("boom"),
            ),
            patch(
                f"{Paths.MODULE_ID}.scripts.plugins.impl.materialx.plugin.logger.warning",
                autospec=True,
            ) as log_warn,
        ):
            plugin.build_catalog_items()
            self.assertEqual(plugin._catalog_items, [])
            self.assertTrue(any("registry unavailable" in str(call.args[0]) for call in log_warn.call_args_list))

    async def test_materialx_node_enumeration_failure_logs_warning(self) -> None:
        """MaterialX plugin should warn on node enumeration errors."""
        plugin = MaterialXPlugin(load_catalog=False)

        class DummyRegistry:
            """Registry stub that raises for node enumeration."""

            def GetShaderNodeNames(self):
                raise RuntimeError("boom")

        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.plugins.impl.materialx.plugin.SdrRegistryWrapper",
                return_value=DummyRegistry(),
            ),
            patch(
                f"{Paths.MODULE_ID}.scripts.plugins.impl.materialx.plugin.logger.warning",
                autospec=True,
            ) as log_warn,
        ):
            plugin.build_catalog_items()
            self.assertEqual(plugin._catalog_items, [])
            self.assertTrue(any("node enumeration failed" in str(call.args[0]) for call in log_warn.call_args_list))

    async def test_mdl_registry_adds_once_per_signature(self) -> None:
        """MDL plugin should not re-register identical module lists."""
        plugin = MdlPlugin(load_catalog=False)
        mdl_path = str(Paths.DATA_PATH / "tests" / "mdl" / "test_int.mdl")
        with (
            patch.object(Settings, "get_mdl_catalog_modules", autospec=True, return_value=[mdl_path]),
            patch("pxr.Ar.GetResolver") as resolver,
            patch("omni.UsdMdl.RegistryUtils.AddModulesToRegistry") as add_modules,
        ):
            resolver.return_value.Resolve.return_value = mdl_path
            plugin.build_catalog_items()
            plugin.build_catalog_items()
            self.assertEqual(add_modules.call_count, 1)

    async def test_mdl_unresolved_path_logs_warning(self) -> None:
        """MDL plugin should warn when module paths cannot resolve."""
        plugin = MdlPlugin(load_catalog=False)
        with (
            patch.object(Settings, "get_mdl_catalog_modules", autospec=True, return_value=["missing.mdl"]),
            patch("pxr.Ar.GetResolver") as resolver,
            patch(
                f"{Paths.MODULE_ID}.scripts.plugins.impl.mdl.plugin.logger.warning",
                autospec=True,
            ) as log_warn,
        ):
            resolver.return_value.Resolve.return_value = ""
            plugin.build_catalog_items()
            self.assertTrue(any("cannot be resolved" in str(call.args[0]) for call in log_warn.call_args_list))

    async def test_mdl_registry_add_modules_failure_logs_warning(self) -> None:
        """MDL plugin should warn when registry registration fails."""
        plugin = MdlPlugin(load_catalog=False)
        with (
            patch.object(Settings, "get_mdl_catalog_modules", autospec=True, return_value=["test.mdl"]),
            patch("pxr.Ar.GetResolver") as resolver,
            patch("omni.UsdMdl.RegistryUtils.AddModulesToRegistry", side_effect=RuntimeError("boom")),
            patch(
                f"{Paths.MODULE_ID}.scripts.plugins.impl.mdl.plugin.logger.warning",
                autospec=True,
            ) as log_warn,
        ):
            resolver.return_value.Resolve.return_value = "resolved"
            plugin.build_catalog_items()
            self.assertEqual(plugin._catalog_items, [])
            self.assertTrue(
                any("failed to register MDL modules" in str(call.args[0]) for call in log_warn.call_args_list)
            )

    async def test_mdl_unused_annotation_excluded_by_default(self) -> None:
        """MDL nodes annotated as unused should be excluded from catalog by default."""
        plugin = MdlPlugin(load_catalog=False)

        sdr_node = _DummySdrNode(metadata={omni.UsdMdl.Metadata.Annotation: "{'unused': True}"})
        self.assertIsNone(plugin._create_shader_item("Dummy", sdr_node))

    async def test_malformed_mdl_annotations_do_not_abort_catalog_item(self) -> None:
        """Malformed top-level and nested annotations are isolated to their node."""
        plugin = MdlPlugin(load_catalog=False)
        malformed_values = ["[]", "42", "{'thumbnail': [], 'icon': 3, 'ui_order': 'bad'}"]

        for raw_annotations in malformed_values:
            with self.subTest(raw_annotations=raw_annotations):
                sdr_node = _DummySdrNode(metadata={omni.UsdMdl.Metadata.Annotation: raw_annotations})
                self.assertIsNotNone(plugin._create_shader_item("Dummy", sdr_node))

    async def test_mdl_can_connect_supported_builtin_type_conversions(self) -> None:
        """MDL-compatible builtin type conversions should pass editor validation."""
        plugin = MdlPlugin(load_catalog=False)
        accepted_pairs = [
            (Sdf.ValueTypeNames.Color3f, Sdf.ValueTypeNames.Float),
            (Sdf.ValueTypeNames.Color3f, Sdf.ValueTypeNames.Float3),
            (Sdf.ValueTypeNames.Float, Sdf.ValueTypeNames.Float3),
            (Sdf.ValueTypeNames.Int, Sdf.ValueTypeNames.Float),
            (Sdf.ValueTypeNames.Bool, Sdf.ValueTypeNames.Float),
            (Sdf.ValueTypeNames.Float, Sdf.ValueTypeNames.Color3f),
            (Sdf.ValueTypeNames.Float3, Sdf.ValueTypeNames.Color3f),
        ]

        for source_type, target_type in accepted_pairs:
            with self.subTest(source_type=str(source_type), target_type=str(target_type)):
                # Distinct render_type values exercise the NO_MATCH -> UNKNOWN conversion path.
                self.assertTrue(
                    plugin.can_connect(
                        self._create_mdl_port_model(source_type, str(source_type)),
                        self._create_mdl_port_model(target_type, str(target_type)),
                    )
                )

    async def test_mdl_unresolved_interface_candidate_matching(self) -> None:
        """Unresolved interface ports should use candidate types for compatibility checks."""
        plugin = MdlPlugin(load_catalog=False)
        unresolved_float = self._create_unresolved_interface_model(Sdf.ValueTypeNames.Float, ["float"])
        unresolved_float3 = self._create_unresolved_interface_model(Sdf.ValueTypeNames.Float3, ["float3"])
        unresolved_bool = self._create_unresolved_interface_model(Sdf.ValueTypeNames.Bool, ["bool"])
        unresolved_int = self._create_unresolved_interface_model(Sdf.ValueTypeNames.Int, ["int"])
        unresolved_construct_color = self._create_unresolved_interface_model(
            Sdf.ValueTypeNames.Float,
            ["float", "float3", "::base::texture_return"],
        )
        concrete_float3 = self._create_mdl_port_model(Sdf.ValueTypeNames.Float3, "float3")
        concrete_color = self._create_mdl_port_model(Sdf.ValueTypeNames.Color3f, "color3f", name="outputs:out")
        concrete_bool = self._create_mdl_port_model(Sdf.ValueTypeNames.Bool, "bool", name="outputs:out")
        concrete_int = self._create_mdl_port_model(Sdf.ValueTypeNames.Int, "int", name="outputs:out")
        material_struct = self._create_mdl_port_model(
            Sdf.ValueTypeNames.Token,
            omni.UsdMdl.Types.Struct,
            name="outputs:out",
        )
        material_struct.proxy_attribute.mdl_struct_type = "material"
        material_struct.proxy_attribute.mdl_symbol = "::material"
        texture_return_struct = self._create_mdl_port_model(
            Sdf.ValueTypeNames.Token,
            omni.UsdMdl.Types.Struct,
            name="outputs:out",
        )
        texture_return_struct.proxy_attribute.mdl_struct_type = "texture_return"
        texture_return_struct.proxy_attribute.mdl_symbol = "::base::texture_return"
        texture_return_symbol_only = self._create_mdl_port_model(
            Sdf.ValueTypeNames.Token,
            None,
            name="outputs:out",
        )
        texture_return_symbol_only.proxy_attribute.mdl_symbol = "::base::texture_return"
        texture_return_symbol_preferred = self._create_mdl_port_model(
            Sdf.ValueTypeNames.Token,
            omni.UsdMdl.Types.Struct,
            name="outputs:out",
        )
        texture_return_symbol_preferred.proxy_attribute.mdl_struct_type = "user"
        texture_return_symbol_preferred.proxy_attribute.mdl_symbol = "::base::texture_return"

        self.assertTrue(plugin._can_connect_unresolved_interface_models(unresolved_float, concrete_float3))
        self.assertTrue(plugin._can_connect_unresolved_interface_models(unresolved_float, unresolved_float3))
        self.assertTrue(plugin._can_connect_unresolved_interface_models(unresolved_float, unresolved_float))
        self.assertTrue(plugin._can_connect_unresolved_interface_models(unresolved_bool, unresolved_bool))
        self.assertTrue(plugin._can_connect_unresolved_interface_models(concrete_color, unresolved_construct_color))
        self.assertFalse(plugin._can_connect_unresolved_interface_models(material_struct, unresolved_construct_color))
        self.assertTrue(plugin._can_connect_unresolved_interface_models(concrete_int, unresolved_float))
        self.assertTrue(
            plugin._can_connect_unresolved_interface_models(texture_return_struct, unresolved_construct_color)
        )
        self.assertTrue(
            plugin._can_connect_unresolved_interface_models(texture_return_symbol_only, unresolved_construct_color)
        )
        self.assertTrue(
            plugin._can_connect_unresolved_interface_models(texture_return_symbol_preferred, unresolved_construct_color)
        )
        self.assertTrue(plugin._can_connect_unresolved_interface_models(concrete_bool, unresolved_int))
        with patch.object(plugin, "can_connect_polymorphic_models", autospec=True, return_value=True):
            self.assertTrue(plugin.can_connect(concrete_color, unresolved_construct_color))
            self.assertFalse(plugin.can_connect(material_struct, unresolved_construct_color))
            self.assertTrue(plugin.can_connect(concrete_int, unresolved_float))
            self.assertTrue(plugin.can_connect(texture_return_struct, unresolved_construct_color))
            self.assertTrue(plugin.can_connect(texture_return_symbol_only, unresolved_construct_color))
            self.assertTrue(plugin.can_connect(texture_return_symbol_preferred, unresolved_construct_color))

    async def test_mdl_unresolved_connection_permutation_matrix_matches_concrete_policy(self) -> None:
        """Every builtin direction must agree for concrete and unresolved endpoints."""
        plugin = MdlPlugin(load_catalog=False)
        type_names = ("bool", "int", "float", "float2", "float3", "float4", "color3f", "material")
        accepted_conversions = {
            ("bool", "int"),
            ("bool", "float"),
            ("int", "float"),
            ("float", "float2"),
            ("float", "float3"),
            ("float", "float4"),
            ("float", "color3f"),
            ("float3", "color3f"),
            ("color3f", "float"),
            ("color3f", "float3"),
        }

        for source_type in type_names:
            for target_type in type_names:
                expected = source_type == target_type or (source_type, target_type) in accepted_conversions
                concrete_source = self._create_mdl_port_model(source_type, source_type, name="outputs:out")
                concrete_target = self._create_mdl_port_model(target_type, target_type, name="inputs:in")
                unresolved_source = self._create_unresolved_interface_model(
                    source_type, [source_type], name="outputs:out"
                )
                unresolved_target = self._create_unresolved_interface_model(target_type, [target_type])

                with self.subTest(source_type=source_type, target_type=target_type):
                    self.assertEqual(plugin.can_connect(concrete_source, concrete_target), expected)
                    self.assertEqual(plugin.can_connect(concrete_source, unresolved_target), expected)
                    self.assertEqual(plugin.can_connect(unresolved_source, concrete_target), expected)
                    self.assertEqual(plugin.can_connect(unresolved_source, unresolved_target), expected)

        missing_candidates = self._create_unresolved_interface_model("float", [])
        concrete_float = self._create_mdl_port_model("float", "float", name="outputs:out")
        self.assertFalse(plugin.can_connect(concrete_float, missing_candidates))

    async def test_mdl_rejects_unresolved_polymorphic_source_to_uniform_input(self) -> None:
        """Unresolved polymorphic outputs should not connect to uniform inputs."""
        plugin = MdlPlugin(load_catalog=False)
        source = self._create_mdl_port_model(Sdf.ValueTypeNames.Float, "float", name="outputs:out")
        source.proxy_attribute.polymorphic_unresolved = True
        target = self._create_mdl_port_model(
            Sdf.ValueTypeNames.Float,
            "float",
            variability=Sdf.VariabilityUniform,
            name="inputs:uniformIn",
        )

        self.assertFalse(plugin.can_connect(source, target))

    async def test_mdl_single_input_constructor_catalog_group_uses_result_type_name(self) -> None:
        """Single-input construct_* overloads should collapse under the result type name."""
        plugin = MdlPlugin(load_catalog=False)

        single_input = _DummySdrNode(label="Color from float", inputs=["a"])
        multi_input = _DummySdrNode(label="Color from floats", inputs=["r", "g", "b"])

        self.assertEqual(
            plugin._polymorphic_catalog_group_name(single_input, "construct_color(float)"),
            "Color",
        )
        self.assertEqual(
            plugin._polymorphic_catalog_group_name(single_input, "::base::construct_color(float)"),
            "Color",
        )
        self.assertEqual(
            plugin._polymorphic_catalog_group_name(multi_input, "construct_color(float,float,float)"),
            "Color from floats",
        )

    async def test_mdl_struct_candidate_type_uses_mdl_struct_name(self) -> None:
        """Polymorphic candidate tooltips should show MDL type names instead of token/user/struct."""

        self.assertEqual(
            resolve_property_display_type_name(
                _DummyShaderProperty(ndr_type="user", sdr_type="::base::texture_return")
            ),
            "::base::texture_return",
        )
        self.assertEqual(
            resolve_property_display_type_name(
                _DummyShaderProperty(
                    ndr_type="struct",
                    sdr_type="struct",
                    metadata={omni.UsdMdl.Metadata.Symbol: "::base::texture_return"},
                )
            ),
            "::base::texture_return",
        )
        self.assertEqual(
            resolve_property_display_type_name(
                _DummyShaderProperty(
                    ndr_type="struct",
                    sdr_type="struct",
                    metadata={
                        Sdr.PropertyMetadata.RenderType: omni.UsdMdl.Types.Struct,
                        omni.UsdMdl.Metadata.StructType: "::base::texture_return",
                    },
                ),
            ),
            "::base::texture_return",
        )

    async def test_mdl_can_connect_rejects_unsupported_builtin_type_conversions(self) -> None:
        """Unsupported MDL builtin type conversions should remain blocked."""
        plugin = MdlPlugin(load_catalog=False)
        rejected_pairs = [
            (Sdf.ValueTypeNames.Float4, Sdf.ValueTypeNames.Color3f),
            (Sdf.ValueTypeNames.Token, Sdf.ValueTypeNames.Float),
        ]

        with patch.object(plugin, "can_connect_polymorphic_models", autospec=True, return_value=False):
            for source_type, target_type in rejected_pairs:
                with self.subTest(source_type=str(source_type), target_type=str(target_type)):
                    self.assertFalse(
                        plugin.can_connect(
                            self._create_mdl_port_model(source_type, str(source_type)),
                            self._create_mdl_port_model(target_type, str(target_type)),
                        )
                    )

    async def test_mdl_array_render_type_compares_element_metadata(self) -> None:
        """MDL array render types should compare element type and struct symbol metadata."""
        plugin = MdlPlugin(load_catalog=False)
        source = self._create_mdl_port_model(Sdf.ValueTypeNames.Token, omni.UsdMdl.Types.Array)
        target = self._create_mdl_port_model(Sdf.ValueTypeNames.Token, omni.UsdMdl.Types.Array)

        self.assertEqual(plugin.compare_render_types(source, target), plugin.RenderTypeMatch.NO_MATCH)

        source.proxy_attribute.mdl_array_element_type = "float"
        target.proxy_attribute.mdl_array_element_type = "float"
        self.assertEqual(plugin.compare_render_types(source, target), plugin.RenderTypeMatch.MATCH)

        target.proxy_attribute.mdl_array_element_type = "int"
        self.assertEqual(plugin.compare_render_types(source, target), plugin.RenderTypeMatch.NO_MATCH)

        source.proxy_attribute.mdl_array_element_type = omni.UsdMdl.Types.Struct
        target.proxy_attribute.mdl_array_element_type = omni.UsdMdl.Types.Struct
        source.proxy_attribute.mdl_struct_type = "::test::lookup_value"
        target.proxy_attribute.mdl_struct_type = "::test::lookup_value"
        source.proxy_attribute.mdl_symbol = "::test::lookup_value"
        target.proxy_attribute.mdl_symbol = "::test::lookup_value"
        self.assertEqual(plugin.compare_render_types(source, target), plugin.RenderTypeMatch.MATCH)

        target.proxy_attribute.mdl_struct_type = "::test::different_lookup_value"
        self.assertEqual(plugin.compare_render_types(source, target), plugin.RenderTypeMatch.NO_MATCH)

        source.proxy_attribute.mdl_array_element_type = omni.UsdMdl.Types.Enum
        target.proxy_attribute.mdl_array_element_type = omni.UsdMdl.Types.Enum
        source.proxy_attribute.mdl_symbol = "::test::mode"
        target.proxy_attribute.mdl_symbol = "::test::other_mode"
        self.assertEqual(plugin.compare_render_types(source, target), plugin.RenderTypeMatch.NO_MATCH)

    async def test_mdl_polymorphic_family_requires_consistent_signature_pattern(self) -> None:
        """Mixed clamp signatures should not be registered as polymorphic."""
        plugin = MdlPlugin(load_catalog=False)

        source_asset = type("Asset", (), {"path": "test.mdl", "resolvedPath": "resolved.mdl"})()
        clamp_subidentifiers = [
            "clamp(float2,float2,float2)",
            "clamp(float2,float2,float)",
        ]
        sdr_nodes = {
            ("clamp", source_asset.path): [
                (
                    _DummySdrNode(clamp_subidentifiers[0], ["float2", "float2", "float2"], ["float2"]),
                    source_asset,
                    clamp_subidentifiers[0],
                ),
                (
                    _DummySdrNode(clamp_subidentifiers[1], ["float2", "float2", "float"], ["float2"]),
                    source_asset,
                    clamp_subidentifiers[1],
                ),
            ]
        }
        captured_items = []

        with (
            patch.object(plugin, "_create_shader_item", autospec=True, return_value=_DummyShaderItem()),
            patch.object(
                plugin,
                "_add_shader_item_to_groups",
                autospec=True,
                side_effect=lambda _groups, shader_item: captured_items.append(shader_item),
            ),
        ):
            plugin._build_polymorphic_entries(sdr_nodes, groups={}, polymorphic_enabled=True)

        self.assertEqual(len(captured_items), 1)
        item = captured_items[0]
        self.assertNotIn("is_polymorphic", item.extra_mime_data)
        self.assertEqual(
            item.extra_mime_data.get("variant_subidentifiers"),
            sorted(clamp_subidentifiers),
        )
        output_types = item.extra_mime_data.get("variant_output_types", {})
        self.assertEqual(output_types.get("clamp(float2,float2,float2)"), "-> float2")
        self.assertEqual(output_types.get("clamp(float2,float2,float)"), "-> float2")
        self.assertTrue(item.extra_mime_data.get("requires_variant_selection"))

    async def test_mdl_polymorphic_family_accepts_consistent_signature_pattern(self) -> None:
        """Uniform add signatures should be registered as polymorphic."""
        plugin = MdlPlugin(load_catalog=False)

        source_asset = type("Asset", (), {"path": "test.mdl", "resolvedPath": "resolved.mdl"})()
        add_subidentifiers = [
            "add(float,float,float)",
            "add(float3,float3,float3)",
        ]
        sdr_nodes = {
            ("add", source_asset.path): [
                (
                    _DummySdrNode(add_subidentifiers[0], ["float", "float", "float"], ["float"]),
                    source_asset,
                    add_subidentifiers[0],
                ),
                (
                    _DummySdrNode(add_subidentifiers[1], ["float3", "float3", "float3"], ["float3"]),
                    source_asset,
                    add_subidentifiers[1],
                ),
            ]
        }
        captured_items = []

        with (
            patch.object(plugin, "_create_shader_item", autospec=True, return_value=_DummyShaderItem()),
            patch.object(
                plugin,
                "_add_shader_item_to_groups",
                autospec=True,
                side_effect=lambda _groups, shader_item: captured_items.append(shader_item),
            ),
        ):
            plugin._build_polymorphic_entries(sdr_nodes, groups={}, polymorphic_enabled=True)

        self.assertEqual(len(captured_items), 1)
        self.assertTrue(captured_items[0].extra_mime_data.get("is_polymorphic", False))
        self.assertEqual(captured_items[0].extra_mime_data.get("polymorphic_base_name"), "add")

    async def test_mdl_single_overload_family_has_no_unbound_variant_error(self) -> None:
        """Single-overload families should build without relying on polymorphic locals."""
        plugin = MdlPlugin(load_catalog=False)

        source_asset = type("Asset", (), {"path": "test.mdl", "resolvedPath": "resolved.mdl"})()
        subidentifier = "single(float)"
        sdr_nodes = {("single", source_asset.path): [(_DummySdrNode(subidentifier), source_asset, subidentifier)]}
        captured_items = []

        with (
            patch.object(plugin, "_create_shader_item", autospec=True, return_value=_DummyShaderItem()),
            patch.object(
                plugin,
                "_add_shader_item_to_groups",
                autospec=True,
                side_effect=lambda _groups, shader_item: captured_items.append(shader_item),
            ),
        ):
            plugin._build_polymorphic_entries(sdr_nodes, groups={}, polymorphic_enabled=True)

        self.assertEqual(len(captured_items), 1)
        self.assertEqual(captured_items[0].extra_mime_data.get("variant_subidentifiers"), [subidentifier])
        self.assertFalse(captured_items[0].extra_mime_data.get("requires_variant_selection"))

    async def test_usd_plugin_reload_recovers_after_failure(self) -> None:
        """UsdPlugin should retry resolver after reload."""
        plugin = UsdPlugin(load_catalog=False)
        mdl_path = str(Paths.DATA_PATH / "tests" / "mdl" / "test_int.mdl")
        with (
            patch("pxr.Ar.GetResolver") as resolver,
            patch("omni.UsdMdl.RegistryUtils.AddModuleToRegistry") as add_module,
            patch("omni.UsdMdl.RegistryUtils.GetSubIdentifiersForAsset", return_value=[]),
        ):
            resolver.return_value.Resolve.return_value = ""
            plugin.build_catalog_items()
            plugin.reload()
            resolver.return_value.Resolve.return_value = mdl_path
            plugin.build_catalog_items()
            self.assertTrue(add_module.called)

    async def test_usd_preview_surface_unresolved_logs_warning(self) -> None:
        """UsdPlugin should warn when UsdPreviewSurface cannot resolve."""
        plugin = UsdPlugin(load_catalog=False)
        with (
            patch("pxr.Ar.GetResolver") as resolver,
            patch(
                f"{Paths.MODULE_ID}.scripts.plugins.impl.usd.plugin.logger.warning",
                autospec=True,
            ) as log_warn,
        ):
            resolver.return_value.Resolve.return_value = ""
            plugin.build_catalog_items()
            self.assertEqual(plugin._catalog_items, [])
            self.assertTrue(any("could not be resolved" in str(call.args[0]) for call in log_warn.call_args_list))

    async def test_usd_preview_surface_register_failure_logs_warning(self) -> None:
        """UsdPlugin should warn when registry registration fails."""
        plugin = UsdPlugin(load_catalog=False)
        with (
            patch("pxr.Ar.GetResolver") as resolver,
            patch("omni.UsdMdl.RegistryUtils.AddModuleToRegistry", side_effect=RuntimeError("boom")),
            patch(
                f"{Paths.MODULE_ID}.scripts.plugins.impl.usd.plugin.logger.warning",
                autospec=True,
            ) as log_warn,
        ):
            resolver.return_value.Resolve.return_value = "resolved"
            plugin.build_catalog_items()
            self.assertEqual(plugin._catalog_items, [])
            self.assertTrue(
                any("failed to register UsdPreviewSurface.mdl" in str(call.args[0]) for call in log_warn.call_args_list)
            )
