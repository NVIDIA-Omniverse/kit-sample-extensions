# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


from omni.scene.optimizer.core.scripts import commands, standalone

from .test_utils import Test_Operation


class TestCommands(Test_Operation):
    """Generic Command tests"""

    async def test_list_operations(self):
        """Test listing plugins"""

        # Assert there are operations
        cmd = commands.SceneOptimizerListOperations()
        operations = cmd.do()
        self.assertGreater(len(operations), 0)

    async def test_list_operation_arguments(self):
        """Test listing the arguments of an operation"""

        cmd = commands.SceneOptimizerListOperationArguments("merge")
        args = cmd.do()
        self.assertGreater(len(args), 0)
