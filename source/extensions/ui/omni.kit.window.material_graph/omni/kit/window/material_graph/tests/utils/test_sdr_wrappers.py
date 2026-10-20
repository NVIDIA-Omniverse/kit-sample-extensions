import omni.kit.test
from pxr import Sdf

from ...scripts.utils.sdr_wrappers import (
    mdl_polymorphic_family_key,
    mdl_type_matches_polymorphic_constraint,
    mdl_type_polymorphic_constraint_score,
    mdl_types_match,
    mdl_value_type_conversion_score,
    mdl_value_types_are_compatible,
    parse_mdl_subidentifier_argument_types,
    resolve_output_value_type,
    resolve_property_type_name,
    resolve_sdf_value_type_name,
    wrap_shader_node,
)


class _DummyTypeIndicatorWithNdrType:
    def GetNdrType(self) -> str:
        return "color3f"

    def GetSdfType(self) -> str:
        return "token"


class _DummyTypeIndicatorLegacySdr:
    def HasSdfType(self) -> bool:
        return False

    def GetSdrType(self) -> str:
        return "terminal"


class _DummyProperty:
    def __init__(self, indicator: object) -> None:
        self._indicator = indicator

    def GetTypeAsSdfType(self) -> object:
        return self._indicator


class _DummyNodeMissingApis:
    def __init__(self) -> None:
        self.identifier = "node-id"

    def GetInputNames(self):
        return ["legacyInA", "legacyInB"]

    def GetOutputNames(self):
        return ["legacyOut"]

    def GetIdentifier(self) -> str:
        return self.identifier


class _DummyNodeShaderApis:
    def GetShaderInputNames(self):
        return ["shaderIn"]

    def GetShaderOutputNames(self):
        return ["shaderOut"]


class _DummyLabelNode:
    def __init__(self, label: str) -> None:
        self._label = label

    def GetLabel(self) -> str:
        return self._label


