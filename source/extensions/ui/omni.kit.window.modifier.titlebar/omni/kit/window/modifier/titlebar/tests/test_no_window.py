import sys

from .test_titlebar import WindowModifierTestCase


class TestNoWindowChanged(WindowModifierTestCase):
    async def setUp(self):
        self._need_restore = False
        if "--no-window" not in sys.argv:
            sys.argv.append("--no-window")
            self._need_restore = True

        await super().setUp(True)

    async def tearDown(self):
        await super().tearDown()
        if self._need_restore:
            sys.argv.remove("--no-window")
