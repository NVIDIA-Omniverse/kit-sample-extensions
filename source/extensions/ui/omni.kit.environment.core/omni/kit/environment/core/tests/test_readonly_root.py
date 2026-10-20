# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
from pathlib import Path

import carb.settings
import omni.kit.app
import omni.kit.test
import omni.usd
from omni.kit.environment.core import EnvironmentSettings, SkyHelper, SkyType
from omni.kit.environment.core.utils import can_remove_environment_content
from pxr import Sdf, UsdLux

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
SKIES_PATH = f"{TEST_DATA_PATH}/Skies"
HDR_SKY_URL = f"{SKIES_PATH}/Hdr/CarLight_512x256.hdr"
DYNAMIC_SKY_URL = f"{SKIES_PATH}/Dynamic/simple.usd"
# Brings the same prim below the sky in as DYNAMIC_SKY_URL, through the reference of the sky
DYNAMIC_SKY_ALT_URL = f"{SKIES_PATH}/Dynamic/simple_alt.usda"
# Brings the same properties in as DYNAMIC_SKY_ALT_URL, also through the reference of the sky
DYNAMIC_SKY_REF_URL = f"{SKIES_PATH}/Dynamic/simple_ref.usda"
SCENE_TEMPLATE_URL = f"{SKIES_PATH}/Template/template.usd"
SKY_PATH = "/Environment/sky"
REFERENCED_SKY_CHILD_PATH = "/Environment/sky/Cone"
REFERENCED_ATTRIBUTE = "skyMode"
REFERENCED_RELATIONSHIP = "skyTarget"
OLD_ONLY_ATTRIBUTE = "oldOnly"


