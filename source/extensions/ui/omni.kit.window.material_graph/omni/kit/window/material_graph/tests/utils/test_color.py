import omni.kit.test

from ...scripts.config.color import rgb_to_abgr, tuple_to_abgr


class TestColorUtils(omni.kit.test.AsyncTestCase):
    """Color helpers convert RGB to ABGR for the graph UI. We test integer and tuple inputs,
    normalization of values outside 0–1, and invalid tuples returning transparent."""

    async def test_rgb_to_abgr(self) -> None:
        """RGB int maps to ABGR."""
        self.assertEqual(rgb_to_abgr(0x112233), 0xFF332211)

    async def test_tuple_to_abgr(self) -> None:
        """RGB tuple maps to ABGR with normalization."""
        self.assertEqual(tuple_to_abgr((1.0, 0.0, 0.0)), 0xFF0000FF)
        self.assertEqual(tuple_to_abgr((2.0, 0.0, 0.0)), 0xFF0000FF)
        self.assertEqual(tuple_to_abgr((0.0, 0.0, 0.0)), 0xFF000000)

    async def test_tuple_to_abgr_invalid(self) -> None:
        """Invalid tuple returns transparent."""
        self.assertEqual(tuple_to_abgr(()), 0x00000000)
        self.assertEqual(tuple_to_abgr((1.0,)), 0x00000000)
