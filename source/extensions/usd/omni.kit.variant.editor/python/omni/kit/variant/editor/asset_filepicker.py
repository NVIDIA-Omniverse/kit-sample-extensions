# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from __future__ import annotations

import asyncio
from functools import partial
from typing import Any, Callable, Tuple

import carb.settings
import omni.client
import omni.ui as ui
from omni.kit.window.file_importer import get_file_importer
from pxr import Sdf

from .variant_property_models import SdfAssetPathAttributeModelVariant

DEFAULT_FILE_EXTS = ("*.*", "All Files")


def show_asset_file_picker(
    title: str,
    assign_value_fn: Callable[[Any, str], None],
    model_weak,
    stage_weak,
    layer_weak=None,
    file_exts: Tuple[Tuple[str, str]] = None,
    frame=None,
    multi_selection: bool = False,
    on_selected_fn=None,
):
    model = model_weak()
    if not model:
        return

    navigate_to = None
    fallback = None
    if isinstance(model, SdfAssetPathAttributeModelVariant):
        navigate_to = model.get_wildcard_resolved_path()
    elif isinstance(model, ui.AbstractValueModel):
        if not hasattr(model, "is_array_type") or not model.is_array_type():
            navigate_to = model.get_value_as_string()

    if navigate_to is None:
        stage = stage_weak()
        if stage and not stage.GetRootLayer().anonymous:
            # If asset path is empty, open the USD rootlayer folder
            # But only if filepicker didn't already have a folder remembered (thus fallback)
            fallback = stage.GetRootLayer().identifier

    if layer_weak:
        layer = layer_weak()
        if layer:
            navigate_to = layer.ComputeAbsolutePath(navigate_to)

    if navigate_to:
        navigate_to = replace_query(navigate_to, None)

    file_importer = get_file_importer()
    if file_importer:
        file_exts = None

        if isinstance(model, SdfAssetPathAttributeModelVariant):
            custom_data = model.metadata.get(Sdf.PrimSpec.CustomDataKey, {})
            file_exts_dict = custom_data.get("fileExts", {})
            file_exts = tuple((key, value) for (key, value) in file_exts_dict.items())
        if not file_exts:
            file_exts = (DEFAULT_FILE_EXTS,)

        def on_import(model_weak, stage_weak, filename, dirname, selections=[]):
            paths = selections.copy()
            if not paths:
                # fallback to filename
                paths.append(omni.client.combine_urls(dirname, filename))

            # get_current_selections comes in random (?) order, it does not follow selection order. sort it so
            # at least the result is ordered alphabetically.
            paths.sort()

            if not multi_selection:
                paths = paths[-1:]

            async def check_paths(paths):
                for path in paths:
                    result, entry = await omni.client.stat_async(path)
                    if result == omni.client.Result.OK:
                        if (
                            file_exts
                            and file_exts != (DEFAULT_FILE_EXTS,)
                            and entry.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN
                        ):
                            carb.log_warn("Please select a file, not a folder!")
                            return
                    else:
                        carb.log_warn(f"Selected file {path} does not exist!")
                        return

            asyncio.ensure_future(check_paths(paths))

            if on_selected_fn:
                on_selected_fn(stage_weak, model_weak, "\n".join(paths), assign_value_fn, frame)

        file_importer.show_window(
            title=title,
            import_button_label="Select",
            import_handler=partial(on_import, model_weak, stage_weak),
            file_extension_types=file_exts,
            filename_url=navigate_to,
        )

        # fallback to a fallback directory if the filepicker dialog didn't have saved history
        if fallback and not file_importer._dialog.get_current_directory():
            file_importer._dialog.show(fallback)


def replace_query(url, new_query):
    client_url = omni.client.break_url(url)
    return omni.client.make_url(
        scheme=client_url.scheme,
        user=client_url.user,
        host=client_url.host,
        port=client_url.port,
        path=client_url.path,
        query=new_query,
        fragment=client_url.fragment,
    )
