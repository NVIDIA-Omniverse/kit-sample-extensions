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
Payload gating in the USD reader.

A payload naming somewhere other than the file that references it is what froze the app: composing
it makes USD resolve that location, and an unreachable server costs minutes with the GIL held. A
1 KB fixture whose payload named a dead server measured 141 s against 4 ms with the payload left
alone. Payloads sitting beside their referrer are cheap and still loaded, so their materials are
still found.
"""

import os
import tempfile
from pathlib import Path

import carb.settings
import omni.kit.test
from pxr import Usd

from ..usd_reader import (
    DEFAULT_SKIP_FOREIGN_ARCS,
    SETTING_SKIP_FOREIGN_ARCS,
    _load_local_payloads,
    _location_of,
    _read_usd_materials,
    _skip_foreign_arcs,
)

# defaultPrim matters: a payload with no target prim path composes the target layer's default
# prim, and a layer without one contributes nothing at all.
TARGET_USDA = """#usda 1.0
(
    defaultPrim = "Root"
)

def Xform "Root"
{
    def Material "PayloadMaterial"
    {
    }
}
"""

MAIN_TEMPLATE = """#usda 1.0
(
    defaultPrim = "World"
)

def Xform "World"
{
    def Xform "Holder" (
        prepend payload = @%s@
    )
    {
    }
}
"""


class TestUsdReaderPayloads(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._dir = Path(self._tmp.name)
        (self._dir / "target.usda").write_text(TARGET_USDA, encoding="utf-8")

    async def tearDown(self):
        self._tmp.cleanup()

    def _write(self, name, payload):
        path = self._dir / name
        path.write_text(MAIN_TEMPLATE % payload, encoding="utf-8")
        return path.as_posix()

    async def test_location_classification(self):
        """(target or origin) == origin is the whole decision, so these must be right."""
        same = [
            ("C:/a/b.usd", "C:/a/c.usd"),
            ("C:/a/b.usd", "sub/c.usd"),  # relative: resolves beside its referrer
            ("C:/a/b.usd", ""),  # internal payload
            ("omniverse://srv/a.usd", "omniverse://srv/b.usd"),
            ("//share/a/b.usd", "//share/a/c.usd"),
            ("file:///C:/a/b.usd", "C:/a/c.usd"),
            ("file://localhost/C:/a/b.usd", "C:/a/c.usd"),  # localhost is this machine
            ("file://server/share/a.usd", "//server/share/b.usd"),  # same host, either spelling
        ]
        different = [
            ("C:/a/b.usd", "omniverse://srv/c.usd"),
            ("omniverse://srv/a.usd", "omniverse://other/b.usd"),
            ("omniverse://srv/a.usd", "C:/a/b.usd"),
            ("//share/a/b.usd", "//elsewhere/c.usd"),
            # A host makes it remote whatever the scheme says. Treating this as local is what let
            # a dead server through to Usd.Stage.Open and its retry budget.
            ("C:/a/b.usd", "file://server/share/c.usd"),
            ("file://server/share/a.usd", "file://other/share/b.usd"),
        ]
        for origin, target in same:
            o, t = _location_of(origin), _location_of(target)
            self.assertEqual(t or o, o, f"{target} should count as beside {origin}")
        for origin, target in different:
            o, t = _location_of(origin), _location_of(target)
            self.assertNotEqual(t or o, o, f"{target} should not count as beside {origin}")

    async def test_a_payload_alongside_is_loaded(self):
        """The materials inside a local payload must still be found - this is the cost of LoadNone."""
        url = self._write("main_local.usda", "target.usda")

        stage = Usd.Stage.Open(url, load=Usd.Stage.LoadNone)
        self.assertEqual(_load_local_payloads(stage, url), 1, "the local payload was not loaded")

        found = _read_usd_materials(url, skip_foreign_arcs=True)
        self.assertEqual(len(found or []), 1, "gating lost a material that lives beside the file")

    async def test_a_payload_elsewhere_is_left_alone(self):
        """
        The freeze. Asserted through _load_local_payloads rather than by timing the open: a
        regression here would otherwise make this test hang for minutes on a real connection
        attempt instead of failing.
        """
        url = self._write("main_foreign.usda", "omniverse://fake-server/Assets/edify.usd")

        stage = Usd.Stage.Open(url, load=Usd.Stage.LoadNone)
        self.assertEqual(_load_local_payloads(stage, url), 0, "a foreign payload was loaded")

    async def test_the_gate_can_be_turned_off(self):
        settings = carb.settings.get_settings()
        try:
            self.assertTrue(DEFAULT_SKIP_FOREIGN_ARCS, "the gate ships on")
            settings.set(SETTING_SKIP_FOREIGN_ARCS, False)
            self.assertFalse(_skip_foreign_arcs(), "the setting did not turn the gate off")
            settings.set(SETTING_SKIP_FOREIGN_ARCS, True)
            self.assertTrue(_skip_foreign_arcs())
        finally:
            settings.set(SETTING_SKIP_FOREIGN_ARCS, DEFAULT_SKIP_FOREIGN_ARCS)

    async def test_a_malformed_file_does_not_raise(self):
        """Usd.Stage.Open raises on an unparsable .usda; a scan of a whole drive will meet those."""
        bad = self._dir / "broken.usda"
        bad.write_text("I'm a totally invalid usda file.", encoding="utf-8")
        self.assertIsNone(_read_usd_materials(bad.as_posix(), skip_foreign_arcs=True))
        self.assertIsNone(_read_usd_materials(bad.as_posix(), skip_foreign_arcs=False))


class TestSubMaterialIdentity(omni.kit.test.AsyncTestCase):
    """A prim path is not a file path, and USD does not fold its case."""

    async def test_prim_paths_of_different_case_are_different_materials(self):
        from ..data import UsdSubMaterial

        one = UsdSubMaterial("/World/Looks/Mat")
        other = UsdSubMaterial("/world/Looks/Mat")
        self.assertFalse(one.equals(other), "two prims were treated as one because a path folded")

    async def test_material_names_of_different_case_are_different_materials(self):
        """
        A sub material's url is its identifier, not a path.

        It defaults to the material name, and mdl names are case-sensitive, so putting them through
        the filesystem's case rules merged two materials inside one file.
        """
        from ..data import SubMaterial

        self.assertFalse(SubMaterial("Wood").equals(SubMaterial("wood")), "two materials became one")

    async def test_a_thumbnail_appearing_makes_a_sub_material_different(self):
        """What is left to notice, once the file itself has been matched."""
        from ..data import SubMaterial

        bare = SubMaterial("Wood")
        shown = SubMaterial("Wood", thumbnail="C:/Assets/.thumbs/Wood.png")
        self.assertFalse(bare.equals(shown), "a thumbnail appearing went unnoticed")
        self.assertTrue(
            shown.equals(SubMaterial("Wood", thumbnail="c:/assets/.thumbs/wood.png")),
            "the same thumbnail spelled differently counted as a change",
        )

    async def test_the_same_prim_path_is_the_same_material(self):
        from ..data import UsdSubMaterial

        self.assertTrue(UsdSubMaterial("/World/Looks/Mat").equals(UsdSubMaterial("/World/Looks/Mat")))

    async def test_a_material_file_is_matched_however_it_is_spelled(self):
        """The file url beside them is a file, so it keeps the filesystem's rules."""
        from ..data import MaterialFile

        if os.name != "nt":
            # The rule is the filesystem's, and two spellings really are two files off Windows.
            # Asked of the platform, not of the url: the url here is a literal, so testing it for a
            # drive letter always said Windows and the test failed on the Linux runners.
            self.skipTest("case folding is a Windows rule")
        upper = MaterialFile("C:/Assets/Wood.mdl")
        lower = MaterialFile("c:/assets/wood.mdl")
        self.assertTrue(upper.equals(lower), "two spellings of one mdl did not match")


