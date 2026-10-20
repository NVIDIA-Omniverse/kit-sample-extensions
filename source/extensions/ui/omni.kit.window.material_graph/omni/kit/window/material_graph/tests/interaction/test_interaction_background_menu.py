from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ...scripts.config.paths import Paths
from ...scripts.models.catalog.items.compound import CompoundItem
from ...scripts.models.catalog.items.shader import ShaderItem
from ...scripts.models.catalog.items.texture import TextureItem
from ...scripts.ui.controllers.interaction.events import InteractionController
from ..base import MaterialGraphTestBase

MODULE_ID = Paths.MODULE_ID


class _CatalogChild:
    """Catalog child stub."""

    def __init__(self, name: str, filtered: bool = True) -> None:
        """Initialize with a name and filter state."""
        self.name = name
        self.filtered = filtered


class _CatalogGroup:
    """Catalog group stub containing children."""

    def __init__(self, name: str, children: list[_CatalogChild], filtered: bool = True) -> None:
        """Initialize with children and filter state."""
        self.name = name
        self.children = children
        self.filtered = filtered


class _CatalogModel:
    """Catalog model stub."""

    def __init__(self, groups: list[_CatalogGroup]) -> None:
        """Initialize with group list."""
        self.children = groups


class _NodeCreation:
    """Node creation stub for background menu tests."""

    def __init__(self) -> None:
        """Initialize tracked creations."""
        self.created = []

    def get_hovered_position(self) -> tuple[int, int]:
        """Return a fixed hover position."""
        return (10, 20)

    def create_from_catalog(self, item: object, mouse_position: tuple[int, int] | None = None) -> None:
        """Record created catalog items."""
        self.created.append((item, mouse_position))


