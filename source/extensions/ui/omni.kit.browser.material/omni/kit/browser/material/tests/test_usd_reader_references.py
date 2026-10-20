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
Reference gating in the USD reader.

The payload gate does not cover this: ``load=Usd.Stage.LoadNone`` defers payloads and nothing else,
so a reference naming an unreachable server is composed by ``Usd.Stage.Open`` itself - 139 s for one
2.8 KB file, against 0.003 s to read the reference off its layer.

Nothing here opens a stage on a foreign arc, deliberately: a regression would then take minutes to
fail instead of failing.
"""

import tempfile
from pathlib import Path

import carb.settings
import omni.kit.test

from ..usd_reader import (
    DEFAULT_SKIP_FOREIGN_ARCS,
    SETTING_SKIP_FOREIGN_ARCS,
    _foreign_arcs,
    _materials_in_layer,
    _read_usd_materials,
    _skip_foreign_arcs,
)

# A local material beside a reference that goes somewhere else. The local one must survive the gate:
# it is the whole reason the file is read off its layer rather than skipped.
MIXED_TEMPLATE = """#usda 1.0
(
    defaultPrim = "LocalMaterial"
)

def Material "LocalMaterial"
{
}

def Xform "Elsewhere" (
    prepend references = @%s@
)
{
}
"""

LOCAL_TEMPLATE = """#usda 1.0
(
    defaultPrim = "LocalMaterial"
)

def Material "LocalMaterial"
{
}

def Xform "Nearby" (
    prepend references = @%s@
)
{
}
"""

TARGET_USDA = """#usda 1.0
(
    defaultPrim = "Root"
)

def Xform "Root"
{
    def Material "ReferencedMaterial"
    {
    }
}
"""

NESTED_TEMPLATE = """#usda 1.0
(
    defaultPrim = "Looks"
)

def Scope "Looks"
{
    def Material "Wood"
    {
    }

    def Material "Steel"
    {
    }
}

def Xform "Away" (
    prepend references = @%s@
)
{
}
"""

# A foreign payload beside a local reference. LoadNone defers the payload, so this file can and
# should still be composed - the reference's material is only found that way.
PAYLOAD_AND_LOCAL_REF_TEMPLATE = """#usda 1.0
(
    defaultPrim = "LocalMaterial"
)

def Material "LocalMaterial"
{
}

def Xform "Far" (
    prepend payload = @%s@
)
{
}

def Xform "Near" (
    prepend references = @target.usda@
)
{
}
"""

PAYLOAD_AND_REFERENCE_TEMPLATE = """#usda 1.0

def Xform "AsPayload" (
    prepend payload = @%s@
)
{
}

def Xform "AsReference" (
    prepend references = @%s@
)
{
}
"""

DEAD_HOST = "omniverse://fake-server/Assets/streetlamp.usd"


class TestUsdReaderReferences(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._dir = Path(self._tmp.name)
        (self._dir / "target.usda").write_text(TARGET_USDA, encoding="utf-8")

    async def tearDown(self):
        self._tmp.cleanup()

    def _write(self, name, template, target):
        path = self._dir / name
        path.write_text(template % target, encoding="utf-8")
        return path.as_posix()

    async def test_a_reference_elsewhere_is_seen_without_composing_it(self):
        """The freeze, caught by reading the layer - which is what makes it cost milliseconds."""
        url = self._write("mixed.usda", MIXED_TEMPLATE, DEAD_HOST)
        self.assertEqual(_foreign_arcs(url), [DEAD_HOST])

    async def test_a_reference_alongside_is_not_foreign(self):
        """A file whose references are all local must still take the normal path."""
        url = self._write("local.usda", LOCAL_TEMPLATE, "target.usda")
        self.assertEqual(_foreign_arcs(url), [], "a local reference was treated as foreign")

        found = _read_usd_materials(url)
        paths = sorted(m.path for m in found or [])
        self.assertEqual(
            paths,
            ["/LocalMaterial", "/Nearby/ReferencedMaterial"],
            "composing a local reference should still find the material inside it",
        )

    async def test_a_local_material_survives_the_gate(self):
        """
        Skipping the file wholesale would lose this. The point of reading the layer is that what
        the file declares itself still counts.
        """
        url = self._write("mixed.usda", MIXED_TEMPLATE, DEAD_HOST)

        found = _read_usd_materials(url)
        self.assertEqual([m.path for m in found or []], ["/LocalMaterial"])
        self.assertTrue(found[0].is_default, "the default prim flag was lost with the stage")

    async def test_the_layer_reader_finds_nested_materials(self):
        """Materials are not always root prims, and Traverse has to reach the nested ones."""
        path = self._dir / "nested.usda"
        path.write_text(NESTED_TEMPLATE % DEAD_HOST, encoding="utf-8")
        url = path.as_posix()
        self.assertEqual(_foreign_arcs(url), [DEAD_HOST])
        self.assertEqual(sorted(m.path for m in _materials_in_layer(url)), ["/Looks/Steel", "/Looks/Wood"])
        self.assertFalse(
            any(m.is_default for m in _materials_in_layer(url)),
            "a nested material is not the default prim",
        )

    async def test_a_foreign_payload_alone_does_not_trip_this_gate(self):
        """
        The payload gate already handles those, and better: LoadNone defers a payload, so the file
        can still be composed - which is how the materials behind its *local* reference are found.
        Tripping this gate on a payload would trade a working case for nothing.
        """
        path = self._dir / "payload_only.usda"
        path.write_text(PAYLOAD_AND_LOCAL_REF_TEMPLATE % DEAD_HOST, encoding="utf-8")
        url = path.as_posix()
        self.assertEqual(_foreign_arcs(url), [], "a foreign payload should be left to the payload gate")

        found = _read_usd_materials(url)
        self.assertEqual(
            sorted(m.path for m in found or []),
            ["/LocalMaterial", "/Near/ReferencedMaterial"],
            "the file should still be composed, so the local reference's material is found",
        )

    async def test_a_path_used_as_both_payload_and_reference_still_trips_the_gate(self):
        """Being deferred as a payload does not help when a reference pulls in the same layer."""
        path = self._dir / "both.usda"
        path.write_text(PAYLOAD_AND_REFERENCE_TEMPLATE % (DEAD_HOST, DEAD_HOST), encoding="utf-8")
        self.assertEqual(_foreign_arcs(path.as_posix()), [DEAD_HOST])

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

    async def test_asking_for_the_old_behaviour_bypasses_the_gate(self):
        """skip_foreign_arcs=False means compose everything, so the gate must stand aside."""
        url = self._write("local.usda", LOCAL_TEMPLATE, "target.usda")
        found = _read_usd_materials(url, skip_foreign_arcs=False)
        self.assertEqual(len(found or []), 2)

    async def test_a_malformed_file_is_left_to_the_stage_open(self):
        """
        An unparsable file must not be mistaken for one with foreign arcs, or the reader would
        return an empty list where it used to return None and the caller could not tell the
        difference between "no materials" and "unreadable".
        """
        bad = self._dir / "broken.usda"
        bad.write_text("I'm a totally invalid usda file.", encoding="utf-8")
        self.assertEqual(_foreign_arcs(bad.as_posix()), [])
        self.assertIsNone(_read_usd_materials(bad.as_posix()))
