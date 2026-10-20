"""Provides functions to register and deregister deep link actions for creating and applying deep links."""

import omni.kit.actions.core


def register_actions(owner, extension_id):
    """Register deep link actions for creating and applying deep links.

    Registers two actions: 'generate_link_clicked' for creating deep links and 'apply_link_clicked' for applying deep links. Both actions are tagged as 'Deep Link Actions'.

    Args:
        owner (object): Object that provides the callback methods for deep link operations.
        extension_id (str): Extension identifier used to register the actions.
    """
    action_registry = omni.kit.actions.core.get_action_registry()
    actions_tag = "Deep Link Actions"

    action_registry.register_action(
        extension_id,
        "generate_link_clicked",
        lambda: owner._generate_link_clicked(),
        display_name="Deep Link->Create",
        description="Create a deep link.",
        tag=actions_tag,
    )
    action_registry.register_action(
        extension_id,
        "apply_link_clicked",
        lambda: owner._apply_link_clicked(),
        display_name="Deep Link->Apply",
        description="Apply a deep link.",
        tag=actions_tag,
    )


def deregister_actions(extension_id):
    """Deregister all deep link actions for the specified extension.

    Removes all previously registered actions associated with the extension from the action registry.

    Args:
        extension_id (str): Extension identifier whose actions should be deregistered.
    """
    action_registry = omni.kit.actions.core.get_action_registry()
    action_registry.deregister_all_actions_for_extension(extension_id)
