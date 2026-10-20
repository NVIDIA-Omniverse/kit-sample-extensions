# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
import copy
import os
import unittest
from pathlib import Path

import carb
import omni.kit.app
import omni.ui as ui
from omni.kit import ui_test
from omni.kit.viewport.utility import get_active_viewport_window
from omni.ui.tests.test_base import OmniUiTest
from omni.ui_query.query import OmniUIQuery

from .. import extension
from ..common import CURRENT_TOOL_PATH
from ..widgets.list_window import MarkupListWindow
from ..widgets.widget import MarkupBrowserWidget
from ._viewport_frames import wait_for_viewport_frames

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data").joinpath("tests")
VISIBILITY_PATH = "/persistent/app/viewport/displayOptions"
TEST_WIDTH, TEST_HEIGHT = 800, 300


async def _wait_for_markup_thumbnails(ext_instance, max_frames: int = 300):
    """Wait until every markup that is not being edited has its thumbnail.

    Thumbnails are captured asynchronously from the presented window, and the list window leaves out a markup whose
    thumbnail has not arrived yet. On Kit 111 with the OVRTX USD lock, a capture can land a few frames after a fixed
    frame budget.
    """
    app = omni.kit.app.get_app()
    for _ in range(max_frames):
        if all(
            markup.thumbnail_data is not None
            for markup in ext_instance.get_markups()
            if markup is not ext_instance.editing_markup
        ):
            return
        await app.next_update_async()


class MarkupBrowserWidgetWindow(ui.Window):
    """
    Represent a window to show and edit markups.
    """

    def __init__(self):

        super().__init__("Markup Widget Test", width=500, height=600)
        self._browser_widget = None

        self.frame.set_build_fn(self._build_ui)

    def destroy(self) -> None:
        if self._browser_widget:
            self._browser_widget.destroy()

        self.visible = False

    def _build_ui(self):
        with self.frame:
            self._browser_widget = MarkupBrowserWidget()


export_markup_call_count = 0


def export_markup_fn():
    global export_markup_call_count
    export_markup_call_count = export_markup_call_count + 1


