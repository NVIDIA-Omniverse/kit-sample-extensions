import omni.kit.test

from .test_mixin import MaterialGraphTestMixin


class MaterialGraphTestBase(MaterialGraphTestMixin, omni.kit.test.AsyncTestCase):
    """Base class for Material Graph tests with a fresh stage."""

    async def setUp(self) -> None:
        """Set up a fresh USD stage for tests."""
        await self._setup_common(create_stage=True)

    async def tearDown(self) -> None:
        """Tear down common test resources."""
        await self._teardown_common()
