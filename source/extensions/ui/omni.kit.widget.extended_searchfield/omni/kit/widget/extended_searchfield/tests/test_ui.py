# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
from contextlib import contextmanager
from pathlib import Path
from typing import List

import omni.kit.app
import omni.ui as ui
from carb.input import KeyboardInput
from omni.kit.ui_test import (
    emulate_char_press,
    emulate_keyboard_press,
    emulate_mouse_move,
    emulate_mouse_move_and_click,
)
from omni.kit.ui_test.vec2 import Vec2
from omni.kit.widget.extended_searchfield.extended_search_field import ExtendedSearchField
from omni.kit.widget.extended_searchfield.image_menu import ImageMenu
from omni.kit.widget.extended_searchfield.search_menu import SearchMenu
from omni.ui.tests.test_base import OmniUiTest

from ..engine_selection import PersistentEngineSelection
from .fake_server import FakeDeepSearchService, fake_server

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data", "tests")


@contextmanager
def searchfield(search_fn, **kwargs):
    window_flags = ui.WINDOW_FLAGS_NO_SCROLLBAR | ui.WINDOW_FLAGS_NO_TITLE_BAR | ui.WINDOW_FLAGS_NO_RESIZE
    window = ui.Window(
        "Test",
        dockPreference=ui.DockPreference.DISABLED,
        flags=window_flags,
        width=600,
        height=200,
        position_x=0,
        position_y=0,
    )
    field = ExtendedSearchField(
        on_search_fn=search_fn,
        engine_delegate=PersistentEngineSelection(),
        parent_window=window,
        max_tokens=3,
        **kwargs,
    )
    with window.frame:
        with ui.VStack(height=20):
            with ui.HStack(width=500):
                field.build_ui()

    yield field


