"""Context menu registry implementation and callback lifecycle helpers."""

import functools
import inspect
import threading
import weakref
from typing import Dict, Iterable, List, Optional, Set, Tuple, Union

import carb.settings

from ...config.logging import logger
from .types import Callback, ContextMenuItem, OriginalCallback, WeakOwnerRef, normalize_node_types


def _should_log_warnings() -> bool:
    """Return True when warnings should be emitted in the current runtime."""
    settings = carb.settings.get_settings()
    return not bool(settings.get("/app/isTestRun")) if settings else True


def _should_log_info() -> bool:
    """Return True when info logs should be emitted in the current runtime."""
    settings = carb.settings.get_settings()
    return not bool(settings.get("/app/isTestRun")) if settings else True


def _normalize_node_types(node_types: Optional[Union[str, Iterable[str]]]) -> Optional[Set[str]]:
    """Normalize node types and log invalid user inputs."""
    normalized = normalize_node_types(node_types)
    if node_types is not None and normalized is None:
        if _should_log_warnings():
            logger.warning(
                "context menu registration rejected invalid node_types value=%r type=%s; expected str or iterable of str",
                node_types,
                type(node_types).__name__,
            )
    return normalized


def _describe_callback(callback: object) -> str:
    """Return a stable, user-actionable callback name for diagnostics."""
    target = callback.func if isinstance(callback, functools.partial) else callback
    module = getattr(target, "__module__", None)
    name = getattr(target, "__qualname__", None) or getattr(target, "__name__", None)
    if module and name:
        return f"{module}.{name}"
    return f"{type(callback).__module__}.{type(callback).__qualname__}"


def _is_callback_compatible(callback: Callback, min_positional_args: int) -> bool:
    """Return True when a callback can accept the expected args."""
    if not callable(callback):
        return False
    try:
        signature = inspect.signature(callback)
    except (TypeError, ValueError):
        return False

    try:
        signature.bind(*([object()] * min_positional_args))
        return True
    except TypeError:
        return False


def _resolve_original_callback(item: ContextMenuItem) -> Optional[Callback]:
    """Return the original callback if it is still alive."""
    original = item.original_callback
    if isinstance(original, weakref.ReferenceType):
        return original()
    if isinstance(original, tuple):
        if len(original) == 3:
            weak_method, args, kwargs = original
            target = weak_method() if isinstance(weak_method, weakref.ReferenceType) else None
            if not target:
                return None
            return functools.partial(target, *args, **kwargs)
        if len(original) == 4:
            owner_ref, method, args, kwargs = original
            target = owner_ref() if isinstance(owner_ref, weakref.ReferenceType) else None
            if not target:
                return None
            return functools.partial(method, target, *args, **kwargs)
    return original


def _matches_partial_weak_method(
    callback: functools.partial, weak_method: object, args: Tuple[object, ...], kwargs: Dict[str, object]
) -> bool:
    """Match callback against partial metadata stored as weak method tuple."""
    target = weak_method() if isinstance(weak_method, weakref.ReferenceType) else None
    return target == callback.func and args == callback.args and (kwargs or {}) == (callback.keywords or {})


def _matches_partial_bound_meta(
    callback: functools.partial,
    owner_ref: object,
    method: Callback,
    args: Tuple[object, ...],
    kwargs: Dict[str, object],
) -> bool:
    """Match callback against partial metadata stored as owner+method tuple."""
    target = owner_ref() if isinstance(owner_ref, weakref.ReferenceType) else None
    callback_self = callback.func.__self__ if inspect.ismethod(callback.func) else None
    callback_func = callback.func.__func__ if inspect.ismethod(callback.func) else None
    if (
        target == callback_self
        and method == callback_func
        and args == callback.args
        and (kwargs or {}) == (callback.keywords or {})
    ):
        return True
    try:
        proxy_meta = vars(callback.func).get("__material_graph_partial__", None)
    except TypeError:
        proxy_meta = None
    if not proxy_meta:
        return False
    proxy_owner_ref, proxy_method = proxy_meta
    proxy_target = proxy_owner_ref() if isinstance(proxy_owner_ref, weakref.ReferenceType) else None
    return (
        proxy_target == target
        and proxy_method == method
        and args == callback.args
        and (kwargs or {}) == (callback.keywords or {})
    )


def _matches_partial_metadata(callback: Callback, original_callback: OriginalCallback) -> bool:
    """Match callback against stored original_callback partial metadata."""
    if not isinstance(callback, functools.partial) or not isinstance(original_callback, tuple):
        return False
    if len(original_callback) == 3:
        weak_method, args, kwargs = original_callback
        return _matches_partial_weak_method(callback, weak_method, args, kwargs)
    if len(original_callback) == 4:
        owner_ref, method, args, kwargs = original_callback
        return _matches_partial_bound_meta(callback, owner_ref, method, args, kwargs)
    return False