class TestStartupOpensNothing(omni.kit.test.AsyncTestCase):
    """
    Starting the readers must not touch USD.

    Opening a stage initialises USD, and on the startup path that happens before the extensions
    that register schemas have finished: omni.kit.property.usd then cannot find OmniPlaybackAPI,
    and omni.kit.window.material's startup test fails on the error it logs.

    The pool is built here; a thread only exists once there is a file to read.
    """

    async def test_starting_the_readers_queues_nothing(self):
        from .. import usd_reader

        settings = carb.settings.get_settings()
        was = settings.get(usd_reader.SETTING_THREADED)
        try:
            settings.set(usd_reader.SETTING_THREADED, True)
            usd_reader.shutdown_usd_readers()
            usd_reader.start_usd_readers()

            pool = usd_reader._executor
            self.assertIsNotNone(pool, "the pool was not built")
            # A ThreadPoolExecutor starts a thread when it is first given work, so an idle pool is
            # the observable form of "nothing was submitted at startup".
            self.assertEqual(pool._work_queue.qsize(), 0, "startup queued work on the reader")
            self.assertFalse(pool._threads, "startup started a reader thread")
        finally:
            usd_reader.shutdown_usd_readers()
            if was is None:
                settings.destroy_item(usd_reader.SETTING_THREADED)
            else:
                settings.set(usd_reader.SETTING_THREADED, was)
            usd_reader.start_usd_readers()
