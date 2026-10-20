## Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##
from functools import partial

import carb
import omni.client
import omni.ui as ui
from omni.kit.property.usd import UsdAttributeModel
from omni.kit.property.usd.relationship import RelationshipTargetPicker
from omni.kit.window.file_importer import get_file_importer
from pxr import Sdf

from .style import ICON_SIZE, spawn_property_style
from .utils import SPAWN_ATTR_SOURCE_PATH, locate_file, set_spawn_source_paths


def build_source_paths_ui(widget, stage, node):
    attr = node.get_attribute(SPAWN_ATTR_SOURCE_PATH)

    def build_source_paths_frame():
        source_paths = attr.get()

        def add_paths(paths: list):
            new_paths = [path for path in paths if path not in source_paths]
            if len(new_paths) > 0:
                set_spawn_source_paths(node, source_paths + new_paths)

        def replace_path(id, new_path):
            if isinstance(new_path, list):
                new_path = new_path[-1]
            if new_path not in source_paths:
                source_paths[id] = new_path

                if not Sdf.Path.IsValidPathString(new_path):
                    for char in new_path:
                        if char.isalpha() or char.isdigit() or char in r"/\_-:@":
                            continue
                        else:
                            carb.log_warn(f"{new_path} seems not a valid prim path or file path.")
                            break

                set_spawn_source_paths(node, source_paths)

        def remove_path(id):
            del source_paths[id]
            set_spawn_source_paths(node, source_paths)

        def on_select_file(id, filename, dirname, selections=[]):
            if dirname and not dirname.endswith("/"):
                dirname += "/"
            path = omni.client.combine_urls(dirname, filename)
            if id < 0:
                add_paths([path])
            else:
                replace_path(id, path)

        def show_file_importer(id=-1):
            file_importer = get_file_importer()
            if file_importer:
                file_importer.show_window(
                    title="Spawn asset path",
                    import_button_label="Select",
                    import_handler=partial(on_select_file, id),
                )

        def show_prim_picker(id=-1):
            picker = RelationshipTargetPicker(stage, [], None, {})
            if id < 0:
                picker.show(0, add_paths)
            else:
                picker.show(1, partial(replace_path, id))

        with ui.VStack(spacing=5):
            # buttons
            with ui.HStack():
                ui.Spacer()
                ui.Button("Add External Asset", name="string", clicked_fn=show_file_importer)
                ui.Spacer()
                ui.Button("Add Stage Prims", name="string", clicked_fn=show_prim_picker)
                ui.Spacer()

            for i, path in enumerate(source_paths):
                with ui.HStack():
                    # The text input box for path
                    path_field = ui.StringField()
                    path_field.model.set_value(path)

                    def on_source_path_end_edit(id, model):
                        new_path = model.as_string
                        replace_path(id, new_path)

                    path_field.model.add_end_edit_fn(partial(on_source_path_end_edit, i))

                    ui.Button(
                        name="prim", width=ICON_SIZE, tooltip="Select Prim", clicked_fn=partial(show_prim_picker, i)
                    )
                    ui.Button(
                        name="asset", width=ICON_SIZE, tooltip="Select Asset", clicked_fn=partial(show_file_importer, i)
                    )
                    ui.Button(
                        name="locate",
                        width=ICON_SIZE,
                        tooltip="Locate Asset",
                        clicked_fn=partial(locate_file, path_field.model),
                    )
                    ui.Button(name="trash", width=ICON_SIZE, tooltip="Remove", clicked_fn=partial(remove_path, i))

    # UI for source paths
    source_paths_frame = ui.CollapsableFrame(
        "Entity Prototypes", name="subFrame", build_header_fn=widget._build_frame_header
    )
    source_paths_frame.style = spawn_property_style
    source_paths_frame.set_build_fn(build_source_paths_frame)

    def on_attr_value_changed(model):
        source_paths_frame.rebuild()

    attr_paths = Sdf.Path(attr.get_path())
    model = UsdAttributeModel(stage, [attr_paths], False, {})
    model.add_value_changed_fn(on_attr_value_changed)
    widget._models[attr_paths].append(model)
