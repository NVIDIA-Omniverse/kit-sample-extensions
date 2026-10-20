# Copyright (c) 2021-2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
from pathlib import Path

import carb
import omni.kit.actions.core
from omni.kit.test import AsyncTestCase
from pxr import Tf, Usd, UsdGeom, UsdLux

EXT_TEST_PATH = Path(carb.tokens.get_tokens_interface().resolve("${omni.kit.viewport.menubar.lighting}")).absolute()
TEST_USD_PATH = EXT_TEST_PATH.joinpath("data", "tests", "scenes")


class TestActions(AsyncTestCase):
    async def setUp(self):
        super().setUp()

    async def tearDown(self):
        super().tearDown()

    async def wait_frames(self, n_frames: int = 5):
        app = omni.kit.app.get_app()
        for _ in range(n_frames):
            await app.next_update_async()

    async def test_action_registered(self):
        """Test known actions are registered."""
        ar = omni.kit.actions.core.get_action_registry()
        self.assertIsNotNone(ar.get_action("omni.kit.viewport.menubar.lighting", "set_lighting_mode_off"))
        self.assertIsNotNone(ar.get_action("omni.kit.viewport.menubar.lighting", "set_lighting_mode_stage"))
        self.assertIsNotNone(ar.get_action("omni.kit.viewport.menubar.lighting", "set_lighting_mode_camera"))
        self.assertIsNotNone(ar.get_action("omni.kit.viewport.menubar.lighting", "set_lighting_mode_rig"))

    async def test_action_valid(self):
        """Test known actions are valid when executed."""
        ar = omni.kit.actions.core.get_action_registry()
        ar.get_action("omni.kit.viewport.menubar.lighting", "set_lighting_mode_off").execute()
        ar.get_action("omni.kit.viewport.menubar.lighting", "set_lighting_mode_stage").execute()
        ar.get_action("omni.kit.viewport.menubar.lighting", "set_lighting_mode_camera").execute()
        ar.get_action("omni.kit.viewport.menubar.lighting", "set_lighting_mode_rig").execute()

    async def test_action_set_lighting_mode_rig(self):
        """Test arguments to set_lighting_mode_rig action."""
        ar = omni.kit.actions.core.get_action_registry()
        set_lighting_mode_rig = ar.get_action("omni.kit.viewport.menubar.lighting", "set_lighting_mode_rig")
        n_runs = 5

        usd_context = omni.usd.get_context()
        usd_path = TEST_USD_PATH.joinpath("no_lights.usda")
        await usd_context.open_stage_async(str(usd_path))

        for _ in range(n_runs):
            set_lighting_mode_rig.execute(0, usd_context=usd_context)
            await self.wait_frames()

            set_lighting_mode_rig.execute(1, usd_context=usd_context)
            await self.wait_frames()

            set_lighting_mode_rig.execute(2, usd_context=usd_context)
            await self.wait_frames()

            set_lighting_mode_rig.execute(-1, usd_context=usd_context)
            await self.wait_frames()

        from omni.kit.viewport.utility import get_active_viewport

        viewport = get_active_viewport()
        for _ in range(n_runs):
            set_lighting_mode_rig.execute(0, viewport=viewport)
            await self.wait_frames()

            set_lighting_mode_rig.execute(1, viewport=viewport)
            await self.wait_frames()

            set_lighting_mode_rig.execute(2, viewport=viewport)
            await self.wait_frames()

            set_lighting_mode_rig.execute(-1, viewport=viewport)
            await self.wait_frames()

        for _ in range(n_runs):
            set_lighting_mode_rig.execute(0)
            await self.wait_frames()

            set_lighting_mode_rig.execute(1)
            await self.wait_frames()

            set_lighting_mode_rig.execute(2)
            await self.wait_frames()

            set_lighting_mode_rig.execute(-1)
            await self.wait_frames()

    async def test_honor_stage_window_hidden(self):
        """Test honoring of hide_in_stage_window metadata during iteration."""
        usd_context = omni.usd.get_context()
        usd_path = TEST_USD_PATH.joinpath("stage_window_hidden.usda")
        prim_paths = ["/World/DiskLight_01", "/World/DiskLight_02", "/World/DiskLight_03", "/World/DiskLight_04"]

        ar = omni.kit.actions.core.get_action_registry()
        set_lighting_mode_rig = ar.get_action("omni.kit.viewport.menubar.lighting", "set_lighting_mode_rig")

        settings = carb.settings.get_settings()
        setting_key = "/exts/omni.kit.viewport.menubar.lighting/stageWindow/skipHidden"
        test_values = [
            (True, ["inherited", "inherited", "invisible", "invisible"]),
            (False, ["invisible", "invisible", "invisible", "invisible"]),
        ]
        restore_value = settings.get(setting_key)

        async def test_visibility(stage, prim_paths, visibility_strs):
            for prim_path, vis_value in zip(prim_paths, visibility_strs):
                prim = stage.GetPrimAtPath(prim_path)
                self.assertTrue(prim.IsValid())
                self.assertEqual(str(UsdGeom.Imageable(prim).ComputeVisibility()), vis_value)

        try:
            for tst_values in test_values:
                set_value, vis_value = tst_values
                settings.set(setting_key, set_value)

                await usd_context.open_stage_async(str(usd_path))
                stage = usd_context.get_stage()

                set_lighting_mode_rig.execute(0)
                await self.wait_frames()
                await test_visibility(stage, prim_paths, vis_value)

                set_lighting_mode_rig.execute(-1)
                await self.wait_frames()
                await test_visibility(stage, prim_paths, vis_value)

        finally:
            settings.set(setting_key, restore_value)

    async def __test_import_lighting_rig_action(
        self,
        env_name: str = "/Environment",
        rig_name: str | None = None,
        children_cleared: bool = True,
        import_args: dict = {},
    ):
        async def restart_stage(dflt_name: str):
            usd_context = omni.usd.get_context()
            await usd_context.new_stage_async()
            return usd_context.get_stage(), (rig_name or dflt_name)

        ar = omni.kit.actions.core.get_action_registry()
        import_lighting_rig = ar.get_action("omni.kit.viewport.menubar.lighting", "import_lighting_rig")
        self.assertIsNotNone(import_lighting_rig)

        set_lighting_mode_rig = ar.get_action("omni.kit.viewport.menubar.lighting", "set_lighting_mode_rig")
        self.assertIsNotNone(set_lighting_mode_rig)

        # Would be great to test an error is raised when no light rig is applied.
        # But omni.kit.actions.core.python seems to eat the excpetion and carb.log_error
        # stage = await restart_stage()
        # try:
        #     import_lighting_rig.execute()
        # except RuntimeError as e:
        #     self.assertEqual(e.args, ("UsdContext named '' had no light rig"))

        # Test 0: Colored_Lights
        stage, rig_loc = await restart_stage("Colored_Lights")
        self.assertFalse(bool(stage.GetPrimAtPath(f"{env_name}")))
        set_lighting_mode_rig.execute(0)
        import_lighting_rig.execute(**import_args)
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}")))
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}/{rig_loc}")))

        # Test 1: Default
        stage, rig_loc = await restart_stage("Default")
        self.assertFalse(bool(stage.GetPrimAtPath(f"{env_name}")))
        set_lighting_mode_rig.execute(1)
        import_lighting_rig.execute(**import_args)
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}")))
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}/{rig_loc}")))

        # Test 2: Grey Studio with default clearing of /Environment children
        stage, rig_loc = await restart_stage("Grey_Studio")
        self.assertFalse(bool(stage.GetPrimAtPath(f"{env_name}")))
        UsdGeom.Xform.Define(stage, f"{env_name}")
        UsdGeom.Xform.Define(stage, f"{env_name}/Child1")
        UsdGeom.Xform.Define(stage, f"{env_name}/Child2")

        UsdGeom.Xform.Define(stage, f"{env_name}/Child3")
        UsdLux.SphereLight.Define(stage, f"{env_name}/Child3/SphereLight")

        UsdGeom.Xform.Define(stage, f"{env_name}/Child4")
        UsdGeom.Mesh.Define(stage, f"{env_name}/Child4/Mesh")

        UsdGeom.Xform.Define(stage, f"{env_name}/Child5")
        UsdLux.SphereLight.Define(stage, f"{env_name}/Child5/SphereLight")
        UsdGeom.Mesh.Define(stage, f"{env_name}/Child5/Mesh")

        UsdGeom.Xform.Define(stage, f"{env_name}/Child6")
        UsdGeom.Xform.Define(stage, f"{env_name}/Child6/Child6b")
        UsdLux.SphereLight.Define(stage, f"{env_name}/Child6/Child6b/SphereLight")
        UsdGeom.Mesh.Define(stage, f"{env_name}/Child6/Child6b/Mesh")

        UsdGeom.Scope.Define(stage, f"{env_name}/Child7")
        UsdLux.SphereLight.Define(stage, f"{env_name}/Child7/SphereLightA")
        UsdLux.DistantLight.Define(stage, f"{env_name}/Child7/DistantLight")
        UsdLux.SphereLight.Define(stage, f"{env_name}/Child7/SphereLightB")

        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}")))
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}/Child1")))
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}/Child2")))
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}/Child3/SphereLight")))
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}/Child4/Mesh")))
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}/Child5/SphereLight")))
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}/Child5/Mesh")))
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}/Child6/Child6b/SphereLight")))
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}/Child6/Child6b/Mesh")))
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}/Child7")))
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}/Child7/SphereLightA")))
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}/Child7/SphereLightB")))
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}/Child7/DistantLight")))

        set_lighting_mode_rig.execute(2)
        import_lighting_rig.execute(**import_args)
        # These should have been added
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}")))
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}/{rig_loc}")))
        # Check the validity of children based on whether they should have been cleared
        self.assertEqual(bool(stage.GetPrimAtPath(f"{env_name}/Child1")), not children_cleared)
        self.assertEqual(bool(stage.GetPrimAtPath(f"{env_name}/Child2")), not children_cleared)
        self.assertEqual(bool(stage.GetPrimAtPath(f"{env_name}/Child3")), not children_cleared)
        self.assertEqual(bool(stage.GetPrimAtPath(f"{env_name}/Child3/SphereLight")), not children_cleared)
        self.assertEqual(bool(stage.GetPrimAtPath(f"{env_name}/Child5/SphereLight")), not children_cleared)

        self.assertEqual(bool(stage.GetPrimAtPath(f"{env_name}/Child7")), not children_cleared)
        self.assertEqual(bool(stage.GetPrimAtPath(f"{env_name}/Child7/SphereLightA")), not children_cleared)
        self.assertEqual(bool(stage.GetPrimAtPath(f"{env_name}/Child7/SphereLightB")), not children_cleared)
        self.assertEqual(bool(stage.GetPrimAtPath(f"{env_name}/Child7/DistantLight")), not children_cleared)

        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}/Child6/Child6b/SphereLight")))
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}/Child6/Child6b/Mesh")))
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}/Child4/Mesh")))
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}/Child5/Mesh")))

        # Run an undo to check stage restoration
        omni.kit.undo.undo()

        # These two should come back to life
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}/Child1")))
        self.assertTrue(bool(stage.GetPrimAtPath(f"{env_name}/Child2")))
        # And this should now be gone
        self.assertFalse(bool(stage.GetPrimAtPath(f"{env_name}/{rig_loc}")))

    async def test_stage_lights_restore_propagation(self):
        """OMPE-99588: restoring Stage Lights must propagate renderer-visible state changes."""
        settings = carb.settings.get_settings()
        auto_rig_key = "/persistent/exts/omni.kit.viewport.menubar.lighting/autoLightRig/enabled"
        restore_auto_rig = settings.get(auto_rig_key)
        settings.set(auto_rig_key, False)

        usd_context = omni.usd.get_context()
        await usd_context.new_stage_async()
        stage = usd_context.get_stage()
        session_layer = stage.GetSessionLayer()

        dome = UsdLux.DomeLight.Define(stage, "/World/DomeLight").GetPrim()
        sphere = UsdLux.SphereLight.Define(stage, "/World/SphereLight").GetPrim()
        # A light the user hid in the root layer must stay hidden across the rig cycle
        UsdGeom.Imageable(sphere).GetVisibilityAttr().Set(UsdGeom.Tokens.invisible)

        ar = omni.kit.actions.core.get_action_registry()
        set_lighting_mode_rig = ar.get_action("omni.kit.viewport.menubar.lighting", "set_lighting_mode_rig")
        set_lighting_mode_stage = ar.get_action("omni.kit.viewport.menubar.lighting", "set_lighting_mode_stage")

        try:
            set_lighting_mode_rig.execute("Default", usd_context=usd_context)
            await self.wait_frames()

            self.assertEqual(UsdGeom.Imageable(dome).ComputeVisibility(), UsdGeom.Tokens.invisible)
            self.assertIsNotNone(session_layer.GetPropertyAtPath("/World/DomeLight.visibility"))

            events = []

            def on_changed(notice, sender):
                events.append(
                    (
                        [str(p) for p in notice.GetResyncedPaths()],
                        [str(p) for p in notice.GetChangedInfoOnlyPaths()],
                    )
                )

            listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, on_changed, stage)
            try:
                set_lighting_mode_stage.execute()
            finally:
                listener.Revoke()
            await self.wait_frames()

            # Composed state: dome restored, user-hidden sphere still invisible
            self.assertEqual(UsdGeom.Imageable(dome).ComputeVisibility(), UsdGeom.Tokens.inherited)
            self.assertEqual(UsdGeom.Imageable(sphere).ComputeVisibility(), UsdGeom.Tokens.invisible)

            # Session overrides removed so weaker-layer edits are not shadowed
            self.assertIsNone(session_layer.GetPropertyAtPath("/World/DomeLight.visibility"))
            self.assertIsNone(session_layer.GetPropertyAtPath("/World/SphereLight.visibility"))

            # Restore must emit a visibility value-change and a prim-level resync (OMPE-99588)
            info_changed = [p for resynced, info in events for p in info]
            resynced_paths = [p for resynced, info in events for p in resynced]
            self.assertIn("/World/DomeLight.visibility", info_changed)
            self.assertIn("/World/DomeLight", resynced_paths)
            self.assertIn("/World/SphereLight", resynced_paths)

            # The temporary active=true opinions are cleaned up a frame later
            self.assertFalse(dome.HasAuthoredActive())
            self.assertFalse(sphere.HasAuthoredActive())

            # And a subsequent user visibility edit still composes correctly
            UsdGeom.Imageable(dome).GetVisibilityAttr().Set(UsdGeom.Tokens.invisible)
            await self.wait_frames()
            self.assertEqual(UsdGeom.Imageable(dome).ComputeVisibility(), UsdGeom.Tokens.invisible)
        finally:
            settings.set(auto_rig_key, bool(restore_auto_rig))

    async def test_stage_lights_restore_preserves_session_active(self):
        """OMPE-99588: restoring Stage Lights must preserve a pre-existing session 'active' opinion."""
        settings = carb.settings.get_settings()
        auto_rig_key = "/persistent/exts/omni.kit.viewport.menubar.lighting/autoLightRig/enabled"
        restore_auto_rig = settings.get(auto_rig_key)
        settings.set(auto_rig_key, False)

        usd_context = omni.usd.get_context()
        await usd_context.new_stage_async()
        stage = usd_context.get_stage()
        root_layer = stage.GetRootLayer()
        session_layer = stage.GetSessionLayer()

        sphere = UsdLux.SphereLight.Define(stage, "/World/SphereLight").GetPrim()

        # Root authors active=false; a stronger session opinion re-activates the light.
        with Usd.EditContext(stage, root_layer):
            sphere.SetActive(False)
        with Usd.EditContext(stage, session_layer):
            sphere.SetActive(True)

        self.assertTrue(sphere.IsActive())
        self.assertEqual(root_layer.GetPrimAtPath("/World/SphereLight").active, False)
        self.assertEqual(session_layer.GetPrimAtPath("/World/SphereLight").active, True)

        ar = omni.kit.actions.core.get_action_registry()
        set_lighting_mode_rig = ar.get_action("omni.kit.viewport.menubar.lighting", "set_lighting_mode_rig")
        set_lighting_mode_stage = ar.get_action("omni.kit.viewport.menubar.lighting", "set_lighting_mode_stage")

        try:
            set_lighting_mode_rig.execute("Default", usd_context=usd_context)
            await self.wait_frames()

            self.assertEqual(UsdGeom.Imageable(sphere).ComputeVisibility(), UsdGeom.Tokens.invisible)
            self.assertIsNotNone(session_layer.GetPropertyAtPath("/World/SphereLight.visibility"))

            events = []

            def on_changed(notice, sender):
                events.append([str(p) for p in notice.GetResyncedPaths()])

            listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, on_changed, stage)
            try:
                set_lighting_mode_stage.execute()
            finally:
                listener.Revoke()
            await self.wait_frames()

            # Restore must still emit a prim-level resync even though session active was already true
            resynced_paths = [p for resynced in events for p in resynced]
            self.assertIn("/World/SphereLight", resynced_paths)

            # Session visibility override removed and the light is visible again
            self.assertIsNone(session_layer.GetPropertyAtPath("/World/SphereLight.visibility"))
            self.assertEqual(UsdGeom.Imageable(sphere).ComputeVisibility(), UsdGeom.Tokens.inherited)

            # Deferred cleanup must restore the pre-existing opinions, not clear them, so the light stays active
            self.assertTrue(sphere.IsActive())
            root_spec = root_layer.GetPrimAtPath("/World/SphereLight")
            session_spec = session_layer.GetPrimAtPath("/World/SphereLight")
            self.assertIsNotNone(root_spec)
            self.assertTrue(root_spec.HasActive())
            self.assertEqual(root_spec.active, False)
            self.assertIsNotNone(session_spec)
            self.assertTrue(session_spec.HasActive())
            self.assertEqual(session_spec.active, True)
        finally:
            # Reset to a fresh stage so any deferred active-cleanup drains and later tests start clean
            await usd_context.new_stage_async()
            await self.wait_frames()
            settings.set(auto_rig_key, bool(restore_auto_rig))

    async def test_import_lighting_rig_action(self):
        """Test import of light rig honors scene hierarchy and settings to control it."""

        settings = carb.settings.get_settings()
        # Build a list of all the settings this test may change
        rig_import_section = "/exts/omni.kit.viewport.menubar.lighting/rigImport"
        settings_in = [
            f"{rig_import_section}{child}" for child in ["/primName", "/root", "/lightRemovalLimit", "PrimName"]
        ]
        # Build a dict of the setting key to start-value
        settings_in = {k: settings.get(k) for k in settings_in}

        def restore_setting(k):
            v = settings_in.get(k)
            if v is not None:
                settings.set(k, v)
            else:
                settings.destroy_item(k)

        try:
            await self.__test_import_lighting_rig_action()

            await self.__test_import_lighting_rig_action(rig_name="ArgLocation", import_args={"path_to": "ArgLocation"})

            settings.set(f"{rig_import_section}/primName", "CustomPrim")
            await self.__test_import_lighting_rig_action(rig_name="CustomPrim")
            settings.destroy_item(f"{rig_import_section}/primName")

            tst_key = f"{rig_import_section}PrimName"
            settings.set(tst_key, "CustomPrimLegacy")
            await self.__test_import_lighting_rig_action(rig_name="CustomPrimLegacy")
            restore_setting(tst_key)

            tst_key = f"{rig_import_section}/root"
            settings.set(f"{rig_import_section}/root", "/CustomEnvironment")
            await self.__test_import_lighting_rig_action("/CustomEnvironment")

            settings.set(f"{rig_import_section}/lightRemovalLimit", 0)
            await self.__test_import_lighting_rig_action("/CustomEnvironment", children_cleared=False)

            restore_setting(tst_key)
            await self.__test_import_lighting_rig_action(children_cleared=False)

        finally:
            for k in settings_in.keys():
                restore_setting(k)
