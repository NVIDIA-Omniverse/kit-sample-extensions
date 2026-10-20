"""Backdrop overlap analysis and stacking-order computation for nodegraph rendering."""

from typing import Any, Dict, Iterable, Optional, Tuple

from ..backdrop import BackdropModel

# pylint: disable=cell-var-from-loop


class BackdropStackingCalculator:
    """Compute deterministic backdrop stacking order from overlap relationships."""

    @staticmethod
    def get_order(backdrop_model: BackdropModel, cache: Dict[Any, int]) -> int:
        """Return computed stacking order for a backdrop."""
        if not backdrop_model:
            return 0
        return cache.get(backdrop_model.prim_path, backdrop_model.get_stacking_inputs()[2])

    @staticmethod
    def _build_signature(backdrops: Iterable[BackdropModel]) -> Tuple[Any, ...]:
        """Build stable signature used to skip unchanged recomputation."""
        return tuple(
            sorted(
                (
                    str(b.prim_path),
                    tuple((b.get_stacking_inputs()[0] or ())),
                    tuple((b.get_stacking_inputs()[1] or ())),
                    b.get_stacking_inputs()[2],
                )
                for b in backdrops
            )
        )

    @staticmethod
    def _rect(model: BackdropModel) -> Optional[Tuple[float, float, float, float]]:
        """Return backdrop bounds as (left, bottom, right, top) rectangle."""
        pos, size, _order = model.get_stacking_inputs()
        if pos is None or size is None:
            return None
        try:
            w, h = float(size[0]), float(size[1])
            x, y = float(pos[0]), float(pos[1])
        except (TypeError, ValueError):
            return None
        return (x - w * 0.5, y - h * 0.5, x + w * 0.5, y + h * 0.5)

    @staticmethod
    def _overlaps(a, b) -> bool:
        """Return True when two axis-aligned rectangles overlap."""
        return not (a[2] <= b[0] or a[0] >= b[2] or a[3] <= b[1] or a[1] >= b[3])

    @staticmethod
    def _area(rect) -> float:
        """Return rectangle area, clamped to non-negative extents."""
        return max(0.0, rect[2] - rect[0]) * max(0.0, rect[3] - rect[1])

    @staticmethod
    def _clamp_single_order(raw_order: int, min_non_backdrop: Optional[int]) -> int:
        """Clamp standalone backdrop order so non-backdrops stay visually on top."""
        adjusted = raw_order
        if min_non_backdrop is not None and adjusted >= min_non_backdrop:
            adjusted = min_non_backdrop - 1
        return adjusted

    @staticmethod
    def _assign_component_orders(
        component: Iterable[BackdropModel],
        rect_map: Dict[BackdropModel, Tuple[float, float, float, float]],
        raw_order: int,
        non_backdrop_orders: Iterable[int],
        min_non_backdrop: Optional[int],
    ) -> Dict[Any, int]:
        """Assign deterministic orders inside a connected overlap component."""
        component = list(component)
        if len(component) == 1:
            model = component[0]
            return {model.prim_path: BackdropStackingCalculator._clamp_single_order(raw_order, min_non_backdrop)}

        ordered = sorted(component, key=lambda b: (BackdropStackingCalculator._area(rect_map[b]), str(b.prim_path)))
        less = [o for o in non_backdrop_orders if o < raw_order]
        max_less = max(less) if less else None
        min_allowed = (max_less + 1) if max_less is not None else None

        out: Dict[Any, int] = {}
        for index, model in enumerate(ordered):
            adjusted = raw_order - index
            if min_allowed is not None and adjusted < min_allowed:
                adjusted = min_allowed
            if min_non_backdrop is not None and adjusted >= min_non_backdrop:
                adjusted = min_non_backdrop - 1
            out[model.prim_path] = adjusted
        return out

    def _compute_group_cache(
        self,
        raw_order: int,
        items: Iterable[BackdropModel],
        non_backdrop_orders: Iterable[int],
        min_non_backdrop: Optional[int],
    ) -> Dict[Any, int]:
        """Compute cache entries for one raw stacking-order group."""
        items_with_rect = [(b, self._rect(b)) for b in items]
        items_with_rect = [(b, r) for b, r in items_with_rect if r]
        if not items_with_rect:
            return {b.prim_path: self._clamp_single_order(raw_order, min_non_backdrop) for b in items}

        unvisited = set(b for b, _ in items_with_rect)
        rect_map = {b: r for b, r in items_with_rect}
        group_cache: Dict[Any, int] = {}

        while unvisited:
            start = next(iter(unvisited))
            stack = [start]
            component = []
            unvisited.remove(start)
            while stack:
                node = stack.pop()
                component.append(node)
                rect_a = rect_map.get(node)
                for other in list(unvisited):
                    rect_b = rect_map.get(other)
                    if rect_a and rect_b and self._overlaps(rect_a, rect_b):
                        unvisited.remove(other)
                        stack.append(other)
            group_cache.update(
                self._assign_component_orders(component, rect_map, raw_order, non_backdrop_orders, min_non_backdrop)
            )
        return group_cache

    def compute(  # noqa: C901
        self,
        children: Iterable[Any],
        cache: Dict[Any, int],
        signature: Optional[Tuple[Any, ...]],
    ) -> Tuple[Dict[Any, int], Optional[Tuple[Any, ...]]]:
        """Compute/update cache and signature used to avoid redundant recomputation."""
        backdrops = [m for m in children if isinstance(m, BackdropModel)]
        if not backdrops:
            return {}, None

        new_signature = self._build_signature(backdrops)
        if new_signature == signature:
            return cache, signature

        new_cache: Dict[Any, int] = {}
        non_backdrop_orders = [
            getattr(m, "stacking_order", 0) or 0 for m in children if not isinstance(m, BackdropModel)
        ]
        min_non_backdrop = min(non_backdrop_orders) if non_backdrop_orders else None

        groups: Dict[int, list[BackdropModel]] = {}
        for backdrop in backdrops:
            raw_order = backdrop.get_stacking_inputs()[2]
            groups.setdefault(raw_order, []).append(backdrop)

        for raw_order, items in groups.items():
            new_cache.update(self._compute_group_cache(raw_order, items, non_backdrop_orders, min_non_backdrop))

        return new_cache, new_signature
