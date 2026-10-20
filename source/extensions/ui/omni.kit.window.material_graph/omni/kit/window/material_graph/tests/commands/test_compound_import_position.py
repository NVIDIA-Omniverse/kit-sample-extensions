import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pxr import Gf, Sdf, Usd, UsdShade, UsdUI

from ...scripts.commands.impl.nodegraph.import_ import MaterialGraph_ImportNodeGraphCommand, _make_valid_identifier
from .base import CommandsTestBase

# pylint: disable=relative-beyond-top-level,no-member


class TestCompoundImportPosition(CommandsTestBase):
    """When a compound is imported, the drop position must override any position stored in the
    source asset's custom data so the node appears where the user dropped it. We test that the
    command writes the supplied position into the target prim's omni:uiNodegraphNodePos for the
    context."""

    async def test_import_compound_overrides_position(self) -> None:
        """Dropped position overrides authored custom data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            compound_path = f"{temp_dir}/compound.usda"
            source_stage = Usd.Stage.CreateNew(compound_path)
            graph = UsdShade.NodeGraph.Define(source_stage, "/CompoundGraph")
            prim = graph.GetPrim()
            prim.SetCustomDataByKey("omni:uiNodegraphNodePos:mdl", Gf.Vec2f(1.0, 1.0))
            source_stage.GetRootLayer().Save()

            cmd = MaterialGraph_ImportNodeGraphCommand(
                parent_path=self._stage.GetPseudoRoot().GetPath(),
                source_asset=compound_path,
                identifier="/CompoundGraph",
                position=Gf.Vec2f(10.0, 20.0),
                context_name="mdl",
            )
            cmd.do()

            target_prim = self._stage.GetPrimAtPath("/CompoundGraph")
            self.assertTrue(target_prim)
            key = f"omni:{UsdUI.Tokens.uiNodegraphNodePos}:mdl"
            self.assertEqual(target_prim.GetCustomDataByKey(key), Gf.Vec2f(10.0, 20.0))

    async def test_import_rolls_back_after_invalid_attribute_override(self) -> None:
        """Invalid post-copy overrides must not leave a partially imported prim."""
        with tempfile.TemporaryDirectory() as temp_dir:
            compound_path = f"{temp_dir}/compound.usda"
            source_stage = Usd.Stage.CreateNew(compound_path)
            graph = UsdShade.NodeGraph.Define(source_stage, "/CompoundGraph")
            graph.CreateInput("value", Sdf.ValueTypeNames.Float).Set(1.0)
            source_stage.GetRootLayer().Save()

            cmd = MaterialGraph_ImportNodeGraphCommand(
                parent_path=self._stage.GetPseudoRoot().GetPath(),
                source_asset=compound_path,
                identifier="/CompoundGraph",
                attributes_to_set={"bad/path": 2.0},
                stage=self._stage,
            )

            self.assertIsNone(cmd.do())
            self.assertFalse(self._stage.GetPrimAtPath("/CompoundGraph"))

    async def test_import_rolls_back_after_missing_attribute_override(self) -> None:
        """Missing target attributes are a failed import, not a silent partial success."""
        with tempfile.TemporaryDirectory() as temp_dir:
            compound_path = f"{temp_dir}/compound.usda"
            source_stage = Usd.Stage.CreateNew(compound_path)
            UsdShade.NodeGraph.Define(source_stage, "/CompoundGraph")
            source_stage.GetRootLayer().Save()

            cmd = MaterialGraph_ImportNodeGraphCommand(
                parent_path=self._stage.GetPseudoRoot().GetPath(),
                source_asset=compound_path,
                identifier="/CompoundGraph",
                attributes_to_set={"inputs:missing": 2.0},
                stage=self._stage,
            )

            self.assertIsNone(cmd.do())
            self.assertFalse(self._stage.GetPrimAtPath("/CompoundGraph"))

    async def test_import_source_and_identifier_validation_boundaries(self) -> None:
        """Malformed sources and identifiers are rejected before any target spec is authored."""
        cmd = MaterialGraph_ImportNodeGraphCommand(
            parent_path=Sdf.Path.absoluteRootPath,
            source_asset="",
            identifier="",
            stage=self._stage,
        )
        self.assertIsNone(cmd._resolve_source_layer())
        self.assertIsNone(cmd._resolve_source_path())

        cmd._source_asset = object()
        self.assertIsNone(cmd._resolve_source_layer())
        cmd._source_asset = str((Path(tempfile.gettempdir()) / "material-graph-missing.usda").resolve())
        self.assertIsNone(cmd._resolve_source_layer())
        cmd._source_asset = "missing-relative-layer.usda"
        self.assertIsNone(cmd._resolve_source_layer())

        cmd._identifier = "RelativeGraph"
        self.assertEqual(cmd._resolve_source_path(), Sdf.Path("/RelativeGraph"))
        cmd._identifier = "/AbsoluteGraph"
        self.assertEqual(cmd._resolve_source_path(), Sdf.Path("/AbsoluteGraph"))

    async def test_import_position_attribute_and_identifier_helpers(self) -> None:
        """Import helpers clear stale positions, convert assets, and sanitize caller names."""
        self.assertFalse(MaterialGraph_ImportNodeGraphCommand._clear_position_custom_data(None))
        prefix = f"omni:{UsdUI.Tokens.uiNodegraphNodePos}"
        prim = SimpleNamespace(
            GetCustomData=lambda: {f"{prefix}:old": (1, 2), "other": True},
            SetCustomData=MagicMock(return_value=False),
            HasAuthoredCustomDataKey=MagicMock(return_value=False),
            ClearCustomDataByKey=MagicMock(return_value=False),
        )
        self.assertFalse(MaterialGraph_ImportNodeGraphCommand._clear_position_custom_data(prim))

        target = UsdShade.NodeGraph.Define(self._stage, "/ImportHelper")
        target.GetPrim().SetCustomDataByKey("omni:uiNodegraphNodePos:old", (1.0, 2.0))
        malformed = dict(target.GetPrim().GetCustomData())
        malformed["omni:uiNodegraphNodePos:legacy"] = (3.0, 4.0)
        malformed["other"] = True
        target.GetPrim().SetCustomData(malformed)
        self.assertTrue(MaterialGraph_ImportNodeGraphCommand._clear_position_custom_data(target.GetPrim()))
        self.assertFalse(target.GetPrim().HasAuthoredCustomDataKey("omni:uiNodegraphNodePos"))
        self.assertNotIn("omni:uiNodegraphNodePos:legacy", target.GetPrim().GetCustomData())
        self.assertTrue(target.GetPrim().GetCustomDataByKey("other"))
        target.CreateInput("file", Sdf.ValueTypeNames.Asset)
        cmd = MaterialGraph_ImportNodeGraphCommand(
            parent_path=Sdf.Path.absoluteRootPath,
            source_asset="unused",
            identifier="/ImportHelper",
            attributes_to_set={"inputs:file": "missing-texture.png"},
            stage=self._stage,
        )
        self.assertTrue(cmd._apply_attributes(self._stage, Sdf.Path("/ImportHelper")))
        self.assertEqual(target.GetInput("file").Get(), Sdf.AssetPath("missing-texture.png"))
        cmd._attributes_to_set = None
        self.assertTrue(cmd._apply_attributes(self._stage, Sdf.Path("/ImportHelper")))
        cmd._position = None
        self.assertTrue(cmd._apply_position(target.GetPrim()))

        with patch("pxr.Tf.MakeValidIdentifier", side_effect=TypeError("injected")):
            self.assertEqual(_make_valid_identifier("bad name!"), "bad_name_")
            self.assertEqual(_make_valid_identifier("!!!"), "___")
