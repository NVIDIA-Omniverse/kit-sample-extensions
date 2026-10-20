# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
r"""
Directory loops.

Windows ships junctions that point at their own parent - ``AppData\Local\Application Data`` is
``AppData\Local`` - and a traverse that trusts the listing follows them until the paths grow too
long to open. Scanning C: cannot finish without this.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import carb.settings
import omni.kit.test

from ..models import TreeFolderBrowserModel
from ..models.folder_identity import derive_folder_key, find_links_async, resolve_folder_key

SETTING_ROOT = "/exts/omni.kit.browser.folder.core/test/cycle_root"


def make_junction(link: Path, target: Path) -> bool:
    """A junction needs no privileges, unlike a symlink. False if the platform will not make one."""
    if sys.platform != "win32":
        return False
    done = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    return done.returncode == 0


class TestTraverseCycles(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._root = Path(self._tmp.name)
        (self._root / "a.usd").write_text("x", encoding="utf-8")
        sub = self._root / "sub"
        sub.mkdir()
        (sub / "b.usd").write_text("x", encoding="utf-8")
        # sub/loop points back at the root, so following it re-finds a.usd, sub, and loop again.
        self._made = make_junction(sub / "loop", self._root)

    async def tearDown(self):
        self._tmp.cleanup()

    async def _traverse(self):
        carb.settings.get_settings().set(SETTING_ROOT, [self._root.as_posix()])
        model = TreeFolderBrowserModel(setting_folders=SETTING_ROOT, filter_file_suffixes=[".usd"])
        for _ in range(10):
            await omni.kit.app.get_app().next_update_async()
        folder = model.get_root_folder(self._root.as_posix())
        model._register_active_folder(folder)
        await folder.start_traverse()
        return model, folder

    async def test_junction_loop_terminates(self):
        if not self._made:
            raise unittest.SkipTest("junctions are a Windows thing")
        model, folder = await self._traverse()

        # Two files exist. Following the loop even once would find a.usd again.
        self.assertEqual(folder.traverse_ctx.files_found, 2)
        self.assertEqual(folder.traverse_ctx.files_resolved, 2)

        # The loop folder is walked, recognised, and pruned for having nothing in it.
        names = [f.name for f in folder.sub_folders]
        self.assertNotIn("loop", names)

        model.destroy()

    async def test_key_collapses_a_junction(self):
        if not self._made:
            raise unittest.SkipTest("junctions are a Windows thing")
        loop = self._root / "sub" / "loop"
        self.assertEqual(resolve_folder_key(loop.as_posix()), resolve_folder_key(self._root.as_posix()))
        # A real sub directory keeps its own identity.
        self.assertNotEqual(
            resolve_folder_key((self._root / "sub").as_posix()), resolve_folder_key(self._root.as_posix())
        )

    async def test_a_plain_child_is_keyed_from_its_parent(self):
        """
        The cheap path, and the reason a scan can afford this at all.

        Resolving every directory cost 0.155 ms of blocked event loop each, hundreds of thousands
        of times over a drive - it became the freeze it was meant to prevent. A child that is not
        itself a link takes its parent's key plus its name, with no filesystem call.
        """
        parent = resolve_folder_key(self._root.as_posix())
        derived = derive_folder_key(parent, "sub")
        resolved = resolve_folder_key((Path(self._tmp.name) / "sub").as_posix())
        self.assertEqual(derived, resolved, "the derived key must match what resolving would give")

    async def test_only_links_are_resolved(self):
        """find_links_async reports the junction and stays silent about the ordinary folder."""
        if not self._made:
            raise unittest.SkipTest("junctions are a Windows thing")
        root = Path(self._tmp.name)
        plain = (root / "sub").as_posix()
        loop = (root / "sub" / "loop").as_posix()

        links = await find_links_async([plain, loop])

        self.assertIn(loop, links, "the junction was not reported as a link")
        self.assertNotIn(plain, links, "an ordinary folder must not be resolved")
        self.assertEqual(links[loop], resolve_folder_key(self._root.as_posix()), "the junction resolves to the root")

    async def test_remote_urls_key_on_the_url(self):
        """No link information exists for a server, so the url is the identity."""
        self.assertEqual(
            resolve_folder_key("omniverse://content/Materials/"),
            resolve_folder_key("omniverse://content/Materials"),
        )
        self.assertNotEqual(
            resolve_folder_key("omniverse://content/Materials"),
            resolve_folder_key("omniverse://content/Props"),
        )