class TestUI(OmniUiTest):
    # Before running each test
    async def setUp(self):
        self._engine_selection = PersistentEngineSelection()
        await super().setUp()
        self._golden_img_dir = TEST_DATA_PATH

    # After running each test
    async def tearDown(self):
        await super().tearDown()

    async def _click_on_widget(self, widget, clicks: int = 1):
        if clicks == 0:
            return await emulate_mouse_move(
                Vec2(
                    widget.screen_position_x + widget.computed_content_width / 2,
                    widget.screen_position_y + widget.computed_content_height / 2,
                ),
            )
        double = True if (clicks == 2) else False
        await emulate_mouse_move_and_click(
            Vec2(
                widget.screen_position_x + widget.computed_content_width / 2,
                widget.screen_position_y + widget.computed_content_height / 2,
            ),
            double=double,
        )

    def search_fn(self, query: List[str], search_dir: str, callback: callable = None):
        if query is not None:
            self._search_queries += query
        if callback:
            callback()

    async def test_extended_searchfield(self):
        self._search_queries = []
        with fake_server("FakeSearchService"):
            with searchfield(self.search_fn) as field:
                field.search_dir = "omniverse://test.ov.nvidia.com"
                # Wait one frame
                await omni.kit.app.get_app().next_update_async()
                container = field._container
                # single click on search field
                await self._click_on_widget(field._search_field)

                for _ in range(5):
                    await omni.kit.app.get_app().next_update_async()

                await self.finalize_test(
                    golden_img_dir=self._golden_img_dir,
                    golden_img_name="test_clicked_widget.png",
                )

                # type a word
                await emulate_char_press("red rusty barrel")
                await emulate_keyboard_press(KeyboardInput.ENTER)
                # press enter to create word tokens

                await omni.kit.app.get_app().next_update_async()
                assert len(field._search_words) == 3
                assert "red" in field._search_words
                assert "rusty" in field._search_words
                assert "barrel" in field._search_words
                for _ in range(5):
                    await omni.kit.app.get_app().next_update_async()
                assert self._search_queries == ["red", "rusty", "barrel"]

                for _ in range(10):
                    await omni.kit.app.get_app().next_update_async()

                await self.finalize_test(
                    golden_img_dir=self._golden_img_dir,
                    golden_img_name="test_red_rusty_barrel.png",
                )

                # single click on right side of field to convert tokens to string
                await emulate_mouse_move_and_click(
                    Vec2(
                        field._search_field.screen_position_x + field._search_field.computed_content_width - 10,
                        field._search_field.screen_position_y + field._search_field.computed_content_height / 2,
                    )
                )

                await omni.kit.app.get_app().next_update_async()
                assert len(field._search_words) == 0
                assert field._search_model.get_value_as_string().strip() == "red rusty barrel"

                # erase the word "barrel" plus the space after it
                for _ in range(7):
                    await emulate_keyboard_press(KeyboardInput.BACKSPACE)

                # click outside to create word tokens
                await emulate_mouse_move_and_click(
                    Vec2(
                        container.screen_position_x + container.computed_width / 2,
                        container.screen_position_y + container.computed_height * 1.5,
                    )
                )

                await omni.kit.app.get_app().next_update_async()
                assert len(field._search_words) == 2
                assert "red" in field._search_words
                assert "rusty" in field._search_words
                assert "barrel" not in field._search_words
                for _ in range(5):
                    await omni.kit.app.get_app().next_update_async()

                # Confirm that we did NOT search yet (no ENTER was pressed)
                assert self._search_queries == ["red", "rusty", "barrel"]

                # single click on right side of field to convert tokens to string
                await emulate_mouse_move_and_click(
                    Vec2(
                        field._search_field.screen_position_x + field._search_field.computed_content_width - 10,
                        field._search_field.screen_position_y + field._search_field.computed_content_height / 2,
                    )
                )

                await emulate_keyboard_press(KeyboardInput.ENTER)
                for _ in range(5):
                    await omni.kit.app.get_app().next_update_async()

                assert self._search_queries[-2:] == ["red", "rusty"]
                assert len(self._search_queries) == 5

    async def test_date_field_no_error(self):
        self._search_queries = []
        with fake_server("FakeDeepSearchService"):
            with searchfield(self.search_fn) as field:
                await omni.kit.app.get_app().next_update_async()
                field.search_dir = "omniverse://test.ov.nvidia.com"
                # Wait one frame
                await omni.kit.app.get_app().next_update_async()
                search_menu: SearchMenu = field._popup_menus[1]
                clear_button: ui.Button = field._clear_button

                await self._click_on_widget(field._search_field)
                await emulate_char_press("modified_after:2022-11-02 modified_before:2022-11-05")
                await emulate_keyboard_press(KeyboardInput.ENTER)
                await self._click_on_widget(search_menu._button)
                for _ in range(10):
                    await omni.kit.app.get_app().next_update_async()
                # breakpoint()
                assert search_menu._fields["modified_before"].model.get_value_as_string() == "2022-11-05"
                assert search_menu._fields["modified_after"].model.get_value_as_string() == "2022-11-02"
                await self.finalize_test(
                    golden_img_dir=self._golden_img_dir,
                    golden_img_name="test_date_no_error.png",
                )

                # close menu and clear field for the next test
                await self._click_on_widget(search_menu._button)
                await self._click_on_widget(clear_button)

                await self._click_on_widget(field._search_field)
                await emulate_char_press("modified_before:2022-11-02 modified_after:2022-11-05")
                await emulate_keyboard_press(KeyboardInput.ENTER)
                await self._click_on_widget(search_menu._button)
                for _ in range(10):
                    await omni.kit.app.get_app().next_update_async()
                assert search_menu._fields["modified_before"].model.get_value_as_string() == "2022-11-02"
                assert search_menu._fields["modified_after"].model.get_value_as_string() == "2022-11-05"
                await self.finalize_test(
                    golden_img_dir=self._golden_img_dir,
                    golden_img_name="test_date_error.png",
                )

                await self._click_on_widget(search_menu._button)

    async def test_incorrect_queries(self):
        self._search_queries = []
        with fake_server("FakeDeepSearchService"):
            with searchfield(self.search_fn) as field:
                await omni.kit.app.get_app().next_update_async()
                field.search_dir = "omniverse://test.ov.nvidia.com"
                # Wait one frame
                await omni.kit.app.get_app().next_update_async()
                clear_button: ui.Button = field._clear_button

                for query in [
                    "larger_than:1.2.3",
                    "larger_than:small",
                    "max:small",
                    'smaller_than:"1 unit of some size"',
                ]:
                    await self._click_on_widget(field._search_field)
                    await emulate_char_press(query)
                    await emulate_keyboard_press(KeyboardInput.ENTER)
                    self.assertIsNotNone(field.parsing_succeeded())
                    self.assertFalse(field.parsing_succeeded())
                    self.assertIsNotNone(field._search_tokens)
                    self.assertFalse(field._search_tokens[0].is_supported())
                    await self._click_on_widget(clear_button)

    async def test_deepsearch_get_prefixes_s3(self):
        self._search_queries = []
        with fake_server("FakeDeepSearchService"):
            with searchfield(self.search_fn) as field:
                field.search_dir = "https://test-bucket.s3.fake-region.amazonaws.com"
                field._engine_delegate.current_engine = "FakeDeepSearchService"
                _ = field._get_search_prefixes()
                for _ in range(10):
                    await omni.kit.app.get_app().next_update_async()
                prefixes = field._get_search_prefixes()
                assert prefixes == await FakeDeepSearchService.get_prefixes(field.search_dir)

    async def test_deepsearch_prefix_menu_case_omniverse(self):

        self._search_queries = []
        with fake_server("FakeDeepSearchService") as server:
            with searchfield(self.search_fn) as field:
                # Wait one frame
                await omni.kit.app.get_app().next_update_async()

                assert len(field._popup_menus) == 2
                assert isinstance(field._popup_menus[0], ImageMenu)
                assert isinstance(field._popup_menus[1], SearchMenu)
                image_menu: ImageMenu = field._popup_menus[0]
                search_menu: SearchMenu = field._popup_menus[1]

                # nothing visible - no server selected
                assert not image_menu.visible
                assert not search_menu.visible
                assert not image_menu._button
                assert not search_menu._button

                field.search_dir = "omniverse://test.ov.nvidia.com"
                await omni.kit.app.get_app().next_update_async()
                await omni.kit.app.get_app().next_update_async()

                # mouse over search field
                await self._click_on_widget(field._search_field, clicks=0)
                for _ in range(20):
                    await omni.kit.app.get_app().next_update_async()

                assert not image_menu.visible
                assert not search_menu.visible
                assert image_menu._button_container.visible
                assert search_menu._button_container.visible

                # open search menu
                for _ in range(5):
                    await omni.kit.app.get_app().next_update_async()
                await self._click_on_widget(search_menu._button, clicks=1)

                # # Wait two frames
                for _ in range(5):
                    await omni.kit.app.get_app().next_update_async()

                assert search_menu.visible
                assert "description" in search_menu._fields
                assert search_menu._fields["description"]._string_field.visible
                await self._click_on_widget(search_menu._fields["description"]._string_field)
                await emulate_char_press("blue car")
                await omni.kit.app.get_app().next_update_async()
                await emulate_keyboard_press(KeyboardInput.ENTER)
                await omni.kit.app.get_app().next_update_async()
                assert not search_menu.visible
                assert self._search_queries[-1].lower().find('description:"blue car"') != -1
                assert len(self._search_queries) == 1
                clear_button: ui.Button = field._clear_button
                await self._click_on_widget(clear_button)

    async def test_auto_search_delay(self):

        self._search_queries = []
        delay = 0.2

        with fake_server("FakeSearchService") as server:
            with searchfield(self.search_fn, auto_search_delay=delay) as field:
                field.search_dir = "omniverse://test.ov.nvidia.com"
                # Wait one frame
                await omni.kit.app.get_app().next_update_async()
                # single click on search field
                await self._click_on_widget(field._search_field)

                # type a word.
                await emulate_char_press("red rusty barrel")
                # force a keyboard press to cause event.
                await emulate_keyboard_press(KeyboardInput.SPACE)

                await omni.kit.app.get_app().next_update_async()

                # give some extra time
                await asyncio.sleep(delay * 2)

                # no search bubbles because we are still typing
                assert len(field._search_words) == 0
                assert field._search_field.model.get_value_as_string().strip() == "red rusty barrel"
                for _ in range(5):
                    await omni.kit.app.get_app().next_update_async()

                assert self._search_queries == ["red", "rusty", "barrel"]
                assert len(self._search_queries) == 3

    async def test_no_auto_search_delay(self):

        self._search_queries = []
        delay = None

        with fake_server("FakeSearchService"):
            with searchfield(self.search_fn, auto_search_delay=delay) as field:
                field.search_dir = "omniverse://test.ov.nvidia.com"
                # Wait one frame
                await omni.kit.app.get_app().next_update_async()
                # single click on search field
                await self._click_on_widget(field._search_field)

                # type a word.
                await emulate_char_press("red rusty barrel")
                # force a keyboard press to cause event. For some reason this doesn't add a space to the model.
                await emulate_keyboard_press(KeyboardInput.SPACE)

                await omni.kit.app.get_app().next_update_async()

                # give some extra time
                await asyncio.sleep(0.1)

                assert len(field._search_words) == 0
                assert field._search_field.model.get_value_as_string().strip() == "red rusty barrel"
                for _ in range(5):
                    await omni.kit.app.get_app().next_update_async()
                assert len(self._search_queries) == 0

    async def test_search_parsing(self):
        self._search_queries = []
        delay = None

        # Run a series of tests. The KEY is the string field value, the VALUE is the expected result in the model(s).
        tests = {
            "name:a": {"name": "a"},
            "name:a name:b": {"name": "a b"},
            'name:"a b"': {"name": '"a b"'},
            "ext:usd": {"ext": "usd"},
            "ext:usd ext:png": {"ext": "usd png"},
            'ext:"usd png"': {"ext": '"usd png"'},
            "tag:car": {"tag": "car"},
            "tag:blue tag:car": {"tag": "blue car"},
            'tag:"blue car"': {"tag": '"blue car"'},
            "description:abc": {"description": "abc"},
            'description:"a b"': {"description": "a b"},
            "description:a description:b": {"description": "a b"},
            "created_by:user@example.com": {"created_by": "user@example.com"},
            "modified_by:user@example.com": {"modified_by": "user@example.com"},
            "larger_than:5": {"larger_than": "5"},
            'larger_than:"5 MB"': {"larger_than": "5 MB"},
            "smaller_than:5": {"smaller_than": "5"},
            'smaller_than:"5 MB"': {"smaller_than": "5 MB"},
            "modified_after:2020-2-2": {"modified_after": "2020-2-2"},
            "modified_before:2022-1-1": {"modified_before": "2022-1-1"},
            "name:a description:b ext:usd tag:car created_by:me modified_by:you larger_than:3MB modified_before:2022 modified_after:2020": {
                "name": "a",
                "description": "b",
                "ext": "usd",
                "tag": "car",
                "created_by": "me",
                "modified_by": "you",
                "modified_before": "2022",
                "modified_after": "2020",
            },
        }

        with fake_server("FakeDeepSearchService"):
            with searchfield(self.search_fn, auto_search_delay=delay) as field:
                # Wait one frame
                await omni.kit.app.get_app().next_update_async()

                field.search_dir = "omniverse://test.ov.nvidia.com"
                await omni.kit.app.get_app().next_update_async()

                search_menu: SearchMenu = field._popup_menus[1]
                clear_button: ui.Button = field._clear_button

                for test_string, result in tests.items():
                    await self._click_on_widget(field._search_field)
                    await emulate_char_press(test_string)
                    await emulate_keyboard_press(KeyboardInput.ENTER)
                    await self._click_on_widget(search_menu._button)

                    import carb

                    for f, value in result.items():
                        carb.log_warn(f"{search_menu._fields[f].model.get_value_as_string()} == {value}")
                        # assert(search_menu._fields[f].model.get_value_as_string() == value)

                    # close menu and clear field for another round
                    await self._click_on_widget(search_menu._button)
                    await self._click_on_widget(clear_button)

    async def test_extended_max_search_word_length(self):
        self._search_queries = []
        with fake_server("FakeSearchService"):
            with searchfield(self.search_fn) as field:
                field.search_dir = "omniverse://test.ov.nvidia.com"
                # Wait one frame
                await omni.kit.app.get_app().next_update_async()
                # single click on search field
                await self._click_on_widget(field._search_field)

                for _ in range(5):
                    await omni.kit.app.get_app().next_update_async()

                # type a word
                very_long_input = "description:" + "".join(["very_long_input"] * 100)
                await emulate_char_press(very_long_input)
                await emulate_keyboard_press(KeyboardInput.ENTER)
                # press enter to create word tokens

                await omni.kit.app.get_app().next_update_async()
                assert len(field._search_words) == 1
                assert very_long_input in field._search_words

                for _ in range(10):
                    await omni.kit.app.get_app().next_update_async()

                await self.finalize_test(
                    golden_img_dir=self._golden_img_dir,
                    golden_img_name="test_very_long_input.png",
                )
