# Copyright (c) 2026, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import unittest
from unittest.mock import Mock, patch

from omni.kit.viewport.menubar.lighting import utility
from pxr import Sdf, Usd, UsdGeom, UsdLux


class TestLightingScan(unittest.TestCase):
    def setUp(self):
        # Exercise the USD fallback, independently of whether Fabric is loaded in Kit.
        self._settings = Mock()
        self._settings.get.return_value = True
        self._patches = [
            patch.object(utility, "_get_usd_rt_stage", return_value=None),
            patch.object(utility.carb.settings, "get_settings", return_value=self._settings),
        ]
        for item in self._patches:
            item.start()
            self.addCleanup(item.stop)
        self.stage = Usd.Stage.CreateInMemory()
        world = UsdGeom.Xform.Define(self.stage, "/World").GetPrim()
        self.stage.SetDefaultPrim(world)
        # Exceed the bounded shallow search so tests also exercise native discovery.
        for index in range(160):
            UsdGeom.Xform.Define(self.stage, f"/World/Empty{index}")

    def _gather(self, api_types=("LightAPI",)):
        edit = utility.VisibilityEdit(
            self.stage,
            None,
            lambda prim, path: prim.HasAPI(UsdLux.LightAPI),
            api_types_for_prune=api_types,
        )
        edit._VisibilityEdit__gather_prims()
        return {str(path): instance for path, instance in edit._VisibilityEdit__path_to_change.items()}

    def test_shallow_light_does_not_require_full_scan(self):
        UsdLux.DistantLight.Define(self.stage, "/Sun")
        with patch.object(utility, "_get_light_prims", side_effect=AssertionError("Unexpected full scan")):
            self.assertTrue(utility.stage_has_api_type(self.stage, UsdLux.LightAPI))

    def test_changes_override_stale_authored_light_list(self):
        self.assertFalse(utility.stage_has_api_type(self.stage, UsdLux.LightAPI))
        first = UsdLux.RectLight.Define(self.stage, "/World/First").GetPrim()
        api = getattr(UsdLux, "LightListAPI", None) or UsdLux.ListAPI
        api.Apply(self.stage.GetDefaultPrim()).StoreLightList([first.GetPath()])
        self.stage.RemovePrim(first.GetPath())
        self.assertFalse(utility.stage_has_api_type(self.stage, UsdLux.LightAPI))
        self.assertEqual(self._gather(), {})
        UsdLux.RectLight.Define(self.stage, "/World/Second")
        self.assertTrue(utility.stage_has_api_type(self.stage, UsdLux.LightAPI))
        self.assertEqual(self._gather(), {"/World/Second": False})

    def test_default_subtree_and_runtime_fallback(self):
        prim = UsdLux.DistantLight.Define(self.stage, "/World/Fallback").GetPrim()
        prim.SetCustomDataByKey("omni:runtime:fallbackLight", True)
        UsdLux.RectLight.Define(self.stage, "/Outside")
        self.assertFalse(utility.stage_has_api_type(self.stage, UsdLux.LightAPI, True))
        self.assertTrue(utility.stage_has_api_type(self.stage, UsdLux.LightAPI))
        UsdLux.LightAPI.Apply(self.stage.GetDefaultPrim())
        # The default prim itself is excluded by the original descendant-only search.
        self.assertFalse(utility.stage_has_api_type(self.stage, UsdLux.LightAPI, True))

    def test_default_predicate_and_light_filters(self):
        inactive = UsdLux.RectLight.Define(self.stage, "/World/Inactive").GetPrim()
        inactive.SetActive(False)
        abstract = self.stage.CreateClassPrim("/World/Abstract")
        UsdLux.LightAPI.Apply(abstract)
        UsdLux.LightFilter.Define(self.stage, "/World/Filter")
        payload = Sdf.Layer.CreateAnonymous("payload.usda")
        payload_stage = Usd.Stage.Open(payload)
        UsdLux.RectLight.Define(payload_stage, "/Asset/Light")
        unloaded = self.stage.DefinePrim("/World/Unloaded", "Xform")
        unloaded.GetPayloads().AddPayload(payload.identifier, "/Asset")
        self.stage.Unload(unloaded.GetPath())
        self.assertFalse(utility.stage_has_api_type(self.stage, UsdLux.LightAPI))
        self.assertEqual(self._gather(), {})

    def test_hidden_ancestor_and_hidden_setting(self):
        hidden = UsdGeom.Xform.Define(self.stage, "/World/Hidden").GetPrim()
        hidden.SetMetadata("hide_in_stage_window", True)
        UsdLux.RectLight.Define(self.stage, "/World/Hidden/Nested/Light")
        direct = UsdLux.RectLight.Define(self.stage, "/World/HiddenLight").GetPrim()
        direct.SetMetadata("hide_in_stage_window", True)
        UsdLux.RectLight.Define(self.stage, "/World/Visible")
        self.assertEqual(self._gather(), {"/World/Visible": False})
        self._settings.get.return_value = False
        self.assertEqual(
            set(self._gather()),
            {
                "/World/Hidden/Nested/Light",
                "/World/HiddenLight",
                "/World/Visible",
            },
        )

    def test_instance_proxies_and_visibility_edit(self):
        source = UsdGeom.Xform.Define(self.stage, "/Source").GetPrim()
        UsdLux.RectLight.Define(self.stage, "/Source/Light")
        instance = self.stage.DefinePrim("/World/Instance", "Xform")
        instance.GetReferences().AddInternalReference(source.GetPath())
        instance.SetInstanceable(True)
        # Existence historically excludes proxies, while visibility edits include them.
        self.assertFalse(utility.stage_has_api_type(self.stage, UsdLux.LightAPI, True))
        self.assertEqual(self._gather(), {"/Source/Light": False, "/World/Instance": True})
        edit = utility.VisibilityEdit(
            self.stage,
            None,
            lambda prim, path: prim.HasAPI(UsdLux.LightAPI),
            api_types_for_prune=["LightAPI"],
        )
        edit.run()
        self.assertEqual(UsdGeom.Imageable(instance).GetVisibilityAttr().Get(), UsdGeom.Tokens.invisible)
        self.assertEqual(UsdGeom.Imageable(source).GetVisibilityAttr().Get(), UsdGeom.Tokens.inherited)

    def test_hidden_instance_is_skipped(self):
        source = UsdGeom.Xform.Define(self.stage, "/Source").GetPrim()
        UsdLux.RectLight.Define(self.stage, "/Source/Light")
        instance = self.stage.DefinePrim("/World/Instance", "Xform")
        instance.GetReferences().AddInternalReference(source.GetPath())
        instance.SetInstanceable(True)
        instance.SetMetadata("hide_in_stage_window", True)
        self.assertEqual(self._gather(), {"/Source/Light": False})

    def test_mixed_instance_keeps_geometry_visible(self):
        source = UsdGeom.Xform.Define(self.stage, "/Source").GetPrim()
        UsdLux.RectLight.Define(self.stage, "/Source/Light")
        UsdGeom.Mesh.Define(self.stage, "/Source/Mesh")
        instance = self.stage.DefinePrim("/World/Instance", "Xform")
        instance.GetReferences().AddInternalReference(source.GetPath())
        instance.SetInstanceable(True)
        utility.VisibilityEdit(
            self.stage,
            None,
            lambda prim, path: prim.HasAPI(UsdLux.LightAPI),
            api_types_for_prune=["LightAPI"],
        ).run()
        self.assertEqual(UsdGeom.Imageable(instance).GetVisibilityAttr().Get(), UsdGeom.Tokens.inherited)
        self.assertEqual(
            UsdGeom.Imageable(self.stage.GetPrimAtPath("/World/Instance/Mesh")).ComputeVisibility(),
            UsdGeom.Tokens.inherited,
        )

    def test_other_api_and_generic_visibility_traversal(self):
        model = self.stage.GetPrimAtPath("/World/Empty159")
        self.assertFalse(utility.stage_has_api_type(self.stage, UsdGeom.ModelAPI))
        UsdGeom.ModelAPI.Apply(model)
        self.assertTrue(utility.stage_has_api_type(self.stage, UsdGeom.ModelAPI))
        mesh = UsdGeom.Mesh.Define(self.stage, "/World/Mesh")
        utility.VisibilityEdit(
            self.stage,
            None,
            lambda prim, path: prim.IsA(UsdGeom.Mesh),
            types_for_prune=["Mesh"],
        ).run()
        self.assertEqual(mesh.GetVisibilityAttr().Get(), UsdGeom.Tokens.invisible)
