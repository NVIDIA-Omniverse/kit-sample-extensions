# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import omni.kit.test

from ..ui.string_list_field_utils import parse_string_list_ui_text


class TestStringListFieldUtils(omni.kit.test.AsyncTestCase):
    async def test_empty_and_whitespace(self):
        self.assertEqual(parse_string_list_ui_text(""), [])
        self.assertEqual(parse_string_list_ui_text("   "), [])
        self.assertEqual(parse_string_list_ui_text(None), [])

    async def test_comma_separated(self):
        self.assertEqual(parse_string_list_ui_text("a, b, c"), ["a", "b", "c"])
        self.assertEqual(parse_string_list_ui_text("  , delta ,  , epsilon  "), ["delta", "epsilon"])

    async def test_json_string_array(self):
        self.assertEqual(parse_string_list_ui_text('["a", "b", "c"]'), ["a", "b", "c"])
        self.assertEqual(parse_string_list_ui_text('  ["x", "y"]  '), ["x", "y"])

    async def test_json_numbers_or_booleans_not_string_list_preserve_whole_paste(self):
        """Config STRING_LIST fields are ``List[str]``; non-strings keep one token (full JSON)."""
        raw_nums = "[1, 2, 3]"
        self.assertEqual(parse_string_list_ui_text(raw_nums), [raw_nums])
        raw_bool = "[true, false]"
        self.assertEqual(parse_string_list_ui_text(raw_bool), [raw_bool])
        raw_mixed = '["a", 1]'
        self.assertEqual(parse_string_list_ui_text(raw_mixed), [raw_mixed])

    async def test_json_invalid_syntax_falls_back_to_comma(self):
        self.assertEqual(parse_string_list_ui_text('["a", "b"'), ['["a"', '"b"'])

    async def test_json_nested_structure_preserved_as_single_token(self):
        raw = '["ok", {"nested": 1}]'
        self.assertEqual(parse_string_list_ui_text(raw), [raw])

    async def test_bracket_looking_comma_field_not_json(self):
        self.assertEqual(parse_string_list_ui_text("[section, foo"), ["[section", "foo"])
