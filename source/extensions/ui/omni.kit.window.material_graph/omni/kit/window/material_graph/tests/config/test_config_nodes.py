# pylint: disable=relative-beyond-top-level
from ...scripts.config.nodes import Nodes
from ..base import MaterialGraphTestBase


class TestConfigNodes(MaterialGraphTestBase):
    """Nodes config holds color constants and backdrop defaults used by the graph UI. Colors must be
    valid 32-bit ARGB values and backdrop size/color must be well-formed so rendering and layout
    don't break. We test type and range of color constants and structure of backdrop defaults."""

    async def test_color_constants_are_argb_ints(self) -> None:
        """Node color constants are 32-bit integers."""
        values = [
            Nodes.ERROR_BACKGROUND_COLOR,
            Nodes.ERROR_HIGHLIGHT_COLOR,
            Nodes.WARNING_BACKGROUND_COLOR,
            Nodes.WARNING_HIGHLIGHT_COLOR,
            Nodes.WARNING_LABEL_COLOR,
            Nodes.EXPANSION_ON_COLOR_ABGR,
            Nodes.EXPANSION_OFF_COLOR_ABGR,
            Nodes.COMPOUND_BACKGROUND_COLOR_ABGR,
            Nodes.DROP_OVERLAY_ACCEPT_ABGR,
            Nodes.DROP_OVERLAY_REJECT_ABGR,
        ]
        for value in values:
            self.assertIsInstance(value, int)
            self.assertGreaterEqual(value, 0x00000000)
            self.assertLessEqual(value, 0xFFFFFFFF)

    async def test_backdrop_defaults_valid(self) -> None:
        """Backdrop defaults well-formed."""
        size = Nodes.Backdrop.DEFAULT_SIZE
        self.assertEqual(len(size), 2)
        self.assertTrue(all(isinstance(v, (int, float)) for v in size))
        self.assertTrue(all(v > 0 for v in size))
