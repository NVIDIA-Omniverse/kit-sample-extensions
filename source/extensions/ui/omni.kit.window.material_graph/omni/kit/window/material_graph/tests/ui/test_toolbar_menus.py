from unittest.mock import MagicMock, patch

from ...scripts.config.paths import Paths
from ...scripts.extension import GraphExtension
from ...scripts.ui.sections.toolbar.menus import ToolbarMenuBuilder
from ..ui_base import MaterialGraphUiTestBase

MENU_MODULE = f"{Paths.MODULE_ID}.scripts.ui.sections.toolbar.menus"
PREFERENCES_MODULE = "omni.kit.window.preferences"


class TestToolbarMenuBuilder(MaterialGraphUiTestBase):
    """Toolbar menu builder behavior."""

    async def test_menu_is_replaced_instead_of_cleared_during_button_events(self) -> None:
        """Repeated menu opens must not mutate an OmniUI container in-place."""
        builder = ToolbarMenuBuilder(GraphExtension._WINDOW_NAME)
        first = MagicMock()
        second = MagicMock()

        with patch(f"{MENU_MODULE}.omni.ui.Menu", side_effect=[first, second]) as create_menu:
            self.assertIs(builder._ensure_menu(), first)
            self.assertIs(builder._ensure_menu(), second)

        first.hide.assert_called_once_with()
        second.hide.assert_not_called()
        self.assertEqual(create_menu.call_count, 2)

    async def test_edit_menu_opens_preferences(self) -> None:
        """Edit menu should open preferences and focus the window."""
        window_name = GraphExtension._WINDOW_NAME
        builder = ToolbarMenuBuilder(window_name)

        fake_menu = MagicMock()
        fake_menu.__enter__.return_value = fake_menu
        fake_menu.__exit__.return_value = False
        builder._ensure_menu = MagicMock(return_value=fake_menu)

        captured = {}

        def fake_menu_item(_label: str, triggered_fn=None, **_kwargs) -> None:
            """Capture the triggered callback for later invocation."""
            captured["triggered_fn"] = triggered_fn

        page = MagicMock()
        page.get_title.return_value = window_name
        pref_window = MagicMock()
        with (
            patch(f"{MENU_MODULE}.omni.ui.MenuItem", side_effect=fake_menu_item),
            patch(f"{PREFERENCES_MODULE}.get_page_list", return_value=[page]),
            patch(f"{PREFERENCES_MODULE}.show_preferences_window") as show_prefs,
            patch(f"{PREFERENCES_MODULE}.select_page") as select_page,
            patch(f"{MENU_MODULE}.omni.ui.Workspace.get_window", return_value=pref_window),
        ):
            builder.show_edit_menu()
            self.assertIsNotNone(captured.get("triggered_fn"))
            captured["triggered_fn"]()

        show_prefs.assert_called_once()
        select_page.assert_called_once_with(page)
        pref_window.focus.assert_called_once()

    async def test_view_menu_enables_items_based_on_model(self) -> None:
        """View menu should enable items based on model availability."""
        builder = ToolbarMenuBuilder(GraphExtension._WINDOW_NAME)

        fake_menu = MagicMock()
        fake_menu.__enter__.return_value = fake_menu
        fake_menu.__exit__.return_value = False
        builder._ensure_menu = MagicMock(return_value=fake_menu)

        menu_calls = []

        def fake_menu_item(label: str, triggered_fn=None, enabled: bool = True, **_kwargs) -> None:
            """Track menu labels and enabled state."""
            menu_calls.append((label, enabled))

        with (
            patch(f"{MENU_MODULE}.omni.ui.MenuItem", side_effect=fake_menu_item),
            patch(f"{MENU_MODULE}.omni.ui.Separator"),
        ):
            builder.show_view_menu(False, MagicMock(), MagicMock())
            builder.show_view_menu(True, MagicMock(), MagicMock())

        self.assertIn(("Auto Layout Nodes", False), menu_calls)
        self.assertIn(("Frame Nodes", False), menu_calls)
        self.assertIn(("Auto Layout Nodes", True), menu_calls)
        self.assertIn(("Frame Nodes", True), menu_calls)