class TestInteractionBackgroundMenu(MaterialGraphTestBase):
    async def test_repeated_background_menu_replaces_event_owned_container(self) -> None:
        """A second right-click must not clear an OmniUI menu during dispatch."""
        controller = InteractionController(
            widget=MagicMock(),
            node_creation_controller=_NodeCreation(),
            catalog_model=_CatalogModel([]),
        )
        menus = [MagicMock(), MagicMock()]
        for menu in menus:
            menu.__enter__.return_value = menu
            menu.__exit__.return_value = False

        with (
            patch("omni.ui.Menu", side_effect=menus),
            patch(
                f"{MODULE_ID}.scripts.ui.controllers.interaction.events.get_background_menu_items",
                return_value=[],
            ),
            patch(f"{MODULE_ID}.scripts.ui.controllers.interaction.events.show_menu_at_cursor"),
        ):
            controller.on_right_mouse_button_pressed([])
            controller.on_right_mouse_button_pressed([])

        menus[0].hide.assert_called_once_with()
        menus[1].hide.assert_not_called()
        self.assertIs(controller._right_click_menu, menus[1])

    async def test_background_menu_unexpected_failure_is_logged_and_contained(self) -> None:
        """Right-click failures should leave the UI alive and produce an actionable log."""
        node_creation = MagicMock()
        node_creation.get_hovered_position.side_effect = KeyError("pointer unavailable")
        widget = MagicMock()
        widget.current_context = "mdl"
        controller = InteractionController(
            widget=widget,
            node_creation_controller=node_creation,
            catalog_model=_CatalogModel([]),
        )

        with patch(f"{MODULE_ID}.scripts.ui.controllers.interaction.events.log_exception") as log_failure:
            controller.on_right_mouse_button_pressed([])

        log_failure.assert_called_once()
        self.assertIsInstance(log_failure.call_args.kwargs["exc"], KeyError)

    async def test_background_menu_builds_catalog_and_background_items(self) -> None:
        """Background menu should include catalog and background items."""
        texture_group = _CatalogGroup("TextureGroup", [_CatalogChild("TexA")])
        setattr(texture_group, "is_texture_group", True)
        ungrouped_texture = TextureItem("LooseTex", "C:/textures/loose.png", "C:/textures/loose.png")
        catalog = _CatalogModel(
            [
                _CatalogGroup("GroupA", [_CatalogChild("Child1"), _CatalogChild("Child2")]),
                texture_group,
                ungrouped_texture,
            ]
        )
        node_creation = _NodeCreation()
        controller = InteractionController(
            widget=MagicMock(), node_creation_controller=node_creation, catalog_model=catalog
        )

        menu_names = []

        menu_items = []

        def fake_menu_item(label: str, **_kwargs: object) -> None:
            """Capture menu item labels."""
            menu_items.append(label)

        def fake_menu(name: str):
            menu = MagicMock()
            menu.__enter__.return_value = menu
            menu.__exit__.return_value = False
            menu_names.append(name)
            return menu

        background_items = [
            SimpleNamespace(label="BackgroundA", callback=lambda _items, _pos: None),
        ]

        with (
            patch("omni.ui.Menu", side_effect=fake_menu),
            patch("omni.ui.MenuItem", side_effect=fake_menu_item),
            patch("omni.ui.Separator") as separator,
            patch(
                f"{MODULE_ID}.scripts.ui.controllers.interaction.events.get_background_menu_items",
                autospec=True,
                return_value=background_items,
            ),
            patch(
                f"{MODULE_ID}.scripts.ui.controllers.interaction.events.show_menu_at_cursor",
                autospec=True,
            ) as show_menu,
        ):
            controller.on_right_mouse_button_pressed([])

        self.assertIn("Child1", menu_items)
        self.assertIn("Child2", menu_items)
        self.assertIn("TexA", menu_items)
        self.assertIn("LooseTex", menu_items)
        self.assertIn("BackgroundA", menu_items)
        self.assertIn("Nodes", menu_names)
        self.assertIn("Textures", menu_names)
        separator.assert_called_once()
        show_menu.assert_called_once()

    async def test_background_menu_ignores_catalog_filtering(self) -> None:
        """Catalog filtering should not affect right-click menu entries."""
        catalog = _CatalogModel(
            [
                _CatalogGroup("GroupA", [_CatalogChild("Visible"), _CatalogChild("Hidden", filtered=False)]),
                _CatalogGroup("HiddenGroup", [_CatalogChild("Child")], filtered=False),
            ]
        )
        node_creation = _NodeCreation()
        controller = InteractionController(
            widget=MagicMock(), node_creation_controller=node_creation, catalog_model=catalog
        )

        menu = MagicMock()
        menu.__enter__.return_value = menu
        menu.__exit__.return_value = False

        menu_items = []

        def fake_menu_item(label: str, **_kwargs: object) -> None:
            """Capture menu item labels."""
            menu_items.append(label)

        with (
            patch("omni.ui.Menu", return_value=menu),
            patch("omni.ui.MenuItem", side_effect=fake_menu_item),
            patch(
                f"{MODULE_ID}.scripts.ui.controllers.interaction.events.get_background_menu_items",
                autospec=True,
                return_value=[],
            ),
            patch(
                f"{MODULE_ID}.scripts.ui.controllers.interaction.events.show_menu_at_cursor",
                autospec=True,
            ),
        ):
            controller.on_right_mouse_button_pressed([])

        self.assertIn("Visible", menu_items)
        self.assertIn("Hidden", menu_items)
        self.assertIn("Child", menu_items)

    async def test_background_menu_places_shader_with_sub_menu_under_nested_menu(self) -> None:
        """Shader items with sub_menu should appear under that submenu."""
        shader_a = ShaderItem(
            name="ShaderA",
            context="mdl",
            identifier="shader_a",
            sub_menu="Utility",
        )
        shader_b = ShaderItem(
            name="ShaderB",
            context="mdl",
            identifier="shader_b",
            sub_menu="Utility",
        )
        plain = _CatalogChild("PlainChild")
        catalog = _CatalogModel([_CatalogGroup("GroupA", [shader_a, plain, shader_b])])
        controller = InteractionController(
            widget=MagicMock(), node_creation_controller=_NodeCreation(), catalog_model=catalog
        )

        menu_names = []
        menu_items = []

        def fake_menu(name: str):
            menu = MagicMock()
            menu.__enter__.return_value = menu
            menu.__exit__.return_value = False
            menu_names.append(name)
            return menu

        def fake_menu_item(label: str, **_kwargs: object) -> None:
            menu_items.append(label)

        with (
            patch("omni.ui.Menu", side_effect=fake_menu),
            patch("omni.ui.MenuItem", side_effect=fake_menu_item),
            patch(
                f"{MODULE_ID}.scripts.ui.controllers.interaction.events.get_background_menu_items",
                autospec=True,
                return_value=[],
            ),
            patch(
                f"{MODULE_ID}.scripts.ui.controllers.interaction.events.show_menu_at_cursor",
                autospec=True,
            ),
        ):
            controller.on_right_mouse_button_pressed([])

        self.assertIn("GroupA", menu_names)
        self.assertIn("Utility", menu_names)
        self.assertIn("ShaderA", menu_items)
        self.assertIn("ShaderB", menu_items)
        self.assertIn("PlainChild", menu_items)

    async def test_background_menu_shows_when_items_present(self) -> None:
        """Menu should show even when there are hovered items."""
        catalog = _CatalogModel([])
        node_creation = _NodeCreation()
        controller = InteractionController(
            widget=MagicMock(), node_creation_controller=node_creation, catalog_model=catalog
        )

        with patch(
            f"{MODULE_ID}.scripts.ui.controllers.interaction.events.show_menu_at_cursor", autospec=True
        ) as show_menu:
            controller.on_right_mouse_button_pressed([object()])

        show_menu.assert_called_once()

    async def test_background_menu_shows_when_items_present_but_cursor_on_background(self) -> None:
        """Menu should show when items exist but hit-test confirms background click."""
        catalog = _CatalogModel([])
        node_creation = _NodeCreation()
        widget = MagicMock()
        controller = InteractionController(widget=widget, node_creation_controller=node_creation, catalog_model=catalog)

        menu = MagicMock()
        menu.__enter__.return_value = menu
        menu.__exit__.return_value = False

        with (
            patch("omni.ui.Menu", return_value=menu),
            patch("omni.ui.MenuItem"),
            patch(
                f"{MODULE_ID}.scripts.ui.controllers.interaction.events.get_background_menu_items",
                autospec=True,
                return_value=[],
            ),
            patch(
                f"{MODULE_ID}.scripts.ui.controllers.interaction.events.show_menu_at_cursor",
                autospec=True,
            ) as show_menu,
        ):
            controller.on_right_mouse_button_pressed([object()], 100, 100)

        show_menu.assert_called_once()

    async def test_background_menu_shows_when_items_present_and_cursor_over_node(self) -> None:
        """Menu should still show when items are present and pointer is over a node."""
        catalog = _CatalogModel([])
        node_creation = _NodeCreation()
        widget = MagicMock()
        controller = InteractionController(widget=widget, node_creation_controller=node_creation, catalog_model=catalog)

        with patch(
            f"{MODULE_ID}.scripts.ui.controllers.interaction.events.show_menu_at_cursor", autospec=True
        ) as show_menu:
            controller.on_right_mouse_button_pressed([object()], 100, 100)

        show_menu.assert_called_once()

    async def test_background_menu_sorts_sections_and_items_alphabetically(self) -> None:
        """Sections and nested menu items should be alphabetically ordered."""
        texture_group = _CatalogGroup("TextureGroup", [_CatalogChild("TexZ"), _CatalogChild("TexA")])
        setattr(texture_group, "is_texture_group", True)
        nodegraph_group = _CatalogGroup("NodeGraphGroup", [_CatalogChild("NodeGraphZ"), _CatalogChild("NodeGraphA")])
        setattr(nodegraph_group, "is_compound_group", True)
        compound = CompoundItem(
            name="CompoundZ",
            info="",
            icon="",
            tooltip="",
            source_asset="/tmp/c.usda",
            identifier="compound_z",
        )
        catalog = _CatalogModel(
            [
                texture_group,
                _CatalogGroup("GroupB", [_CatalogChild("zeta"), _CatalogChild("alpha")]),
                nodegraph_group,
                _CatalogGroup("GroupA", [_CatalogChild("beta")]),
                compound,
            ]
        )
        controller = InteractionController(
            widget=MagicMock(), node_creation_controller=_NodeCreation(), catalog_model=catalog
        )

        menu_names = []
        menu_items = []

        def fake_menu(name: str):
            menu = MagicMock()
            menu.__enter__.return_value = menu
            menu.__exit__.return_value = False
            menu_names.append(name)
            return menu

        def fake_menu_item(label: str, **_kwargs: object) -> None:
            menu_items.append(label)

        background_items = [
            SimpleNamespace(label="Zulu", callback=lambda _items, _pos: None),
            SimpleNamespace(label="Alpha", callback=lambda _items, _pos: None),
        ]

        with (
            patch("omni.ui.Menu", side_effect=fake_menu),
            patch("omni.ui.MenuItem", side_effect=fake_menu_item),
            patch(
                f"{MODULE_ID}.scripts.ui.controllers.interaction.events.get_background_menu_items",
                autospec=True,
                return_value=background_items,
            ),
            patch(
                f"{MODULE_ID}.scripts.ui.controllers.interaction.events.show_menu_at_cursor",
                autospec=True,
            ),
        ):
            controller.on_right_mouse_button_pressed([])

        self.assertLess(menu_names.index("NodeGraphs"), menu_names.index("Nodes"))
        self.assertLess(menu_names.index("Nodes"), menu_names.index("Textures"))
        self.assertLess(menu_names.index("GroupA"), menu_names.index("GroupB"))
        self.assertLess(menu_items.index("alpha"), menu_items.index("zeta"))
        self.assertLess(menu_items.index("CompoundZ"), menu_items.index("NodeGraphA"))
        self.assertLess(menu_items.index("NodeGraphA"), menu_items.index("NodeGraphZ"))
        self.assertLess(menu_items.index("TexA"), menu_items.index("TexZ"))
        self.assertLess(menu_items.index("Alpha"), menu_items.index("Zulu"))
