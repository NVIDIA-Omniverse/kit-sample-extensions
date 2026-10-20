"""Shared helpers for preferences list-style widgets."""

from typing import Callable, Iterable

# pylint: disable=no-member
import omni.ui

from ..core.constants import BUTTON_WIDTH


def get_list_height(builder, count: int) -> int:
    """Return a bounded list height based on item count."""
    rows = max(builder.list_min_rows, min(builder.list_max_rows, count or 1))
    return rows * builder.row_height + builder.list_padding


def build_path_list(builder, paths: Iterable[str], remove_fn: Callable[[str], None]) -> None:
    """Build a scrollable list of paths."""
    path_list = list(paths)
    list_height = get_list_height(builder, len(path_list))
    with omni.ui.ScrollingFrame(
        height=list_height,
        vertical_scrollbar_policy=omni.ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
        horizontal_scrollbar_policy=omni.ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
    ):
        with omni.ui.VStack(height=0, spacing=builder.item_spacing):
            for path in path_list:
                with omni.ui.HStack(height=builder.row_height):
                    omni.ui.Label(path, height=builder.row_height, width=0)
                    omni.ui.Spacer()
                    omni.ui.Button(
                        "Remove",
                        clicked_fn=lambda p=path: remove_fn(p),
                        height=builder.row_height,
                        width=BUTTON_WIDTH,
                    )
