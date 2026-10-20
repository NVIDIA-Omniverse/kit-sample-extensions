# pylint: disable=relative-beyond-top-level,protected-access
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pxr import Sdf, UsdShade

from ...scripts.commands import export as export_utils
from ...scripts.config.paths import Paths
from ...scripts.settings import utils
from ...scripts.settings.settings import Settings
from ...scripts.settings.utils import COMPOUND_DEFAULT_PATH
from ..base import MaterialGraphTestBase


class TestExportUtils(MaterialGraphTestBase):
    """export_utils handles USD export (export, export_nodegraph) and resolve_export_directory for
    compound/nodegraph paths. We test invalid-pr and layer/copy failures logging, success path,
    export_nodegraph using the exporter, and resolve_export_directory for non-local, UNC, default,
    and override settings—all with patches to avoid real USD/disk and to assert logging."""

    async def test_export_invalid_prim_logs_warning(self) -> None:
        """Invalid prim logs a warning."""
        # Patch logger.warning to assert export(None) logs.
        with patch(
            f"{Paths.MODULE_ID}.scripts.commands.export.prim.logger.warning",
            autospec=True,
        ) as log_warn:
            export_utils.export("dummy.usda", None)
        log_warn.assert_called()

    async def test_export_layer_create_failure_logs(self) -> None:
        """Layer creation failure logs a warning."""

        # Patch Sdf.Layer.CreateNew to raise; patch logger.warning to assert.
        class DummyPrim:
            """Prim stub that returns a dummy stage."""

            def GetStage(self) -> object:
                """Return a non-USD stage object."""
                return object()

            def GetPath(self) -> Sdf.Path:
                """Return an empty path."""
                return Sdf.Path()

        with (
            patch("pxr.Sdf.Layer.CreateNew", side_effect=RuntimeError("boom")),
            patch(
                f"{Paths.MODULE_ID}.scripts.commands.export.prim.logger.warning",
                autospec=True,
            ) as log_warn,
        ):
            export_utils.export("dummy.usda", DummyPrim())
            log_warn.assert_called()

    async def test_export_copy_spec_failure_logs(self) -> None:
        """CopySpec failure logs a warning."""

        # Patch CreateNew, CopySpec (raise), and logger.warning to assert.
        class DummyStage:
            """Stage stub that flattens to a placeholder layer."""

            def Flatten(self) -> object:
                """Return a dummy flattened layer."""
                return object()

        class DummyPrim:
            """Prim stub that returns a dummy stage and path."""

            def GetStage(self) -> DummyStage:
                """Return the dummy stage."""
                return DummyStage()

            def GetPath(self) -> object:
                """Return a dummy path object."""

                class DummyPath:
                    """Path stub with a name field."""

                    name = "Prim"

                return DummyPath()

        with (
            patch("pxr.Sdf.Layer.CreateNew", return_value=object()),
            patch("pxr.Sdf.CopySpec", side_effect=RuntimeError("boom")),
            patch(
                f"{Paths.MODULE_ID}.scripts.commands.export.prim.logger.warning",
                autospec=True,
            ) as log_warn,
        ):
            export_utils.export("dummy.usda", DummyPrim())
            log_warn.assert_called()

    async def test_export_copy_spec_false_returns_failure(self) -> None:
        """A false CopySpec result must not be reported as a successful export."""

        class DummyStage:
            def Flatten(self) -> object:
                return object()

        class DummyPrim:
            def GetStage(self) -> DummyStage:
                return DummyStage()

            def GetPath(self) -> Sdf.Path:
                return Sdf.Path("/World/Prim")

        with (
            patch("pxr.Sdf.Layer.CreateNew", return_value=object()),
            patch("pxr.Sdf.CopySpec", return_value=False),
        ):
            result = export_utils.export("dummy.usda", DummyPrim())

        self.assertFalse(result.success)
        self.assertEqual(result.message, "copy spec failed")

    async def test_export_success(self) -> None:
        """Export returns success for valid prims."""

        # Patch CreateNew, CopySpec, AttributeSpec, queue_event, logger.info to avoid USD/disk.
        class DummyStage:
            """Stage stub that flattens to a placeholder layer."""

            def Flatten(self) -> object:
                """Return a dummy flattened layer."""
                return object()

        class DummyPrim:
            """Prim stub that returns a dummy stage and path."""

            def GetStage(self) -> DummyStage:
                """Return the dummy stage."""
                return DummyStage()

            def GetPath(self) -> Sdf.Path:
                """Return a valid path."""
                return Sdf.Path("/World/Prim")

        class DummyLayer:
            """Target layer stub."""

            def __init__(self):
                self.defaultPrim = None

            def GetPrimAtPath(self, _path):
                return SimpleNamespace(attributes={})

            def Save(self):
                return None

        target_layer = DummyLayer()
        with (
            patch("pxr.Sdf.Layer.CreateNew", return_value=target_layer),
            patch("pxr.Sdf.CopySpec", return_value=True),
            patch("pxr.Sdf.AttributeSpec", return_value=SimpleNamespace(default=None)),
            patch("omni.kit.app.queue_event", autospec=True),
            patch(
                f"{Paths.MODULE_ID}.scripts.commands.export.prim.logger.info",
                autospec=True,
            ),
        ):
            result = export_utils.export("dummy.usda", DummyPrim())
        self.assertTrue(result.success)
        self.assertEqual(result.message, "exported")

    async def test_resolve_export_directory_rejects_non_string_setting(self) -> None:
        """Malformed persistent settings return a structured failure instead of TypeError."""
        self._settings.set(Settings.COMPOUND_DEFAULT_EXPORT_PATH, 123)
        result = export_utils.resolve_export_directory()
        self.assertFalse(result.success)
        self.assertEqual(result.message, "export directory setting must be a string")

    async def test_export_nodegraph_uses_exporter(self) -> None:
        """export_nodegraph uses exporter and returns success."""
        # Patch resolve_export_directory and ExportPrimUSD so we don't open real UI or touch disk.
        nodegraph = UsdShade.NodeGraph.Define(self._stage, Sdf.Path("/World/Nodegraph"))
        exporter_instances = []

        def _factory(*_args, **_kwargs):
            instance = MagicMock()
            exporter_instances.append(instance)
            return instance

        with (
            patch(
                f"{Paths.MODULE_ID}.scripts.commands.export.nodegraph.resolve_export_directory",
                return_value=export_utils.ExportResult(True, "resolved", target_path="/tmp"),
            ),
            patch(f"{Paths.MODULE_ID}.scripts.commands.export.nodegraph.ExportPrimUSD", _factory),
        ):
            result = export_utils.export_nodegraph(nodegraph.GetPrim())
        self.assertTrue(result.success)
        self.assertEqual(result.target_path, "/tmp")
        self.assertTrue(exporter_instances)
        exporter_instances[0].export.assert_called_once_with([nodegraph.GetPrim()])

    async def test_get_compound_dir_non_local_passthrough(self) -> None:
        """Non-local path passes through untouched."""
        # Patch settings utils tokens to return omniverse path.
        self._settings.set(Settings.COMPOUND_DEFAULT_EXPORT_PATH, "${data}/nodegraphs")

        class DummyTokens:
            """Token resolver stub."""

            def resolve(self, _path: str) -> str:
                """Return a non-local server path."""
                return "omniverse://server/path"

        with patch.object(utils, "tokens", DummyTokens()):
            result = export_utils.resolve_export_directory()
        self.assertTrue(result.success)
        self.assertEqual(result.target_path, "omniverse://server/path")

    async def test_get_compound_dir_does_not_uppercase_unc(self) -> None:
        """UNC path retains casing."""
        # Patch tokens and Path.mkdir to avoid real disk.
        self._settings.set(Settings.COMPOUND_DEFAULT_EXPORT_PATH, "${data}/nodegraphs")

        class DummyTokens:
            """Token resolver stub."""

            def resolve(self, _path: str) -> str:
                """Return a UNC style path."""
                return "//server/share"

        with (
            patch.object(utils, "tokens", DummyTokens()),
            patch.object(Path, "mkdir", autospec=True, return_value=None),
        ):
            result = export_utils.resolve_export_directory()
        self.assertTrue(result.success)
        self.assertTrue(result.target_path.startswith("//"))

    async def test_get_compound_dir_uses_default_setting(self) -> None:
        """Unset path falls back to default token."""

        # Patch tokens and Path.mkdir to control resolution.
        class DummyTokens:
            """Token resolver stub."""

            def __init__(self):
                self.last_path = None

            def resolve(self, path: str) -> str:
                """Capture the path and return a dummy directory."""
                self.last_path = path
                return "/tmp/export"

        self._settings.set(Settings.COMPOUND_DEFAULT_EXPORT_PATH, "")
        tokens = DummyTokens()
        with (
            patch.object(utils, "tokens", tokens),
            patch.object(Path, "mkdir", autospec=True, return_value=None),
        ):
            result = export_utils.resolve_export_directory()
        self.assertTrue(result.success)
        self.assertEqual(result.target_path, COMPOUND_DEFAULT_PATH)

    async def test_get_compound_dir_uses_override_setting(self) -> None:
        """Override setting is used as resolved path."""
        # Patch tokens and Path.mkdir to capture passed path.
        override = "${data}/custom_exports"

        class DummyTokens:
            """Token resolver stub."""

            def __init__(self):
                self.last_path = None

            def resolve(self, path: str) -> str:
                """Capture the path and return a dummy directory."""
                self.last_path = path
                return "/tmp/export"

        self._settings.set(Settings.COMPOUND_DEFAULT_EXPORT_PATH, override)
        tokens = DummyTokens()
        with (
            patch.object(utils, "tokens", tokens),
            patch.object(Path, "mkdir", autospec=True, return_value=None),
        ):
            export_utils.resolve_export_directory()
        self.assertEqual(tokens.last_path, override)