class TestEnvironmentReadOnlyRoot(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self.__settings = carb.settings.get_settings()
        self.__saved_ground = self.__settings.get(EnvironmentSettings.GROUND_ENABLE)
        self.__settings.set(EnvironmentSettings.GROUND_ENABLE, False)
        self.__saved_light_warning = self.__settings.get(EnvironmentSettings.SHOW_LIGHT_WARNING)
        self.__settings.set(EnvironmentSettings.SHOW_LIGHT_WARNING, False)

        try:
            from omni.kit.actions.core import get_action_registry

            self.__action = get_action_registry().get_action("omni.kit.environment.core", "import")
        except ImportError:
            self.__action = None

        self.usd_context = omni.usd.get_context()
        await self.usd_context.new_stage_async()

    async def tearDown(self):
        stage = self.usd_context.get_stage()
        if stage:
            stage.GetRootLayer().SetPermissionToEdit(True)
        self.__settings.set(EnvironmentSettings.GROUND_ENABLE, self.__saved_ground)
        self.__settings.set(EnvironmentSettings.SHOW_LIGHT_WARNING, self.__saved_light_warning)

    async def __import_environment(self, sky_url: str, expected_type: SkyType):
        sky_type = SkyHelper.get_env_file_type(sky_url)
        self.assertEqual(sky_type, expected_type)

        if self.__action:
            self.__action.execute(sky_type, sky_url)
        else:
            from omni.kit.environment.core import import_environment

            import_environment(sky_type, sky_url)

        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

    def __set_root_layer_writable(self, writable: bool):
        self.usd_context.get_stage().GetRootLayer().SetPermissionToEdit(writable)

    def __assert_hdri_sky(self, message: str):
        stage = self.usd_context.get_stage()
        sky_prim = stage.GetPrimAtPath(SKY_PATH)
        self.assertTrue(bool(sky_prim) and sky_prim.IsValid(), message)
        self.assertTrue(sky_prim.IsA(UsdLux.DomeLight), message)
        self.assertTrue(sky_prim.IsActive(), message)
        sky_attr = sky_prim.GetAttribute("inputs:texture:file")
        self.assertIsNotNone(sky_attr.Get(), message)
        self.assertEqual(sky_attr.Get().path, HDR_SKY_URL, message)

    async def test_change_env_with_readonly_root_layer(self):
        # OMPE-64890: root layer not writable/saveable and not in a live session.
        self.__set_root_layer_writable(False)

        await self.__import_environment(HDR_SKY_URL, SkyType.HDRI)

        self.__assert_hdri_sky("Environment sky prim was not created when the root layer is not writable")

    async def test_switch_env_with_readonly_root_layer(self):
        # OMPE-64890: switching also has to remove the previous sky.
        await self.__import_environment(DYNAMIC_SKY_URL, SkyType.DYNAMIC)
        stage = self.usd_context.get_stage()
        dynamic_sky_prim = stage.GetPrimAtPath(SKY_PATH)
        self.assertTrue(dynamic_sky_prim.IsValid())
        dynamic_sky_children = [prim.GetPath().pathString for prim in dynamic_sky_prim.GetChildren()]
        self.assertTrue(dynamic_sky_children, "Dynamic sky was not set up, the test cannot detect leftovers")
        dynamic_sky_prim.CreateAttribute(OLD_ONLY_ATTRIBUTE, Sdf.ValueTypeNames.String).Set("stale")

        self.__set_root_layer_writable(False)
        await self.__import_environment(HDR_SKY_URL, SkyType.HDRI)

        self.__assert_hdri_sky("Environment sky was not switched when the root layer is not writable")
        stage = self.usd_context.get_stage()
        for path in dynamic_sky_children:
            # A hidden prim is still reachable, but no longer part of the scene
            prim = stage.GetPrimAtPath(path)
            self.assertFalse(
                bool(prim) and prim.IsActive(),
                f"Previous dynamic sky prim {path} was left on the stage when the root layer is not writable",
            )
        self.assertIsNone(
            stage.GetPrimAtPath(SKY_PATH).GetAttribute(OLD_ONLY_ATTRIBUTE).Get(),
            "A property of the previous sky still contributes when the root layer is not writable",
        )

    async def test_switch_dynamic_sky_with_readonly_root_layer(self):
        # OMPE-64890: both skies bring the same prim below the sky in through their reference, so
        # hiding it for the previous one would hide it for the new one too.
        await self.__import_environment(DYNAMIC_SKY_URL, SkyType.DYNAMIC)
        child_prim = self.usd_context.get_stage().GetPrimAtPath(REFERENCED_SKY_CHILD_PATH)
        self.assertTrue(bool(child_prim) and child_prim.IsActive(), "The referenced prim is not on the stage")
        replaced_type = child_prim.GetTypeName()

        self.__set_root_layer_writable(False)
        await self.__import_environment(DYNAMIC_SKY_ALT_URL, SkyType.DYNAMIC)

        child_prim = self.usd_context.get_stage().GetPrimAtPath(REFERENCED_SKY_CHILD_PATH)
        self.assertTrue(
            bool(child_prim) and child_prim.IsActive(),
            "The prim referenced by the new dynamic sky is hidden when the root layer is not writable",
        )
        self.assertNotEqual(child_prim.GetTypeName(), replaced_type, "The previous dynamic sky was not replaced")

    def __assert_referenced_sky_properties(self, sky_mode: str, message: str):
        sky_prim = self.usd_context.get_stage().GetPrimAtPath(SKY_PATH)
        self.assertEqual(sky_prim.GetAttribute(REFERENCED_ATTRIBUTE).Get(), sky_mode, message)
        self.assertEqual(
            sky_prim.GetRelationship(REFERENCED_RELATIONSHIP).GetTargets(),
            [Sdf.Path(REFERENCED_SKY_CHILD_PATH)],
            message,
        )

    async def test_switch_dynamic_sky_keeps_its_referenced_properties(self):
        # OMPE-64890: both skies bring these in through their reference, so blocking them for the
        # previous sky would suppress them for the new one.
        await self.__import_environment(DYNAMIC_SKY_REF_URL, SkyType.DYNAMIC)
        self.__assert_referenced_sky_properties("base", "The referenced properties are not on the stage")

        self.__set_root_layer_writable(False)
        await self.__import_environment(DYNAMIC_SKY_ALT_URL, SkyType.DYNAMIC)

        self.__assert_referenced_sky_properties(
            "alt", "The properties of the new dynamic sky are suppressed when the root layer is not writable"
        )

    async def test_switch_hdri_to_dynamic_sky_with_readonly_root_layer(self):
        # OMPE-64890: the hdri sky authors its properties on the sky prim itself, the dynamic sky
        # replacing it brings its own in through a reference.
        await self.__import_environment(HDR_SKY_URL, SkyType.HDRI)

        self.__set_root_layer_writable(False)
        await self.__import_environment(DYNAMIC_SKY_ALT_URL, SkyType.DYNAMIC)

        self.__assert_referenced_sky_properties(
            "alt", "The properties of the dynamic sky are suppressed when the root layer is not writable"
        )
        self.assertIsNone(
            self.usd_context.get_stage().GetPrimAtPath(SKY_PATH).GetAttribute("inputs:texture:file").Get(),
            "A property of the replaced hdri sky still contributes when the root layer is not writable",
        )

    async def test_scene_template_is_refused_with_readonly_root_layer(self):
        # OMPE-64890: the environment a template replaces cannot be removed, so it is refused.
        await self.__import_environment(HDR_SKY_URL, SkyType.HDRI)

        self.__set_root_layer_writable(False)
        await self.__import_environment(SCENE_TEMPLATE_URL, SkyType.SCENE)

        self.__assert_hdri_sky("The environment changed even though the scene template was refused")

    async def test_environment_content_is_removable_with_writable_root_layer_only(self):
        # OMPE-64890: the rule delete_environment_prims() removes or hides by, and the one a scene
        # template is refused by, are the same one.
        await self.__import_environment(HDR_SKY_URL, SkyType.HDRI)
        stage = self.usd_context.get_stage()
        self.assertTrue(can_remove_environment_content(stage))

        self.__set_root_layer_writable(False)
        self.assertFalse(can_remove_environment_content(stage))
