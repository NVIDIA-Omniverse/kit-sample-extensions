# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import omni.kit.actions.core
import omni.kit.commands
import omni.usd

from ..prims import valid_ui_prim_types


def register_actions(extension_id, cls, get_self_fn):
    actions_tag = "Create Data2UI Menu Actions"

    omni.kit.actions.core.get_action_registry().register_action(
        extension_id,
        "create_viewport_ui_frame",
        lambda: omni.kit.commands.execute("CreateViewportUIFrame"),
        display_name="Create->UI->Create Viewport UI Frame",
        description="Create Viewport UI Frame",
        tag=actions_tag,
    )

    omni.kit.actions.core.get_action_registry().register_action(
        extension_id,
        "create_window_ui_frame",
        lambda: omni.kit.commands.execute("CreateWindowUIFrame"),
        display_name="Create->UI->Create Window UI Frame",
        description="Create Window UI Frame",
        tag=actions_tag,
    )

    # temporary actions until the core can reorder prims properly
    for direction in ["Up", "Down"]:
        omni.kit.actions.core.get_action_registry().register_action(
            extension_id,
            f"reorder_ui_prims_{direction.lower()}",
            lambda d=direction: omni.kit.commands.execute("ReorderUIPrimsCommand", direction=d),
            display_name=f"Create->UI->Reorder Prims {direction}",
            description=f"Reorder UI Prims {direction}",
            tag=actions_tag,
        )

    for prim_type in valid_ui_prim_types:
        omni.kit.actions.core.get_action_registry().register_action(
            extension_id,
            f"create_ui_prim_{prim_type.lower()}",
            lambda p=prim_type: omni.kit.commands.execute("CreateUIPrimCommand", prim_type=p),
            display_name=f"Create->UI->Create Prim {prim_type}",
            description=f"Create UI Prim {prim_type}",
            tag=actions_tag,
        )


def deregister_actions(extension_id):
    action_registry = omni.kit.actions.core.get_action_registry()
    action_registry.deregister_all_actions_for_extension(extension_id)
