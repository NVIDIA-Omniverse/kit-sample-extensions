from types import SimpleNamespace
from unittest.mock import MagicMock


class FrameStub:
    """Frame context-manager stub used by delegate tests."""

    def __init__(self):
        self.set_style = MagicMock()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class ValidityModel:
    """Model stub exposing a node with a valid flag."""

    def __init__(self, valid: bool):
        self._node = SimpleNamespace(valid=valid)

    def __getitem__(self, _key):
        return self._node
