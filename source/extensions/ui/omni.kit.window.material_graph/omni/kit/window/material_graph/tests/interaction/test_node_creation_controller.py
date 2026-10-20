import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from pxr import Sdf

from ...scripts.commands.result import CommandResult
from ...scripts.config.paths import Paths
from ...scripts.ui.controllers.interaction.node_creation import NodeCreationController

# pylint: disable=no-member
from ..base import MaterialGraphTestBase
from ..fixtures.context_stubs import DummyContextManager
from ..fixtures.widget_stubs import DummyWidget

MODULE_ID = Paths.MODULE_ID


class _DummyRootModel:
    """Minimal graph root model stub used by drop-handler interaction tests."""

    def __init__(self, prim_path):
        self.prim_path = prim_path
        self.selection = []

    @staticmethod
    def get_item_model(_path):
        return None


class TestNodeCreationController(MaterialGraphTestBase):
    """NodeCreationController coordinates drop events onto the graph: it validates payloads (JSON,
    type, context), delegates to CreateShader/CreateBackdrop or path/texture handlers, and surfaces
    errors on the widget. We test accept_drop validation, drop error paths (invalid/missing/mismatch),
    and that valid shader/backdrop/texture drops call the right creation path without running real
    USD commands."""

    async def setUp(self) -> None:
        """Initialize controller with dummy dependencies."""
        await super().setUp()
        self.widget = DummyWidget(
            isolation_model=SimpleNamespace(
                root=_DummyRootModel(Sdf.Path("/World/Looks/material")),
                add_input_or_output=MagicMock(),
            )
        )
        self.context_visibility = MagicMock()
        self.catalog_model = MagicMock()
        self.context_manager = DummyContextManager(node=object())
        self.usd_context = MagicMock()
        self.graph_settings = MagicMock()
        self.controller = NodeCreationController(
            self.widget,
            self.context_visibility,
            self.catalog_model,
            self.context_manager,
            self.usd_context,
            self.graph_settings,
        )

    async def test_accept_drop_rejects_invalid_json(self) -> None:
        """Invalid JSON rejected."""
        self.assertFalse(self.controller.accept_drop("{bad-json}"))

    async def test_accept_drop_rejects_missing_type(self) -> None:
        """Missing type rejected."""
        payload = json.dumps({"identifier": "foo"})
        self.assertFalse(self.controller.accept_drop(payload))

    async def test_accept_drop_rejects_context_mismatch(self) -> None:
        """Context mismatch rejected."""
        payload = json.dumps({"type": "Shader", "context": "other"})
        self.assertFalse(self.controller.accept_drop(payload))

    async def test_accept_drop_accepts_shader_payload(self) -> None:
        """Shader payload accepted."""
        payload = json.dumps({"type": "Shader", "context": "universal"})
        self.assertTrue(self.controller.accept_drop(payload))

    async def test_drop_invalid_payload_shows_error(self) -> None:
        """Invalid payload shows error."""
        event = SimpleNamespace(mime_data="{bad-json}", x=1, y=2)
        self.controller.drop(event)
        self.widget.show_error.assert_called()

    async def test_drop_missing_identifier_shows_error(self) -> None:
        """Missing identifier shows error."""
        payload = json.dumps({"type": "Shader", "context": "universal"})
        event = SimpleNamespace(mime_data=payload, x=1, y=2)
        self.controller.drop(event)
        self.widget.show_error.assert_called()

    async def test_drop_context_mismatch_shows_error(self) -> None:
        """Context mismatch shows error."""
        payload = json.dumps({"type": "Shader", "context": "other", "identifier": "foo"})
        event = SimpleNamespace(mime_data=payload, x=1, y=2)
        self.controller.drop(event)
        self.widget.show_error.assert_called()

    async def test_drop_missing_model_shows_error(self) -> None:
        """Missing isolation model shows error."""
        payload = json.dumps({"type": "Shader", "context": "universal", "identifier": "foo"})
        self.widget.isolation_model = None
        event = SimpleNamespace(mime_data=payload, x=1, y=2)
        self.controller.drop(event)
        self.widget.show_error.assert_called()

    async def test_drop_valid_shader_creates_node(self) -> None:
        """Valid shader payload creates node."""
        # Patch CreateShader to avoid USD/command side effects and assert it was called.
        payload = json.dumps({"type": "Shader", "context": "universal", "identifier": "foo"})
        event = SimpleNamespace(mime_data=payload, x=1, y=2)

        with patch(
            f"{MODULE_ID}.scripts.ui.controllers.interaction.node_creation.CreateShader", autospec=True
        ) as create_shader:
            self.controller.drop(event)

        create_shader.assert_called_once()
        self.widget.clear_error.assert_called()

    async def test_drop_backdrop_applies_visibility(self) -> None:
        """Backdrop visibility is authored by the creation command, not a second direct mutation."""
        payload = json.dumps({"type": "Backdrop"})
        event = SimpleNamespace(mime_data=payload, x=1, y=2)
        self.graph_settings.get_backdrop_drop_settings.return_value = ("position:universal", "universal")

        with patch(
            f"{MODULE_ID}.scripts.ui.controllers.interaction.node_creation.CreateBackdrop",
            autospec=True,
            return_value=CommandResult(
                True, payload=SimpleNamespace(GetPath=lambda: Sdf.Path("/World/Looks/material/Backdrop"))
            ),
        ) as create_backdrop:
            self.controller.drop(event)

        _, position, position_key, visibility = create_backdrop.call_args.args
        self.assertIsNotNone(position)
        self.assertEqual(position_key, "position:universal")
        self.assertEqual(visibility, "universal")
        self.context_visibility.apply_to_prim.assert_not_called()
        self.widget.clear_error.assert_called()

    async def test_drop_texture_url_uses_texture_handler(self) -> None:
        """Texture URL routes to texture handler."""
        # Patch is_valid_url so the drop is treated as a valid URL; patch PathDropHandler.handle_drop to return False so texture path is tried; patch TextureDropHandler.handle_drop to assert it is called.
        event = SimpleNamespace(mime_data="omniverse://textures/test.png", x=1, y=2)
        with (
            patch("omni.client.is_valid_url", autospec=True, return_value=True),
            patch(
                f"{MODULE_ID}.scripts.ui.controllers.drop.paths.PathDropHandler.handle_drop",
                autospec=True,
                return_value=False,
            ),
            patch(
                f"{MODULE_ID}.scripts.ui.controllers.drop.textures.TextureDropHandler.handle_drop",
                autospec=True,
            ) as handle_drop,
        ):
            self.controller.drop(event)

        handle_drop.assert_called_once()