def _has_matching_item(items: List[ContextMenuItem], label: str, callback: Callback) -> bool:
    """Return True if a label/callback pair is already registered."""
    for item in items:
        if item.label != label:
            continue
        resolved = _resolve_original_callback(item)
        if resolved == callback:
            return True
        if _matches_partial_metadata(callback, item.original_callback):
            return True
    return False


def _item_matches_callback(item: ContextMenuItem, callback: Callback) -> bool:
    """Return True for direct callbacks and reconstructed equivalent partials."""
    return _resolve_original_callback(item) == callback or _matches_partial_metadata(callback, item.original_callback)


def _get_bound_method(callback: Callback) -> Optional[Callback]:
    """Return a bound method if the callback is bound, otherwise None."""
    if inspect.ismethod(callback) and callback.__self__ is not None:
        return callback
    return None


def _weaken_partial_callback(callback: functools.partial, owner_ref: WeakOwnerRef, method: Callback) -> bool:
    """Reduce strong references held by a functools.partial to its owner."""
    try:
        if vars(callback).get("__material_graph_weakened__", False):
            return True
    except TypeError:
        pass

    owner = owner_ref()
    if not owner:
        return False

    try:
        proxy = weakref.proxy(owner)
    except TypeError:
        proxy = owner

    try:
        callback.func = method
        callback.args = (proxy,) + tuple(callback.args)
        callback.__material_graph_weakened__ = True
        return True
    except (AttributeError, TypeError) as exc:
        logger.debug("partial callback rewrite skipped: %s", exc)

    def _proxy(*args, **kwargs):
        """Invoke underlying bound method while resolving owner weakref."""
        target = owner_ref()
        if not target:
            if _should_log_warnings():
                logger.warning(
                    "context menu callback '%s' was skipped because its owning object no longer exists",
                    _describe_callback(method),
                )
            return None
        return method(target, *args, **kwargs)

    try:
        _proxy.__material_graph_partial__ = (owner_ref, method)
        callback.func = _proxy
    except (AttributeError, TypeError) as exc:
        logger.debug("partial callback proxy install failed: %s", exc)
        return False
    return True


def _wrap_callback(callback: Callback) -> Callback:
    """Wrap callbacks so bound methods are held via weak references."""
    bound_method = _get_bound_method(callback)
    if bound_method:
        weak_method = weakref.WeakMethod(bound_method)
        callback_name = _describe_callback(bound_method)

        def _wrapped(*args, **kwargs):
            """Invoke wrapped bound-method callback when target is alive."""
            target = weak_method()
            if not target:
                if _should_log_warnings():
                    logger.warning(
                        "context menu callback '%s' was skipped because its owning object no longer exists",
                        callback_name,
                    )
                return None
            return target(*args, **kwargs)

        _wrapped.__material_graph_weakref__ = weak_method
        return _wrapped
    if isinstance(callback, functools.partial):
        func = callback.func
        bound_method = _get_bound_method(func)
        if bound_method:
            owner = bound_method.__self__
            method = bound_method.__func__
            owner_ref = weakref.ref(owner)
            callback_name = _describe_callback(method)
            _weaken_partial_callback(callback, owner_ref, method)
            args = callback.args
            kwargs = callback.keywords or {}

            def _wrapped(*call_args, **call_kwargs):
                """Invoke wrapped partial callback with merged arguments."""
                target = owner_ref()
                if not target:
                    if _should_log_warnings():
                        logger.warning(
                            "context menu callback '%s' was skipped because its owning object no longer exists",
                            callback_name,
                        )
                    return None
                merged_kwargs = dict(kwargs)
                merged_kwargs.update(call_kwargs)
                return method(target, *args, *call_args, **merged_kwargs)

            _wrapped.__material_graph_weakref__ = owner_ref
            _wrapped.__material_graph_partial__ = (owner_ref, method, args, kwargs)
            return _wrapped
    return callback


def _is_callback_alive(callback: Callback) -> bool:
    """Return True if a weakly wrapped callback still has a live target."""
    try:
        weak_method = vars(callback).get("__material_graph_weakref__", None)
    except TypeError:
        weak_method = None
    if weak_method is None:
        return True
    return weak_method() is not None


