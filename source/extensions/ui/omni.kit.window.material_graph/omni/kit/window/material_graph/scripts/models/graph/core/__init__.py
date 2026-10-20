"""Core graph-model foundations and shared types.

This package provides the base model class (GraphModelBase), proxy item
mixin (ProxyItemMixin), and model state (ModelState) used by all graph
model layers. These types define the common interface for stage-backed
graph models.

Architectural role: Core graph types are foundational; prim, attribute,
and isolation models build on GraphModelBase and use ModelState for
shared state.

Typical consumers: PrimModel, AttributeModel, MaterialGraphIsolationModel,
and graph widget integration.
"""

from .base import GraphModelBase
from .proxy_item_mixin import ProxyItemMixin
from .state import ModelState

__all__ = [
    "GraphModelBase",
    "ModelState",
    "ProxyItemMixin",
]
