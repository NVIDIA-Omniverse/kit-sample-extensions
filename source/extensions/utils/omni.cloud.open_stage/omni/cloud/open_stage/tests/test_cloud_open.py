from pathlib import Path

# NOTE:
#   omni.kit.test - std python's unittest module with additional wrapping to add suport for async/await tests
#   For most things refer to unittest docs: https://docs.python.org/3/library/unittest.html
# Import extension python module we are testing with absolute import path, as if we are external user (other extension)
import carb.tokens
import omni.kit.test
import omni.kit.ui_test as ui_test
from omni.cloud.open_stage import get_endpoint_performance, get_session_status, open_stage_async


# Having a test class dervived from omni.kit.test.AsyncTestCase declared on the root of module will make it auto-discoverable by omni.kit.test
class Test(omni.kit.test.AsyncTestCase):
    # Before running each test
    async def setUp(self):
        # Capture test usd file path
        root = carb.tokens.get_tokens_interface().resolve("${omni.cloud.open_stage}")
        self.__test_stage = Path(root) / "data" / "test_stage.usd"

    # After running each test
    async def tearDown(self):
        pass

    async def test_open_stage(self):
        await open_stage_async(str(self.__test_stage))

        await ui_test.human_delay(10)
        session_status = get_session_status()
        # The open is in progress or finished: on Kit 111 ASSETS_LOADED can already have followed OPENED within these
        # frames (status "loaded"); a failed or unknown open is still an error.
        self.assertIn(session_status["scene_status"], ("opening", "loaded"))
        self.assertTrue(Path(session_status["scene_name"]) == self.__test_stage)

        await ui_test.human_delay(10)
        await get_endpoint_performance()
