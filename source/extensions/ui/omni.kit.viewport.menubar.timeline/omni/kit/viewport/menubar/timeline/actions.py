from contextlib import suppress
from typing import Any, Callable

import carb  # type: ignore

actions_core = None
with suppress(ImportError):
    import omni.kit.actions.core as actions_core  # type: ignore


__all__ = ["register_action", "deregister_action", "deregister_all_actions_for_extension"]


def register_action(
    extension_name: str, action_id: str, callback_fn: Callable, display_name: str, description: str, tag: str = ""
) -> Any:
    if not actions_core:
        carb.log_warn("Actions are not supported in the current Kit version.")
        return

    action_registry = actions_core.get_action_registry()
    action = action_registry.register_action(
        extension_name, action_id, callback_fn, display_name=display_name, description=description, tag=tag
    )

    return action


def deregister_action(action) -> None:
    if action is None:
        return

    if not actions_core:
        carb.log_warn("Actions are not supported in the current Kit version.")
        return

    action_registry = actions_core.get_action_registry()
    action_registry.deregister_action(action)


def deregister_all_actions_for_extension(extension_name: str) -> None:
    if not actions_core:
        carb.log_warn("Actions are not supported in the current Kit version.")
        return

    action_registry = actions_core.get_action_registry()
    action_registry.deregister_all_actions_for_extension(extension_name)
