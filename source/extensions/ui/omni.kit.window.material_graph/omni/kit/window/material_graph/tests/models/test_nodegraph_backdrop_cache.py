from pxr import Sdf

from ...scripts.models.graph.nodes.backdrop import BackdropModel
from ...scripts.models.graph.nodes.material import MaterialModel
from ...scripts.validation.validator import MaterialValidator
from ..base import MaterialGraphTestBase
from .helpers import DummyPlugin


class TestNodeGraphBackdropCache(MaterialGraphTestBase):
    """Backdrop stacking cache behavior."""

    async def setUp(self) -> None:
        """Load scene and initialize a material model."""
        await super().setUp()
        await self._load_scene("simple.usda")
        self._material_path = Sdf.Path("/World/Looks/material")
        self._plugin = DummyPlugin()
        self._validator = MaterialValidator()

        material_prim = self._get_prim_at_path(self._material_path)
        self._model = MaterialModel(material_prim, "universal", self._usd_context, self._plugin, self._validator)
        self._model.sync()

    async def test_stacking_cache_reuse_and_invalidate(self) -> None:
        """Backdrop stacking cache should reuse signature and invalidate on changes."""
        # This test validates two behaviors in the stacking cache:
        # - a stable signature reuses the cached data
        # - modifying a backdrop changes the signature and invalidates the cache
        self._model._backdrop_stacking_cache["sentinel"] = 1
        signature = self._model._backdrop_stacking_signature

        self._model._compute_backdrop_stacking_cache()
        self.assertEqual(self._model._backdrop_stacking_signature, signature)
        self.assertIn("sentinel", self._model._backdrop_stacking_cache)

        backdrops = [m for m in self._model._children.values() if isinstance(m, BackdropModel)]
        self.assertTrue(backdrops)
        backdrops[0].set_stacking_inputs(position=(999, 999))

        self._model._backdrop_stacking_cache["sentinel"] = 1
        self._model._compute_backdrop_stacking_cache()
        self.assertNotIn("sentinel", self._model._backdrop_stacking_cache)
