from pathlib import Path

import carb
import omni.kit
import omni.kit.app
import omni.kit.test
import omni.usd
from omni.kit import ui_test
from omni.kit.viewport.utility import get_active_viewport_window, next_viewport_frame_async
from omni.ui.tests.test_base import OmniUiTest

TEST_DATA_PATH = Path(carb.tokens.get_tokens_interface().resolve("${omni.graph.visualization.nodes}/data/tests"))
OUTPUTS_DIR = Path(omni.kit.test.get_test_output_path())


class TestDrawScreenSpaceText(OmniUiTest):
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = TEST_DATA_PATH.absolute().resolve().joinpath("golden")

    # After running each test
    async def tearDown(self):
        self._golden_img_dir = None
        await super().tearDown()

    async def setup_viewport(self, resolution_x: int = 800, resolution_y: int = 600):
        await self.create_test_area(resolution_x, resolution_y)
        return get_active_viewport_window()

    async def test_draw_screen_space_text(self):
        viewport_window = await self.setup_viewport()
        viewport = viewport_window.viewport_api

        test_file = TEST_DATA_PATH.joinpath("draw_screen_space_text.usda")
        context = omni.usd.get_context()
        await context.open_stage_async(str(test_file))
        stage = context.get_stage()

        # Wait until the Viewport has delivered some frames
        await next_viewport_frame_async(viewport, 2)

        await ui_test.wait_n_updates(10)

        await self.finalize_test(golden_img_dir=self._golden_img_dir, golden_img_name="test_draw_screen_space_text.png")

        await context.close_stage_async()