class TestSdrWrappers(omni.kit.test.AsyncTestCase):
    async def test_type_name_resolution_prefers_ndr_and_supports_legacy(self) -> None:
        self.assertEqual(resolve_property_type_name(_DummyProperty(_DummyTypeIndicatorWithNdrType())), "color3f")
        self.assertEqual(resolve_property_type_name(_DummyProperty(_DummyTypeIndicatorLegacySdr())), "terminal")

    async def test_output_type_resolution_has_token_fallback(self) -> None:
        value_type = resolve_output_value_type(_DummyProperty(_DummyTypeIndicatorLegacySdr()))
        self.assertEqual(value_type, Sdf.ValueTypeNames.Token)

    async def test_sdr_semantic_types_use_token_for_usd_authoring(self) -> None:
        """Renderer semantic names must never become invalid USD attribute types."""
        for semantic_type in ("EDF", "VDF", "surfaceshader", "volumeshader", "unknown-struct"):
            with self.subTest(semantic_type=semantic_type):
                self.assertEqual(resolve_sdf_value_type_name(semantic_type), Sdf.ValueTypeNames.Token)

        self.assertEqual(resolve_sdf_value_type_name("color3f"), Sdf.ValueTypeNames.Color3f)

    async def test_parse_mdl_subidentifier_argument_types(self) -> None:
        self.assertEqual(parse_mdl_subidentifier_argument_types("construct_color()"), [])
        self.assertEqual(
            parse_mdl_subidentifier_argument_types("construct_color(::base::texture_return)"),
            ["::base::texture_return"],
        )
        self.assertEqual(
            parse_mdl_subidentifier_argument_types("construct_color(float,float3,color)"),
            ["float", "float3", "color"],
        )
        self.assertEqual(
            parse_mdl_subidentifier_argument_types("construct_color(unknown_type,123)"),
            ["unknown_type", "123"],
        )
        for subidentifier in (
            "",
            "construct_color",
            "construct_color(",
            "construct_color(,)",
            "construct_color(float,)",
        ):
            with self.subTest(subidentifier=subidentifier):
                with self.assertRaises(ValueError):
                    parse_mdl_subidentifier_argument_types(subidentifier)
        with self.assertRaises(TypeError):
            parse_mdl_subidentifier_argument_types(None)

    async def test_mdl_types_match_base_qualified_local_names(self) -> None:
        self.assertTrue(mdl_types_match("::base::texture_return", "::base::texture_return"))
        self.assertTrue(mdl_types_match("texture_return", "texture_return"))
        self.assertTrue(mdl_types_match("texture_return", "::base::texture_return"))
        self.assertFalse(mdl_types_match("::df::light_profile", "light_profile"))
        self.assertFalse(mdl_types_match("material", "::base::texture_return"))
        self.assertFalse(mdl_types_match("uniform float", "float"))
        self.assertTrue(mdl_types_match("Texture_Return", "texture_return"))

    async def test_mdl_builtin_connection_permutation_matrix(self) -> None:
        """Concrete and polymorphic checks must agree for every builtin type direction."""
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
                with self.subTest(source_type=source_type, target_type=target_type):
                    self.assertEqual(mdl_value_types_are_compatible(source_type, target_type), expected)
                    self.assertEqual(mdl_value_type_conversion_score(source_type, target_type) is not None, expected)
                    self.assertEqual(
                        mdl_type_polymorphic_constraint_score(target_type, source_type, is_input=True) is not None,
                        expected,
                    )
                    self.assertEqual(
                        mdl_type_polymorphic_constraint_score(source_type, target_type, is_input=False) is not None,
                        expected,
                    )
                    self.assertEqual(
                        mdl_type_matches_polymorphic_constraint(target_type, source_type, is_input=True), expected
                    )

        self.assertEqual(mdl_type_polymorphic_constraint_score("int", "int", is_input=True), 0)
        self.assertEqual(mdl_type_polymorphic_constraint_score("int", "bool", is_input=True), 1)
        self.assertEqual(mdl_type_polymorphic_constraint_score("float", "bool", is_input=True), 2)
        self.assertIsNone(mdl_type_polymorphic_constraint_score("::df::light_profile", "light_profile", True))

    async def test_mdl_polymorphic_family_keys_keep_constructor_arities_separate(self) -> None:
        """Single-input constructor families must not absorb multi-input nodes with the same base name."""
        self.assertEqual(
            mdl_polymorphic_family_key(_DummyLabelNode("Float3 from color"), "construct_float3(color)"), "Float3"
        )
        self.assertEqual(
            mdl_polymorphic_family_key(_DummyLabelNode("Float3 from int3"), "construct_float3(int3)"), "Float3"
        )
        self.assertEqual(
            mdl_polymorphic_family_key(_DummyLabelNode("Float3 from floats"), "construct_float3(float,float,float)"),
            "Float3 from floats",
        )
        self.assertEqual(
            mdl_polymorphic_family_key(_DummyLabelNode("Float2 from float"), "construct_float2(float)"), "Float2"
        )
        self.assertEqual(
            mdl_polymorphic_family_key(_DummyLabelNode("Float2 from floats"), "construct_float2(float,float)"),
            "Float2 from floats",
        )
        self.assertEqual(mdl_polymorphic_family_key(_DummyLabelNode("Absolute"), "abs(float)"), "Absolute")
        self.assertEqual(mdl_polymorphic_family_key(None, "mix(float)"), "mix")
        self.assertEqual(mdl_polymorphic_family_key(None, ""), "")

    async def test_node_wrapper_uses_legacy_name_fallback_and_delegation(self) -> None:
        wrapped = wrap_shader_node(_DummyNodeMissingApis())
        self.assertIsNotNone(wrapped)
        self.assertEqual(wrapped.GetShaderInputNames(), ["legacyInA", "legacyInB"])
        self.assertEqual(wrapped.GetShaderOutputNames(), ["legacyOut"])
        self.assertEqual(wrapped.GetIdentifier(), "node-id")

    async def test_node_wrapper_uses_shader_name_methods_when_present(self) -> None:
        wrapped = wrap_shader_node(_DummyNodeShaderApis())
        self.assertEqual(wrapped.GetShaderInputNames(), ["shaderIn"])
        self.assertEqual(wrapped.GetShaderOutputNames(), ["shaderOut"])
