from unittest.mock import patch

from ...scripts.config.paths import Paths
from ...scripts.models.graph.ports.internal.connections import AttributeConnections
from ..base import MaterialGraphTestBase


class _DummyModelRoot:
    def __init__(self, mapping):
        self._mapping = mapping

    def get_item_model(self, item):
        return self._mapping.get(item)


class _DummyModel:
    def __init__(self, mapping, can_connect_result):
        self.model_root = _DummyModelRoot(mapping)
        self.path = "/World/Looks/Mat/out"
        self.context_name = "universal"
        self._plugin = object()
        self.validator = _DummyValidator(can_connect_result)


class _DummyValidator:
    def __init__(self, can_connect_result):
        self._can_connect_result = can_connect_result

    def can_connect(self, _context_name, _plugin, _source_model, _target_model):
        return self._can_connect_result

    def would_create_cycle(self, _source_model, _target_model):
        return False


class _DummySourceModel:
    def __init__(self, can_connect_result):
        self.path = "/World/Looks/Mat/in"
        self._can_connect_result = can_connect_result


class TestAttributeConnectionsRejectionLogic(MaterialGraphTestBase):
    """Regression coverage for `_should_reject_sources` compatibility filtering.

    These tests isolate the pre-connect validation path used by
    `AttributeConnections.set_inputs()` to decide whether a source list should
    be rejected before opening an undo group or creating ports.

    Why this matters:
    - A prior inversion bug allowed incompatible sources and rejected compatible
      ones, which breaks connect behavior and downstream variability handling.
    - This helper is intentionally small but high-impact, so direct unit tests
      protect against future semantic regressions without needing full USD stage
      setup.
    - We assert both branches explicitly: incompatible sources are rejected,
      compatible sources are accepted.
    """

    async def test_should_reject_sources_only_for_incompatible_sources(self):
        source_model = _DummySourceModel(can_connect_result=False)
        model = _DummyModel({"src": source_model}, can_connect_result=False)
        connections = AttributeConnections(model, _DummySourceModel)
        self.assertTrue(connections._should_reject_sources(["src"], model))

    async def test_should_not_reject_sources_when_compatible(self):
        source_model = _DummySourceModel(can_connect_result=True)
        model = _DummyModel({"src": source_model}, can_connect_result=True)
        connections = AttributeConnections(model, _DummySourceModel)
        self.assertFalse(connections._should_reject_sources(["src"], model))

    async def test_should_not_reject_sources_when_force_modifier_pressed(self):
        source_model = _DummySourceModel(can_connect_result=False)
        model = _DummyModel({"src": source_model}, can_connect_result=False)
        connections = AttributeConnections(model, _DummySourceModel)

        with patch(
            f"{Paths.MODULE_ID}.scripts.models.graph.ports.internal.connections.is_force_connection_modifier_pressed",
            autospec=True,
            return_value=True,
        ):
            self.assertFalse(connections._should_reject_sources(["src"], model))
