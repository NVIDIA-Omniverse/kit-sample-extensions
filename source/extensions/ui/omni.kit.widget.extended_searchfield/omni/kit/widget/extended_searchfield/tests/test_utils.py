# SPDX-FileCopyrightText: Copyright (c) 2021-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import os

import omni.client
from omni.deepsearch.helper.utils import image_from_base64, image_to_base64
from omni.kit.widget.extended_searchfield.utils import combine_queries, is_omniverse_url, quotify, split_with_quotes
from omni.ui.tests.test_base import OmniUiTest
from PIL import Image, ImageChops, JpegImagePlugin, PngImagePlugin

from ..extended_search_field import ExtendedSearchField

ROOT_DIR = f"{os.path.abspath(os.path.dirname(__file__))}/../../../../.."


class TestUtils(OmniUiTest):
    # Before running each test
    async def setUp(self):
        await super().setUp()

    # After running each test
    async def tearDown(self):
        await super().tearDown()

    def test_split(self):
        valid_input_output_pairs = {
            "": [],
            "a": ["a"],
            " a ": ["a"],
            "a:b": ["a:b"],
            "a:'b'": ["a:'b'"],
            "a:'b c d'": ["a:'b", "c", "d'"],
            "a b": ["a", "b"],
            " a b ": ["a", "b"],
            "a   b": ["a", "b"],
            "a:b c:d": ["a:b", "c:d"],
            "a:'b c d' e": ["a:'b", "c", "d'", "e"],
            "f a:'b c d' e": ["f", "a:'b", "c", "d'", "e"],
            'g a:"b c d" e': ["g", 'a:"b c d"', "e"],
            'h a:"b \\"c d" e': ["h", 'a:"b \\"c d"', "e"],
            'i a:"b \\"c \\\\\\" d" e': ["i", 'a:"b \\"c \\\\\\" d"', "e"],
            'j a:"b c \\\\" d e': ["j", 'a:"b c \\\\"', "d", "e"],
            'l a:"b \\"c \\\\" d e': ["l", 'a:"b \\"c \\\\"', "d", "e"],
            '"a"': ['"a"'],
            '" a b "': ['" a b "'],
            '"a:b"': ['"a:b"'],
        }

        for i, o in valid_input_output_pairs.items():
            assert o == split_with_quotes(i)

        # Test bad inputs
        invalid_input_output_pairs = {
            '"': ['"'],
            '"abcd': ['"abcd'],
            'xyz:"abc': ['xyz:"abc'],
            'x:"ab:c': ['x:"ab:c'],
            'x:ab:c"': ['x:ab:c"'],
            '"x:a"b:c"': ['"x:a"b:c"'],
            '"x:a"b:c" mnop': ['"x:a"', 'b:c"', "mnop"],
        }

        for i, o in invalid_input_output_pairs.items():
            assert o == split_with_quotes(i)

    def test_is_omniverse_url(self):
        for valid in [
            "omniverse://ov.rc.nvidia.com",
            "omniverse://ov.rc.nvidia.com/Projects/Something/Random/",
            "omniverse://ov.rc.nvidia.com/Projects/Something/Random/file.usd",
            "omniverse://localhost/Projects/Something/Random",
        ]:
            assert is_omniverse_url(valid)

        for invalid in [
            "C:/Users/name/code",
            "C:/Users/name/code/",
            "C:/Users/name/code/omniverse.usd",
            "/usr/local/folder",
            "/usr/local/folder/",
            "/usr/local/folder/omniverse.usd",
            "www.nvidia.com",
            "localhost://this.is.not.omniverse",
        ]:
            assert not is_omniverse_url(invalid)

    def test_is_supported_url(self):
        for valid in [
            "omniverse://ov.rc.nvidia.com",
            "omniverse://ov.rc.nvidia.com/Projects/Something/Random/",
            "omniverse://ov.rc.nvidia.com/Projects/Something/Random/file.usd",
            "omniverse://localhost/Projects/Something/Random",
            "https://fake-bucket.s3.fake-region.amazonaws.com",
        ]:
            self.assertTrue(ExtendedSearchField.is_supported_url(omni.client.break_url(valid).scheme), valid)

        for invalid in [
            "C:/Users/name/code",
            "C:/Users/name/code/",
            "C:/Users/name/code/omniverse.usd",
            "/usr/local/folder",
            "/usr/local/folder/",
            "/usr/local/folder/omniverse.usd",
            "http://fake-bucket.s3.amazonaws.com",  # insecure protocol
            "www.nvidia.com",
            "localhost://this.is.not.omniverse",
        ]:
            assert not ExtendedSearchField.is_supported_url(omni.client.break_url(invalid).scheme)

    def test_quotify(self):
        valid_input_output_pairs = {
            "": "",
            "abcd:/efghi": "abcd:/efghi",
            "a b": '"a b"',
            "  a b  ": '"  a b  "',
            '"a b"': '"a b"',
            '"a b c d"': '"a b c d"',
            'a "b" c d': '"a b c d"',
            '"': "",
            '"abcd': "abcd",
            'abc"xyz': "abcxyz",
            'some:"thing som"ething els"e': '"some:thing something else"',
        }
        for i, o in valid_input_output_pairs.items():
            assert o == quotify(i)

    def test_combine_queries(self):

        test_matrix = [
            {"old": [], "new": [], "result": []},
            {"old": ["a"], "new": [], "result": ["a"]},
            {"old": [], "new": ["ext:usd"], "result": ["ext:usd"]},
            {"old": ["a"], "new": ["ext:usd"], "result": ["a", "ext:usd"]},
            {"old": ["ext:usd"], "new": ["ext:usd"], "result": ["ext:usd"]},
            {"old": ["ext:usd"], "new": ["ext:png"], "result": ["ext:png"]},
            {"old": ["ext:usd", "a"], "new": ["ext:png"], "result": ["ext:png", "a"]},
            {"old": ["ext:usd", "a"], "new": ["ext:png", "name:car"], "result": ["ext:png", "a", "name:car"]},
            {
                "old": ["ext:usd", "a", "ext:xyz"],
                "new": ["ext:png", "name:car"],
                "result": ["ext:png", "a", "name:car"],
            },
            {"old": ["a", "ext:xyz"], "new": ["ext:png", "name:car"], "result": ["a", "ext:png", "name:car"]},
            {"old": ["a", "ext:xyz"], "new": ["name:car"], "result": ["a", "name:car"]},
            {
                "old": ["name:a", "name:b"],
                "new": ["name:a", "name:b", "size:5"],
                "result": ["name:a", "name:b", "size:5"],
            },
            {
                "old": ["name:a", "name:b"],
                "new": ["name:x", "name:b", "size:3"],
                "result": ["name:x", "name:b", "size:3"],
            },
            {
                "old": ["name:a", "a", "name:b"],
                "new": ["name:x", "name:b", "size:3"],
                "result": ["name:x", "a", "name:b", "size:3"],
            },
        ]

        for test_dict in test_matrix:
            assert combine_queries(test_dict["old"], test_dict["new"]) == test_dict["result"]

    def test_image_coversion(self):
        img = Image.open(f"{ROOT_DIR}/data/preview.png").convert("RGB")
        base64_string = image_to_base64(img, format="PNG")
        self.assertIsInstance(base64_string, str)
        reconstructed_im = image_from_base64(base64_string)
        diff = ImageChops.difference(img, reconstructed_im)
        self.assertIsNone(diff.getbbox())

    def test_covert_image_function(self):
        base64_string = ExtendedSearchField._convert_image(f"{ROOT_DIR}/data/preview.png")
        self.assertIsInstance(base64_string, str)
        reconstructed_im = image_from_base64(base64_string)
        self.assertIsInstance(
            reconstructed_im,
            (
                JpegImagePlugin.JpegImageFile,
                PngImagePlugin.PngImageFile,
            ),
        )
