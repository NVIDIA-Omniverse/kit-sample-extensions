# SPDX-FileCopyrightText: Copyright (c) 2021-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


__doc__ = """
There is one primary command that is used to execute Scene Optimizer operations.
The command takes an operation name and a dict of args.

This command can be executed directly, or the standard approach is to execute
it via kit:

>>> operationName = "merge"
>>> args = { ... }
>>> omni.kit.commands.execute("SceneOptimizerOperation", operation=operationName, args=myArgs)

There is an optional **context** argument that can be provided to any command.
This is a way to customize some generic settings used when running operations.

For example, by default operations run on the current omni stage. You can use the
context to specify an alternate stage to run on.

The `usdStageId` property accepts the value returned when the `stage` is inserted into the `UsdUtils.StageCache`.

>>> context = omni.scene.optimizer.core._ExecutionContext()
>>> context.usdStageId = UsdUtils.StageCache().Get().Insert(stage).ToLongInt()
>>> context.generateReport = 1
>>> context.captureStats = 1
>>> omni.kit.commands.execute("SceneOptimizerOperation", operation=operationName, args=myArgs, context=context)

The commands :class:`SceneOptimizerListOperations` and :class:`SceneOptimizerListOperationArguments`
can be used to query the registered operations and the arguments they accept.
"""

import base64
import binascii
import functools
import json
import time
import types

import carb
import omni.kit.commands
from pxr import UsdGeom, UsdUtils
from usd_optimize.impl.core import ExecutionContext

IFACE = None


class Commands:
    def __init__(self, iface):
        global IFACE
        IFACE = iface

    def shutdown(self):  # pragma: no cover
        global IFACE
        IFACE = None


class _SceneOptimizerOperation(omni.kit.commands.Command):

    _OPERATION_INFO = {}

    @classmethod
    def get_operation_info(cls):
        """Get the operation info used to display a rich argument interface"""
        return cls._OPERATION_INFO.copy()

    def __init__(self, operation, args=None, context=None) -> None:
        super().__init__()

        # Construct defaults for unsupplied arguments.
        if args is None:
            args = dict()

        if context is None:
            import omni.usd

            context = ExecutionContext()
            stage = omni.usd.get_context().get_stage()
            if stage is not None:
                context.usdStageId = UsdUtils.StageCache().Get().Insert(stage).ToLongInt()

        # Store arguments and context for access during execution.
        self._operation = operation
        self._args = args
        self._context = context

        # perform sub class initialization
        self._post_init()

    def _post_init(self):
        """Called after initialization so that sub classes can complete setup"""
        # Classes that inherit from _SceneOptimizerOperation should not implement __init__

        # Instead they should implement _post_init and in that function populate the instance of the class in the same
        # manner they would normally do within __init__

        # We do this so that the constructors are consistent and the addition of new __init__ arguments are handled in
        # a single place.
        pass  # pragma: no cover


class SceneOptimizerOperation(_SceneOptimizerOperation):
    """
    This is the primary command used to execute Scene Optimizer operations.
    See the top of this page for more detail.
    """

    def _post_init(self):
        # If there are no serialized args, make sure it's an empty string to pass
        # through
        if not self._args:
            self._args = ""
        elif isinstance(self._args, dict):
            # If a dict is passed in, dump to JSON
            self._args = json.dumps(self._args)

    def do(self):
        # Time and execute the operation
        time_start = time.time()
        result = IFACE.execute_operation(self._operation, self._context, self._args)
        time_total = time.time() - time_start
        carb.log_info(f"[SceneOptimizer] Ran {self._operation} ({time_total:.3f}s)")
        return result

    def undo(self):
        pass  # pragma: no cover


class SceneOptimizerListOperations(omni.kit.commands.Command):
    """Returns a list of the names of all currently registered operations."""

    def __init__(self) -> None:
        super().__init__()

    def do(self):
        return IFACE.get_operations()


class SceneOptimizerListOperationArguments(omni.kit.commands.Command):
    """Retrieves a dictionary describing the available arguments for a specified
    operation.

    :param str operation: The operation to query arguments for.
    """

    def __init__(self, operation) -> None:
        super().__init__()
        self._operation = operation

    def do(self):
        return IFACE.get_operation_arguments(self._operation)


class SceneOptimizerJsonParser(_SceneOptimizerOperation):
    """Reads JSON data containing commands to execute via the Scene Optimizer.

    :param str jsonFile: Either the path to a JSON file on disk, or a JSON string.

    Example:

    >>> j = '[{"operation": "decimateMeshes", "maxMeanError": 1.0}]'
    >>> myArgs = {"jsonFile": j}
    >>> omni.kit.commands.execute("SceneOptimizerJsonParser", context=context, args=myArgs)
    """

    def __init__(self, args=None, context=None) -> None:
        super().__init__(operation="jsonParser", args=args, context=context)

    def _post_init(self):
        self._jsonFile = self._args["jsonFile"]

    def do(self):
        return IFACE.json_parser(self._context, self._jsonFile)


# Register commands with kit
omni.kit.commands.register_all_commands_in_module(__name__)
