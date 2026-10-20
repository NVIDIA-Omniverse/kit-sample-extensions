"""Reusable test stubs and fixtures for material graph tests.

This module provides fake implementations used across interaction and UI tests: context manager
and drop-handler context stubs (context_stubs), delegate and frame stubs (delegate_stubs), graph
view stubs (graph_stubs), port and mapping models (port_stubs), and widget stubs (widget_stubs).
We centralize these so that tests can exercise controllers and delegates without starting the
full app or real USD/Omni UI; they also keep expectations consistent (e.g. drop handler tests
all use the same DropHandlerWidget interface). Import from this package when writing new
interaction or UI tests that need a minimal context or graph surface."""

from .context_stubs import DropHandlerContextManager, DummyContextManager  # noqa: F401
from .delegate_stubs import FrameStub, ValidityModel  # noqa: F401
from .graph_stubs import DummyGraphView  # noqa: F401
from .port_stubs import MappingModel, PortModel  # noqa: F401
from .widget_stubs import DropHandlerWidget, DummyWidget  # noqa: F401

__all__ = [
    "DummyContextManager",
    "DummyGraphView",
    "DummyWidget",
    "DropHandlerContextManager",
    "DropHandlerWidget",
    "FrameStub",
    "MappingModel",
    "PortModel",
    "ValidityModel",
]