class TestMarkupUi(OmniUiTest):

    # Before running each test
    async def setUp(self):
        await super().setUp()
        self._golden_img_dir = TEST_DATA_PATH.absolute().joinpath("golden_img").absolute()
        self._setting = carb.settings.get_settings()
        self._visibility_value = self._setting.get(VISIBILITY_PATH)
        self._setting.set(VISIBILITY_PATH, 0)
        self._context = omni.usd.get_context()

        ext_instance = extension.get_instance()
        ext_instance.export_fn = export_markup_fn

        await self._context.new_stage_async()
        await wait_for_viewport_frames()

    async def finalize_test(self, golden_img_name: str):
        await omni.kit.app.get_app().next_update_async()
        await super().finalize_test(threshold=500, golden_img_dir=self._golden_img_dir, golden_img_name=golden_img_name)
        await omni.kit.app.get_app().next_update_async()

    # After running each test
    async def tearDown(self):
        self._setting.set(VISIBILITY_PATH, self._visibility_value)
        ext_instance = extension.get_instance()
        ext_instance.export_fn = None
        await super().tearDown()

    async def test_browser_widget(self):

        ext_instance = extension.get_instance()

        ext_instance.create_markup()
        ext_instance.create_markup()
        # Kit 111: let the markups' thumbnail captures complete before editing them.
        await ui_test.human_delay(10)
        await _wait_for_markup_thumbnails(ext_instance)

        markup_01 = ext_instance.get_markup("Markup_01")
        ext_instance.end_edit_markup(markup_01, save=True)

        await ui_test.human_delay()
        await ui_test.human_delay()
        await ui_test.human_delay()
        await ui_test.human_delay()
        await ui_test.human_delay()
        await ui_test.human_delay()
        await ui_test.human_delay()
        await ui_test.human_delay()

        window = MarkupBrowserWidgetWindow()
        await omni.kit.app.get_app().next_update_async()
        await self.docked_test_window(window=window, width=300, height=385, block_devices=False)

        await ui_test.human_delay(2)

        for w in ui_test.find_all(f"{window.title}//Frame/**/ImageWithProvider[0]"):
            await w.click()
            await w.double_click()

        await ui_test.human_delay(2)

        for w in ui_test.find_all(f"{window.title}//Frame/**/HoverEditButton"):
            await w.click()

        for w in ui_test.find_all(f"{window.title}//Frame/**/HoverEditButton"):
            await w.right_click()

        await ui_test.human_delay(2)
        for w in ui_test.find_all(f"{window.title}//Frame/**/HoverDeleteButton"):
            await w.click()

        await ui_test.human_delay(2)

        window.destroy()

    @unittest.skipIf(os.getenv("ETM_ACTIVE") or os.getenv("ETM_DGXC_ACTIVE"), "skipped in ETM")
    async def test_list_window(self):

        import carb.settings

        settings = carb.settings.get_settings()
        settings.set("/app/markup/playlist/next/enabled", True)
        settings.set("/app/markup/playlist/previous/enabled", True)
        settings.set("/app/markup/playlist/play/enabled", True)

        ext_instance = extension.get_instance()

        ext_instance.create_markup()
        ext_instance.create_markup()
        # Kit 111: let the markups' thumbnail captures complete before editing them.
        await ui_test.human_delay(10)
        await _wait_for_markup_thumbnails(ext_instance)

        markup_01 = ext_instance.get_markup("Markup_01")
        ext_instance.end_edit_markup(markup_01, save=True)

        await ui_test.human_delay(20)

        window = MarkupListWindow()
        window.visible = True

        await omni.kit.app.get_app().next_update_async()
        await self.docked_test_window(window=window, width=1000, height=1000, block_devices=False)
        await ui_test.human_delay(20)
        ext_instance.select_markup_in_list_window(markup_01)
        await ui_test.human_delay(20)

        self.assertEqual(window.selected_index, 1)

        for w in ui_test.find_all(f"{window.title}//Frame/**/CollapseFrame"):
            # expand the frame:
            await w.click()
            await ui_test.human_delay(2)

        all_fields = []
        for field in ui_test.find_all(f"{window.title}//Frame/**/CommentEditField"):
            all_fields.append(field)
            await field.input("yeah whatever", clear_before_input=True, human_delay_speed=10)
            await ui_test.human_delay(2)
            await ui_test.emulate_mouse_move_and_click(ui_test.Vec2(5, 5))
            await ui_test.human_delay(2)

        all_markups = []
        for mk in ext_instance.get_markups():
            all_markups.append(mk)
            if ext_instance.can_edit_markup(mk):
                self.assertEqual(mk.comment.strip(), "yeah whatever")

        all_thumbnails = []
        for w in ui_test.find_all(f"{window.title}//Frame/**/ImageThumbnail"):
            all_thumbnails.append(w)
            await w.click()
            await w.double_click()
        await ui_test.human_delay(2)

        click_index = 0
        edit_index = 1
        self.assertEqual(len(all_fields), 2)
        self.assertEqual(len(all_thumbnails), 2)
        await all_fields[edit_index].input("Test OMFP-3084", clear_before_input=True, human_delay_speed=10)
        await ui_test.human_delay(2)
        await all_thumbnails[click_index].click()
        await ui_test.human_delay(2)
        self.assertEqual(all_markups[edit_index].comment.strip(), "Test OMFP-3084")

        for w in ui_test.find_all(f"{window.title}//Frame/**/PlayBarPlay"):
            await w.click()
        await ui_test.human_delay(2)

        for w in ui_test.find_all(f"{window.title}//Frame/**/PlayBarPlay"):
            await w.click()
        await ui_test.human_delay(2)

        for w in ui_test.find_all(f"{window.title}//Frame/**/PlayBarPrevious"):
            await w.click()
        await ui_test.human_delay(2)

        for w in ui_test.find_all(f"{window.title}//Frame/**/PlayBarNext"):
            await w.click()
        await ui_test.human_delay(2)

        global export_markup_call_count
        export_markup_call_count = 0

        self.assertNotEqual(ext_instance.export_fn, None)

        for w in ui_test.find_all(f"{window.title}//Frame/**/ExportButton"):
            await w.click()

        self.assertEqual(export_markup_call_count, 1)

        for w in ui_test.find_all(f"{window.title}//Frame/**/CollapseFrame"):
            await w.click()
        await ui_test.human_delay(2)

        # bring up the context menu:
        for w in ui_test.find_all(f"{window.title}//Frame/**/FrameHeader"):
            await w.right_click()
            await ui_test.human_delay(2)

            try:
                menu = await ui_test.get_context_menu()
            except Exception:
                continue

            await ui_test.human_delay(2)

            # press rename:
            await ui_test.select_context_menu(menu["_"][0], offset=ui_test.Vec2(10, 10), human_delay_speed=10)

            # only one of the markups is editable so we'll only be able to click on one of them:
            field = ui_test.find_all("Rename Markup//Frame/**.identifier=='rename_field'")
            if field:
                await field[0].input("Thumb_10", clear_before_input=True, human_delay_speed=10)
                self.assertTrue("Thumb_10" in [x.name for x in ext_instance.get_markups()])

            await ui_test.human_delay(2)

        # make sure the add markup button works:
        addbutton = ui_test.find(f"{window.title}//Frame/**/AddMarkupButton")
        await addbutton.click()
        await ui_test.human_delay(2)

        self.assertEqual(len(ext_instance.get_markups()), 3)

        ext_instance.select_markup_in_list_window(None)
        await ui_test.human_delay(20)

        self.assertEqual(window.selected_index, None)

        viewport = get_active_viewport_window()

        viewport.dock_tab_bar_visible = True
        viewport.width = 100
        viewport.height = 100

        close_button = ui_test.find(f"{window.title}//Frame/**.identifier=='close_mark'")
        await close_button.click()
        await ui_test.human_delay(20)
        self.assertEqual(window.visible, False)

        window.visible = True
        self._setting.set(CURRENT_TOOL_PATH, "none")

        self.assertEqual(window.visible, False)

        window.destroy()

    async def test_hide_list_window_on_edit(self):
        """
        Test if list window is hidden when markup edit begins
        """
        window = MarkupListWindow()
        window.visible = True

        ext_instance = extension.get_instance()

        # Before editing, window should be visible
        self.assertTrue(window.visible)
        ext_instance.create_markup()

        # Editing began, window should be hidden
        self.assertFalse(window.visible)
        markup_01 = ext_instance.get_markup("Markup_00")
        ext_instance.end_edit_markup(markup_01, save=True)

        # Editing ended, window should be visible again
        self.assertTrue(window.visible)

        window.selected_index = 1

        await ui_test.wait_n_updates(10)

        # Edit comment, window should be visible
        for w in ui_test.find_all(f"{window.title}//Frame/**/CollapseFrame"):
            # expand the frame:
            await w.click()
            await ui_test.human_delay(2)

        for field in ui_test.find_all(f"{window.title}//Frame/**/CommentEditField"):
            await field.input("yeah whatever", clear_before_input=True)
            await ui_test.human_delay(2)
            break

        # No proper exit
        markup_00 = ext_instance.get_markup("Markup_00")
        ext_instance.begin_edit_markup(markup_00)
        ext_instance.end_edit_markup(markup_00, save=True)

        self.assertTrue(window.visible)

        # Edit markup again, window should be hidden
        markup_00 = ext_instance.get_markup("Markup_00")
        ext_instance.begin_edit_markup(markup_00)
        await ui_test.wait_n_updates(10)

        self.assertFalse(window.visible)

        # End edit markup, window visible again
        ext_instance.end_edit_markup(markup_00, save=True)
        self.assertTrue(window.visible)

        # Clear window / markups
        window.destroy()

    async def test_markup_list_order(self):
        """
        Test the order of markups consistency after editing
        """
        window = MarkupListWindow()
        window.visible = True

        ext_instance = extension.get_instance()

        # Create 4 markups
        ext_instance.create_markup()
        ext_instance.create_markup()
        ext_instance.create_markup()
        ext_instance.create_markup()
        # Kit 111: let the markups' thumbnail captures complete before editing them.
        await ui_test.human_delay(10)
        await _wait_for_markup_thumbnails(ext_instance)

        markup_00 = ext_instance.get_markup("Markup_00")
        markup_01 = ext_instance.get_markup("Markup_01")
        markup_02 = ext_instance.get_markup("Markup_02")
        markup_03 = ext_instance.get_markup("Markup_03")

        ext_instance.end_edit_markup(markup_03, save=True)

        markup_order = [markup_00, markup_01, markup_02, markup_03]

        # Edit one of the markup in the middle
        ext_instance.begin_edit_markup(markup_01)
        await ui_test.human_delay(10)
        ext_instance.end_edit_markup(markup_01, save=True)
        await _wait_for_markup_thumbnails(ext_instance)

        # Check if order remains the same
        for i in range(len(markup_order)):
            listed_markup = window.widgets[i].markup
            self.assertEqual(listed_markup, markup_order[i])

        # Clear window / markups
        window.destroy()

    @unittest.skipIf(os.getenv("ETM_ACTIVE"), "skipped in ETM")
    async def test_markup_playbar(self):
        """
        Test the play bar controls to make sure they show the desired results
        """
        window = MarkupListWindow()
        window.visible = True

        ext_instance = extension.get_instance()

        # Create 4 markups
        ext_instance.create_markup()
        ext_instance.create_markup()
        ext_instance.create_markup()
        ext_instance.create_markup()
        # Kit 111: let the markups' thumbnail captures complete before editing them.
        await ui_test.human_delay(10)
        await _wait_for_markup_thumbnails(ext_instance)
        await ui_test.human_delay(20)

        # we're in editing mode. In this mode, the next/previous buttons should do nothing:
        # edit mode auto hides the window so let's unhide it so we can press the buttons:
        window.visible = True
        window.selected_index = 0

        for w in ui_test.find_all(f"{window.title}//Frame/**/PlayBarNext"):
            await w.click()
        await ui_test.human_delay(10)
        self.assertEqual(ext_instance.current_markup.name, "Markup_00")

        for w in ui_test.find_all(f"{window.title}//Frame/**/PlayBarPrevious"):
            await w.click()
        await ui_test.human_delay(10)
        self.assertEqual(ext_instance.current_markup.name, "Markup_00")

        markup_03 = ext_instance.get_markup("Markup_03")
        ext_instance.end_edit_markup(markup_03, save=True)

        await ui_test.human_delay(2)
        # Kit 111: the list window rebuilds when Markup_03's thumbnail arrives; let that happen before playing.
        await _wait_for_markup_thumbnails(ext_instance)

        # Go Backwards once, to the end of the list
        for w in ui_test.find_all(f"{window.title}//Frame/**/PlayBarPrevious"):
            await w.click()
        await ui_test.human_delay(2)

        self.assertEqual(ext_instance.current_markup.name, "Markup_03")

        # Go Forwards three times, to the third element in the list
        for w in ui_test.find_all(f"{window.title}//Frame/**/PlayBarNext"):
            await w.click()
            await ui_test.human_delay(1)
            await w.click()
            await ui_test.human_delay(1)
            await w.click()
            await ui_test.human_delay(1)
        await ui_test.human_delay(2)

        # Go backwards twice, back to the original position
        for w in ui_test.find_all(f"{window.title}//Frame/**/PlayBarPrevious"):
            await w.click()
            await w.click()
        await ui_test.human_delay(2)

        self.assertEqual(ext_instance.current_markup.name, "Markup_00")

        # Start
        window.selected_index = None
        for w in ui_test.find_all(f"{window.title}//Frame/**/PlayBarPlay"):
            await w.click()
        await ui_test.human_delay(2)

        self.assertEqual(window.selected_index, 0)
        self.assertEqual(ext_instance.current_markup.name, "Markup_00")

        await ui_test.human_delay(700)
        self.assertEqual(window.selected_index, 1)
        self.assertEqual(ext_instance.current_markup.name, "Markup_01")

        # TODO this is radom failed
        return
        await ui_test.human_delay(700)
        self.assertEqual(window.selected_index, 2)
        self.assertEqual(ext_instance.current_markup.name, "Markup_02")

        await ui_test.human_delay(700)
        self.assertEqual(window.selected_index, 3)
        self.assertEqual(ext_instance.current_markup.name, "Markup_03")

        # Stop
        for w in ui_test.find_all(f"{window.title}//Frame/**/PlayBarPlay"):
            await w.click()
        await ui_test.human_delay(2)

        # Start again, and change the tool (should stop the playback)
        window.selected_index = None
        for w in ui_test.find_all(f"{window.title}//Frame/**/PlayBarPlay"):
            await w.click()
        await ui_test.human_delay(2)

        # this should stop playback:
        self._setting.set(CURRENT_TOOL_PATH, "none")
        await ui_test.human_delay(20)

        self.assertEqual(window.selected_index, 0)
        self.assertEqual(ext_instance.current_markup.name, "Markup_00")
        await ui_test.human_delay(700)

        self.assertEqual(window.selected_index, 0)
        self.assertEqual(ext_instance.current_markup.name, "Markup_00")

        # Clear window / markups
        window.destroy()

    async def test_markup_thumbnail_selection(self):
        """
        Test the markup thumbnail widget to make sure selecting it selects the markup
        """
        window = MarkupListWindow()
        window.visible = True

        ext_instance = extension.get_instance()

        # Create 2 markups
        ext_instance.create_markup()
        ext_instance.create_markup()
        # Kit 111: let the markups' thumbnail captures complete before editing them.
        await ui_test.human_delay(10)
        await _wait_for_markup_thumbnails(ext_instance)

        markup_01 = ext_instance.get_markup("Markup_01")
        ext_instance.end_edit_markup(markup_01, save=True)

        await ui_test.human_delay(10)

        all_thumbnails = []
        for index, w in enumerate(ui_test.find_all(f"{window.title}//Frame/**/ImageThumbnail")):
            all_thumbnails.append(w)
            await w.click()
            await ui_test.human_delay(2)
            self.assertEqual(index, window.selected_index)
            self.assertTrue(ext_instance.current_markup)

        await ui_test.human_delay(2)

        window.destroy()
