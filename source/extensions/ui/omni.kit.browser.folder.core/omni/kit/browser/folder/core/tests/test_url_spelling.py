# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
"""
One spelling per local path.

Windows reaches a file under either case of its drive letter, and the browser compares urls as
strings. A collection added as ``c:/x`` - which is what an extension token resolves to - lists its
files as ``C:/x``, because that is what omni.client reports, so no listed file matches its own
cached copy and every one of them is shown twice.

That surfaced as a browser test picking the wrong item out of a collection it believed held two
different materials, and it sticks: once a cache is written under one spelling, every later run
duplicates until the cache is deleted.
"""

import os
import tempfile
from pathlib import Path

import carb.settings
import omni.kit.app
import omni.kit.test

from ..models import TreeFolderBrowserModel
from ..models.folder_identity import local_url_key, normalize_url

SETTING_ROOT = "/exts/omni.kit.browser.folder.core/test/url_spelling"


class TestUrlSpelling(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        (root / "a.usd").write_text("x", encoding="utf-8")
        self._root = root.as_posix()

        carb.settings.get_settings().set(SETTING_ROOT, [])
        self._model = TreeFolderBrowserModel(setting_folders=SETTING_ROOT, filter_file_suffixes=[".usd"])
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()

    async def tearDown(self):
        self._model.destroy()
        self._tmp.cleanup()

    def _lower_drive(self, url: str) -> str:
        if url[1:2] != ":":
            self.skipTest("drive letters are a Windows thing")
        return url[0].lower() + url[1:]

    async def test_a_local_root_keeps_one_spelling(self):
        """However it is spelled going in, one spelling comes out - the one omni.client reports."""
        folder = self._model.append_root_folder(self._lower_drive(self._root), save=False, sync=False)
        self.assertIsNotNone(folder, "a lower case drive root could not be added")
        self.assertEqual(folder.url, normalize_url(self._root), "the drive letter was left as given")

    async def test_a_root_is_found_by_either_spelling(self):
        """
        Both spellings name one collection, so neither can add a second or fail to remove the first.

        Without this, adding the same folder twice under different cases silently makes two
        collections of it.
        """
        lower = self._lower_drive(self._root)
        folder = self._model.append_root_folder(lower, save=False, sync=False)
        self.assertIsNotNone(folder)

        self.assertIs(self._model.get_root_folder(lower), folder, "not found by the spelling used to add it")
        self.assertIs(self._model.get_root_folder(self._root), folder, "not found by the other spelling")
        self.assertIsNone(
            self._model.append_root_folder(self._root, save=False, sync=False),
            "the same folder was added twice under two spellings",
        )

    async def test_every_component_of_a_local_path_is_one_identity(self):
        """
        Windows is case-insensitive for the whole path, not just the drive.

        A root added as C:/Users/me and a listing reporting C:/users/me are the same directory, so
        keying on the drive letter alone still counted one file as two.
        """
        root = self._root
        if root[1:2] != ":":
            self.skipTest("case folding is the local filesystem's rule, and posix does not fold")

        self.assertEqual(local_url_key(root), local_url_key(root.upper()))
        self.assertEqual(local_url_key(root), local_url_key(root.lower()))
        self.assertEqual(
            local_url_key(root + "/Sub/Dir"), local_url_key(root + "/sub/dir"), "component case split one path in two"
        )

    async def test_a_local_file_url_is_the_same_place_as_the_path(self):
        """``file:///C:/x`` is another spelling of ``C:/x``, and used to be a different one."""
        root = self._root
        if root[1:2] != ":":
            self.skipTest("drive letters are a Windows thing")
        self.assertEqual(local_url_key(f"file:///{root}"), local_url_key(root))
        self.assertEqual(local_url_key(f"file:///{root.lower()}"), local_url_key(root))

    async def test_a_root_is_found_whatever_the_case(self):
        """The lookup has to agree with the key, or the same folder is added twice."""
        root = self._root
        if root[1:2] != ":":
            self.skipTest("drive letters are a Windows thing")
        folder = self._model.append_root_folder(root, save=False, sync=False)
        self.assertIsNotNone(folder)
        self.assertIs(self._model.get_root_folder(root.upper()), folder, "not found by an upper case spelling")
        self.assertIs(self._model.get_root_folder(root.lower()), folder, "not found by a lower case spelling")

    async def test_a_unc_path_folds_like_any_other_windows_path(self):
        """
        A share is reached through the same path stack as a drive, and it is just as forgiving
        about case, so the same identity rule applies to it.
        """
        if self._root[1:2] != ":":
            self.skipTest("UNC paths are a Windows thing")
        self.assertEqual(local_url_key("//server/share/Assets"), local_url_key("//SERVER/Share/assets"))

    async def test_two_file_hosts_are_two_places(self):
        """
        ``file://`` can name a host, and two of them are two shares.

        The key was built from the url's path alone, so file://a/share/x and file://b/share/x came
        out identical - one collection, and one set of cached files, for two different servers.
        """
        a = local_url_key("file://server-a/share/Assets/x.usd")
        b = local_url_key("file://server-b/share/Assets/x.usd")
        self.assertNotEqual(a, b, "two hosts collapsed onto one path")
        self.assertEqual(a, local_url_key("//server-a/share/Assets/x.usd"), "a host is a UNC path")

    async def test_localhost_is_this_machine(self):
        """``file://localhost/C:/x`` names no other host, so it is the local path it looks like."""
        root = self._root
        if root[1:2] != ":":
            self.skipTest("drive letters are a Windows thing")
        self.assertEqual(local_url_key(f"file://localhost/{root}"), local_url_key(root))

    async def test_files_that_are_equal_hash_alike(self):
        """
        Equality moved to the canonical key, and the hash has to move with it.

        BrowserFile is used as a dictionary key - the browser item cache is keyed by one - so a
        file looked up under another of its spellings would miss, and the row it belongs to would
        be rebuilt beside the one already there.
        """
        from ..models import FileSystemFile

        # None of this is about spelling, so none of it skips: equal files must hash alike
        # wherever they are, and no thumbnail must equal an empty one.
        blank = FileSystemFile(f"{self._root}/Assets/B.usd", thumbnail=None)
        empty = FileSystemFile(f"{self._root}/Assets/B.usd", thumbnail="")
        self.assertTrue(blank.equals(empty), "no thumbnail and an empty thumbnail differed")
        self.assertEqual(hash(blank), hash(empty), "equal files hashed differently")
        self.assertEqual(len({blank, empty}), 1, "one file went into a set twice")

        if self._root[1:2] != ":":
            return  # the rest is about two spellings of one path, which posix does not have
        upper = FileSystemFile(f"{self._root}/Assets/A.usd", thumbnail=f"{self._root}/Assets/A.png")
        lower = FileSystemFile(f"{self._root.lower()}/assets/a.usd", thumbnail=f"{self._root.lower()}/assets/a.png")
        self.assertTrue(upper.equals(lower), "two spellings of one file did not compare equal")
        self.assertEqual(hash(upper), hash(lower), "equal files hashed differently")
        self.assertEqual(len({upper, lower}), 1, "one file went into a set twice")

    async def test_a_thumbnail_found_later_updates_the_identity(self):
        """
        Identity is cached, so everything that changes a url has to say so.

        A thumbnail is often discovered after the file it belongs to - the browser lists the files
        and then walks the thumbnail folder - and set_thumbnail assigned the field rather than the
        property, leaving the cached key describing the file as it was. Two files that had just
        become equal would still compare and hash apart, and the cache would keep both.
        """
        from ..models import FileSystemFile

        # No skip: a thumbnail arriving has to update the cached identity on every platform. Only
        # the spelling half of this file is Windows' business.
        found = FileSystemFile(f"{self._root}/Assets/A.usd")
        cached = FileSystemFile(f"{self._root}/Assets/A.usd", thumbnail=f"{self._root}/Assets/.thumbs/A.usd.png")

        # Read first, which is what puts the stale value in place.
        self.assertNotEqual(found._thumbnail_identity(), cached._thumbnail_identity())

        self.assertTrue(found.set_thumbnail(f"{self._root}/Assets/.thumbs/A.usd.png"))

        self.assertEqual(
            found._thumbnail_identity(), cached._thumbnail_identity(), "the cached identity was left behind"
        )
        self.assertTrue(found.equals(cached), "the file did not match its cached copy")
        self.assertEqual(hash(found), hash(cached), "equal files hashed differently")

    async def test_a_one_letter_scheme_is_not_a_drive(self):
        """
        ``c://host/x`` is a url, ``c:/x`` is a drive.

        The classification is done by looking at the string rather than parsing it, because parsing
        every url costs three times as much and this runs per file. A single letter is a legal
        scheme, though, and reading one as a drive folded its case - so two hosts differing only in
        case would have been the same place.
        """
        self.assertEqual(local_url_key("c://Host/Proj/A.usd"), "c://Host/Proj/A.usd", "a scheme was folded")
        self.assertNotEqual(
            local_url_key("c://Host/Proj/A.usd"),
            local_url_key("c://host/proj/a.usd"),
            "two hosts became one place",
        )
        # And the drive it could be confused with is still a drive. Only on Windows: elsewhere
        # "c:/Proj" is an ordinary relative-looking path and its case is its own.
        if os.name == "nt":
            self.assertEqual(local_url_key("c:/Proj/A.usd"), local_url_key("C:/proj/a.usd"))

    async def test_remote_urls_are_left_alone(self):
        """Case can be significant off the local filesystem, and no rule here knows which host cares."""
        for url in (
            "omniverse://server/Projects/x",
            "https://example.com/Materials/2023_1",
        ):
            self.assertEqual(normalize_url(url), url, f"{url} was rewritten")
            self.assertEqual(local_url_key(url), url, f"{url} was folded, and case can matter there")
            self.assertNotEqual(
                local_url_key(url), local_url_key(url.upper()), f"{url} folded case it should have kept"
            )
