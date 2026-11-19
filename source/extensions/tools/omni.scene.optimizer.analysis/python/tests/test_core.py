# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


import pathlib

import omni.kit.app
import omni.kit.test
import omni.usd
from omni.scene.optimizer import analysis


# Test classes derived from omni.kit.test.AsyncTestCase will be auto-discoverable by omni.kit.test
class Test_Core(omni.kit.test.AsyncTestCase):

    def __get_test_data_file_path(self, name):
        """Get the path for a file within the test data directory of this extension"""
        extension_path = omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
        test_data_path = pathlib.Path(extension_path).joinpath("data")
        test_file_path = test_data_path.joinpath(name).absolute()
        return str(test_file_path)

    def __open_stage(self, file_path):
        usd_context = omni.usd.get_context()
        path = self.__get_test_data_file_path(file_path)
        if usd_context.open_stage(path):
            print("Opened stage:", path)
            return usd_context.get_stage()

    async def test_analyze(self):
        # build a list of operations to run analysis on
        operations = [
            analysis.OperationConfig("sparseMeshes"),  # sparse meshes is a valid analysis operation
            analysis.OperationConfig(
                "pythonScript"
            ),  # python script does not support analysis, but is a valid operation
            analysis.OperationConfig("doesNotExist"),  # invalid operation
        ]

        # open the stage
        stage = self.__open_stage("factory.usda")

        # call analysis
        analysis_result = analysis.analyze(stage, operations)

        # verify the sparse meshes result
        self.assertTrue("sparseMeshes" in analysis_result)
        sparse_meshes_result = analysis_result["sparseMeshes"]
        self.assertTrue(len(sparse_meshes_result) == 3)
        self.assertTrue(sparse_meshes_result[0])
        sparse_meshes_data = sparse_meshes_result[2]
        self.assertTrue("analysis" in sparse_meshes_data)  # should have an analysis section
        sparse_meshes_analysis = sparse_meshes_data["analysis"]
        # check there is a disjointSparseMeshes section
        self.assertTrue("disjointSparseMeshes" in sparse_meshes_analysis)
        # check there is a suggestedOperations section
        self.assertTrue("suggestedOperations" in sparse_meshes_analysis)

        # verify the python script result
        self.assertTrue("pythonScript" in analysis_result)
        python_script_result = analysis_result["pythonScript"]
        self.assertTrue(len(python_script_result) == 3)
        self.assertFalse(python_script_result[0])
        # should have an error since python script does not support analysis
        self.assertTrue(python_script_result[1])

        # verify the doesNotExist result
        self.assertTrue("doesNotExist" in analysis_result)
        does_not_exist_result = analysis_result["doesNotExist"]
        self.assertTrue(len(does_not_exist_result) == 3)
        self.assertFalse(does_not_exist_result[0])
        # should have an error since the operation does not exist
        self.assertTrue(does_not_exist_result[1])

    async def test_optimize(self):
        # build a list of operations to run scene optimizer on
        operations = [
            analysis.OperationConfig("sparseMeshes"),
            analysis.OperationConfig("doesNotExist"),
        ]

        # open the stage
        stage = self.__open_stage("factory.usda")

        # call analysis
        analysis_result = analysis.analyze(stage, operations)

        # create operations from the analysis result
        operations = analysis.create_operations_from_analysis_result(analysis_result)

        # verify one split meshes operation was created
        self.assertTrue(len(operations) == 1)
        self.assertTrue(operations[0].name == "splitMeshes")

        # call optimize
        optimize_result = analysis.optimize(stage, operations)

        # verify the splitMeshes operation has completed successfully
        self.assertTrue("splitMeshes" in optimize_result)
        split_meshes_result = optimize_result["splitMeshes"]
        self.assertTrue(len(split_meshes_result) == 3)
        self.assertTrue(split_meshes_result[0])
