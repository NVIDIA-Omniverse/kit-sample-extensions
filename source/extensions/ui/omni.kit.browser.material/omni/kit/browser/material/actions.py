# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
from .delegate import MaterialDetailDelegate
from .model import MaterialBrowserModel


def drop_material(url: str) -> str:
    """
    Drop material.

    Args:
        url (str): Url of dragging item form material browser.

    Returns:
        Return path of created material.
    """
    material_url, sub_material = MaterialDetailDelegate.get_material_info_from_drop(url)
    return MaterialBrowserModel.create_material_by_url(material_url, sub_material)


def register_actions(extension_id):
    try:
        import omni.kit.actions.core

        action_registry = omni.kit.actions.core.get_action_registry()
        actions_tag = "Material Browser"

        action_registry.register_action(
            extension_id,
            "drop",
            lambda url: drop_material(url),
            display_name="Material Browser->Drop",
            description="Drop material item",
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
