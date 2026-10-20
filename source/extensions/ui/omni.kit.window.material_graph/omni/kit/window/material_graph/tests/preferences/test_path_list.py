# pylint: disable=relative-beyond-top-level
from unittest.mock import MagicMock, patch

from ...scripts.preferences.ui import lists as path_list
from ...scripts.preferences.ui.lists import build_path_list, get_list_height
from ..base import MaterialGraphTestBase


class _DummyBuilder:
    """Simple builder stub for list sizing tests."""

    def __init__(self, min_rows=1, max_rows=5, row_height=10, padding=4, spacing=2):
        self.list_min_rows = min_rows
        self.list_max_rows = max_rows
        self.row_height = row_height
        self.list_padding = padding
        self.item_spacing = spacing


class _DummyFrame:
    """Context manager for UI frame stubs."""

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class TestPathList(MaterialGraphTestBase):
    """Direct tests for path_list helpers."""

    async def test_get_list_height_mid_range(self) -> None:
        """List height should scale between min and max rows."""
        builder = _DummyBuilder(min_rows=1, max_rows=5, row_height=10, padding=4)
        self.assertEqual(get_list_height(builder, 3), 34)

    async def test_get_list_height_empty_uses_min_rows(self) -> None:
        """Empty lists should still use the min row height."""
        builder = _DummyBuilder(min_rows=2, max_rows=6, row_height=10, padding=4)
        self.assertEqual(get_list_height(builder, 0), 24)

    async def test_get_list_height_caps_at_max_rows(self) -> None:
        """List height should cap at the max row count."""
        builder = _DummyBuilder(min_rows=1, max_rows=3, row_height=10, padding=4)
        self.assertEqual(get_list_height(builder, 10), 34)

    async def test_build_path_list_uses_bounded_height(self) -> None:
        """Path list should create a scrolling frame with bounded height."""
        builder = _DummyBuilder(min_rows=2, max_rows=3, row_height=10, padding=4)
        frame_instances = []

        def _frame_factory(**kwargs):
            frame = _DummyFrame(**kwargs)
            frame_instances.append(frame)
            return frame

        with (
            patch.object(path_list.omni.ui, "ScrollingFrame", side_effect=_frame_factory),
            patch.object(path_list.omni.ui, "VStack", side_effect=_frame_factory),
            patch.object(path_list.omni.ui, "HStack", side_effect=_frame_factory),
            patch.object(path_list.omni.ui, "Label", MagicMock()),
            patch.object(path_list.omni.ui, "Spacer", MagicMock()),
            patch.object(path_list.omni.ui, "Button", MagicMock()),
        ):
            build_path_list(builder, ["a", "b", "c", "d"], lambda _p: None)

        self.assertTrue(frame_instances)
        expected_height = get_list_height(builder, 4)
        self.assertEqual(frame_instances[0].kwargs.get("height"), expected_height)
