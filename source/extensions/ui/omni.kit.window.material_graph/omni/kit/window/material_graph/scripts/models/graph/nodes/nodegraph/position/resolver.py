"""Helpers for resolving graph UI position wrappers to concrete model items."""

from typing import Optional, Set

from omni.kit.widget.graph import IsolationGraphModel
from pxr import Sdf

from ......config.logging import logger
from ....ports import AttributeModel, InputAttributeModel, OutputAttributeModel
from ...prim.model import PrimModel


class PositionItemResolver:
    """Resolve UI wrapper items into concrete nodegraph position owners."""

    def __init__(self, model: object) -> None:
        """Initialize with the graph model for item resolution."""
        self._model = model

    @staticmethod
    def is_input_output_node_item(item: object) -> bool:
        """Return True when item is an isolation input/output wrapper."""
        if item is None:
            return False
        get_type_name = getattr(type(item), "get_type_name", None)
        if callable(get_type_name):
            try:
                return get_type_name() in ("InputNode", "OutputNode")
            except (
                RuntimeError,
                ValueError,
                TypeError,
                AttributeError,
            ) as exc:  # pylint: disable=broad-exception-caught
                logger.debug("get_type_name check failed: %s", exc)
                return False
        return False

    def resolve_io_attribute_item(self, item: object) -> Optional[object]:
        """Resolve an IO wrapper node to a concrete attribute model item."""
        if not self.is_input_output_node_item(item):
            return None

        target_cls = InputAttributeModel if type(item).get_type_name() == "InputNode" else OutputAttributeModel
        candidates = []
        candidates.extend(getattr(item, "ports", []) or [])
        try:
            item_model = self._model[item]
            candidates.extend(getattr(item_model, "ports", []) or [])
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:  # pylint: disable=broad-exception-caught
            logger.debug("resolve_io_attribute_item model lookup failed: %s", exc)

        visited: Set[int] = set()
        for candidate in candidates:
            resolved = self._resolve_attribute_candidate(candidate, target_cls, visited)
            if resolved is not None:
                return resolved
        return None

    def _resolve_attribute_candidate(self, candidate: object, target_cls: type, visited: Set[int]) -> Optional[object]:
        """Recursively resolve group/wrapper candidates to a leaf attribute model."""
        if candidate is None:
            return None

        candidate_id = id(candidate)
        if candidate_id in visited:
            return None
        visited.add(candidate_id)

        if isinstance(candidate, target_cls):
            return candidate
        if isinstance(candidate, IsolationGraphModel.EmptyPort):
            return None

        source = getattr(candidate, "source", None)
        resolved = self._resolve_attribute_candidate(source, target_cls, visited)
        if resolved is not None:
            return resolved

        prim_model = getattr(candidate, "prim_model", None)
        resolved = self._resolve_attribute_candidate(prim_model, target_cls, visited)
        if resolved is not None:
            return resolved

        path = getattr(candidate, "path", None)
        if isinstance(path, Sdf.Path):
            resolved_item = self._model.get_item_model(path)
            resolved = self._resolve_attribute_candidate(resolved_item, target_cls, visited)
            if resolved is not None:
                return resolved

        get_path = getattr(candidate, "GetPath", None)
        if callable(get_path):
            try:
                resolved_item = self._model.get_item_model(get_path())
            except (
                RuntimeError,
                ValueError,
                TypeError,
                AttributeError,
            ) as exc:  # pylint: disable=broad-exception-caught
                logger.debug("resolve_io_attribute_item GetPath lookup failed: %s", exc)
                resolved_item = None
            resolved = self._resolve_attribute_candidate(resolved_item, target_cls, visited)
            if resolved is not None:
                return resolved

        for child in getattr(candidate, "ports", None) or []:
            resolved = self._resolve_attribute_candidate(child, target_cls, visited)
            if resolved is not None:
                return resolved
        return None

    def normalize_moving_item(self, item: object) -> Optional[object]:
        """Return a concrete movable item for batch movement operations."""
        if item is None or isinstance(item, (PrimModel, AttributeModel)):
            return item
        is_io_wrapper = self.is_input_output_node_item(item)
        if is_io_wrapper:
            # Keep IO node wrappers as move units regardless of grouped-port
            # structure. Resolving to leaf attributes causes unstable drag
            # behavior when IO ports are grouped.
            return item
        resolved_io = self.resolve_io_attribute_item(item)
        if resolved_io is not None:
            return resolved_io
        prim_model = getattr(item, "prim_model", None)
        if isinstance(prim_model, (PrimModel, AttributeModel)):
            return prim_model
        source = getattr(item, "source", None)
        if isinstance(source, (PrimModel, AttributeModel)):
            return source
        try:
            proxy = self._model[item]
            if isinstance(proxy, (PrimModel, AttributeModel)):
                return proxy
            proxy_source = getattr(proxy, "source", None)
            if isinstance(proxy_source, (PrimModel, AttributeModel)):
                return proxy_source
            proxy_model = getattr(proxy, "prim_model", None)
            if isinstance(proxy_model, (PrimModel, AttributeModel)):
                return proxy_model
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:  # pylint: disable=broad-exception-caught
            logger.debug("normalize_moving_item proxy resolution failed: %s", exc)
        prim_path = getattr(item, "prim_path", None)
        if prim_path is not None:
            resolved_by_prim = self._model.get_item_model(prim_path)
            if isinstance(resolved_by_prim, (PrimModel, AttributeModel)):
                return resolved_by_prim
        path = getattr(item, "path", None)
        if path is not None:
            resolved_by_path = self._model.get_item_model(path)
            if isinstance(resolved_by_path, (PrimModel, AttributeModel)):
                return resolved_by_path
        resolved = self._model.get_item_model(item)
        if isinstance(resolved, (PrimModel, AttributeModel)):
            return resolved
        return item

    def resolve_concrete_position_item(self, item: object) -> Optional[object]:
        """Resolve wrappers/proxies to a concrete PrimModel/AttributeModel item."""
        concrete = self.normalize_moving_item(item)
        if isinstance(concrete, (PrimModel, AttributeModel)):
            return concrete
        if self.is_input_output_node_item(concrete):
            return concrete
        if concrete is not None:
            resolved = self._model.get_item_model(concrete)
            if isinstance(resolved, (PrimModel, AttributeModel)):
                return resolved
        return None
