# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import posixpath
import uuid
from pathlib import Path

from pxr import Sdf, UsdUtils

from .omni_client_wrapper import OmniClientWrapper
from .omni_url import OmniUrl


async def copy_output_assets(source_path: str, output_path: str):
    """Transfer a local staged USD and its generated dependencies.

    Args:
        source_path: Local writable USD. Its layer references are rewritten in place.
        output_path: Destination URL with the same USD filename as the source.

    Dependencies are copied into a unique asset folder and the root USD is uploaded
    last. Returns no value; save and upload failures raise exceptions. Callers own
    staging cleanup and any cleanup of previous or partially uploaded asset folders.
    """
    root = Path(source_path).resolve()
    layers, assets, _ = UsdUtils.ComputeAllDependencies(Sdf.AssetPath(str(root)))
    files = {root} | {Path(layer.realPath).resolve() for layer in layers if layer.realPath}
    texture_folders = {path.parent / "Textures" for path in files}
    for path in assets:
        resolved = Path(path).resolve()
        if resolved.is_file() and (
            resolved.is_relative_to(root.parent) or any(resolved.is_relative_to(folder) for folder in texture_folders)
        ):
            files.add(resolved)
    package = f"{root.stem}_assets_{uuid.uuid4().hex}"
    destinations = {root: root.name}
    for index, path in enumerate(sorted(files - {root})):
        # Partition layers can be authored beside an ancestor of the root layer.
        relative = (
            path.relative_to(root.parent).as_posix()
            if path.is_relative_to(root.parent)
            else f"external/{index}/{path.name}"
        )
        destinations[path] = f"{package}/{relative}"
    for layer in layers:
        layer_path = Path(layer.realPath).resolve()
        if layer_path not in destinations:
            continue

        def remap(path):
            resolved = Path(Sdf.ComputeAssetPathRelativeToLayer(layer, path)).resolve()
            if resolved not in destinations:
                return path
            return posixpath.relpath(destinations[resolved], posixpath.dirname(destinations[layer_path]) or ".")

        UsdUtils.ModifyAssetPaths(layer, remap)
        if not layer.Save():
            raise OSError(f"Could not save staged USD layer: {layer.realPath}")
    destination = OmniUrl(output_path).parent_url
    # Publish the root USD last so it cannot point to assets that failed to copy.
    for path in sorted(files - {root}) + [root]:
        target = destination / destinations[path]
        if not await OmniClientWrapper.create_folder(str(target.parent_url)):
            raise OSError(f"Could not create output asset directory: {target.parent_url}")
        if not await OmniClientWrapper.copy(str(path), str(target)):
            raise OSError(f"Could not copy converted asset to {target}")
