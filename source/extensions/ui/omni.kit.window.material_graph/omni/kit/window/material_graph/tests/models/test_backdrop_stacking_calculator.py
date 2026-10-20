# pylint: disable=relative-beyond-top-level,no-member,protected-access
from pxr import Sdf, UsdUI

from ...scripts.models.graph.nodes.backdrop import BackdropModel
from ...scripts.models.graph.nodes.nodegraph.backdrop_stacking import BackdropStackingCalculator
from ..base import MaterialGraphTestBase
from .helpers import DummyPlugin


class TestBackdropStackingCalculator(MaterialGraphTestBase):
    """Tests for backdrop stacking order calculations."""

    async def test_compute_stacking_cache(self) -> None:
        """Backdrop stacking should compute deterministic cache entries."""
        plugin = DummyPlugin()
        prim_a = UsdUI.Backdrop.Define(self._stage, Sdf.Path("/World/BackdropA")).GetPrim()
        prim_b = UsdUI.Backdrop.Define(self._stage, Sdf.Path("/World/BackdropB")).GetPrim()

        model_a = BackdropModel(prim_a, "mdl", self._usd_context, plugin, None, sync=False)
        model_b = BackdropModel(prim_b, "mdl", self._usd_context, plugin, None, sync=False)

        model_a.set_stacking_inputs(position=(0.0, 0.0), size=(10.0, 10.0))
        model_b.set_stacking_inputs(position=(1.0, 1.0), size=(5.0, 5.0))

        calculator = BackdropStackingCalculator()
        cache, signature = calculator.compute([model_a, model_b], {}, None)

        self.assertIn(model_a.prim_path, cache)
        self.assertIn(model_b.prim_path, cache)
        self.assertIsNotNone(signature)

        cache_again, signature_again = calculator.compute([model_a, model_b], cache, signature)
        self.assertIs(cache_again, cache)
        self.assertEqual(signature_again, signature)
