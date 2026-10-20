# Copyright (c) 2023-2025, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.


from .utils import add_asset_from_drag, add_asset_with_variant_to_stage


def register_actions(extension_id: str, extension_instance):
    """
    Register actions.
    Args:
        extension_id (str): Extension ID which actions belongs to
    """
    try:
        import omni.kit.actions.core

        action_registry = omni.kit.actions.core.get_action_registry()
        actions_tag = "Wrapp"

        action_registry.register_action(
            extension_id,
            "toggle_window",
            lambda: extension_instance._toggle_window(),
            display_name="Package Explorer show/hide window",
            description="Package Explorer show/hide window",
            tag=actions_tag,
        )

        action_registry.register_action(
            extension_id,
            "add_asset",
            lambda raw_data, context="", path_to=None: add_asset_with_variant_to_stage(raw_data, context, path_to),
            display_name="Wrapp->Add Asset",
            description="Add Wrapp asset to stage",
            tag=actions_tag,
        )

        action_registry.register_action(
            extension_id,
            "add_asset_from_drag",
            lambda drag_mime_data, context="", path_to=None: add_asset_from_drag(drag_mime_data, context, path_to),
            display_name="Wrapp->Add Asset From Drag",
            description="Add Wrapp asset to stage from dragging mime data",
            tag=actions_tag,
        )
    except ImportError:
        pass


def deregister_actions(extension_id: str):
    """
    Deregister actions.
    Args:
        extension_id (str): Extension ID whcih actions belongs to
    """
    try:
        import omni.kit.actions.core

        action_registry = omni.kit.actions.core.get_action_registry()
        action_registry.deregister_all_actions_for_extension(extension_id)
    except ImportError:
        pass
