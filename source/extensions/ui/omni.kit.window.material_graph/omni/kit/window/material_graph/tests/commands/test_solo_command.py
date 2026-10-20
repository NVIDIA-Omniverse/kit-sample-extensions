"""Tests for the solo/unsolo context command and the Fabric gate."""

from unittest.mock import patch

import omni.kit.undo
from pxr import Sdf, UsdShade

from ...scripts.commands.impl.solo import MaterialGraph_SoloContextCommand  # noqa: F401
from ...scripts.commands.wrappers.solo import SoloContext, UnsoloContext
from ...scripts.ui.controllers.core.context_solo import (
    _FABRIC_SETTING,
    _MIN_KIT_MAJOR_FOR_FABRIC_SOLO,
    is_solo_supported,
)
from .base import CommandsTestBase


class TestSoloCommand(CommandsTestBase):
    """Verify solo/unsolo session layer edits and the Fabric version gate."""

    async def setUp(self) -> None:
        await super().setUp()
        self._material_path = Sdf.Path("/World/Looks/Material")
        # Fabric-gate tests only inspect settings/version logic.  Reopening a
        # renderer-backed material for them adds no coverage and can leave an
        # asynchronous texture load pending between consecutive test stages.
        if not self._testMethodName.startswith("test_gate_"):
            await self._load_scene("material.usda")

    # ------------------------------------------------------------------
    # Solo: session layer should contain explicit empty connection lists
    # ------------------------------------------------------------------

    async def test_solo_writes_to_session_layer(self) -> None:
        """SoloContext disconnects outputs on the session layer, not the root layer."""
        stage = self._stage
        session = stage.GetSessionLayer()
        root = stage.GetRootLayer()

        root_before = root.ExportToString()

        result = SoloContext(self._material_path, ["mtlx:surface"])
        self.assertTrue(result.success)

        session_spec = session.GetAttributeAtPath(self._material_path.AppendProperty("outputs:mtlx:surface"))
        self.assertIsNotNone(session_spec)
        self.assertEqual(list(session_spec.connectionPathList.GetAddedOrExplicitItems()), [])

        self.assertEqual(root.ExportToString(), root_before, "Root layer must not be modified by solo")

    async def test_solo_composed_connection_is_blocked(self) -> None:
        """After solo the composed stage should show no connection for the disconnected output."""
        material = UsdShade.Material(self._stage.GetPrimAtPath(self._material_path))
        mtlx_out = material.GetOutput("mtlx:surface")
        self.assertTrue(mtlx_out.HasConnectedSource())

        SoloContext(self._material_path, ["mtlx:surface"])

        sources = mtlx_out.GetConnectedSources()
        connected = [s for s in sources[0] if s.source.GetPrim().IsValid()]
        self.assertEqual(len(connected), 0, "Soloed output should have no composed connections")

    # ------------------------------------------------------------------
    # Unsolo: session layer properties should be removed
    # ------------------------------------------------------------------

    async def test_unsolo_restores_connections(self) -> None:
        """UnsoloContext removes session overrides so root layer connections reappear."""
        material = UsdShade.Material(self._stage.GetPrimAtPath(self._material_path))
        mtlx_out = material.GetOutput("mtlx:surface")
        original_sources = mtlx_out.GetConnectedSources()
        self.assertTrue(len(original_sources[0]) > 0)

        SoloContext(self._material_path, ["mtlx:surface"])

        result = UnsoloContext(self._material_path, ["mtlx:surface"])
        self.assertTrue(result.success)

        session = self._stage.GetSessionLayer()
        session_spec = session.GetAttributeAtPath(self._material_path.AppendProperty("outputs:mtlx:surface"))
        self.assertFalse(bool(session_spec), "Session spec should be removed after unsolo")

        restored = mtlx_out.GetConnectedSources()
        self.assertTrue(len(restored[0]) > 0, "Connections should be restored after unsolo")

    # ------------------------------------------------------------------
    # Undo/redo round-trip
    # ------------------------------------------------------------------

    async def test_solo_undo_redo(self) -> None:
        """Undo restores connections, redo re-applies solo."""
        material = UsdShade.Material(self._stage.GetPrimAtPath(self._material_path))
        mtlx_out = material.GetOutput("mtlx:surface")
        session = self._stage.GetSessionLayer()

        SoloContext(self._material_path, ["mtlx:surface"])

        session_spec = session.GetAttributeAtPath(self._material_path.AppendProperty("outputs:mtlx:surface"))
        self.assertIsNotNone(session_spec)

        omni.kit.undo.undo()
        await self._app.next_update_async()

        session_spec = session.GetAttributeAtPath(self._material_path.AppendProperty("outputs:mtlx:surface"))
        self.assertFalse(bool(session_spec), "Undo should remove session spec")
        self.assertTrue(mtlx_out.HasConnectedSource(), "Undo should restore connection")

        omni.kit.undo.redo()
        await self._app.next_update_async()

        session_spec = session.GetAttributeAtPath(self._material_path.AppendProperty("outputs:mtlx:surface"))
        self.assertIsNotNone(session_spec)
        self.assertEqual(list(session_spec.connectionPathList.GetAddedOrExplicitItems()), [])

    async def test_solo_undo_restores_preexisting_session_property_exactly(self) -> None:
        """Undo must restore, rather than delete, an existing session-layer opinion."""
        session = self._stage.GetSessionLayer()
        attr_path = self._material_path.AppendProperty("outputs:mtlx:surface")
        Sdf.JustCreatePrimAttributeInLayer(
            session,
            attr_path,
            Sdf.ValueTypeNames.Token,
            Sdf.VariabilityUniform,
            True,
        )
        spec = session.GetAttributeAtPath(attr_path)
        spec.default = "preexisting"
        spec.SetInfo("displayName", "Pre-existing session output")
        before = session.ExportToString()

        self.assertTrue(SoloContext(self._material_path, ["mtlx:surface"]).success)
        omni.kit.undo.undo()
        await self._app.next_update_async()

        self.assertEqual(session.ExportToString(), before)

    async def test_unsolo_undo_restores_preexisting_override_exactly(self) -> None:
        """Undoing unsolo must reconstruct the complete removed session spec."""
        session = self._stage.GetSessionLayer()
        attr_path = self._material_path.AppendProperty("outputs:mtlx:surface")
        Sdf.JustCreatePrimAttributeInLayer(
            session,
            attr_path,
            Sdf.ValueTypeNames.Token,
            Sdf.VariabilityUniform,
            True,
        )
        spec = session.GetAttributeAtPath(attr_path)
        spec.default = "preexisting"
        spec.SetInfo("displayName", "Pre-existing session output")
        spec.connectionPathList.ClearEditsAndMakeExplicit()
        spec.connectionPathList.explicitItems = []
        before = session.ExportToString()

        self.assertTrue(UnsoloContext(self._material_path, ["mtlx:surface"]).success)
        self.assertFalse(bool(session.GetAttributeAtPath(attr_path)))
        omni.kit.undo.undo()
        await self._app.next_update_async()

        self.assertEqual(session.ExportToString(), before)

    async def test_snapshot_failure_aborts_without_mutating_the_session_layer(self) -> None:
        """A failed lossless snapshot must abort instead of risking destructive undo."""
        session = self._stage.GetSessionLayer()
        attr_path = self._material_path.AppendProperty("outputs:mtlx:surface")
        Sdf.JustCreatePrimAttributeInLayer(
            session,
            attr_path,
            Sdf.ValueTypeNames.Token,
            Sdf.VariabilityUniform,
            True,
        )
        before = session.ExportToString()
        command = MaterialGraph_SoloContextCommand(self._material_path, ["mtlx:surface"])

        with patch("pxr.Sdf.CopySpec", return_value=False):
            result = command.do()

        self.assertFalse(result)
        self.assertEqual(session.ExportToString(), before)

    # ------------------------------------------------------------------
    # Multiple outputs
    # ------------------------------------------------------------------

    async def test_solo_multiple_outputs(self) -> None:
        """Solo can disconnect multiple outputs in one call."""
        result = SoloContext(self._material_path, ["mdl:surface", "mtlx:surface"])
        self.assertTrue(result.success)

        session = self._stage.GetSessionLayer()
        for name in ["mdl:surface", "mtlx:surface"]:
            spec = session.GetAttributeAtPath(self._material_path.AppendProperty(f"outputs:{name}"))
            self.assertIsNotNone(spec, f"Session spec missing for {name}")
            self.assertEqual(list(spec.connectionPathList.GetAddedOrExplicitItems()), [])

    # ------------------------------------------------------------------
    # Edge cases
    # ------------------------------------------------------------------

    async def test_solo_invalid_prim(self) -> None:
        """Solo on a nonexistent prim should not create any session layer specs."""
        session = self._stage.GetSessionLayer()
        SoloContext(Sdf.Path("/Bogus/Prim"), ["surface"])
        spec = session.GetPrimAtPath(Sdf.Path("/Bogus/Prim"))
        self.assertFalse(bool(spec), "No session prim should be created for a bogus path")

    # ------------------------------------------------------------------
    # Fabric gate
    # ------------------------------------------------------------------

    async def test_gate_allows_when_fabric_disabled(self) -> None:
        """Solo is supported when Fabric is off regardless of Kit version."""
        self._settings.set_bool(_FABRIC_SETTING, False)
        supported, reason = is_solo_supported()
        self.assertTrue(supported)
        self.assertEqual(reason, "")

    async def test_gate_blocks_old_kit_with_fabric(self) -> None:
        """Solo is blocked when Fabric is on and Kit version is below threshold."""
        self._settings.set_bool(_FABRIC_SETTING, True)
        mock_app = type("App", (), {"get_kit_version_short": staticmethod(lambda: "110.0")})()
        with patch("omni.kit.app.get_app", return_value=mock_app):
            supported, reason = is_solo_supported()
        self.assertFalse(supported)
        self.assertIn("110.0", reason)
        self._settings.set_bool(_FABRIC_SETTING, False)

    async def test_gate_allows_new_kit_with_fabric(self) -> None:
        """Solo is allowed when Fabric is on and Kit version meets threshold."""
        self._settings.set_bool(_FABRIC_SETTING, True)
        mock_app = type(
            "App",
            (),
            {
                "get_kit_version_short": staticmethod(lambda: f"{_MIN_KIT_MAJOR_FOR_FABRIC_SOLO}.0"),
            },
        )()
        with patch("omni.kit.app.get_app", return_value=mock_app):
            supported, reason = is_solo_supported()
        self.assertTrue(supported)
        self.assertEqual(reason, "")
        self._settings.set_bool(_FABRIC_SETTING, False)
