import os
from unittest.mock import patch

import carb
import omni.client
import omni.kit.commands
import omni.kit.test
import omni.kit.variant.editor.variant_property_models
import omni.usd
from pxr import Gf, Sdf, Tf, Usd, UsdShade, Vt

from ..core import VariantEditorCore
from ..variant_property_models import (
    AllowedAnnoItem,
    GfMatrixAttributeModel,
    GfVecAttributeModelVariant,
    GfVecAttributeSingleChannelModelVariant,
    MdlEnumAttributeModelVariant,
    MetadataObjectModelVariant,
    SdfAssetPathArrayAttributeItemModelVariant,
    SdfAssetPathArrayAttributeSingleEntryModelVariant,
    SdfAssetPathAttributeModelVariant,
    SdfRelationshipArrayItemModelVariant,
    SdfRelationshipArraySingleEntryModelVariant,
    TfTokenAttributeModelVariant,
    UsdAttributeModelVariant,
    VariantSetModel,
    VariantSubIdentifierModel,
)
from .test_cleanup import reset_variant_editor_test_state


class TestModel(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._core = VariantEditorCore.get_instance()
        stage = Usd.Stage.CreateInMemory()
        await omni.usd.get_context().attach_stage_async(stage)
        self._core._update_context_and_stage()
        self.assertIsNotNone(self._core._stage)

    async def tearDown(self):
        await omni.usd.get_context().close_stage_async()
        await reset_variant_editor_test_state(restore_auxiliary_ui=False)

    def setup_simple_variant_case(self, path: Sdf.Path, vset_name: str) -> Usd.VariantSet:
        stage: Usd.Stage = self._core._stage
        prim = stage.GetPrimAtPath(path)
        variant_sets_api = prim.GetVariantSets()
        variant_set_api = variant_sets_api.AddVariantSet(vset_name)
        return variant_set_api

    async def test_variant_token_model(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.Token)
        allowed_tokens = ["A", "B", "C"]
        sdf_attr.allowedTokens = allowed_tokens

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())
        self.assertEqual(Vt.TokenArray(allowed_tokens), attr.GetAllMetadata()["allowedTokens"])

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)

        async def for_each_(fn):
            import asyncio

            for i in range(3):
                vname = "test" + str(i)
                if asyncio.iscoroutinefunction(fn):
                    await fn(i, vname)
                else:
                    fn(i, vname)

        await for_each_(lambda i, vname: variant_set_api.AddVariant(vname))

        model = TfTokenAttributeModelVariant(stage, [temp_path.AppendProperty("test")], True, attr.GetAllMetadata())
        options = model.get_item_children(None)
        self.assertEqual(3, len(options))
        self.assertEqual(allowed_tokens, [opt.model.as_string for opt in options])

        async def write_token(i, vname):
            self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
            variant_set_api.SetVariantSelection(vname)
            model._current_index.set_value(i)
            model._current_index_changed(model._current_index)
            self.assertEqual(chr(ord("A") + i), model.get_value_as_token())

        await for_each_(write_token)

        sdf_prim.RemoveProperty(sdf_attr)

        def test_data(i, vname):
            variant_set_api.SetVariantSelection(vname)
            self.assertEqual(chr(ord("A") + i), attr.Get())

        await for_each_(test_data)

        model.destroy()

    async def test_default_value(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)

        async def test_default_value_impl(self, i, cls):
            sdf_attr = Sdf.AttributeSpec(sdf_prim, f"test_{i}", cls)

            attr = stage.GetAttributeAtPath(temp_path.AppendProperty(f"test_{i}"))
            self.assertTrue(attr.IsValid())

            vset_name = "vset"
            variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)
            vname = "test_v"

            variant_set_api.AddVariant(vname)
            model = UsdAttributeModelVariant(
                stage,
                [temp_path.AppendProperty(f"test_{i}")],
                True,
                attr.GetAllMetadata(),
            )
            model._update_value(True)

            self.assertEqual(cls.defaultValue, model._get_obj_type_default_value(attr))

            model.destroy()

        for i, cls in enumerate(
            [
                Sdf.ValueTypeNames.Asset,
                Sdf.ValueTypeNames.AssetArray,
                Sdf.ValueTypeNames.Bool,
                Sdf.ValueTypeNames.BoolArray,
                Sdf.ValueTypeNames.Color3d,
                Sdf.ValueTypeNames.Color3dArray,
                Sdf.ValueTypeNames.Color3f,
                Sdf.ValueTypeNames.Color3fArray,
                Sdf.ValueTypeNames.Color3h,
                Sdf.ValueTypeNames.Color3hArray,
                Sdf.ValueTypeNames.Color4d,
                Sdf.ValueTypeNames.Color4dArray,
                Sdf.ValueTypeNames.Color4f,
                Sdf.ValueTypeNames.Color4fArray,
                Sdf.ValueTypeNames.Color4h,
                Sdf.ValueTypeNames.Color4hArray,
                Sdf.ValueTypeNames.Double,
                Sdf.ValueTypeNames.Double2,
                Sdf.ValueTypeNames.Double2Array,
                Sdf.ValueTypeNames.Double3,
                Sdf.ValueTypeNames.Double3Array,
                Sdf.ValueTypeNames.Double4,
                Sdf.ValueTypeNames.Double4Array,
                Sdf.ValueTypeNames.DoubleArray,
                Sdf.ValueTypeNames.Float,
                Sdf.ValueTypeNames.Float2,
                Sdf.ValueTypeNames.Float2Array,
                Sdf.ValueTypeNames.Float3,
                Sdf.ValueTypeNames.Float3Array,
                Sdf.ValueTypeNames.Float4,
                Sdf.ValueTypeNames.Float4Array,
                Sdf.ValueTypeNames.FloatArray,
                Sdf.ValueTypeNames.Frame4d,
                Sdf.ValueTypeNames.Frame4dArray,
                Sdf.ValueTypeNames.Half,
                Sdf.ValueTypeNames.Half2,
                Sdf.ValueTypeNames.Half2Array,
                Sdf.ValueTypeNames.Half3,
                Sdf.ValueTypeNames.Half3Array,
                Sdf.ValueTypeNames.Half4,
                Sdf.ValueTypeNames.Half4Array,
                Sdf.ValueTypeNames.HalfArray,
                Sdf.ValueTypeNames.Int,
                Sdf.ValueTypeNames.Int2,
                Sdf.ValueTypeNames.Int2Array,
                Sdf.ValueTypeNames.Int3,
                Sdf.ValueTypeNames.Int3Array,
                Sdf.ValueTypeNames.Int4,
                Sdf.ValueTypeNames.Int4Array,
                Sdf.ValueTypeNames.Int64,
                Sdf.ValueTypeNames.Int64Array,
                Sdf.ValueTypeNames.IntArray,
                Sdf.ValueTypeNames.Matrix2d,
                Sdf.ValueTypeNames.Matrix2dArray,
                Sdf.ValueTypeNames.Matrix3d,
                Sdf.ValueTypeNames.Matrix3dArray,
                Sdf.ValueTypeNames.Matrix4d,
                Sdf.ValueTypeNames.Matrix4dArray,
                Sdf.ValueTypeNames.Normal3d,
                Sdf.ValueTypeNames.Normal3dArray,
                Sdf.ValueTypeNames.Normal3f,
                Sdf.ValueTypeNames.Normal3fArray,
                Sdf.ValueTypeNames.Normal3h,
                Sdf.ValueTypeNames.Normal3hArray,
                Sdf.ValueTypeNames.Point3d,
                Sdf.ValueTypeNames.Point3dArray,
                Sdf.ValueTypeNames.Point3f,
                Sdf.ValueTypeNames.Point3fArray,
                Sdf.ValueTypeNames.Point3h,
                Sdf.ValueTypeNames.Point3hArray,
                Sdf.ValueTypeNames.Quatd,
                Sdf.ValueTypeNames.QuatdArray,
                Sdf.ValueTypeNames.Quatf,
                Sdf.ValueTypeNames.QuatfArray,
                Sdf.ValueTypeNames.Quath,
                Sdf.ValueTypeNames.QuathArray,
                Sdf.ValueTypeNames.String,
                Sdf.ValueTypeNames.StringArray,
                Sdf.ValueTypeNames.TexCoord2d,
                Sdf.ValueTypeNames.TexCoord2dArray,
                Sdf.ValueTypeNames.TexCoord2f,
                Sdf.ValueTypeNames.TexCoord2fArray,
                Sdf.ValueTypeNames.TexCoord2h,
                Sdf.ValueTypeNames.TexCoord2hArray,
                Sdf.ValueTypeNames.TexCoord3d,
                Sdf.ValueTypeNames.TexCoord3dArray,
                Sdf.ValueTypeNames.TexCoord3f,
                Sdf.ValueTypeNames.TexCoord3fArray,
                Sdf.ValueTypeNames.TexCoord3h,
                Sdf.ValueTypeNames.TexCoord3hArray,
                Sdf.ValueTypeNames.TimeCode,
                Sdf.ValueTypeNames.TimeCodeArray,
                Sdf.ValueTypeNames.Token,
                Sdf.ValueTypeNames.TokenArray,
                Sdf.ValueTypeNames.UChar,
                Sdf.ValueTypeNames.UCharArray,
                Sdf.ValueTypeNames.UInt,
                Sdf.ValueTypeNames.UInt64,
                Sdf.ValueTypeNames.UInt64Array,
                Sdf.ValueTypeNames.UIntArray,
                Sdf.ValueTypeNames.Vector3d,
                Sdf.ValueTypeNames.Vector3dArray,
                Sdf.ValueTypeNames.Vector3f,
                Sdf.ValueTypeNames.Vector3fArray,
                Sdf.ValueTypeNames.Vector3h,
                Sdf.ValueTypeNames.Vector3hArray,
            ]
        ):
            await test_default_value_impl(self, i, cls)

    async def test_locked(self):
        touched = False

        def mock_omni_kit_usd_layers_lock_specs(usd_context, spec_paths, hierarchy):
            nonlocal touched
            touched = True

        def mock_omni_kit_usd_layers_unlock_specs(usd_context, spec_paths, hierarchy):
            nonlocal touched
            touched = True

        @patch("omni.kit.usd.layers.unlock_specs", mock_omni_kit_usd_layers_unlock_specs)
        @patch("omni.kit.usd.layers.lock_specs", mock_omni_kit_usd_layers_lock_specs)
        async def test_locked_impl(self):
            stage: Usd.Stage = self._core._stage
            temp_path = Sdf.Path("/temp")
            self._core._update_root_prim_path("/temp")

            layer: Sdf.Layer = stage.GetRootLayer()
            sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
            sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.Int)

            attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
            self.assertTrue(attr.IsValid())

            vset_name = "vset"
            variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)
            vname = "test_v"

            variant_set_api.AddVariant(vname)
            model = UsdAttributeModelVariant(stage, [temp_path.AppendProperty("test")], True, attr.GetAllMetadata())
            model._update_value(True)

            nonlocal touched
            self.assertFalse(touched)
            model.set_locked(True)
            self.assertTrue(touched)
            touched = False
            self.assertFalse(touched)
            model.set_locked(False)
            self.assertTrue(touched)

            model.destroy()

        await test_locked_impl(self)

    @patch("omni.kit.usd.layers.is_spec_locked", return_value=True)
    async def test_write_locked(self, m):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.Int)

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)
        vname = "test_v"

        variant_set_api.AddVariant(vname)
        model = UsdAttributeModelVariant(stage, [temp_path.AppendProperty("test")], True, attr.GetAllMetadata())
        model._update_value(True)

        self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
        variant_set_api.SetVariantSelection(vname)
        model.set_value(42)
        model._set_dirty()
        self.assertEqual(0, model.get_value_as_int())

        model.destroy()

    @patch("pxr.Usd.Prim.IsInstanceProxy", return_value=True)
    async def test_write_proxy(self, m):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.Int)

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)
        vname = "test_v"

        variant_set_api.AddVariant(vname)
        model = UsdAttributeModelVariant(stage, [temp_path.AppendProperty("test")], True, attr.GetAllMetadata())
        model._update_value(True)

        self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
        variant_set_api.SetVariantSelection(vname)
        model.set_value(42)
        model._set_dirty()
        self.assertEqual(0, model.get_value_as_int())

        model.destroy()

    async def test_float(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.Double)

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)

        async def for_each_(fn):
            import asyncio

            for i in range(3):
                vname = "test" + str(i)
                if asyncio.iscoroutinefunction(fn):
                    await fn(i, vname)
                else:
                    fn(i, vname)

        await for_each_(lambda i, vname: variant_set_api.AddVariant(vname))

        model = UsdAttributeModelVariant(stage, [temp_path.AppendProperty("test")], True, attr.GetAllMetadata())
        model._update_value(True)

        async def write_value(i, vname):
            self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
            variant_set_api.SetVariantSelection(vname)
            model.begin_edit()
            model.set_value((i + 1) * 1.1)
            model.end_edit()
            self.assertEqual((i + 1) * 1.1, model.get_value_as_float())
            for _ in range(6):
                await omni.kit.app.get_app().next_update_async()

        await for_each_(write_value)

        sdf_prim.RemoveProperty(sdf_attr)

        def test_data(i, vname):
            variant_set_api.SetVariantSelection(vname)
            self.assertEqual((i + 1) * 1.1, attr.Get())

        await for_each_(test_data)

        model.destroy()

    async def test_int(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.Int)

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)

        async def for_each_(fn):
            import asyncio

            for i in range(3):
                vname = "test" + str(i)
                if asyncio.iscoroutinefunction(fn):
                    await fn(i, vname)
                else:
                    fn(i, vname)

        await for_each_(lambda i, vname: variant_set_api.AddVariant(vname))

        model = UsdAttributeModelVariant(stage, [temp_path.AppendProperty("test")], True, attr.GetAllMetadata())
        model._update_value(True)

        async def write_value(i, vname):
            self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
            variant_set_api.SetVariantSelection(vname)
            model.begin_edit()
            model.set_value((i + 1) * 1)
            model.end_edit()
            self.assertEqual((i + 1) * 1, model.get_value_as_int())

        await for_each_(write_value)

        sdf_prim.RemoveProperty(sdf_attr)

        def test_data(i, vname):
            variant_set_api.SetVariantSelection(vname)
            self.assertEqual((i + 1) * 1, attr.Get())

        await for_each_(test_data)

        model.destroy()

    async def test_soft_range(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.Int)

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())
        attr.SetCustomDataByKey("omni:kit:property:usd:soft_range_ui", Gf.Vec2i(-42, 42))

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)
        vname = "test_v"
        variant_set_api.AddVariant(vname)

        model = UsdAttributeModelVariant(
            stage,
            [temp_path.AppendProperty("test")],
            True,
            attr.GetAllMetadata(),
        )
        self.assertEqual(-42, model._soft_range_min)
        self.assertEqual(42, model._soft_range_max)

    async def test_int_min(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.Int)

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)
        vname = "test_v"
        variant_set_api.AddVariant(vname)

        model = UsdAttributeModelVariant(
            stage,
            [temp_path.AppendProperty("test")],
            True,
            attr.GetAllMetadata(),
            min=10,
        )
        model._update_value(True)

        self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
        variant_set_api.SetVariantSelection(vname)
        model.begin_edit()
        model.set_value(10)
        model.end_edit()
        self.assertEqual(10, model.get_value_as_int())
        self.assertEqual(10, attr.Get())

        model.begin_edit()
        model.set_value(9)
        model.end_edit()
        self.assertEqual(10, model.get_value_as_int())
        self.assertEqual(10, attr.Get())

        model.begin_edit()
        model.set_value(11)
        model.end_edit()
        self.assertEqual(11, model.get_value_as_int())
        self.assertEqual(11, attr.Get())

        model.destroy()

    async def test_int_default(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.Int)
        sdf_attr.customData["default"] = 123

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)
        vname = "test_v"
        variant_set_api.AddVariant(vname)

        model = UsdAttributeModelVariant(
            stage,
            [temp_path.AppendProperty("test")],
            True,
            attr.GetAllMetadata(),
        )
        model._update_value(True)

        self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
        variant_set_api.SetVariantSelection(vname)
        model.begin_edit()
        model.set_value(234)
        model.end_edit()
        self.assertTrue(model._has_default_value)
        self.assertEqual(123, model._default_value)
        self.assertEqual(234, model.get_value_as_int())
        model.set_default()
        self.assertEqual(123, model.get_value_as_int())
        model.destroy()

    async def test_int_min_max(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.Int)

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)
        vname = "test_v"
        variant_set_api.AddVariant(vname)

        model = UsdAttributeModelVariant(
            stage,
            [temp_path.AppendProperty("test")],
            True,
            attr.GetAllMetadata(),
            min=9,
            max=10,
        )
        model._update_value(True)

        self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
        variant_set_api.SetVariantSelection(vname)
        model.begin_edit()
        model.set_value(10)
        model.end_edit()
        self.assertEqual(10, model.get_value_as_int())
        self.assertEqual(10, attr.Get())

        model.begin_edit()
        model.set_value(9)
        model.end_edit()
        self.assertEqual(9, model.get_value_as_int())
        self.assertEqual(9, attr.Get())

        model.begin_edit()
        model.set_value(11)
        model.end_edit()
        self.assertEqual(10, model.get_value_as_int())
        self.assertEqual(10, attr.Get())

        model.begin_edit()
        model.set_value(8)
        model.end_edit()
        self.assertEqual(9, model.get_value_as_int())
        self.assertEqual(9, attr.Get())

        model.destroy()

    async def test_int_invalid_min_max(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.Int)

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)
        vname = "test_v"
        variant_set_api.AddVariant(vname)

        model = UsdAttributeModelVariant(
            stage,
            [temp_path.AppendProperty("test")],
            True,
            attr.GetAllMetadata(),
            min=10,
            max=9,
        )
        model._update_value(True)

        self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
        variant_set_api.SetVariantSelection(vname)

        for i in range(8, 12):
            model.begin_edit()
            model.set_value(i)
            model.end_edit()
            self.assertEqual(i, model.get_value_as_int())
            self.assertEqual(i, attr.Get())

        model.destroy()

    async def test_int_max(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.Int)

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)
        vname = "test_v"
        variant_set_api.AddVariant(vname)

        model = UsdAttributeModelVariant(
            stage,
            [temp_path.AppendProperty("test")],
            True,
            attr.GetAllMetadata(),
            max=10,
        )
        model._update_value(True)

        self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
        variant_set_api.SetVariantSelection(vname)
        model.begin_edit()
        model.set_value(10)
        model.end_edit()
        self.assertEqual(10, model.get_value_as_int())
        self.assertEqual(10, attr.Get())

        model.begin_edit()
        model.set_value(11)
        model.end_edit()
        self.assertEqual(10, model.get_value_as_int())
        self.assertEqual(10, attr.Get())

        model.begin_edit()
        model.set_value(9)
        model.end_edit()
        self.assertEqual(9, model.get_value_as_int())
        self.assertEqual(9, attr.Get())

        model.destroy()

    async def test_bool(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.Bool)

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)

        async def for_each_(fn):
            import asyncio

            for i in range(5):
                vname = "test" + str(i)
                if asyncio.iscoroutinefunction(fn):
                    await fn(i, vname)
                else:
                    fn(i, vname)

        await for_each_(lambda i, vname: variant_set_api.AddVariant(vname))

        model = UsdAttributeModelVariant(stage, [temp_path.AppendProperty("test")], True, attr.GetAllMetadata())
        model._update_value(True)

        async def write_value(i, vname):
            self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
            variant_set_api.SetVariantSelection(vname)
            model.begin_edit()
            model.set_value(i % 2 == 0)
            model.end_edit()
            self.assertEqual(i % 2 == 0, model.get_value_as_bool())

        await for_each_(write_value)

        sdf_prim.RemoveProperty(sdf_attr)

        def test_data(i, vname):
            variant_set_api.SetVariantSelection(vname)
            self.assertEqual(i % 2 == 0, attr.Get())

        await for_each_(test_data)

        model.destroy()

    async def test_str(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.String)

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)

        async def for_each_(fn):
            import asyncio

            for i in range(5):
                vname = "test" + str(i)
                if asyncio.iscoroutinefunction(fn):
                    await fn(i, vname)
                else:
                    fn(i, vname)

        await for_each_(lambda i, vname: variant_set_api.AddVariant(vname))

        model = UsdAttributeModelVariant(stage, [temp_path.AppendProperty("test")], True, attr.GetAllMetadata())
        model._update_value(True)

        async def write_value(i, vname):
            self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
            variant_set_api.SetVariantSelection(vname)
            model.begin_edit()
            model.set_value(vname)
            model.end_edit()
            self.assertEqual(vname, model.get_value_as_string())

        await for_each_(write_value)

        sdf_prim.RemoveProperty(sdf_attr)

        def test_data(i, vname):
            variant_set_api.SetVariantSelection(vname)
            self.assertEqual(vname, attr.Get())

        await for_each_(test_data)

        model.destroy()

    async def test_vec3f(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.Vector3f)

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)

        async def for_each_(fn):
            import asyncio

            for i in range(3):
                vname = "test" + str(i)
                if asyncio.iscoroutinefunction(fn):
                    await fn(i, vname)
                else:
                    fn(i, vname)

        await for_each_(lambda i, vname: variant_set_api.AddVariant(vname))

        COMP = 3

        model = GfVecAttributeModelVariant(
            stage,
            [temp_path.AppendProperty("test")],
            COMP,
            Sdf.ValueTypeNames.Vector3f.type,
            True,
            attr.GetAllMetadata(),
        )

        self.assertEqual(COMP, len(model.get_item_children(None)))

        async def write_value(i, vname):
            self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
            variant_set_api.SetVariantSelection(vname)
            comp_models = model.get_item_children(None)
            for j in range(COMP):
                comp_models[j].model.begin_edit()
                comp_models[j].model.set_value((j + 1) * (i + 1) * 1.1)
                self.assertAlmostEqual(
                    (j + 1) * (i + 1) * 1.1,
                    comp_models[j].model.get_value_as_float(),
                    4,
                )
                comp_models[j].model.end_edit()
                await omni.kit.app.get_app().next_update_async()

        await for_each_(write_value)

        sdf_prim.RemoveProperty(sdf_attr)

        def test_data(i, vname):
            variant_set_api.SetVariantSelection(vname)
            for j in range(COMP):
                self.assertAlmostEqual((j + 1) * (i + 1) * 1.1, attr.Get()[j], 4)

        await for_each_(test_data)

        model.destroy()

    async def test_color(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.Float3)

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)

        async def for_each_(fn):
            import asyncio

            for i in range(3):
                vname = "test" + str(i)
                if asyncio.iscoroutinefunction(fn):
                    await fn(i, vname)
                else:
                    fn(i, vname)

        await for_each_(lambda i, vname: variant_set_api.AddVariant(vname))

        COMP = 3
        channel_models = []
        for i in range(COMP):
            model = GfVecAttributeSingleChannelModelVariant(
                stage,
                [temp_path.AppendProperty("test")],
                i,
                True,
                attr.GetAllMetadata(),
            )
            model._update_value()
            channel_models.append(model)

        async def write_value(i, vname):
            self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
            variant_set_api.SetVariantSelection(vname)
            for j in range(COMP):
                channel_models[j]._update_value()
                channel_models[j].set_value((j + 1) * (i + 1) * 1.1)
                self.assertAlmostEqual((j + 1) * (i + 1) * 1.1, channel_models[j].get_value_as_float(), 4)
                await omni.kit.app.get_app().next_update_async()

        await for_each_(write_value)

        sdf_prim.RemoveProperty(sdf_attr)

        def test_data(i, vname):
            variant_set_api.SetVariantSelection(vname)
            for j in range(COMP):
                self.assertAlmostEqual((j + 1) * (i + 1) * 1.1, attr.Get()[j], 4)

        await for_each_(test_data)

        for model in channel_models:
            model.destroy()

    async def test_int4(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.Int4)

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)

        async def for_each_(fn):
            import asyncio

            for i in range(3):
                vname = "test" + str(i)
                if asyncio.iscoroutinefunction(fn):
                    await fn(i, vname)
                else:
                    fn(i, vname)

        await for_each_(lambda i, vname: variant_set_api.AddVariant(vname))

        COMP = 4
        channel_models = []
        for i in range(COMP):
            model = GfVecAttributeSingleChannelModelVariant(
                stage,
                [temp_path.AppendProperty("test")],
                i,
                True,
                attr.GetAllMetadata(),
            )
            model._update_value()
            channel_models.append(model)

        async def write_value(i, vname):
            self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
            variant_set_api.SetVariantSelection(vname)
            for j in range(COMP):
                channel_models[j]._update_value()
                channel_models[j].set_value((j + 1) * (i + 1))
                self.assertEqual((j + 1) * (i + 1), channel_models[j].get_value_as_int())
                await omni.kit.app.get_app().next_update_async()

        await for_each_(write_value)

        sdf_prim.RemoveProperty(sdf_attr)

        def test_data(i, vname):
            variant_set_api.SetVariantSelection(vname)
            for j in range(COMP):
                self.assertAlmostEqual((j + 1) * (i + 1), attr.Get()[j])

        await for_each_(test_data)

        for model in channel_models:
            model.destroy()

    async def test_bool2(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        # boolN of MDL is actually intN
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.Int2)

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)

        async def for_each_(fn):
            import asyncio

            for i in range(3):
                vname = "test" + str(i)
                if asyncio.iscoroutinefunction(fn):
                    await fn(i, vname)
                else:
                    fn(i, vname)

        await for_each_(lambda i, vname: variant_set_api.AddVariant(vname))

        COMP = 2
        channel_models = []
        for i in range(COMP):
            model = GfVecAttributeSingleChannelModelVariant(
                stage,
                [temp_path.AppendProperty("test")],
                i,
                True,
                attr.GetAllMetadata(),
            )
            model._update_value()
            channel_models.append(model)

        async def write_value(i, vname):
            self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
            variant_set_api.SetVariantSelection(vname)
            for j in range(COMP):
                channel_models[j]._update_value()
                b = (i + j) % 2 == 0
                channel_models[j].set_value(b)
                self.assertEqual(b, channel_models[j].get_value_as_bool())
                self.assertEqual(str(int(b)), channel_models[j].get_value_as_string())
                await omni.kit.app.get_app().next_update_async()

        await for_each_(write_value)

        sdf_prim.RemoveProperty(sdf_attr)

        def test_data(i, vname):
            variant_set_api.SetVariantSelection(vname)
            for j in range(COMP):
                self.assertEqual((i + j) % 2 == 0, attr.Get()[j])

        await for_each_(test_data)

        for model in channel_models:
            model.destroy()

    async def test_vec3i(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.Int3)

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)

        async def for_each_(fn):
            import asyncio

            for i in range(3):
                vname = "test" + str(i)
                if asyncio.iscoroutinefunction(fn):
                    await fn(i, vname)
                else:
                    fn(i, vname)

        await for_each_(lambda i, vname: variant_set_api.AddVariant(vname))

        COMP = 3

        model = GfVecAttributeModelVariant(
            stage,
            [temp_path.AppendProperty("test")],
            COMP,
            Sdf.ValueTypeNames.Int3.type,
            True,
            attr.GetAllMetadata(),
        )

        self.assertEqual(COMP, len(model.get_item_children(None)))

        async def write_value(i, vname):
            self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
            variant_set_api.SetVariantSelection(vname)
            comp_models = model.get_item_children(None)
            for j in range(COMP):
                comp_models[j].model.begin_edit()
                comp_models[j].model.set_value((j + 1) * (i + 1) * 1)
                self.assertEqual((j + 1) * (i + 1) * 1, comp_models[j].model.get_value_as_float())
                comp_models[j].model.end_edit()
                await omni.kit.app.get_app().next_update_async()

        await for_each_(write_value)

        sdf_prim.RemoveProperty(sdf_attr)

        def test_data(i, vname):
            variant_set_api.SetVariantSelection(vname)
            for j in range(COMP):
                self.assertEqual((j + 1) * (i + 1) * 1, attr.Get()[j])

        await for_each_(test_data)

        model.destroy()

    async def test_matrix(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.Matrix2d)

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)

        async def for_each_(fn):
            import asyncio

            for i in range(3):
                vname = "test" + str(i)
                if asyncio.iscoroutinefunction(fn):
                    await fn(i, vname)
                else:
                    fn(i, vname)

        await for_each_(lambda i, vname: variant_set_api.AddVariant(vname))

        COMP = 4

        model = GfMatrixAttributeModel(
            stage,
            [temp_path.AppendProperty("test")],
            2,
            Sdf.ValueTypeNames.Matrix2d.type,
            True,
            attr.GetAllMetadata(),
        )

        self.assertEqual(COMP, len(model.get_item_children(None)))

        async def write_value(i, vname):
            self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
            variant_set_api.SetVariantSelection(vname)
            comp_models = model.get_item_children(None)
            for j in range(COMP):
                comp_models[j].model.begin_edit()
                comp_models[j].model.set_value((j + 1) * (i + 1) * 1.1)
                self.assertAlmostEqual(
                    (j + 1) * (i + 1) * 1.1,
                    comp_models[j].model.get_value_as_float(),
                    4,
                )
                comp_models[j].model.end_edit()
                await omni.kit.app.get_app().next_update_async()

        await for_each_(write_value)

        sdf_prim.RemoveProperty(sdf_attr)

        def test_data(i, vname):
            variant_set_api.SetVariantSelection(vname)
            v = []
            for j in range(2):
                for k in range(2):
                    v.append(attr.Get()[j][k])
            for j in range(4):
                self.assertAlmostEqual((j + 1) * (i + 1) * 1.1, v[j], 4)

        await for_each_(test_data)

        model.destroy()

    async def test_variant_set(self):
        stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")
        temp_prim = stage.DefinePrim(temp_path, "Xform")
        variant_sets_api = temp_prim.GetVariantSets()
        variant_set_api = variant_sets_api.AddVariantSet("color")

        vset_model = VariantSetModel(stage, [temp_path], "color", True)
        self.assertEqual(1, len(vset_model.get_item_children(None)))
        for i in range(3):
            vname = "color" + str(i)
            variant_set_api.AddVariant(vname)

            vnames = variant_set_api.GetVariantNames()
            children = vset_model.get_item_children(None)
            self.assertEqual(1 + len(vnames), len(children))
            self.assertEqual(vname, children[-1].model.as_string)
        variant_set_api.SetVariantSelection("color0")
        self._core.active_variant = temp_path.AppendVariantSelection("color", "color0")
        vset_model._current_index.set_value(1)
        self.assertEqual(1, vset_model._current_index.as_int)
        vset_model._current_index.set_value(2)
        self.assertEqual(2, vset_model._current_index.as_int)

        vset_model.destroy()

    async def test_variant_metadata_model(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")
        temp_prim: Usd.Prim = stage.DefinePrim(temp_path, "Xform")
        variant_sets_api = temp_prim.GetVariantSets()
        variant_set_api = variant_sets_api.AddVariantSet("test")
        attr: Usd.Attribute = temp_prim.CreateAttribute("test", Sdf.ValueTypeNames.Float, True)

        async def for_each_(fn):
            import asyncio

            for i in range(3):
                vname = "test" + str(i)
                if asyncio.iscoroutinefunction(fn):
                    await fn(i, vname)
                else:
                    fn(i, vname)

        await for_each_(lambda i, vname: variant_set_api.AddVariant(vname))

        self._core.active_variant = temp_path.AppendVariantSelection("test", "test0")
        model = MetadataObjectModelVariant(
            stage,
            [attr.GetPath()],
            True,
            attr.GetAllMetadata(),
            key=Sdf.PropertySpec.DisplayNameKey,
            default="A",
            options=["B", "C", "D"],
        )

        async def write_metadata(i, vname):
            self._core.active_variant = temp_path.AppendVariantSelection("test", vname)
            variant_set_api.SetVariantSelection(vname)
            model.set_value(i)
            # metadata model value updating is async, we have to wait
            for _ in range(6):
                await omni.kit.app.get_app().next_update_async()

        await for_each_(write_metadata)

        def test_data(i, vname):
            variant_set_api.SetVariantSelection(vname)
            self._core.active_variant = temp_path.AppendVariantSelection("test", vname)
            model._set_dirty()
            self.assertEqual(chr(ord("B") + i), model.get_value())

        await for_each_(test_data)

        model.destroy()

    async def test_asset_path(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.Asset)

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)

        async def for_each_(fn):
            import asyncio

            for i in range(1):
                vname = "test" + str(i)
                if asyncio.iscoroutinefunction(fn):
                    await fn(i, vname)
                else:
                    fn(i, vname)

        await for_each_(lambda i, vname: variant_set_api.AddVariant(vname))

        model = SdfAssetPathAttributeModelVariant(
            stage, [temp_path.AppendProperty("test")], True, attr.GetAllMetadata()
        )

        # _convert_asset_path is internal implementation from
        # omni.kit.property.usd/omni/kit/property/usd/usd_property_widget_builder.py
        # to simulate the actual value assigning
        def _convert_asset_path(path: str) -> str:
            return omni.usd.make_path_relative_to_current_edit_target(path)

        async def write_value(i, vname):
            self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
            variant_set_api.SetVariantSelection(vname)
            rp = os.path.abspath(__file__)
            p = _convert_asset_path(rp).replace("\\", "/")
            model.set_value(p, rp)
            self.assertEqual(rp.replace("\\", "/").lower(), model.get_resolved_path().lower())
            self.assertEqual(rp.replace("\\", "/").lower(), model.get_value_as_string().lower())

        await for_each_(write_value)

        sdf_prim.RemoveProperty(sdf_attr)

        def test_data(i, vname):
            variant_set_api.SetVariantSelection(vname)
            rp = os.path.abspath(__file__)
            p = _convert_asset_path(rp).replace("\\", "/")
            self.assertEqual(p, attr.Get().path)

        await for_each_(test_data)

        model.destroy()

    def mock_omni_client_list(
        url: str,
        include_deleted_option: omni.client.ListIncludeOption = omni.client.ListIncludeOption.NO_DELETED_FILES,
    ):
        mock_entries = []
        for i in range(3):

            class MockEntry(object):
                pass

            mock_entry = MockEntry()
            setattr(mock_entry, "relative_path", f"test.{i}.jpg")
            mock_entries.append(mock_entry)
        return (omni.client.Result.OK, mock_entries)

    def mock_prim_spec_layer_computeabsolutepath(self, path: str):
        return "abc"

    @patch("pxr.Sdf.Layer.ComputeAbsolutePath", mock_prim_spec_layer_computeabsolutepath)
    @patch("omni.client.list", mock_omni_client_list)
    async def test_asset_path_array(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.AssetArray)

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)

        async def for_each_(fn):
            import asyncio

            for i in range(3):
                vname = "test" + str(i)
                if asyncio.iscoroutinefunction(fn):
                    await fn(i, vname)
                else:
                    fn(i, vname)

        await for_each_(lambda i, vname: variant_set_api.AddVariant(vname))

        model = SdfAssetPathArrayAttributeItemModelVariant(
            stage, [temp_path.AppendProperty("test")], True, attr.GetAllMetadata(), None
        )

        async def write_value(i, vname):
            self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
            variant_set_api.SetVariantSelection(vname)
            paths = []
            for j in range(3):
                p = Sdf.AssetPath(vname + str(j))
                paths.append(p)
            model.set_value(paths)
            model._set_dirty()
            for j in range(3):
                item: SdfAssetPathArrayAttributeItemModelVariant.SdfAssetPathItemVariant = model.get_item_children(
                    None
                )[j]
                sdf_asset_path_model: SdfAssetPathArrayAttributeSingleEntryModelVariant = model.get_item_value_model(
                    item, None
                )[0]
                self.assertEqual(sdf_asset_path_model, item.sdf_asset_path_model)
                self.assertTrue(sdf_asset_path_model.is_valid_path())
                self.assertEqual(j, sdf_asset_path_model.index)

        await for_each_(write_value)

        sdf_prim.RemoveProperty(sdf_attr)

        def test_data(i, vname):
            variant_set_api.SetVariantSelection(vname)
            paths = []
            for j in range(3):
                p = Sdf.AssetPath(vname + str(j))
                paths.append(p)
            self.assertEqual(paths, attr.Get())

        await for_each_(test_data)

        vname = "test0"
        self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
        variant_set_api.SetVariantSelection(vname)
        item: SdfAssetPathArrayAttributeItemModelVariant.SdfAssetPathItemVariant = model.get_item_children(None)[-1]
        sdf_asset_path_model: SdfAssetPathArrayAttributeSingleEntryModelVariant = model.get_item_value_model(
            item, None
        )[0]
        self.assertEqual(sdf_asset_path_model, item.sdf_asset_path_model)
        self.assertTrue(sdf_asset_path_model.is_valid_path())
        self.assertEqual(2, sdf_asset_path_model.index)

        udim_path = "test.<UDIM>.jpg"
        sdf_asset_path_model.set_value(str(udim_path))
        self.assertEqual("abc/test.0.jpg", sdf_asset_path_model.get_wildcard_resolved_path())
        self.assertEqual("test.<UDIM>.jpg", sdf_asset_path_model.get_value_as_string())

        model.destroy()

    async def test_asset_path_array_drop(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.AssetArray)

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)
        vname = "test_v"
        variant_set_api.AddVariant(vname)
        self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)

        model = SdfAssetPathArrayAttributeItemModelVariant(
            stage, [temp_path.AppendProperty("test")], True, attr.GetAllMetadata(), None
        )

        def _convert_asset_path(path: str) -> str:
            return omni.usd.make_path_relative_to_current_edit_target(path)

        variant_set_api.SetVariantSelection(vname)
        paths = []
        for j in range(3):
            p = Sdf.AssetPath(vname + str(j))
            paths.append(p)
        model.set_value(paths)
        model._set_dirty()

        sdf_prim.RemoveProperty(sdf_attr)

        self.assertTrue(model.drop_accepted(None, model.get_item_children(None)[1], 3))
        self.assertFalse(model.drop_accepted(None, model.get_item_children(None)[1], -1))
        self.assertFalse(model.drop_accepted(None, None, 0))
        model.drop(None, model.get_item_children(None)[1], 3)
        model._set_dirty()
        self.assertEqual([paths[0], paths[2], paths[1]], attr.Get())

        model.drop(None, model.get_item_children(None)[2], 1)
        model._set_dirty()
        self.assertEqual(paths, attr.Get())

        model.destroy()

    @patch("pxr.Sdf.Layer.ComputeAbsolutePath", mock_prim_spec_layer_computeabsolutepath)
    @patch("omni.client.list", mock_omni_client_list)
    async def test_asset_wildcard_path(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(sdf_prim, "test", Sdf.ValueTypeNames.Asset)

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)

        async def for_each_(fn):
            import asyncio

            for i in range(1):
                vname = "test" + str(i)
                if asyncio.iscoroutinefunction(fn):
                    await fn(i, vname)
                else:
                    fn(i, vname)

        await for_each_(lambda i, vname: variant_set_api.AddVariant(vname))

        model = SdfAssetPathAttributeModelVariant(
            stage, [temp_path.AppendProperty("test")], True, attr.GetAllMetadata()
        )

        async def write_value(i, vname):
            udim_path = "test.<UDIM>.jpg"
            self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
            variant_set_api.SetVariantSelection(vname)
            model.set_value(str(udim_path))
            self.assertEqual("abc/test.0.jpg", model.get_wildcard_resolved_path())

        await for_each_(write_value)

    async def mock_get_subidentifier_from_material(
        prim: Usd.Prim,
        on_complete_fn: callable,
        use_functions: bool = False,
        show_alert: bool = False,
    ):
        on_complete_fn(["B", "C", "D"])

    async def test_allowed_item(self):
        from omni.kit.material.library import MaterialLibraryExtension

        item = AllowedAnnoItem(None)
        self.assertEqual("", item.model.get_value_as_string())
        self.assertEqual("", item.token)

        item = AllowedAnnoItem("abc", "def")
        self.assertEqual("abc", item.model.get_value_as_string())
        self.assertEqual("def", item.token)

        obj = MaterialLibraryExtension.SubIDEntry("abc", {"subid_token": "def"}, False)
        item = AllowedAnnoItem(obj)
        self.assertEqual("abc", item.model.get_value_as_string())
        self.assertEqual("def", item.token)

        obj = MaterialLibraryExtension.SubIDEntry("def", {"subid_display_name": "abc"}, False)
        item = AllowedAnnoItem(obj)
        self.assertEqual("abc", item.model.get_value_as_string())
        self.assertEqual("def", item.token)

        obj = MaterialLibraryExtension.SubIDEntry("def", {"display_name": "abc"}, False)
        item = AllowedAnnoItem(obj)
        self.assertEqual("abc", item.model.get_value_as_string())
        self.assertEqual("def", item.token)

        obj = MaterialLibraryExtension.SubIDEntry("def", {}, False)
        item = AllowedAnnoItem(obj)
        self.assertEqual("def", item.model.get_value_as_string())
        self.assertEqual("def", item.token)

    @patch(
        "omni.kit.material.library.get_subidentifier_from_material",
        mock_get_subidentifier_from_material,
    )
    async def test_subid(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attr = Sdf.AttributeSpec(
            sdf_prim,
            "info:mdl:sourceAsset:subIdentifier",
            Sdf.ValueTypeNames.Token,
            Sdf.VariabilityUniform,
        )

        attr = stage.GetAttributeAtPath(temp_path.AppendProperty("info:mdl:sourceAsset:subIdentifier"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)

        async def for_each_(fn):
            import asyncio

            for i in range(3):
                vname = "test" + str(i)
                if asyncio.iscoroutinefunction(fn):
                    await fn(i, vname)
                else:
                    fn(i, vname)

        await for_each_(lambda i, vname: variant_set_api.AddVariant(vname))

        model = VariantSubIdentifierModel(
            stage,
            [temp_path.AppendProperty("info:mdl:sourceAsset:subIdentifier")],
            True,
            attr.GetAllMetadata(),
            [],
            attr,
        )

        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()
        self.assertEqual(3, len(model.get_item_children(None)))

        async def write_value(i, vname):
            self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
            variant_set_api.SetVariantSelection(vname)
            model._current_index.set_value(i)
            model._current_index_changed(model._current_index)
            self.assertEqual(chr(ord("B") + i), model.get_value_as_token())

        await for_each_(write_value)

        sdf_prim.RemoveProperty(sdf_attr)
        for _ in range(3):
            await omni.kit.app.get_app().next_update_async()

        def test_data(i, vname):
            variant_set_api.SetVariantSelection(vname)
            self.assertEqual(chr(ord("B") + i), attr.Get())

        await for_each_(test_data)

        model.destroy()

    async def test_relationship(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_rel = Sdf.RelationshipSpec(sdf_prim, "test")

        TGT_CNT = 3

        for i in range(TGT_CNT):
            for j in range(i + 1):
                Sdf.CreatePrimInLayer(layer, f"/tgt_{i}_sub_{j}")

        Sdf.CreatePrimInLayer(layer, "/tgt_x_sub_x")
        rel = stage.GetRelationshipAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(rel.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)

        async def for_each_(fn):
            import asyncio

            for i in range(3):
                vname = "test" + str(i)
                if asyncio.iscoroutinefunction(fn):
                    await fn(i, vname)
                else:
                    fn(i, vname)

        await for_each_(lambda i, vname: variant_set_api.AddVariant(vname))

        model = SdfRelationshipArrayItemModelVariant(
            stage, [temp_path.AppendProperty("test")], rel.GetAllMetadata(), None, {}
        )
        self.assertEqual(1, model.get_item_value_model_count(None))

        async def write_value(i, vname):
            self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
            variant_set_api.SetVariantSelection(vname)
            items = []
            for j in range(i + 1):
                tgt_path = Sdf.Path(f"/tgt_{i}_sub_{j}")
                items.append(tgt_path)
            model.set_value(items)
            model._set_dirty()
            children = model.get_item_children(None)
            self.assertEqual(i + 1, len(children))

        await for_each_(write_value)

        sdf_prim.RemoveProperty(sdf_rel)

        def test_data(i, vname):
            variant_set_api.SetVariantSelection(vname)
            items = []
            for j in range(i + 1):
                tgt_path = Sdf.Path(f"/tgt_{i}_sub_{j}")
                items.append(tgt_path)
            self.assertEqual(items, rel.GetTargets())

        await for_each_(test_data)

        vname = "test2"
        self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
        variant_set_api.SetVariantSelection(vname)
        model._set_dirty()
        item: SdfRelationshipArrayItemModelVariant.SdfRelationshipPathItemVariant = model.get_item_children(None)[-1]
        sdf_relationship_path_model: SdfRelationshipArraySingleEntryModelVariant = model.get_item_value_model(
            item, None
        )[0]
        self.assertEqual(sdf_relationship_path_model, item.sdf_relationship_path_model)
        self.assertEqual(Sdf.Path("/tgt_2_sub_2"), sdf_relationship_path_model.get_value_as_string())
        self.assertEqual(2, sdf_relationship_path_model.index)
        sdf_relationship_path_model.set_value_as_string("/tgt_x_sub_x")
        self.assertEqual(
            "/tgt_x_sub_x",
            model.get_item_children(None)[-1].sdf_relationship_path_model.get_value_as_string(),
        )

        model.destroy()

    async def test_relationship_drop(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_rel = Sdf.RelationshipSpec(sdf_prim, "test")

        TGT_CNT = 3

        for i in range(TGT_CNT):
            Sdf.CreatePrimInLayer(layer, f"/tgt_{i}")

        rel = stage.GetRelationshipAtPath(temp_path.AppendProperty("test"))
        self.assertTrue(rel.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)
        vname = "test_v"
        self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)

        model = SdfRelationshipArrayItemModelVariant(
            stage, [temp_path.AppendProperty("test")], rel.GetAllMetadata(), None, {}
        )

        self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
        variant_set_api.SetVariantSelection(vname)
        items = []
        for i in range(3):
            tgt_path = Sdf.Path(f"/tgt_{i}")
            items.append(tgt_path)
        model.set_value(items)
        model._set_dirty()
        children = model.get_item_children(None)
        self.assertEqual(3, len(children))

        sdf_prim.RemoveProperty(sdf_rel)

        self.assertTrue(model.drop_accepted(None, model.get_item_children(None)[1], 3))
        self.assertFalse(model.drop_accepted(None, model.get_item_children(None)[1], -1))
        self.assertFalse(model.drop_accepted(None, None, 0))
        model.drop(None, children[1], 3)
        model._set_dirty()

        variant_set_api.SetVariantSelection(vname)
        self.assertEqual([items[0], items[2], items[1]], rel.GetTargets())

        children = model.get_item_children(None)
        model.drop(None, children[2], 1)
        model._set_dirty()

        variant_set_api.SetVariantSelection(vname)
        self.assertEqual(items, rel.GetTargets())

        model.destroy()

    async def test_mixed(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attrs = []
        attrs = []
        for i in range(3):
            sdf_attrs.append(Sdf.AttributeSpec(sdf_prim, f"test_{i}", Sdf.ValueTypeNames.Int))
            attrs.append(stage.GetAttributeAtPath(temp_path.AppendProperty(f"test_{i}")))
            self.assertTrue(attrs[-1].IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)
        vname = "test_v"
        variant_set_api.AddVariant(vname)

        model = UsdAttributeModelVariant(
            stage,
            [temp_path.AppendProperty(f"test_{i}") for i in range(3)],
            True,
            attrs[-1].GetAllMetadata(),
        )
        model._update_value(True)

        self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
        variant_set_api.SetVariantSelection(vname)
        self.assertFalse(model.is_ambiguous())
        for i in range(3):
            sel_path = temp_path.AppendVariantSelection(vset_name, vname).AppendProperty(f"test_{i}")
            stage.GetAttributeAtPath(sel_path).Set(i)
        model._update_value(True)
        self.assertTrue(model.is_ambiguous())

        model.destroy()

    async def test_comp_mixed(self):
        stage: Usd.Stage = self._core._stage
        temp_path = Sdf.Path("/temp")
        self._core._update_root_prim_path("/temp")

        layer: Sdf.Layer = stage.GetRootLayer()
        sdf_prim: Sdf.PrimSpec = Sdf.CreatePrimInLayer(layer, temp_path)
        sdf_attrs = []
        attrs = []
        for i in range(3):
            sdf_attrs.append(Sdf.AttributeSpec(sdf_prim, f"test_{i}", Sdf.ValueTypeNames.Int3))
            attrs.append(stage.GetAttributeAtPath(temp_path.AppendProperty(f"test_{i}")))
            self.assertTrue(attrs[-1].IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(temp_path, vset_name)
        vname = "test_v"
        variant_set_api.AddVariant(vname)

        model = UsdAttributeModelVariant(
            stage,
            [temp_path.AppendProperty(f"test_{i}") for i in range(3)],
            True,
            attrs[-1].GetAllMetadata(),
        )
        model._update_value(True)
        self.assertFalse(model.is_ambiguous())

        self._core.active_variant = temp_path.AppendVariantSelection(vset_name, vname)
        variant_set_api.SetVariantSelection(vname)

        for i in range(3):
            sel_path = temp_path.AppendVariantSelection(vset_name, vname).AppendProperty(f"test_{i}")
            stage.GetAttributeAtPath(sel_path).Set(Gf.Vec3i(1, 2, 3))
        model._update_value(True)
        self.assertFalse(model.is_ambiguous())
        self.assertFalse(model.is_comp_ambiguous(3))

        # change 2nd channel value only
        for i in range(3):
            sel_path = temp_path.AppendVariantSelection(vset_name, vname).AppendProperty(f"test_{i}")
            stage.GetAttributeAtPath(sel_path).Set(Gf.Vec3i(1, i, 3))
        model._update_value(True)
        self.assertTrue(model.is_ambiguous())
        self.assertFalse(model.is_comp_ambiguous(0))
        self.assertTrue(model.is_comp_ambiguous(1))
        self.assertFalse(model.is_comp_ambiguous(2))
        self.assertFalse(model.is_comp_ambiguous(3))

        self.assertTrue([False, True, False], model.get_all_comp_ambiguous())

        model.destroy()


class TestMdlModel(omni.kit.test.AsyncTestCase):
    def setup_simple_variant_case(self, path: Sdf.Path, vset_name: str) -> Usd.VariantSet:
        stage: Usd.Stage = self._core._stage
        prim = stage.GetPrimAtPath(path)
        variant_sets_api = prim.GetVariantSets()
        variant_set_api = variant_sets_api.AddVariantSet(vset_name)
        return variant_set_api

    async def setUp(self):
        from omni.kit.variant.editor.extension import TEST_DATA_PATH

        self._core = VariantEditorCore.get_instance()
        usd_path = TEST_DATA_PATH.absolute()
        test_file_path = usd_path.joinpath("mdl.usda").absolute()
        await omni.usd.get_context().open_stage_async(str(test_file_path))
        self._core._update_context_and_stage()
        await omni.kit.app.get_app().next_update_async()
        self.assertIsNotNone(self._core._stage)

    async def tearDown(self):
        await omni.usd.get_context().close_stage_async()
        await reset_variant_editor_test_state(restore_auxiliary_ui=False)

    async def test_mdl_enum(self):
        stage: Usd.Stage = self._core._stage
        shader_path = Sdf.Path("/World/Looks/OmniPBR/Shader")
        self._core._update_root_prim_path(shader_path)
        prim = stage.GetPrimAtPath(shader_path)

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(shader_path, vset_name)

        self.assertTrue(prim.IsValid())
        attr_path = shader_path.AppendProperty("inputs:opacity_mode")
        attr = stage.GetAttributeAtPath(attr_path)
        self.assertIsNotNone(attr.GetMetadata("renderType"))
        sdr_metadata = attr.GetMetadata("sdrMetadata")
        self.assertIsNotNone(sdr_metadata)
        self.assertIsNotNone(sdr_metadata.get("options"))

        async def for_each_(fn):
            import asyncio

            for i in range(3):
                vname = "test" + str(i)
                if asyncio.iscoroutinefunction(fn):
                    await fn(i, vname)
                else:
                    fn(i, vname)

        await for_each_(lambda i, vname: variant_set_api.AddVariant(vname))

        model = MdlEnumAttributeModelVariant(stage, [attr_path], True, attr.GetAllMetadata())

        options = ["mono_alpha", "mono_average", "mono_luminance", "mono_maximum"]
        self.assertEqual(4, len(model.get_item_children(None)))
        self.assertEqual(
            options,
            [item.model.get_value_as_string() for item in model.get_item_children(None)],
        )
        self.assertTrue(model.is_allowed_enum_string("mono_luminance"))
        self.assertFalse(model.is_allowed_enum_string("MONO_LUMINANCE"))

        async def write_value(i, vname):
            self._core.active_variant = shader_path.AppendVariantSelection(vset_name, vname)
            variant_set_api.SetVariantSelection(vname)
            model._current_index.set_value(i)
            self.assertEqual(options[i], model.get_value_as_string())

        await for_each_(write_value)

        async def write_value_enum(i, vname):
            self._core.active_variant = shader_path.AppendVariantSelection(vset_name, vname)
            variant_set_api.SetVariantSelection(vname)
            model.set_from_enum_string(options[i])
            self.assertEqual(options[i], model.get_value_as_string())

        await for_each_(write_value_enum)

        sdf_prim = stage.GetRootLayer().GetPrimAtPath(shader_path)
        sdf_attr = stage.GetRootLayer().GetAttributeAtPath(attr_path)

        sdf_prim.RemoveProperty(sdf_attr)

        def test_data(i, vname):
            variant_set_api.SetVariantSelection(vname)
            self.assertEqual(i, attr.Get())

        await for_each_(test_data)

        model.destroy()

    async def mock_get_subidentifier_from_mdl(
        mdl_file: str,
        on_complete_fn: callable = None,
        use_functions: bool = False,
        show_alert: bool = False,
    ):
        class MockSubidentifier(object):
            def __init__(self):
                self.annotations = dict()
                self.name = "test"

            def __str__(self):
                return self.name

            def __hash__(self) -> int:
                return hash(self.name)

        obj = MockSubidentifier()
        on_complete_fn([obj])

    @patch(
        "omni.kit.material.library.get_subidentifier_from_mdl",
        mock_get_subidentifier_from_mdl,
    )
    async def test_asset_path(self):
        stage: Usd.Stage = self._core._stage
        shader_path = Sdf.Path("/World/Looks/OmniPBR/Shader")
        self._core._update_root_prim_path(shader_path)
        shader_prim = stage.GetPrimAtPath(shader_path)

        attr = stage.GetAttributeAtPath(shader_path.AppendProperty("info:mdl:sourceAsset"))
        self.assertTrue(attr.IsValid())

        vset_name = "vset"
        variant_set_api = self.setup_simple_variant_case(shader_path, vset_name)

        async def for_each_(fn):
            import asyncio

            for i in range(1):
                vname = "test" + str(i)
                if asyncio.iscoroutinefunction(fn):
                    await fn(i, vname)
                else:
                    fn(i, vname)

        await for_each_(lambda i, vname: variant_set_api.AddVariant(vname))

        model = SdfAssetPathAttributeModelVariant(
            stage,
            [shader_path.AppendProperty("info:mdl:sourceAsset")],
            True,
            attr.GetAllMetadata(),
        )

        # _convert_asset_path is internal implementation from
        # omni.kit.property.usd/omni/kit/property/usd/usd_property_widget_builder.py
        # to simulate the actual value assigning
        def _convert_asset_path(path: str) -> str:
            return omni.usd.make_path_relative_to_current_edit_target(path)

        async def write_value(i, vname):
            from omni.kit.variant.editor.extension import TEST_DATA_PATH

            self._core.active_variant = shader_path.AppendVariantSelection(vset_name, vname)
            variant_set_api.SetVariantSelection(vname)
            usd_path = TEST_DATA_PATH.absolute()
            rp = str(usd_path.joinpath("test.mdl").absolute())
            p = _convert_asset_path(rp).replace("\\", "/")
            model.set_value(p, rp)
            for _ in range(3):
                await omni.kit.app.get_app().next_update_async()

        await for_each_(write_value)

        sdf_prim = stage.GetRootLayer().GetPrimAtPath(shader_path)
        sdf_attr = stage.GetRootLayer().GetAttributeAtPath(attr.GetPath())
        sdf_prim.RemoveProperty(sdf_attr)

        def test_data(i, vname):
            from omni.kit.variant.editor.extension import TEST_DATA_PATH

            variant_set_api.SetVariantSelection(vname)
            usd_path = TEST_DATA_PATH.absolute()
            rp = str(usd_path.joinpath("test.mdl").absolute())
            p = _convert_asset_path(rp).replace("\\", "/")
            self.assertEqual(p, attr.Get().path)

        await for_each_(test_data)

        model.destroy()
