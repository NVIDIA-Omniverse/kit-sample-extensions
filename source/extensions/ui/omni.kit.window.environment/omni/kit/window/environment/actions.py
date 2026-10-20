# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb
import omni.kit.commands

from .models import EnvType
from .widgets.delegate import ENV_DRAG_PAYLOAD_PREFIX


def drop_environment(url: str) -> bool:
    if url.startswith(ENV_DRAG_PAYLOAD_PREFIX):
        env_type, env_url = url[len(ENV_DRAG_PAYLOAD_PREFIX) :].split("::")

        # convert type defined in environment.core
        if env_type == EnvType.USD:
            type = "Sky"
        elif env_type == EnvType.HDR:
            type = "HDRI"
        elif env_type == EnvType.TEMPLATE:
            type = "Scene"
        else:
            return False

        try:
            import omni.kit.actions.core

            action_registry = omni.kit.actions.core.get_action_registry()
            action_registry.execute_action("omni.kit.environment.core", "import", type, env_url)
            return True
        except ImportError:
            carb.log_error("Actions not enabled.")
            return False

    return False


def register_actions(extension_id):
    try:
        import omni.kit.actions.core

        action_registry = omni.kit.actions.core.get_action_registry()
        actions_tag = "Environment"

        action_registry.register_action(
            extension_id,
            "drop",
            lambda url: drop_environment(url),
            display_name="Environment->Drop",
            description="Drag and Drop environment window item",
            tag=actions_tag,
        )
    except ImportError:
        pass


def deregister_actions(extension_id):
    try:
        import omni.kit.actions.core

        action_registry = omni.kit.actions.core.get_action_registry()
        action_registry.deregister_all_actions_for_extension(extension_id)
    except ImportError:
        pass
