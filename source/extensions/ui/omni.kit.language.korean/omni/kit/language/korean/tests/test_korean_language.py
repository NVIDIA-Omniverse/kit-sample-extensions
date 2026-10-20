from pathlib import Path

import carb
import omni.kit.app
import omni.kit.test
import omni.kit.ui_test as ui_test
from omni.kit.mainwindow import get_main_window
from omni.kit.test_suite.helpers import get_test_data_path
from omni.ui.tests.compare_utils import CompareMetric
from omni.ui.tests.test_base import OmniUiTest


def _golden_img_name(golden_img_dir: Path, name: str) -> str:
    """'<name>-111.0.png' on Kit 111+ when present, else '<name>.png'.

    Kit 111 draws omni.ui through OVUI: its main menu bar is 22 px instead of 19 px (the Preferences window placed at
    y=0 is clamped 2 px higher), and CJK text wraps at ideographic punctuation instead of only at spaces.
    """
    kit_version = float(omni.kit.app.get_app().get_kit_version_short())
    if kit_version >= 111.0 and golden_img_dir.joinpath(f"{name}-111.0.png").exists():
        return f"{name}-111.0.png"
    return f"{name}.png"


class TestLanguageKorean(OmniUiTest):
    # Before running each test
    async def setUp(self):
        omni.kit.window.preferences.show_preferences_window()

    # After running each test
    async def tearDown(self):
        omni.kit.window.preferences.hide_preferences_window()

    async def test_language_ui(self):
        # verify language zh-CN is known
        extension_path = omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
        expected_info = {
            "language_name": "Korean",
            "language_name_localized": "한국어",
            "pangram": "다람쥐 헌 쳇바퀴에 타고파",
            "font_path": f"{extension_path}/data/fonts/NotoSansKR-SemiBold.ttf",
            "font_scale": 1.2,
            "regions": [
                f"{extension_path}/data/regions/Korean.txt",
                f"{extension_path}/data/regions/Korean_2.txt",
            ],
            "font_overresolution_size": 66,
        }

        self.assertEqual(
            omni.kit.language.core.get_language_info(omni.kit.language.core.get_locale_id()), expected_info
        )

        # select language page
        pages = omni.kit.window.preferences.get_page_list()
        for page in pages:
            if page.get_title() == "Language":
                omni.kit.window.preferences.select_page(page)
                await ui_test.human_delay(50)

        # maximize window
        window = omni.ui.Workspace.get_window("Preferences")
        window.position_x = 0
        window.position_y = 0
        window.width = 1440
        window.height = 900
        await ui_test.human_delay(10)

        # verify golden image
        golden_img_dir = Path(get_test_data_path(__name__, "golden_img"))
        await self.finalize_test(
            golden_img_dir=golden_img_dir,
            golden_img_name=_golden_img_name(golden_img_dir, "test_korean_font"),
            cmp_metric=CompareMetric.MEAN_ERROR_SQUARED,
            hide_menu_bar=False,
        )
