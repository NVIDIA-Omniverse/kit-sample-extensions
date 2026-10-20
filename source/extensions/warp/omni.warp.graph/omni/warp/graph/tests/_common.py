# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shared helpers for the extension's tests."""

import importlib
import os
import tempfile
from typing import Union

import numpy as np
import omni.graph.tools.ogn as ogn
import warp as wp


def register_node(
    cls: type,
    ogn_definition: str,
    extension: str,
) -> None:
    """Registers a new node type based on its class object and OGN code."""
    # Parse the OGN definition.
    interface_wrapper = ogn.NodeInterfaceWrapper(ogn_definition, extension)

    # Generate the node's `og.Database` class and load it as a module.
    db_definition = ogn.generate_python(
        ogn.GeneratorConfiguration(
            node_file_path=None,
            node_interface=interface_wrapper.node_interface,
            extension=extension,
            module=extension,
            base_name=cls.__name__,
            destination_directory=None,
        ),
    )
    module_name = f"{extension}.{cls.__name__}"
    file, file_path = tempfile.mkstemp(suffix=".py")
    try:
        with os.fdopen(file, "w") as f:
            f.write(db_definition)

        spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        os.remove(file_path)

    # Register the node.
    db_cls = getattr(module, f"{cls.__name__}Database")
    db_cls.register(cls)


def array_are_equal(
    a: Union[np.ndarray, wp.array],
    b: Union[np.ndarray, wp.array],
) -> None:
    """Checks whether two arrays are equal."""
    if isinstance(a, wp.array):
        a = a.numpy()

    if isinstance(b, wp.array):
        b = b.numpy()

    if isinstance(a, np.ndarray) and isinstance(b, np.ndarray):
        assert a.shape == b.shape
        assert a.dtype == b.dtype
    else:
        assert len(a) == len(b)

    np.testing.assert_equal(a, b)
