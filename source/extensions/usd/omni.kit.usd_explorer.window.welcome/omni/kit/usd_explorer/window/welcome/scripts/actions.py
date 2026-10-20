import asyncio

import carb
import omni.kit.actions.core


def register_actions(extension_id, cls):
    action_registry = omni.kit.actions.core.get_action_registry()

    # actions
    action_registry.register_action(
        extension_id,
        "show_window",
        lambda: cls.show_window(True),
        display_name="Show Welcome Window",
        description="Show Window",
        tag="Menu Action",
    )


def deregister_actions(extension_id):
    action_registry = omni.kit.actions.core.get_action_registry()
    if action_registry:
        action_registry.deregister_all_actions_for_extension(extension_id)
