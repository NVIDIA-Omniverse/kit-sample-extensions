# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""
Utility functions for USD prim operations.

This module provides helper functions for getting USD selections and duplicating
prims using various methods (Copy, Reference, PointInstancer).
"""

import asyncio
from typing import List

import omni.kit.app
import omni.kit.commands
import omni.usd
from pxr import Sdf


def get_selection() -> List[str]:
    """Get the list of currently selected prims"""
    return omni.usd.get_context().get_selection().get_selected_prim_paths()


def duplicate_prims(transforms: List = [], prim_names: List[str] = [], target_path: str = "", mode: str = "Copy"):
    """
    Returns generator with pairs containing transform matrices and ids to
    arrange multiple objects.

    ### Arguments:

        `transforms: List`
            Pairs containing transform matrices and ids to apply to new objects

        `prim_names: List[str]`
            Prims to duplicate

        `target_path: str`
            The parent for the new prims

        `mode: str`
            "Reference": Create a reference of the given prim path
            "Copy": Create a copy of the given prim path
            "PointInstancer": Create a PointInstancer

    """

    if mode == "PointInstancer":
        omni.kit.commands.execute(
            "ScatterCreatePointInstancer",
            path_to=target_path,
            transforms=transforms,
            prim_names=prim_names,
        )
        return

    usd_context = omni.usd.get_context()
    # Call commands in a single undo group. So the user will undo everything
    # with a single press of ctrl-z
    with omni.kit.undo.group():
        # Create a group
        omni.kit.commands.execute("CreatePrim", prim_path=target_path, prim_type="Scope")

        for i, matrix in enumerate(transforms):
            id = matrix[1]
            matrix = matrix[0]

            path_from = Sdf.Path(prim_names[id])
            path_to = Sdf.Path(target_path).AppendChild(f"{path_from.name}{i}")

            # Create a new prim
            if mode == "Copy":
                omni.kit.commands.execute("CopyPrims", paths_from=[path_from.pathString], paths_to=[path_to.pathString])
            elif mode == "Reference":
                omni.kit.commands.execute(
                    "CreateReference", usd_context=usd_context, prim_path=path_from, path_to=path_to, asset_path=""
                )
            else:
                continue

            # Move
            omni.kit.commands.execute("TransformPrim", path=path_to, new_transform_matrix=matrix)


async def duplicate_prims_async(
    transforms: List = [], prim_names: List[str] = [], target_path: str = "", mode: str = "Copy", batch_size: int = 10
):
    """
    Async version that processes objects in batches to prevent UI freezing
    """
    if mode == "PointInstancer":
        omni.kit.commands.execute(
            "ScatterCreatePointInstancer",
            path_to=target_path,
            transforms=transforms,
            prim_names=prim_names,
        )
        return

    usd_context = omni.usd.get_context()

    with omni.kit.undo.group():
        # Create a group
        omni.kit.commands.execute("CreatePrim", prim_path=target_path, prim_type="Scope")

        # Process in batches to prevent UI freezing
        for batch_start in range(0, len(transforms), batch_size):
            batch_end = min(batch_start + batch_size, len(transforms))

            for i in range(batch_start, batch_end):
                matrix_data = transforms[i]
                id = matrix_data[1]
                matrix = matrix_data[0]

                path_from = Sdf.Path(prim_names[id])
                path_to = Sdf.Path(target_path).AppendChild(f"{path_from.name}{i}")

                # Create a new prim
                if mode == "Copy":
                    omni.kit.commands.execute(
                        "CopyPrims", paths_from=[path_from.pathString], paths_to=[path_to.pathString]
                    )
                elif mode == "Reference":
                    omni.kit.commands.execute(
                        "CreateReference", usd_context=usd_context, prim_path=path_from, path_to=path_to, asset_path=""
                    )
                else:
                    continue

                # Move
                omni.kit.commands.execute("TransformPrim", path=path_to, new_transform_matrix=matrix)

            # Yield control back to UI after each batch
            await omni.kit.app.get_app().next_update_async()
