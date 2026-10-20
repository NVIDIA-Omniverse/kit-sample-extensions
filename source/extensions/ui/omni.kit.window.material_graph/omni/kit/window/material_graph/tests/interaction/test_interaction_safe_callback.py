from unittest.mock import patch

from ...scripts.config.paths import Paths
from ...scripts.models.catalog.items.shader import ShaderItem
from ...scripts.ui.controllers.interaction.events import InteractionController
from ..base import MaterialGraphTestBase


class TestInteractionSafeCallback(MaterialGraphTestBase):
    """Safe menu callback handling."""

    async def test_safe_callback_handles_invalid(self) -> None:
        """None callbacks should warn and return safely."""
        with patch(
            f"{Paths.MODULE_ID}.scripts.ui.controllers.interaction.events.logger.warning",
            autospec=True,
        ) as log_warn:
            InteractionController._safe_menu_callback(None, [], None)
        log_warn.assert_called_once()

    async def test_safe_callback_handles_exception(self) -> None:
        """Callback exceptions should be logged as errors."""

        def _raise(*, items: list, mouse_position: object | None) -> None:
            """Raise an error to validate error handling."""
            raise ValueError("boom")

        with patch(
            f"{Paths.MODULE_ID}.scripts.ui.controllers.interaction.events.log_exception",
            autospec=True,
        ) as log_error:
            InteractionController._safe_menu_callback(_raise, [], None)
        log_error.assert_called_once()

    async def test_trim_redundant_tail_for_variant_selection(self) -> None:
        """Variant-selection entries should trim duplicate name submenu tails."""
        child = ShaderItem("Clamp", "mdl", "clamp(float,float,float)", family="Math:Functions:Clamp")
        child.extra_mime_data = {"requires_variant_selection": True}
        trimmed = InteractionController._trim_redundant_polymorphic_tail(child, ["Functions", "Clamp"])
        self.assertEqual(trimmed, ["Functions"])
