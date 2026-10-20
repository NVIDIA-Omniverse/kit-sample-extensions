# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import json
from functools import partial
from typing import List

import carb
import carb.tokens
from omni.kit.environment.core import SkyType
from omni.kit.stage_templates import get_stage_template, register_template, unregister_template

_cached_env_templates: List[str] = []


def get_template_cache_file():
    return carb.tokens.get_tokens_interface().resolve("${omni_global_cache}/omni.kit.window.environment.templates.json")


def load_stage_templates():
    templates_by_name = None
    try:
        template_cache_file = get_template_cache_file()
        with open(template_cache_file, "r") as json_file:
            templates_by_name = json.load(json_file)
    except FileNotFoundError:
        carb.log_info(f"Failed to open {template_cache_file}!")
        return
    except PermissionError:
        carb.log_error(f"Cannot read {template_cache_file}: permission denied!")
        return
    except Exception as exc:
        carb.log_error(f"Unknown failure to read {template_cache_file}: {exc}")
        return

    if templates_by_name is None:
        return

    try:
        from omni.kit.stage_templates import rebuild_stage_template_menu

        has_rebuild = True
    except ImportError:
        has_rebuild = False

    for name, url in templates_by_name.items():
        register_env_template(name, url, has_rebuild)
        global _cached_env_templates
        _cached_env_templates.append(name)
    if has_rebuild:
        rebuild_stage_template_menu()
    carb.log_info(f"{len(templates_by_name)} templates loaded")


def apply_template(url: str, root_name: str):
    try:
        from omni.kit.actions.core import get_action_registry

        action = get_action_registry().get_action("omni.kit.environment.core", "import")
        if action:
            return action.execute(SkyType.SCENE, url)
        else:
            return ""
    except ImportError:
        from omni.kit.environment.core import import_environment

        return import_environment(SkyType.SCENE, url)


def register_env_template(name: str, url: str, has_rebuild: bool):
    extra_kwargs = {"rebuild": False} if has_rebuild else {}
    if get_stage_template(name):
        unregister_template(name, **extra_kwargs)
        global _cached_env_templates
        if name in _cached_env_templates:
            _cached_env_templates.remove(name)
    register_template(name, partial(apply_template, url), group=1, **extra_kwargs)


def unregister_cached_env_templates(has_rebuild: bool):
    """
    Unregister env templates which:
    - registered from cache
    - not registered again when env updates
    """
    extra_kwargs = {"rebuild": False} if has_rebuild else {}
    global _cached_env_templates
    for name in _cached_env_templates:
        carb.log_info(f"Remove environment template {name}")
        unregister_template(name, **extra_kwargs)
    _cached_env_templates = []
