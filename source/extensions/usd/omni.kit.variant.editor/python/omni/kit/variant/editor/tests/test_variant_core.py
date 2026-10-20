# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from unittest import mock

import omni.kit.app
import omni.kit.test
import omni.kit.usd.layers as layers
import omni.kit.variant.editor
import omni.usd
from omni.kit.variant.editor.core import VariantEditorCore
from pxr import Sdf, Usd

from .test_cleanup import reset_variant_editor_test_state


class _NonUsdContextWrapper:
    """Mimics OMPE-105547: forwards to a working context but fails isinstance(omni.usd.UsdContext)."""

    def __init__(self, usd_context):
        self._usd_context = usd_context

    def __getattr__(self, name):
        return getattr(self._usd_context, name)


# Having a test class dervived from omni.kit.test.AsyncTestCase declared on the root of module will make it auto-discoverable by omni.kit.test
class CoreTest(omni.kit.test.AsyncTestCase):
    # SET-UP AND UTILITY
    async def setUp(self):
        from omni.kit.variant.editor.extension import TEST_DATA_PATH

        self._usd_path = TEST_DATA_PATH.absolute()

    async def tearDown(self):
        await reset_variant_editor_test_state(restore_auxiliary_ui=False)

    async def bootstrap_stage(self, stage_path):
        test_file_path = self._usd_path.joinpath(stage_path).absolute()
        await omni.usd.get_context().open_stage_async(str(test_file_path))
        await omni.kit.app.get_app().next_update_async()

    # TESTS
    async def test_get_core_instance(self):
        result = VariantEditorCore.get_instance()
        self.assertEqual(bool(result), True)

    async def test_get_window(self):
        result = omni.kit.variant.editor.get_window()
        self.assertEqual(bool(result), True)

    async def test_update_context_and_stage(self):
        await self.bootstrap_stage("test_core.usda")
        core = VariantEditorCore.get_instance()
        expected_result = [omni.usd.get_context(), omni.usd.get_context().get_stage()]
        core._update_context_and_stage()
        result = [core._usd_context, core._stage]
        self.assertEqual(result, expected_result)

    async def test_clear_all(self):
        await self.bootstrap_stage("test_core.usda")
        core = VariantEditorCore.get_instance()
        core._update_context_and_stage()
        core._clear_all()
        expected_result = [[], None, None]
        result = [list(core._variant_specs), core._target_prim_path, core.active_variant]
        self.assertEqual(result, expected_result)

    async def test_set_root_prim_path(self):
        await self.bootstrap_stage("test_core.usda")
        core = VariantEditorCore.get_instance()
        core._update_context_and_stage()
        root_prim_path = "/World/TestSetRootPrimPath"
        core._update_root_prim_path(root_prim_path)
        result = core._target_prim_path
        self.assertEqual(result, root_prim_path)

    async def test_get_root_prim_path(self):
        await self.bootstrap_stage("test_core.usda")
        core = VariantEditorCore.get_instance()
        core._update_context_and_stage()
        expected_root_prim_path = "/World"
        result = core._get_root_prim_path()
        self.assertEqual(result, expected_root_prim_path)

    async def test_get_active_variant(self):
        await self.bootstrap_stage("test_core.usda")
        core = VariantEditorCore.get_instance()
        core._update_context_and_stage()
        variant_path = Sdf.Path("/World{VariantSet=Variant}")
        core.active_variant = variant_path
        result = core._get_active_variant()
        self.assertEqual(result, variant_path)

    async def test_get_active_variant_set(self):
        await self.bootstrap_stage("test_core.usda")
        core = VariantEditorCore.get_instance()
        core._update_context_and_stage()
        variant_path = Sdf.Path("/World{VariantSet=Variant}")
        core.active_variant = variant_path
        result = core._get_active_variant_set()
        expected_variant_set = "VariantSet"
        self.assertEqual(result, expected_variant_set)

    async def test_get_edit_target_layer(self):
        await self.bootstrap_stage("test_core.usda")
        core = VariantEditorCore.get_instance()
        core._update_context_and_stage()
        variant_path = Sdf.Path("/World{VariantSet=Variant}")
        core.active_variant = variant_path
        result = core._get_edit_target_layer()
        self.assertTrue(bool(result))

    async def test_get_prim_spec_from_path(self):
        await self.bootstrap_stage("test_core.usda")
        core = VariantEditorCore.get_instance()
        core._update_context_and_stage()
        path = Sdf.Path("/World{TestChildren=TestChildren}")
        result = core._get_prim_spec_from_path(path)
        self.assertTrue(bool(result))

    async def test_get_variant_set_names_from_path(self):
        await self.bootstrap_stage("test_core.usda")
        core = VariantEditorCore.get_instance()
        core._update_context_and_stage()
        path = Sdf.Path("/World")
        expected_variant_set_names = ["TestChildren", "TestDummy"]
        result = core._get_variant_set_names_from_path(path)
        self.assertEqual(result, expected_variant_set_names)

    async def test_get_variants_from_set(self):
        await self.bootstrap_stage("test_core.usda")
        core = VariantEditorCore.get_instance()
        core._update_context_and_stage()
        vset = "TestChildren"
        expected_variants = ["TestChildren", "TestChildren_1"]
        result = core._get_variants_from_set(vset)
        self.assertEqual(result, expected_variants)

    async def test_get_variants_from_spec(self):
        await self.bootstrap_stage("test_core.usda")
        core = VariantEditorCore.get_instance()
        core._update_context_and_stage()
        spec_path = Sdf.Path("/World{TestChildren=}")
        spec = core._get_prim_spec_from_path(spec_path)
        expected_variants = ["TestChildren", "TestChildren_1"]
        result = core._get_variants_from_spec(spec)
        result_variants = []
        for spec in result:
            result_variants.append(spec.name)
        self.assertEqual(result_variants, expected_variants)

    async def test_collect_variant_sets(self):
        await self.bootstrap_stage("test_core.usda")
        core = VariantEditorCore.get_instance()
        core._update_context_and_stage()
        expected_sets = ["TestChildren", "TestDummy"]
        result = core._collect_variant_sets()
        self.assertEqual(result, expected_sets)

    async def test_get_variant_specs(self):
        await self.bootstrap_stage("test_core.usda")
        core = VariantEditorCore.get_instance()
        window = omni.kit.variant.editor.get_window()
        window.show()
        core._update_context_and_stage()
        variant_path = Sdf.Path("/World")
        core.active_variant = variant_path
        result = core._get_variant_specs()
        result_specs = []
        for spec in result:
            result_specs.append(spec.name)
        expected_specs = ["SubLayerXForm"]
        self.assertEqual(result_specs, expected_specs)

    async def test_check_specs_for_properties(self):
        await self.bootstrap_stage("test_core.usda")
        core = VariantEditorCore.get_instance()
        window = omni.kit.variant.editor.get_window()
        window.show()
        core._update_context_and_stage()
        variant_path = Sdf.Path("/World{TestChildren=TestChildren}")
        core._select_variant_by_path(variant_path)
        core.active_variant = variant_path
        expected_prims = ["ParentCube", "ParentXForm", "SubLayerCube"]
        result = core._check_specs_for_properties(core.active_variant)
        result_specs = []
        for spec in result:
            result_specs.append(spec.name)
        result_specs.sort()
        self.assertEqual(result_specs, expected_prims)

    async def test_get_variant_set_by_name(self):
        await self.bootstrap_stage("test_core.usda")
        core = VariantEditorCore.get_instance()
        core._update_context_and_stage()
        name = "TestChildren"
        result = core._get_variant_set_by_name(name)
        self.assertTrue(bool(result))

    async def test_get_ref_path(self):
        await self.bootstrap_stage("test_core.usda")
        core = VariantEditorCore.get_instance()
        core._update_context_and_stage()
        prim = core._stage.GetPrimAtPath("/World/ReferenceXForm")
        expected_path = "./Rock_Small_01.usd"
        result = core._get_ref_path(prim)
        self.assertEqual(result, expected_path)

    async def test_get_variant_edit_context(self):
        await self.bootstrap_stage("test_core.usda")
        core = VariantEditorCore.get_instance()
        window = omni.kit.variant.editor.get_window()
        window.show()
        core._update_context_and_stage()
        core.active_variant = "/World{TestChildren=TestChildren}"
        result = core._get_variant_edit_context()
        self.assertTrue(bool(result))

    async def test_get_next_valid_variant_name(self):
        await self.bootstrap_stage("test_core.usda")
        core = VariantEditorCore.get_instance()
        core._update_context_and_stage()
        name = "TestChildren"
        vset = "TestChildren"
        expected_name = "TestChildren_2"
        result = core._get_next_valid_variant_name(name, vset)
        self.assertEqual(result, expected_name)

    async def test_is_variant_name_available(self):
        await self.bootstrap_stage("test_core.usda")
        core = VariantEditorCore.get_instance()
        core._update_context_and_stage()
        name = "TestChildren_1"
        vset = "TestChildren"
        result = core._is_variant_name_available(name, vset)
        self.assertFalse(result)

    async def test_prim_path_metadata(self):
        await self.bootstrap_stage("test_metadata.usda")
        core = VariantEditorCore.get_instance()
        add_to_all = core.add_props_to_all_variants
        core.add_props_to_all_variants = False
        core._update_context_and_stage()
        core._update_root_prim_path("/World")
        variant_path = "/World{TestMetadata=TestMeta1}"
        core.active_variant = variant_path
        core._active_variant = variant_path
        vspec = core._get_edit_target_layer().GetObjectAtPath(variant_path)
        v_prim_spec = vspec.primSpec

        # Test 1 - Add prim path metadata
        test_path = "../Xform/AddCube"
        core._add_target_prim_metadata(variant_path=variant_path, new_path=test_path)
        custom_data = v_prim_spec.customData
        self.assertTrue(test_path in custom_data["variantPrimPaths"])

        # Test 2 - Remove prim path metadata
        test_path = "../Xform/RemoveCube"
        core._remove_prim_path_from_metadata(variant_path=variant_path, removed_prim_path=test_path)
        custom_data = v_prim_spec.customData
        self.assertFalse(test_path in custom_data["variantPrimPaths"])

        # Test 3 - Is prim path in metadata
        valid_test_path = "/World/Xform/ValidCube"
        invalid_test_path = "/World/Xform/InvalidCube"
        valid_paths = core.is_prim_path_in_metadata(valid_test_path)
        invalid_paths = core.is_prim_path_in_metadata(invalid_test_path)
        self.assertEqual(len(valid_paths), 2)
        self.assertFalse(invalid_paths)

        # Teardown - restore add to all setting
        core.add_props_to_all_variants = add_to_all

    async def test_on_stage_opened_recovers_context_from_stage(self):
        """OMPE-105547: a Python-level wrapper around UsdContext must not disable layer events.

        The real layers.get_layers() rejects the wrapper (neither a str nor an
        omni.usd.UsdContext), but _on_stage_opened() resolves the context from the
        stage through C++, so the subscription is still established.
        """
        await self.bootstrap_stage("test_core.usda")

        window = omni.kit.variant.editor.get_window()
        core = window._editor_core
        usd_context = omni.usd.get_context()
        wrapped_context = _NonUsdContextWrapper(usd_context)

        # The real get_layers() must reject the wrapper - this is the reported mechanism.
        self.assertIsNone(layers.get_layers(wrapped_context))

        def _update_context_and_stage(core_self, usd_context_name: str = ""):
            core_self._usd_context = wrapped_context
            core_self._stage = usd_context.get_stage()

        window._layer_event_sub = "stale subscription"
        try:
            with mock.patch.object(VariantEditorCore, "_update_context_and_stage", _update_context_and_stage):
                window._on_stage_opened()

            # Recovered via get_context_from_stage(): the subscription is real, not skipped.
            # assertIsNotNone alone would also pass if nothing touched the attribute and the
            # seeded sentinel simply survived, so pin that the stale value was replaced.
            self.assertNotEqual(window._layer_event_sub, "stale subscription")
            self.assertIsNotNone(window._layer_event_sub)
        finally:
            # _on_stage_opened() writes core._usd_context / core._stage, and neither is reset
            # by reset_variant_editor_test_state(). Restore them even if the handler or the
            # assertion above raised, so a failure here cannot cascade into other tests.
            core._update_context_and_stage()

    async def test_on_stage_opened_without_layers_interface(self):
        """The None guard: when no context resolves at all, skip subscribing instead of raising."""
        await self.bootstrap_stage("test_core.usda")

        window = omni.kit.variant.editor.get_window()
        core = window._editor_core
        wrapped_context = _NonUsdContextWrapper(omni.usd.get_context())
        # A stage that no UsdContext owns, so get_context_from_stage() cannot recover one.
        orphan_stage = Usd.Stage.CreateInMemory()
        self.assertIsNone(omni.usd.get_context_from_stage(orphan_stage))

        def _update_context_and_stage(core_self, usd_context_name: str = ""):
            core_self._usd_context = wrapped_context
            core_self._stage = orphan_stage

        window._layer_event_sub = "stale subscription"
        try:
            with mock.patch.object(VariantEditorCore, "_update_context_and_stage", _update_context_and_stage):
                window._on_stage_opened()  # must not raise

            # Guard fired: no subscription, and the previous stage's stale one was cleared.
            self.assertIsNone(window._layer_event_sub)
        finally:
            # Drop the orphan stage / wrapper from the singleton even on failure.
            core._update_context_and_stage()

        # Healthy path, asserted after restoration.
        window._on_stage_opened()
        self.assertIsNotNone(window._layer_event_sub)
        self.assertIsInstance(core._usd_context, omni.usd.UsdContext)
