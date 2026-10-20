from .test_titlebar import WindowModifierTestCase


class TestWithRegionChanged(WindowModifierTestCase):
    async def setUp(self):
        await super().setUp(True)
