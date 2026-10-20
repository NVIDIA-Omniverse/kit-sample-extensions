# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


from pxr import UsdUtils
from usd_optimize.impl.core import ExecutionContext

from ..bindings._omni_scene_optimizer_core import acquire_interface


def execute_commands_from_json(stage, filepath):
    """Execute a series of commands described in a Json file on the given Usd.Stage"""
    # acquire the interface and then release it after execution
    iface = acquire_interface()

    # Configure the execution context
    context = ExecutionContext()
    context.usdStageId = UsdUtils.StageCache().Get().Insert(stage).ToLongInt()

    # Execute the Operation stack described within the JSON Config
    result = iface.json_parser(context, filepath)

    # Note: we should not (currently) call release. If this is called from within the unit_tests
    #       where commands.py also has the interface, we end up releasing it behind the back of
    #       other things that want it.
    # release_interface(iface)
    return result


def get_output_paths(operation):
    """Return any output paths the operation may have set"""
    iface = acquire_interface()

    return iface.get_output_paths(operation)


def get_output_path_arrays(operation):
    """Return any output path arrays the operation may have set"""
    iface = acquire_interface()

    return iface.get_output_path_arrays(operation)


def map_config(config):
    """Map a Scene Optimizer JSON configuration

    Takes a Scene Optimizer config consisting of one or more operations and
    ensures the operation and attribute names are up to date. That is, if an
    operation has been renamed or had attributes renamed since the config was
    created, then it will be updated to reflect the latest naming.

    Any operations in the returned configuration will be up to date. However,
    any invalid data (missing an operation name, invalid operation) will be
    discarded.
    """
    iface = acquire_interface()

    return iface.map_config(config)
