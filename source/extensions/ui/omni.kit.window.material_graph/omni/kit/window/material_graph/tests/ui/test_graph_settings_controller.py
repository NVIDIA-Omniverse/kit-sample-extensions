# pylint: disable=relative-beyond-top-level,protected-access,no-member
from unittest.mock import MagicMock, patch

from ...scripts.settings.settings import Settings
from ...scripts.ui.controllers.core.graph_settings import GraphSettingsController
from ..base import MaterialGraphTestBase


class _DummyWidget:
    """Widget stub for graph settings controller tests."""

    def __init__(self) -> None:
        self.current_context = "mdl"
        self.request_model_refresh = MagicMock()


class _DummySettings:
    """Settings stub for subscription handling."""

    def __init__(self) -> None:
        self.subscriptions = []

    def subscribe_to_tree_change_events(self, _key, _cb):
        sub = MagicMock()
        self.subscriptions.append(sub)
        return sub


class TestGraphSettingsController(MaterialGraphTestBase):
    """GraphSettingsController behavior."""

    async def test_drop_settings_respect_confine_flags(self) -> None:
        """Drop settings should be gated by confine flags."""
        widget = _DummyWidget()
        dummy_settings = _DummySettings()
        with (
            patch("carb.settings.get_settings", return_value=dummy_settings),
            patch.object(Settings, "confine_backdrops", return_value=False),
            patch.object(Settings, "confine_nodegraphs", return_value=True),
        ):
            controller = GraphSettingsController(widget)
            self.assertEqual(controller.get_backdrop_drop_settings(), (None, None))
            key, visibility = controller.get_nodegraph_drop_settings()
            self.assertIn(widget.current_context, visibility)
            self.assertIn(widget.current_context, key)
            controller.destroy()

    async def test_setting_change_requests_refresh(self) -> None:
        """Settings changes should request model refresh."""
        widget = _DummyWidget()
        dummy_settings = _DummySettings()
        with patch("carb.settings.get_settings", return_value=dummy_settings):
            controller = GraphSettingsController(widget)
            controller._on_setting_changed(None, None, None)
            widget.request_model_refresh.assert_called()
            controller.destroy()
