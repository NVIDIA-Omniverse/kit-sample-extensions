from unittest.mock import MagicMock, patch

from omni.kit.widget.graph import IsolationGraphModel
from pxr import Sdf, UsdShade

from ...scripts.ui.controllers.interaction.events import InteractionController

# pylint: disable=relative-beyond-top-level,no-member
from ..base import MaterialGraphTestBase


class _FakeNodeModel:
    """Node model stub with a fixed type."""

    def __init__(self, node_type: object) -> None:
        """Initialize with a node type."""
        self.type = node_type


class _FakePortModel:
    """Port model stub indicating a placeholder port."""

    def __init__(self) -> None:
        """Initialize the placeholder flag."""
        self.placeholder = True


class _FakeIONodeModel:
    """I/O node stub used for double-click tests."""

    def remove_input(self) -> None:
        """No-op input removal."""
        return None


class _RawIONodeItem:
    """Raw IO node wrapper stub with type-name API."""

    @staticmethod
    def get_type_name() -> str:
        """Return IO node type token."""
        return IsolationGraphModel.InputNode.get_type_name()


class _FakeModel:
    """Graph model stub that maps items to models."""

    def __init__(self, mapping: dict) -> None:
        """Initialize with a mapping of item to model."""
        self._mapping = mapping

    def get_item_model(self, item: object) -> object | None:
        """Return a mapped model for a given item."""
        return self._mapping.get(item)


class TestInteractionDoubleClick(MaterialGraphTestBase):
    async def test_double_click_nodegraph_body_opens_compound(self) -> None:
        """Double-clicking one NodeGraph body should navigate into that graph."""
        widget = MagicMock()
        node_path = Sdf.Path("/Looks/Graph")
        widget.model = _FakeModel({node_path: _FakeNodeModel(UsdShade.NodeGraph)})
        widget.is_mouse_over_node_header.return_value = False

        controller = InteractionController(
            widget=widget, node_creation_controller=MagicMock(), catalog_model=MagicMock()
        )
        controller.on_left_mouse_button_double_clicked([node_path])

        widget.set_current_compound.assert_called_once_with(node_path)

    async def test_double_click_nodegraph_header_does_not_open(self) -> None:
        """Header double-clicks are reserved for inline editing, not graph navigation."""
        widget = MagicMock()
        node_path = Sdf.Path("/Looks/Graph")
        widget.model = _FakeModel({node_path: _FakeNodeModel(UsdShade.NodeGraph)})
        widget.is_mouse_over_node_header.return_value = True

        controller = InteractionController(
            widget=widget, node_creation_controller=MagicMock(), catalog_model=MagicMock()
        )
        controller.on_left_mouse_button_double_clicked([node_path])

        widget.set_current_compound.assert_not_called()

    async def test_double_click_unexpected_failure_is_logged_and_contained(self) -> None:
        """UI event failures should not propagate back into Kit's callback dispatcher."""
        widget = MagicMock()
        widget.current_context = "mdl"
        widget.model.get_item_model.side_effect = OSError("model unavailable")
        controller = InteractionController(
            widget=widget, node_creation_controller=MagicMock(), catalog_model=MagicMock()
        )

        with patch(
            "omni.kit.window.material_graph.scripts.ui.controllers.interaction.events.log_exception"
        ) as log_failure:
            controller.on_left_mouse_button_double_clicked([object()])

        log_failure.assert_called_once()
        self.assertIsInstance(log_failure.call_args.kwargs["exc"], OSError)

    async def test_double_click_property_path_does_not_open(self) -> None:
        """Double-clicking a property path should not open a graph."""
        widget = MagicMock()
        prop_path = Sdf.Path("/Looks/Mat.inputs:diffuse")
        widget.model = _FakeModel({prop_path: _FakePortModel()})
        widget.is_mouse_over_node_header.return_value = False

        controller = InteractionController(
            widget=widget, node_creation_controller=MagicMock(), catalog_model=MagicMock()
        )
        controller.on_left_mouse_button_double_clicked([prop_path])

        widget.set_current_compound.assert_not_called()

    async def test_double_click_mixed_property_path_does_not_open(self) -> None:
        """Property-path hits should prevent graph-level navigation."""
        widget = MagicMock()
        prop_path = Sdf.Path("/Looks/Mat.inputs:diffuse")
        node_path = Sdf.Path("/Looks/Graph")
        widget.model = _FakeModel(
            {
                prop_path: _FakePortModel(),
                node_path: _FakeNodeModel(UsdShade.NodeGraph),
            }
        )
        widget.is_mouse_over_node_header.return_value = False

        controller = InteractionController(
            widget=widget, node_creation_controller=MagicMock(), catalog_model=MagicMock()
        )
        controller.on_left_mouse_button_double_clicked([prop_path, node_path])

        widget.set_current_compound.assert_not_called()

    async def test_double_click_input_output_node_does_not_open(self) -> None:
        """Double-clicking input/output nodes should not open a graph."""
        widget = MagicMock()
        node_path = Sdf.Path("/Looks/IO")
        widget.model = _FakeModel({node_path: _FakeIONodeModel()})
        widget.is_mouse_over_node_header.return_value = False

        controller = InteractionController(
            widget=widget, node_creation_controller=MagicMock(), catalog_model=MagicMock()
        )
        controller.on_left_mouse_button_double_clicked([node_path])

        widget.set_current_compound.assert_not_called()

    async def test_double_click_raw_io_item_does_not_open(self) -> None:
        """Raw IO wrapper items should block graph-level navigation."""
        widget = MagicMock()
        item = _RawIONodeItem()
        widget.model = _FakeModel({})
        widget.is_mouse_over_node_header.return_value = False

        controller = InteractionController(
            widget=widget, node_creation_controller=MagicMock(), catalog_model=MagicMock()
        )
        controller.on_left_mouse_button_double_clicked([item])

        widget.set_current_compound.assert_not_called()
