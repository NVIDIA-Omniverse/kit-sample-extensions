import omni.kit.app
import omni.kit.test
import omni.usd
from omni.kit.text3d import create_text_prim
from pxr import Sdf


class TestText3d(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        await omni.usd.get_context().new_stage_async()

    async def test_text_creation(self):
        """Test that we can create a Text Prim"""
        stage = omni.usd.get_context().get_stage()
        text_prim_path = create_text_prim(stage, Sdf.Path("/Text"))
        text_prim = stage.GetPrimAtPath(Sdf.Path(text_prim_path))
        self.assertTrue(text_prim.IsValid())
        for txt in ("Lorem ipsum dolor sit amet, consectetur adipiscing elit", "Foo"):
            stage.GetAttributeAtPath(f"{text_prim_path}/PushGraph/generate_3d_text.inputs:text").Set(txt)
            # Wait a bit for node to compute
            await omni.kit.app.get_app().next_update_async()
            await omni.kit.app.get_app().next_update_async()
            # Verify the instancer has been updated
            positions = stage.GetAttributeAtPath(f"{text_prim_path}/instancer.positions").Get()
            self.assertEqual(len(positions), len(txt.replace(" ", "")))
