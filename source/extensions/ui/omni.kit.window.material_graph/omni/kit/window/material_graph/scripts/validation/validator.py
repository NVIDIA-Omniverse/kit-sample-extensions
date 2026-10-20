"""Material validation service with subscriptions and compatibility cache."""

from typing import Callable, Optional

from pxr import Usd

from ..config.logging import logger
from ..models.graph.ports.internal.validation import would_create_cycle as would_create_prim_cycle
from ..settings.settings import Settings
from .pipeline import validate_material_context
from .result import ValidationResult

ValidatorCallback = Callable[..., None]
CanConnectCacheKey = tuple


class MaterialValidator:
    """Coordinates validation execution, events, and compatibility caching."""

    def __init__(self) -> None:
        """Initialize callback subscriptions and cache containers."""
        self._callbacks: dict[str, dict[int, ValidatorCallback]] = {
            "started": {},
            "finished": {},
            "state_changed": {},
        }
        self._next_callback_id = 1
        self._last_results: dict[str, ValidationResult] = {}
        self._can_connect_cache: dict[CanConnectCacheKey, bool] = {}
        self._root_path: Optional[str] = None

    def subscribe(self, event_name: str, callback: ValidatorCallback) -> int:
        """Subscribe to validator events and return a subscription id."""
        if event_name not in self._callbacks:
            raise ValueError(f"unknown validator event '{event_name}'")
        sub_id = self._next_callback_id
        self._next_callback_id += 1
        self._callbacks[event_name][sub_id] = callback
        return sub_id

    def unsubscribe(self, sub_id: int) -> None:
        """Unsubscribe a previously registered callback id."""
        for callbacks in self._callbacks.values():
            callbacks.pop(sub_id, None)

    def set_root_prim(self, root_prim: Optional[Usd.Prim]) -> None:
        """Reset caches when the active material root changes."""
        path = str(root_prim.GetPath()) if root_prim and root_prim.IsValid() else None
        if path == self._root_path:
            return
        self._root_path = path
        self._can_connect_cache.clear()
        self._last_results = {}

    def _can_connect_proxy(
        self,
        context_name: str,
        plugin: object,
        source_proxy: object,
        target_proxy: object,
    ) -> bool:
        """Return cached proxy compatibility for validation pipeline checks."""
        key = (
            context_name,
            str(id(plugin)),
            str(source_proxy.type_name),
            str(target_proxy.type_name),
            f"{source_proxy.render_type}->{target_proxy.render_type}",
            f"{getattr(source_proxy, 'variability', '')}->{getattr(target_proxy, 'variability', '')}",
            f"{getattr(source_proxy, 'connectability', '')}->{getattr(target_proxy, 'connectability', '')}",
            f"{getattr(source_proxy, 'owner_is_interface', False)}"
            f"->{getattr(target_proxy, 'owner_is_interface', False)}",
            Settings.get_force_connect(),
        )
        cached = self._can_connect_cache.get(key)
        if cached is not None:
            return cached
        allowed = bool(plugin.can_connect(_ProxyModelAdapter(source_proxy), _ProxyModelAdapter(target_proxy)))
        self._can_connect_cache[key] = allowed
        return allowed

    @staticmethod
    def would_create_cycle(source_model: object, target_model: object) -> bool:
        """Return True when connecting source->target would create a cyclical dependency."""
        source_port = source_model.usdshade_port
        source_prim = source_port.GetPrim() if source_port else None
        target_prim = target_model.prim
        return would_create_prim_cycle(source_prim, target_prim)

    def can_connect(
        self,
        context_name: str,
        plugin: object,
        source_model: object,
        target_model: object,
    ) -> bool:
        """Return whether source->target is allowed: cycle check first, plugin check second."""
        if self.would_create_cycle(source_model, target_model):
            return False

        source_proxy = source_model.proxy_attribute
        target_proxy = target_model.proxy_attribute

        # Skip cache when either port belongs to a polymorphic node —
        # port types change with retargeting, making cached results unreliable.
        src_poly = bool(getattr(source_proxy, "polymorphic_unresolved", False))
        tgt_poly = bool(getattr(target_proxy, "polymorphic_unresolved", False))
        src_node_poly = (
            hasattr(source_model, "prim_model")
            and hasattr(getattr(source_model, "prim_model", None) or object(), "_is_polymorphic")
            and getattr(getattr(source_model, "prim_model", None), "_is_polymorphic", False)
        )
        tgt_node_poly = (
            hasattr(target_model, "prim_model")
            and hasattr(getattr(target_model, "prim_model", None) or object(), "_is_polymorphic")
            and getattr(getattr(target_model, "prim_model", None), "_is_polymorphic", False)
        )
        if src_poly or tgt_poly or src_node_poly or tgt_node_poly:
            return bool(plugin.can_connect(source_model, target_model))

        # Interactive model metadata and plugin policy can change while paths
        # remain stable. Re-evaluate this inexpensive check instead of serving
        # a stale path-keyed compatibility result.
        return bool(plugin.can_connect(source_model, target_model))

    def validate(
        self,
        context_name: str,
        root_prim: Optional[Usd.Prim],
        plugin: object,
        *,
        model: Optional[object] = None,
    ) -> ValidationResult:
        """Run validation and notify subscribers."""
        # Proxy compatibility results are valid only within one validation
        # snapshot; plugin settings and authored port metadata may change
        # between runs without changing the active material root.
        self._can_connect_cache.clear()
        self._emit("started", context_name)
        previous = self._last_results.get(context_name)
        result = validate_material_context(
            root_prim,
            context_name,
            plugin,
            can_connect_fn=self._can_connect_proxy,
            model=model,
        )
        self._last_results[context_name] = result
        self._emit("finished", context_name, result)
        if previous is None or previous.issues != result.issues:
            self._emit("state_changed", context_name, previous, result)
        return result

    def _emit(self, event_name: str, *args) -> None:
        """Emit an event to all callbacks for the event."""
        for callback in list(self._callbacks[event_name].values()):
            try:
                callback(*args)
            except Exception:  # pylint: disable=broad-exception-caught
                logger.exception("material validator '%s' subscriber failed", event_name)


class _ProxyModelAdapter:
    """Adapter exposing model-like fields for proxy-only validation calls.

    Pipeline compatibility checks are proxy-based and do not have a concrete
    graph-model instance. Some plugin `can_connect` paths still touch
    `model.prim`, so we provide a minimal compatible surface and leave `prim`
    unset (`None`) by design.
    """

    def __init__(self, proxy_attribute: object) -> None:
        self.proxy_attribute = proxy_attribute
        self.prim = None
        self.parent = None
