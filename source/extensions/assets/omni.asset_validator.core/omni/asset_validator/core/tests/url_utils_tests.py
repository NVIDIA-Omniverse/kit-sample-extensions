# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import os
import tempfile

import omni.kit.test
from omni.asset_validator import UriResolver

from .._url_utils import OmniUriResolver


class OmniUriResolverTests(omni.kit.test.AsyncTestCase):

    async def test_satisfies_protocol(self):
        self.assertIsInstance(OmniUriResolver(), UriResolver)

    async def test_list_uris(self):
        resolver = OmniUriResolver()
        with tempfile.TemporaryDirectory() as d:
            names = ["a.usd", "b.usd"]
            for name in names:
                with open(os.path.join(d, name), "w"):
                    pass
            result = resolver.list_uris(d)
            self.assertEqual(sorted(os.path.basename(p) for p in result), sorted(names))

    async def test_parent_uri(self):
        resolver = OmniUriResolver()
        parent = resolver.parent_uri("omniverse://localhost/path/to/file.usd")
        self.assertEqual(parent, "omniverse://localhost/path/to")

    async def test_parent_uri_at_root(self):
        resolver = OmniUriResolver()
        parent = resolver.parent_uri("omniverse://localhost/")
        self.assertEqual(parent, "omniverse://localhost/")

    async def test_join_uri(self):
        resolver = OmniUriResolver()
        joined = resolver.join_uri("omniverse://localhost/path/to", "file.usd")
        self.assertEqual(joined, "omniverse://localhost/path/to/file.usd")

    async def test_basename_file(self):
        resolver = OmniUriResolver()
        self.assertEqual(resolver.basename("omniverse://localhost/path/to/file.usd"), "file.usd")

    async def test_basename_directory(self):
        resolver = OmniUriResolver()
        self.assertEqual(resolver.basename("omniverse://localhost/path/to/subdir"), "subdir")

    async def test_basename_trailing_slash(self):
        resolver = OmniUriResolver()
        self.assertEqual(resolver.basename("omniverse://localhost/path/to/subdir/"), "subdir")

    async def test_relative_uri_child(self):
        resolver = OmniUriResolver()
        rel = resolver.relative_uri("omniverse://localhost/path/base", "omniverse://localhost/path/base/child/file.usd")
        self.assertEqual(rel, "./child/file.usd")

    async def test_relative_uri_sibling(self):
        resolver = OmniUriResolver()
        rel = resolver.relative_uri("omniverse://localhost/path/base", "omniverse://localhost/path/other/file.usd")
        self.assertEqual(rel, "../other/file.usd")

    async def test_relative_uri_parent(self):
        resolver = OmniUriResolver()
        rel = resolver.relative_uri("omniverse://localhost/path/base/sub", "omniverse://localhost/path/file.usd")
        self.assertEqual(rel, "../../file.usd")