class ContextMenuRegistry:
    """Registry for context menu items with thread-safe access."""

    def __init__(self) -> None:
        """Initialize empty node/background registries and synchronization lock."""
        self._node_menu_items: List[ContextMenuItem] = []
        self._background_menu_items: List[ContextMenuItem] = []
        self._lock = threading.Lock()

    def _prune_dead_items(self) -> None:
        """Remove entries whose weak callback targets are no longer alive."""
        before_nodes = len(self._node_menu_items)
        before_background = len(self._background_menu_items)
        self._node_menu_items = [item for item in self._node_menu_items if _is_callback_alive(item.callback)]
        self._background_menu_items = [
            item for item in self._background_menu_items if _is_callback_alive(item.callback)
        ]
        if _should_log_info():
            if before_nodes != len(self._node_menu_items) or before_background != len(self._background_menu_items):
                logger.info("context menu registry pruned dead callbacks")

    def add_node_menu_item(
        self,
        label: str,
        callback: Callback,
        node_types: Optional[Union[str, Iterable[str]]] = None,
    ) -> bool:
        """Register an item for the node context menu. node_types=None means all nodes."""
        if not _is_callback_compatible(callback, 2):
            if _should_log_warnings():
                logger.warning(
                    "node menu item '%s' was not registered: callback '%s' must accept (node_type, prim_path)",
                    label,
                    _describe_callback(callback),
                )
            return False
        with self._lock:
            self._prune_dead_items()
            if _has_matching_item(self._node_menu_items, label, callback):
                if _should_log_warnings():
                    logger.warning("node menu item already registered: %s", label)
                return False
            wrapped = _wrap_callback(callback)
            wrapped_meta = vars(wrapped).get("__material_graph_partial__", None)
            if isinstance(callback, functools.partial) and wrapped_meta is not None:
                original_ref = wrapped_meta
            else:
                original_ref = weakref.WeakMethod(callback) if inspect.ismethod(callback) else callback
            self._node_menu_items.append(
                ContextMenuItem(label, wrapped, _normalize_node_types(node_types), original_callback=original_ref)
            )
        if _should_log_info():
            logger.info("node menu item registered: %s", label)
        return True

    def remove_node_menu_item(
        self,
        label: str,
        callback: Optional[Callback] = None,
    ) -> None:
        """Unregister node menu items by label (and optionally callback)."""
        with self._lock:
            self._prune_dead_items()
            if callback is None:
                self._node_menu_items = [i for i in self._node_menu_items if i.label != label]
            else:
                self._node_menu_items = [
                    i for i in self._node_menu_items if not (i.label == label and _item_matches_callback(i, callback))
                ]
        if _should_log_info():
            logger.info("node menu item deregistered: %s", label)

    def add_background_menu_item(
        self,
        label: str,
        callback: Callback,
    ) -> bool:
        """Register an item for the background context menu."""
        if not _is_callback_compatible(callback, 2):
            if _should_log_warnings():
                logger.warning(
                    "background menu item '%s' was not registered: callback '%s' must accept "
                    "(items, mouse_position)",
                    label,
                    _describe_callback(callback),
                )
            return False
        with self._lock:
            self._prune_dead_items()
            if _has_matching_item(self._background_menu_items, label, callback):
                if _should_log_warnings():
                    logger.warning("background menu item already registered: %s", label)
                return False
            wrapped = _wrap_callback(callback)
            wrapped_meta = vars(wrapped).get("__material_graph_partial__", None)
            if isinstance(callback, functools.partial) and wrapped_meta is not None:
                original_ref = wrapped_meta
            else:
                original_ref = weakref.WeakMethod(callback) if inspect.ismethod(callback) else callback
            self._background_menu_items.append(ContextMenuItem(label, wrapped, None, original_callback=original_ref))
        if _should_log_info():
            logger.info("background menu item registered: %s", label)
        return True

    def remove_background_menu_item(
        self,
        label: str,
        callback: Optional[Callback] = None,
    ) -> None:
        """Unregister background menu items by label (and optionally callback)."""
        with self._lock:
            self._prune_dead_items()
            if callback is None:
                self._background_menu_items = [i for i in self._background_menu_items if i.label != label]
            else:
                self._background_menu_items = [
                    i
                    for i in self._background_menu_items
                    if not (i.label == label and _item_matches_callback(i, callback))
                ]
        if _should_log_info():
            logger.info("background menu item deregistered: %s", label)

    def get_node_menu_items(self, node_type: Optional[str]) -> List[ContextMenuItem]:
        """Return node menu items applicable to the node type."""
        if node_type is None:
            return []
        items: List[ContextMenuItem] = []
        with self._lock:
            self._prune_dead_items()
            for item in self._node_menu_items:
                if item.node_types is None or node_type in item.node_types:
                    items.append(ContextMenuItem(item.label, item.callback, item.node_types, item.original_callback))
        return list(items)

    def get_background_menu_items(self) -> List[ContextMenuItem]:
        """Return a snapshot of registered background menu items."""
        with self._lock:
            self._prune_dead_items()
            return [
                ContextMenuItem(item.label, item.callback, item.node_types, item.original_callback)
                for item in self._background_menu_items
            ]

    def clear_node_menu_items(self) -> None:
        """Clear all node menu items."""
        with self._lock:
            self._node_menu_items = []
        if _should_log_info():
            logger.info("cleared node menu items")

    def clear_background_menu_items(self) -> None:
        """Clear all background menu items."""
        with self._lock:
            self._background_menu_items = []
        if _should_log_info():
            logger.info("cleared background menu items")
