"""Lifecycle manager for stage listener creation, teardown, and subscription state."""

from typing import Any, List

import carb
import omni.usd

from ......config.logging import logger
from ......utils.lifecycle_registry import LifecycleRegistry
from .listener import StageListener


class StageListenerManager:
    """Manage stage event subscriptions and listener lifecycle."""

    def __init__(self, model: Any, lifecycle: LifecycleRegistry) -> None:
        """Initialize instance state for this material graph component."""

        self._model = model
        self._lifecycle = lifecycle
        self._stage_listener = None
        self._subscriptions: List[Any] = []

    def activate(self) -> None:
        """Subscribe to stage events and start listener."""
        if not self._model._is_context_root:
            logger.debug("stage listener activation skipped: model is not a context root")
            return
        usd_context = getattr(self._model, "_usd_context", None) or omni.usd.get_context()
        self._subscriptions = [
            carb.eventdispatcher.get_eventdispatcher().observe_event(
                event_name=usd_context.stage_event_name(omni.usd.StageEventType.SELECTION_CHANGED),
                on_event=self._on_stage_selection_event,
                observer_name=f"{__name__} {omni.usd.StageEventType.SELECTION_CHANGED.name}",
            ),
            carb.eventdispatcher.get_eventdispatcher().observe_event(
                event_name=usd_context.stage_event_name(omni.usd.StageEventType.SAVING),
                on_event=self._on_stage_saving_event,
                observer_name=f"{__name__} {omni.usd.StageEventType.SAVING.name}",
            ),
            carb.eventdispatcher.get_eventdispatcher().observe_event(
                event_name=usd_context.stage_event_name(omni.usd.StageEventType.SAVED),
                on_event=self._on_stage_saved_event,
                observer_name=f"{__name__} {omni.usd.StageEventType.SAVED.name}",
            ),
        ]
        for subscription in self._subscriptions:
            self._lifecycle.add_unsubscribe(subscription)

        self._replace_stage_listener(self._model._stage)

    def _replace_stage_listener(self, stage: Any = None) -> None:
        """Destroy the current listener before optionally creating its replacement."""
        if self._stage_listener:
            self._stage_listener.destroy()
        self._stage_listener = StageListener(self._model, stage) if stage else None

    def clear(self) -> None:
        """Destroy stage listener and release all event subscriptions owned by manager."""
        self._replace_stage_listener()
        if self._lifecycle:
            self._lifecycle.cleanup()
        self._subscriptions = []

    def _on_stage_selection_event(self, _event: Any) -> None:
        """Execute on stage selection event behavior for material graph workflows."""

        self._model._selection_changed()

    def _on_stage_saving_event(self, _event: Any) -> None:
        """Execute on stage saving event behavior for material graph workflows."""

        self._replace_stage_listener()

    def _on_stage_saved_event(self, _event: Any) -> None:
        """Execute on stage saved event behavior for material graph workflows."""

        self._replace_stage_listener(self._model._stage)
