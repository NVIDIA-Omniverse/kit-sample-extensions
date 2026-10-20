from pathlib import Path

import omni.kit.test
from pxr import Plug, Tf, Usd, UsdGeom


class SceneVisualizationSchemaTest(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._context = omni.usd.get_context()
        await self._context.new_stage_async()
        self._stage = self._context.get_stage()

    async def tearDown(self):
        pass

    async def test_types(self):

        schema_plugin = Plug.Registry().GetPluginWithName("omniSceneVisualizationSchema")
        self.assertTrue(schema_plugin is not None)

        reg = Usd.SchemaRegistry()
        api_type = "OmniSceneVisualizationAPI"
        self.assertTrue(reg.IsAppliedAPISchema(api_type))

    async def test_apply(self):

        prim = self._stage.DefinePrim("/somePrim", "Xform")

        schema_name = "OmniSceneVisualizationAPI"

        # Some contortion here where we get a type with the OmniDynamics prefix prepended to the schema name;
        # there must be a cleaner USD way to do this...
        api = Usd.SchemaRegistry.GetAPITypeFromSchemaTypeName(schema_name)

        prim.ApplyAPI(api)

        # Did we apply the schema correctly?
        self.assertEqual(prim.GetAppliedSchemas(), [schema_name])

        # Do we have the attrs we'd expect from the schema?
        property_names = prim.GetPropertyNames()
        attrs = ["omni:scene:visualization:drawWireframe"]
        for attr in attrs:
            self.assertTrue(attr in property_names)
