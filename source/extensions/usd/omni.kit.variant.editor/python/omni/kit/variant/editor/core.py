# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import asyncio
import re
import threading
import weakref
from typing import Any, List, Set

import carb
import omni
import omni.kit.material.library as matlib
import omni.kit.notification_manager as nm
from pxr import Sdf, Tf, Usd, UsdGeom, UsdShade, Vt

from . import editor_const as e_c

# cache that holds the shader display name for a given shader input name
# for example:
# {
#     "inputs:diffuse_color_constant": "Albedo Color",
#     "inputs:opacity_texture": "Opacity Map"
# }
SHADER_DISPLAY_NAME_CACHE = {}


def cache_shader_display_name(input_name: str, display_name: str) -> None:
    SHADER_DISPLAY_NAME_CACHE[input_name] = display_name
    if not input_name.startswith("inputs:"):
        SHADER_DISPLAY_NAME_CACHE[f"inputs:{input_name}"] = display_name


def get_shader_display_name(input_name: str) -> str:
    if input_name in SHADER_DISPLAY_NAME_CACHE:
        display_name = SHADER_DISPLAY_NAME_CACHE[input_name]
        if display_name:
            return display_name

    return input_name


def get_mdl_subids(mdl_path: str) -> Vt.TokenArray:
    result_container = []

    # Function to run in a separate thread with its own event loop
    def run_in_thread():
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # Define an async function that calls the material library function and waits
        async def get_subids_async():
            # Create a future to receive the result
            future = asyncio.Future()

            def on_subids_loaded(sub_ids):
                # Set the future's result
                future.set_result([i.name for i in sub_ids])

            # Call the async function and await the future
            await omni.kit.material.library.get_subidentifier_from_mdl(
                mdl_file=mdl_path,
                on_complete_fn=on_subids_loaded,
                use_functions=True,
                show_alert=True,
            )

            # Wait for the result with timeout
            try:
                result = await asyncio.wait_for(future, timeout=5.0)
                result_container.append(Vt.TokenArray(result))
            except asyncio.TimeoutError:
                carb.log_warn(f"Timeout waiting for MDL subidentifiers for {mdl_path}")

        # Run the async function to completion in this thread's event loop
        loop.run_until_complete(get_subids_async())
        loop.close()

    # Create and start the thread
    thread = threading.Thread(target=run_in_thread)
    thread.start()
    thread.join(timeout=10.0)  # Wait with timeout

    return result_container[0] if result_container else Vt.TokenArray()


def has_local_opinion(stage, property_path):
    """
    Check if a property has a local opinion in the current edit target layer.

    Args:
        stage (Usd.Stage): The USD stage
        property_path (str or Sdf.Path): Path to the property

    Returns:
        bool: True if property has a local opinion, False otherwise
    """
    # Convert path to Sdf.Path if needed
    if not isinstance(property_path, Sdf.Path):
        property_path = Sdf.Path(property_path)

    # Get the property
    prop = stage.GetPropertyAtPath(property_path.StripAllVariantSelections())
    if not prop or not prop.IsValid():
        return False

    # Get edit target layer
    local_layer = stage.GetEditTarget().GetLayer()

    # Get property stack (all opinions)
    property_stack = prop.GetPropertyStack(Usd.TimeCode.Default())

    # Check for local opinion
    for spec in property_stack:
        # If this spec is in the local layer and not in a variant path
        if spec.layer == local_layer and not Sdf.Path(spec.path).ContainsPrimVariantSelection():
            # Check if it has a value
            has_value = (hasattr(spec, "default") and spec.default is not None) or isinstance(
                spec, Sdf.RelationshipSpec
            )
            if has_value:
                return True

    return False


class VariantEditorCore:
    _variant_editor_core_instance = None

    class AuthorVariant:
        def __enter__(self):
            VariantEditorCore.get_instance().authoring_variant += 1

        def __exit__(self, exc_type, exc_value, traceback):
            VariantEditorCore.get_instance().authoring_variant -= 1

    def __init__(self):
        # Core Variables
        self._usd_context = None
        self._stage = None
        self._settings = carb.settings.get_settings()
        self._target_prim_path = None
        self._active_variant = None
        self._add_props_to_all_variants = False
        self._create_visibility_by_default = True
        self._observers = []
        self._variant_specs = []
        self._paired_properties = [["info:mdl:sourceAsset", "info:mdl:sourceAsset:subIdentifier"]]
        self._new_prop = None
        self.authoring_variant = 0
        self.ref_prim_path = None
        self.get_settings()
        self._custom_data_backup_layer = Sdf.Layer.CreateAnonymous()

    @property
    def add_props_to_all_variants(self):
        return self._add_props_to_all_variants

    @add_props_to_all_variants.setter
    def add_props_to_all_variants(self, value):
        self._add_props_to_all_variants = value
        if self._settings.get(e_c.ADD_PROPS_TO_ALL_VARIANTS_SETTING) != value:
            self._settings.set(e_c.ADD_PROPS_TO_ALL_VARIANTS_SETTING, value)

    @property
    def create_visibility_by_default(self):
        return self._create_visibility_by_default

    @create_visibility_by_default.setter
    def create_visibility_by_default(self, value):
        self._create_visibility_by_default = value
        if self._settings.get(e_c.CREATE_VISIBILITY_BY_DEFAULT_SETTING) != value:
            self._settings.set(e_c.CREATE_VISIBILITY_BY_DEFAULT_SETTING, value)

    @property
    def active_variant(self):
        return self._active_variant

    @active_variant.setter
    def active_variant(self, value):
        prev = self._active_variant
        self._active_variant = value
        for callback in self._observers:
            callback(self._active_variant, prev)

    def bind_to(self, callback):
        self._observers.append(callback)

    @staticmethod
    def get_instance():
        if VariantEditorCore._variant_editor_core_instance is None:
            VariantEditorCore._variant_editor_core_instance = VariantEditorCore()
        return VariantEditorCore._variant_editor_core_instance

    def destroy(self):
        self._observers.clear()
        self._clear_all()

    def get_settings(self):
        self.add_props_to_all_variants = self._settings.get(e_c.ADD_PROPS_TO_ALL_VARIANTS_SETTING)

    # ================== Core Logic =====================

    # Create a variant set
    def _create_variant_set(self, name, log_warning: bool = False):
        root_prim_path = self._get_root_prim_path()

        result, name = omni.kit.commands.execute(
            "AddVariantSet",
            prim_path=root_prim_path.pathString,
            variant_set_name=name,
            auto_postfix=True,
        )

        if name is not None:
            return name
        else:
            if log_warning:
                carb.log_warn("Could not create a valid variant set")

    # Create a Variant
    def _create_variant(self, vset_name, vname):
        result, ret = omni.kit.commands.execute(
            "AddVariant",
            prim_path=self._get_root_prim_path(),
            variant_set_name=vset_name,
            variant_name=vname,
            auto_postfix=False,
        )
        return ret

    # Remove a Variant Set
    def _remove_variant_set(self, path: str):
        root_prim_path = self._get_root_prim_path()

        variant_set_spec = self._get_edit_target_layer().GetObjectAtPath(path)

        if variant_set_spec is not None:
            with omni.kit.undo.group():
                # If current active variant is in this set, reset active variant
                if self._active_variant is not None:
                    variant_path = Sdf.Path(self._active_variant)
                    if variant_path.GetPrimPath() == variant_set_spec.owner.path:
                        if variant_path.GetVariantSelection()[0] == variant_set_spec.name:
                            omni.kit.commands.execute(
                                "SetVariantEditorActiveVariant",
                                variant_path=None,
                            )

                name = variant_set_spec.name

                omni.kit.commands.execute(
                    "RemoveVariantSet",
                    prim_path=root_prim_path,
                    variant_set_name=variant_set_spec.name,
                )

                # Clear variant selection
                self._clear_variant_selection(name)

            return True
        else:
            # We can't delete this spec bacause it's authored in another layer
            # Find out which layer it is authored in
            variant_layer_name = "another layer."
            authored_layer = self._get_variant_authored_layer(Sdf.Path(path))
            if authored_layer is not None:
                authored_layer_name = authored_layer.GetDisplayName()
                variant_layer_name = (
                    f'layer: "{authored_layer_name}".\nPlease switch to that layer to remove variant set.'
                )

            nm.post_notification(
                f"Couldn't delete variant set because it was authored in {variant_layer_name}",
                status=nm.NotificationStatus.WARNING,
            )
            return False

    # Remove a Variant
    def _remove_variant(self, path: str, clear_variant_selection=True):
        variant_spec = self._get_edit_target_layer().GetObjectAtPath(Sdf.Path(path))

        # Check if this variant is authored in current layer, only remove when it is
        if variant_spec is not None:
            set_name, variant = Sdf.Path(path).GetVariantSelection()
            result, ret = omni.kit.commands.execute(
                "RemoveVariant",
                prim_path=self._get_root_prim_path(),
                variant_set_name=set_name,
                variant_name=variant,
            )

            # If the variant to remove is set as variant seletion, then clear variant selection before removing
            if ret:
                vset = self._get_variant_set_by_name(set_name)
                if clear_variant_selection:
                    curr_variant_selection: str = vset.GetVariantSelection()

                    if variant == curr_variant_selection:
                        self._clear_variant_selection(set_name)
            return ret
        else:
            # We can't delete this spec bacause it's authored in another layer
            # Find out which layer it is authored in
            variant_layer_name = "another layer."
            authored_layer = self._get_variant_authored_layer(Sdf.Path(path))
            if authored_layer is not None:
                authored_layer_name = authored_layer.GetDisplayName()
                variant_layer_name = f'layer: "{authored_layer_name}".\nPlease switch to that layer to remove variant.'

            nm.post_notification(
                f"Couldn't delete variant because it was authored in {variant_layer_name}",
                status=nm.NotificationStatus.WARNING,
            )

            return False

    # Remove all variants from a variant set
    def _remove_all_variants_from_set(self, v_set_spec):
        if v_set_spec:
            for v in v_set_spec.variants:
                v_set_spec.RemoveVariant(v)

    # Set Variant Selection by Variant Set Name and Variant Name
    def _select_variant(self, vset, vname):
        omni.kit.commands.execute(
            "SelectVariantPrim",
            prim_path=vset.GetPrim().GetPath(),
            vset_name=vset.GetName(),
            var_name=vname,
        )

    # Set variant selection by path
    def _select_variant_by_path(self, path):
        set_name, variant = Sdf.Path(path).GetVariantSelection()
        vset = self._get_variant_set_by_name(set_name)
        self._select_variant(vset, variant)

    # Clear Variant Selection (Unclear now if we actually ever want to do this.)
    def _clear_variant_selection(self, variant_set_name):
        with omni.kit.undo.group():
            omni.kit.commands.execute(
                "SelectVariantPrim",
                prim_path=self._get_root_prim_path(),
                vset_name=variant_set_name,
                var_name=None,
            )

            # Reset active variant only when active variant belongs to input variant set
            active_variant_set_name = self._get_active_variant_set()

            if variant_set_name == active_variant_set_name:
                omni.kit.commands.execute(
                    "SetVariantEditorActiveVariant",
                    variant_path=None,
                )

    # Rename a Variant Set
    def _rename_variant_set(self, old_name, new_name):
        root_prim_path = self._get_root_prim_path()
        old_vset_path = Sdf.Path(root_prim_path).AppendVariantSelection(old_name, "")
        layer = self._get_edit_target_layer()

        if layer.GetObjectAtPath(old_vset_path) is None:
            # Can't rename this variant set bacause it's authored in another layer
            # Find out which layer this variant is in
            variant_layer_name = "another layer."
            authored_layer = self._get_variant_authored_layer(old_vset_path)
            if authored_layer is not None:
                authored_layer_name = authored_layer.GetDisplayName()
                variant_layer_name = (
                    f'layer: "{authored_layer_name}".\nPlease switch to that layer to rename variant set.'
                )

            nm.post_notification(
                f"Couldn't rename variant set because it was authored in {variant_layer_name}",
                status=nm.NotificationStatus.WARNING,
            )

            return None
        elif not self._is_variant_set_name_available(new_name):
            nm.post_notification(
                "That variant set name is not available. Please try another name.",
                status=nm.NotificationStatus.WARNING,
            )
            return None
        else:
            with omni.kit.undo.group():
                prim = self._stage.GetPrimAtPath(root_prim_path)
                vset = prim.GetVariantSet(old_name)
                v_name = vset.GetVariantSelection()
                old_variant_path = prim.GetPath().AppendVariantSelection(old_name, v_name).pathString

                result, ret = omni.kit.commands.execute(
                    "RenameVariantSet",
                    prim_path=root_prim_path,
                    variant_set_name=old_name,
                    new_name=new_name,
                )
                if ret:
                    if old_variant_path == self.active_variant:
                        new_variant_path = prim.GetPath().AppendVariantSelection(new_name, v_name).pathString
                        omni.kit.commands.execute(
                            "SetVariantEditorActiveVariant",
                            variant_path=new_variant_path,
                        )
                    return Sdf.Path(root_prim_path).AppendVariantSelection(new_name, "")
                else:
                    return None

    # Rename a Variant
    def _rename_variant(self, vset, old_name, new_name):
        vset_name = vset.GetName()
        root_prim_path = self._get_root_prim_path()
        old_vnt_path = root_prim_path.AppendVariantSelection(vset_name, old_name)

        new_vnt_path = root_prim_path.AppendVariantSelection(vset_name, new_name)
        layer = self._get_edit_target_layer()
        vspec = layer.GetObjectAtPath(old_vnt_path)

        if vspec is None:
            # Can't rename this variant bacause it's authored in another layer
            # Find out which layer this variant is in
            variant_layer_name = "another layer."
            authored_layer = self._get_variant_authored_layer(old_vnt_path)
            if authored_layer is not None:
                authored_layer_name = authored_layer.GetDisplayName()
                variant_layer_name = f'layer: "{authored_layer_name}".\nPlease switch to that layer to rename variant.'

            nm.post_notification(
                f"Couldn't rename variant because it was authored in {variant_layer_name}",
                status=nm.NotificationStatus.WARNING,
            )

            return None
        elif not self._is_variant_name_available(new_name, vset):
            nm.post_notification(
                f"That variant name is not available.  Please try another name.",
                status=nm.NotificationStatus.WARNING,
            )
            return None
        else:
            with omni.kit.undo.group():
                result, ret = omni.kit.commands.execute(
                    "RenameVariant",
                    prim_path=root_prim_path,
                    variant_set_name=vset_name,
                    variant_name=old_name,
                    new_name=new_name,
                )
                if ret:
                    if old_vnt_path == self.active_variant:
                        new_variant_path = (
                            Sdf.Path(root_prim_path).AppendVariantSelection(vset_name, new_name).pathString
                        )
                        omni.kit.commands.execute(
                            "SetVariantEditorActiveVariant",
                            variant_path=new_variant_path,
                        )
                    return new_vnt_path

    def _duplicate_variant(self, variant_path):
        curr_layer = self._get_edit_target_layer()

        root_prim_path = self._get_root_prim_path()
        vset = Sdf.Path(variant_path).GetVariantSelection()[0]
        old_variant_name = Sdf.Path(variant_path).GetVariantSelection()[1]
        old_variant_path = root_prim_path.AppendVariantSelection(vset, old_variant_name)

        # Check if current layer contains this variant, because it maybe authord in another layer
        variant_spec: Sdf.VariantSpec = curr_layer.GetObjectAtPath(old_variant_path)
        if variant_spec is None:
            # We can't copy this spec bacause it's authored in another layer
            variant_layer_name = "another layer."
            authored_layer = self._get_variant_authored_layer(old_variant_path)
            if authored_layer is not None:
                authored_layer_name = authored_layer.GetDisplayName()
                variant_layer_name = (
                    f'layer: "{authored_layer_name}".\nPlease switch to that layer to duplicate variant.'
                )

            nm.post_notification(
                f"Couldn't duplicate variant because it was authored in {variant_layer_name}",
                status=nm.NotificationStatus.WARNING,
            )
            return None, None
        else:
            result, new_variant_name = omni.kit.commands.execute(
                "DuplicateVariant",
                prim_path=root_prim_path,
                variant_set_name=vset,
                variant_name=old_variant_name,
                new_name=old_variant_name,
                auto_postfix=True,
            )

            new_variant_path = root_prim_path.AppendVariantSelection(vset, new_variant_name)

            return new_variant_path, new_variant_name

    def _copy_custom_display_name(self, prim: Usd.Prim, prop_name: str, vset: Usd.VariantSet):
        custom_display_name = self.get_property_display_name(prim.GetPath().AppendProperty(prop_name))
        if custom_display_name:
            paths = [prim.GetPath().AppendProperty(prop_name)]
            cmd_args = {
                "object_paths": paths,
                "key": Sdf.PropertySpec.DisplayNameKey,
                "value": custom_display_name,
            }
            omni.kit.commands.execute(
                "EditVariant",
                prim_path=vset.GetPrim().GetPath().pathString,
                variant_set_name=vset.GetName(),
                cmd_name="ChangeMetadata",
                cmd_args=cmd_args,
            )

    # Add a new property (Attribute or Relationship) to a variant
    def _add_variant_property(self, prim_path, prop_class, prop_name, prop_value_type=None, target_path=None):
        prim = self._stage.GetPrimAtPath(prim_path)
        prim_def = prim.GetPrimDefinition()
        vset_name = self._get_active_variant_set()
        vset = self._get_variant_set_by_name(vset_name)
        new_props = []

        def add_property(prop_class, prop_name):
            def get_existing_prop_default_value(existing_prop):
                existing_prop_value = None
                prop_spec = prim_def.GetSchemaPropertySpec(existing_prop.GetPath().name)
                if prop_spec and prop_spec.default is not None:
                    existing_prop_value = prop_spec.default
                elif prop_spec and prop_spec.typeName:
                    warning_msg = f'Property "{prop_name}" of "{prim.GetPath()}" does not have a default value. Fallback to type\'s default value.'
                    carb.log_warn(warning_msg)
                    existing_prop_value = prop_spec.typeName.defaultValue
                elif prim.GetTypeName() == "Shader" and prop_name.startswith("inputs:"):
                    usdshade_shader = UsdShade.Shader(prim)
                    sdr_shader_node = usdshade_shader.GetShaderNodeForSourceType("mdl")
                    if sdr_shader_node and hasattr(sdr_shader_node, "GetShaderInput"):
                        sdr_shader_property = sdr_shader_node.GetShaderInput(prop_name[7:])  # remove "inputs:" prefix
                        if sdr_shader_property:
                            existing_prop_value = sdr_shader_property.GetDefaultValue()
                    if existing_prop_value is None:
                        carb.log_warn(f'Could not get default for shader input "{prop_name}" on {prim.GetPath()}.')
                else:
                    warning_msg = f'Property "{prop_name}" of "{prim.GetPath()}" does not have a valid type. Please check your attribute.'
                    carb.log_warn(warning_msg)
                return existing_prop_value

            # Attributes
            if prop_class in (Usd.Attribute, Sdf.AttributeSpec):
                # Some properties need to be processed together
                for prop_list in self._paired_properties:
                    if prop_name in prop_list:
                        props = []
                        for paired_property_name in prop_list:
                            existing_prop = prim.GetAttribute(paired_property_name)
                            existing_prop_value = existing_prop.Get()
                            if existing_prop_value is None:
                                existing_prop_value = get_existing_prop_default_value(existing_prop)

                            # Capture value of existing property
                            omni.kit.commands.execute(
                                "EditVariant",
                                prim_path=vset.GetPrim().GetPath().pathString,
                                variant_set_name=vset_name,
                                cmd_name="ChangeProperty",
                                cmd_args={
                                    "prop_path": existing_prop.GetPath(),
                                    "value": existing_prop_value,
                                    "prev": None,
                                },
                            )
                            props.append(existing_prop)
                        # We want to get and set all linked properties, but we only want to make one card.  The widgets should be built together.
                        return props
                    else:
                        existing_prop = prim.GetAttribute(prop_name)
                        existing_prop_value = existing_prop.Get()
                        if existing_prop_value is None:
                            existing_prop_value = get_existing_prop_default_value(existing_prop)

                        omni.kit.commands.execute(
                            "EditVariant",
                            prim_path=vset.GetPrim().GetPath().pathString,
                            variant_set_name=vset_name,
                            cmd_name="ChangeProperty",
                            cmd_args={
                                "prop_path": existing_prop.GetPath(),
                                "value": existing_prop_value,
                                "prev": None,
                            },
                        )
                        return existing_prop
            # Relationships
            elif prop_class in (Usd.Relationship, Sdf.RelationshipSpec):
                omni.kit.commands.execute(
                    "EditVariant",
                    prim_path=vset.GetPrim().GetPath().pathString,
                    variant_set_name=vset_name,
                    cmd_name="CreateUsdRelationship",
                    cmd_args={"prim": prim, "rel_name": prop_name},
                )
                prop = prim.GetRelationship(prop_name)
                current_targets = prop.GetTargets()
                for target in current_targets:
                    omni.kit.commands.execute(
                        "EditVariant",
                        prim_path=vset.GetPrim().GetPath().pathString,
                        variant_set_name=vset_name,
                        cmd_name="AddRelationshipTarget",
                        cmd_args={"relationship": prop, "target": target},
                    )
                return prim.GetRelationship(prop_name)
            # Variant Selections
            elif prop_class == Usd.VariantSet:
                target_set = prim.GetVariantSet(prop_name)
                target_var = target_set.GetVariantSelection()

                omni.kit.commands.execute(
                    "EditVariant",
                    prim_path=vset.GetPrim().GetPath().pathString,
                    variant_set_name=vset_name,
                    cmd_name="SelectVariantPrim",
                    cmd_args={
                        "prim_path": prim.GetPath(),
                        "vset_name": prop_name,
                        "var_name": target_var,
                    },
                )
                return target_set
            else:
                carb.log_warn(
                    "Property type is not Attribute, Relationship or Variant Selection.  Could not create property"
                )
                return None

        with omni.kit.undo.group(), self.AuthorVariant():
            # if property exists in session layer, we have to move
            # it to authoring layer first.
            omni.kit.commands.execute("CollapseSessionProperty", prim=prim, prop_name=prop_name)
            new_prop = add_property(prop_class, prop_name)
            # copy display name of property into variant one
            self._copy_custom_display_name(prim, prop_name, vset)

            # Handle the case where add_property returns a list of properties (for paired properties)
            if isinstance(new_prop, list):
                new_props.extend(new_prop)
            else:
                new_props.append(new_prop)

            active_variant_name = Sdf.Path(self.active_variant).GetVariantSelection()[1]

            if self._settings.get(e_c.ADD_PROPS_TO_ALL_VARIANTS_SETTING) is True:
                for variant in vset.GetVariantNames():
                    if variant == active_variant_name:
                        continue

                    omni.kit.commands.execute(
                        "SelectVariantPrim",
                        prim_path=vset.GetPrim().GetPath(),
                        vset_name=vset.GetName(),
                        var_name=variant,
                    )

                    new_prop = add_property(prop_class, prop_name)
                    self._copy_custom_display_name(prim, prop_name, vset)

                    # Handle the case where add_property returns a list (for paired properties)
                    if isinstance(new_prop, list):
                        for prop in new_prop:
                            mapped_prop = vset.GetVariantEditTarget().MapToSpecPath(prop.GetPath())
                            new_props.append(mapped_prop)
                    else:
                        new_prop = vset.GetVariantEditTarget().MapToSpecPath(new_prop.GetPath())
                        new_props.append(new_prop)

                omni.kit.commands.execute(
                    "SelectVariantPrim",
                    prim_path=vset.GetPrim().GetPath(),
                    vset_name=vset.GetName(),
                    var_name=active_variant_name,
                )

        if new_props:
            return new_props
        else:
            return None

    # Remove a property from a variant

    def _remove_variant_property(self, prim_path, property):
        if not self.validate_variant_edit():
            return

        if isinstance(property, Sdf.PropertySpec):
            prop_name = property.name
        elif isinstance(property, Usd.Property):
            prop_name = property.GetName()
        elif isinstance(property, Usd.VariantSet):
            prop_name = property.GetName()
            prim_spec = self._get_prim_spec_from_path(prim_path)
            selections = prim_spec.variantSelections
            # TODO: Trying to figure out how to find these orphaned variant specs and delete them
        set_name = self._get_active_variant_set()
        vset = self._get_variant_set_by_name(set_name)
        with self.AuthorVariant():
            prim_path = Sdf.Path(prim_path).StripAllVariantSelections()
            if isinstance(property, Usd.VariantSet):
                omni.kit.commands.execute(
                    "EditVariant",
                    prim_path=vset.GetPrim().GetPath().pathString,
                    variant_set_name=set_name,
                    cmd_name="SelectVariantPrim",
                    cmd_args={
                        "prim_path": prim_path,
                        "vset_name": prop_name,
                        "var_name": "",
                    },
                )
            else:
                omni.kit.commands.execute(
                    "EditVariant",
                    prim_path=vset.GetPrim().GetPath().pathString,
                    variant_set_name=set_name,
                    cmd_name="RemoveProperty",
                    cmd_args={
                        "prop_path": prim_path.AppendProperty(prop_name),
                        "remove_from_layers": [vset.GetPrim().GetStage().GetEditTarget().GetLayer()],
                    },
                )

    # Remove references from a variant
    def _clear_variant_references(self, prim_path, references):
        # todo. clean up without using _remove_variant_reference.
        with omni.kit.undo.group():
            for ref in references:
                self._remove_variant_reference(prim_path, ref)

    # Remove payloads from a variant
    def _clear_variant_payloads(self, prim_path, payloads):
        # todo. clean up without using _remove_variant_payload.
        with omni.kit.undo.group():
            for p in payloads:
                self._remove_variant_payload(prim_path, p)

    # Remove a reference from a variant
    def _remove_variant_reference(self, prim_path, reference):
        if not self.validate_variant_edit():
            return

        prim_path = Sdf.Path(prim_path).StripAllVariantSelections()
        prim = self._stage.GetPrimAtPath(prim_path)
        edit_target_layer = self._get_edit_target_layer()
        set_name = self._get_active_variant_set()
        vset = self._get_variant_set_by_name(set_name)
        refs_and_layers = omni.usd.get_composed_references_from_prim(prim)
        with self.AuthorVariant():
            for ref, intro_layer in refs_and_layers:
                layer_weak = weakref.ref(intro_layer) if intro_layer else None
                intro_layer = layer_weak() if layer_weak else None
                if intro_layer and intro_layer != edit_target_layer:
                    reference = self.anchor_reference_asset_path_to_layer(reference, intro_layer, edit_target_layer)

                omni.kit.commands.execute(
                    "EditVariant",
                    prim_path=vset.GetPrim().GetPath().pathString,
                    variant_set_name=set_name,
                    cmd_name="RemoveReference",
                    cmd_args={
                        "stage": self._stage,
                        "prim_path": prim_path,
                        "reference": reference,
                    },
                )

    # Remove a payload from a variant
    def _remove_variant_payload(self, prim_path, payload):
        if not self.validate_variant_edit():
            return

        prim_path = Sdf.Path(prim_path).StripAllVariantSelections()
        prim = self._stage.GetPrimAtPath(prim_path)
        edit_target_layer = self._get_edit_target_layer()
        set_name = self._get_active_variant_set()
        vset = self._get_variant_set_by_name(set_name)
        refs_and_layers = omni.usd.get_composed_payloads_from_prim(prim)
        with self.AuthorVariant():
            for ref, intro_layer in refs_and_layers:
                layer_weak = weakref.ref(intro_layer) if intro_layer else None
                intro_layer = layer_weak() if layer_weak else None
                if intro_layer and intro_layer != edit_target_layer:
                    payload = self.anchor_payload_asset_path_to_layer(payload, intro_layer, edit_target_layer)

                omni.kit.commands.execute(
                    "EditVariant",
                    prim_path=vset.GetPrim().GetPath().pathString,
                    variant_set_name=set_name,
                    cmd_name="RemovePayload",
                    cmd_args={
                        "stage": self._stage,
                        "prim_path": prim_path,
                        "payload": payload,
                    },
                )

    # Variants in referenced layers should not be edited
    def validate_variant_edit(self, show_warning=True):
        if not self.active_variant:
            return True

        vs_name, v_name = Sdf.Path(self.active_variant).GetVariantSelection()

        v_spec = self._find_variant_spec(vs_name, v_name)
        if not v_spec:
            return True

        self._stage.HasLocalLayer(v_spec.layer)
        if self._stage.HasLocalLayer(v_spec.layer):
            if v_spec.path.HasPrefix(self._get_root_prim_path()):
                return True

        if show_warning:
            message = f"Couldn't edit variant because it is authored in a referenced layer {v_spec.layer.identifier}"
            carb.log_warn(message)
            nm.post_notification(message, status=nm.NotificationStatus.WARNING)
        self.ref_prim_path = v_spec.layer.identifier
        return False

    # Update variant attribute doesn't record, it's for editing purpose
    def _update_variant_attribute(self, attr_path, value):
        if not self.validate_variant_edit(False):
            return

        vset_name = self._get_active_variant_set()
        vset = self._get_variant_set_by_name(vset_name)
        with vset.GetVariantEditContext():
            attr = self._stage.GetAttributeAtPath(attr_path)
            omni.usd.set_prop_val(attr, value, Usd.TimeCode.Default(), auto_target_layer=False)

    # Set the value for a variant within variant edit context
    def _set_variant_attribute(self, attr_path, value, prev=None):
        if not self.validate_variant_edit():
            return

        vset_name = self._get_active_variant_set()
        vset = self._get_variant_set_by_name(vset_name)
        with self.AuthorVariant():
            omni.kit.commands.execute(
                "EditVariant",
                prim_path=vset.GetPrim().GetPath().pathString,
                variant_set_name=vset_name,
                cmd_name="ChangeProperty",
                cmd_args={"prop_path": attr_path, "value": value, "prev": prev},
            )

    def _set_variant_selection_as_attribute(self, prim_path, variant_set_name, variant_name):
        if not self.validate_variant_edit():
            return

        meta_vset_name = self._get_active_variant_set()
        with self.AuthorVariant():
            omni.kit.commands.execute(
                "EditVariant",
                prim_path=self._get_root_prim_path().pathString,
                variant_set_name=meta_vset_name,
                cmd_name="SelectVariantPrim",
                cmd_args={
                    "prim_path": prim_path,
                    "vset_name": variant_set_name,
                    "var_name": variant_name,
                },
            )

    # Set relationship targets within a variant edit context
    def _set_relationship_value(self, prop, value):
        if not self.validate_variant_edit():
            return

        vset_name = self._get_active_variant_set()
        vset = self._get_variant_set_by_name(vset_name)
        with self.AuthorVariant():
            omni.kit.commands.execute(
                "EditVariant",
                prim_path=vset.GetPrim().GetPath().pathString,
                variant_set_name=vset_name,
                cmd_name="SetRelationshipTargets",
                cmd_args={"relationship": prop, "targets": value},
            )

    # Add a new reference or payload to a variant with a given asset path, within variant edit context
    def _add_ref_or_payload(self, prim_path, name, asset_path):
        if not self.validate_variant_edit():
            return

        if asset_path:
            vset_name = self._get_active_variant_set()
            vset = self._get_variant_set_by_name(vset_name)
            with self.AuthorVariant():
                if name == "Reference":
                    args = {
                        "stage": vset.GetPrim().GetStage(),
                        "prim_path": prim_path,
                        "reference": Sdf.Reference(asset_path),
                    }
                    omni.kit.commands.execute(
                        "EditVariant",
                        prim_path=vset.GetPrim().GetPath().pathString,
                        variant_set_name=vset_name,
                        cmd_name="AddReference",
                        cmd_args=args,
                    )
                else:
                    args = {
                        "stage": vset.GetPrim().GetStage(),
                        "prim_path": prim_path,
                        "payload": Sdf.Payload(asset_path),
                    }
                    omni.kit.commands.execute(
                        "EditVariant",
                        prim_path=vset.GetPrim().GetPath().pathString,
                        variant_set_name=vset_name,
                        cmd_name="AddPayload",
                        cmd_args=args,
                    )
        else:
            carb.log_warn("No valid asset path provided.")

    # Automatically create variants in a given variant set, create payloads or references based on a given list of assets
    def _create_geom_variant_from_files(self, vset_name, file_list, ref_type):
        self._update_context_and_stage()
        root_path = self._get_root_prim_path()
        vset = self._get_variant_set_by_name(vset_name)
        with omni.kit.undo.group(), self.AuthorVariant():
            for variant_file in file_list:
                usd_path = variant_file
                variant_name = usd_path.split("/")[-1]
                variant_name = variant_name.split(".")[0]
                self._create_variant(vset_name, variant_name)
                self._select_variant(vset, variant_name)
                variant_path = vset.GetPrim().GetPath().AppendVariantSelection(vset_name, variant_name).pathString
                omni.kit.commands.execute("SetVariantEditorActiveVariant", variant_path=variant_path)
                ref_name = None
                if ref_type != "payload":
                    ref_name = "Reference"
                self._add_ref_or_payload(root_path, ref_name, usd_path)

    # Automatically create variants in a given variant set, create material bindings based on a given list of materials
    def _create_material_variant_from_files(self, vset_name, mat_list):
        self._update_context_and_stage()
        root_path = self._get_root_prim_path()
        root_prim = self._stage.GetPrimAtPath(root_path)
        vset = self._get_variant_set_by_name(vset_name)
        with omni.kit.undo.group(), self.AuthorVariant():
            for mat_path in mat_list:
                variant_name = mat_path.split("/")[-1]
                variant_name = variant_name.split(".")[0]
                material_stage_path = matlib.create_mdl_material(
                    self._stage, mat_path, variant_name, on_create_fn=self._mat_created
                )
                self._create_variant(vset_name, variant_name)
                self._select_variant(vset, variant_name)
                rel_a = root_prim.CreateRelationship("material:binding")
                omni.kit.commands.execute(
                    "EditVariant",
                    prim_path=vset.GetPrim().GetPath().pathString,
                    variant_set_name=vset_name,
                    cmd_name="AddRelationshipTarget",
                    cmd_args={"relationship": rel_a, "target": material_stage_path},
                )

    def _mat_created(self, prim):
        pass

    def _create_visibility_variant_from_files(self, vset_name, file_list, ref_type):
        self._update_context_and_stage()
        root_path = self._get_root_prim_path()
        vset = self._get_variant_set_by_name(vset_name)
        new_prims = []
        for variant_file in file_list:
            usd_path = variant_file
            variant_name = usd_path.split("/")[-1]
            variant_name = variant_name.split(".")[0]
            new_prim_path = Sdf.Path(root_path.AppendPath(variant_name))
            new_prim_path = omni.usd.get_stage_next_free_path(self._stage, new_prim_path, False)
            omni.kit.commands.execute(
                "CreatePrim",
                prim_path=new_prim_path,
                prim_type="Xform",
            )
            new_prim = self._stage.GetPrimAtPath(new_prim_path)
            new_prims.append(new_prim)
            self._create_variant(vset.GetName(), variant_name)

            if ref_type != "payload":
                omni.kit.commands.execute(
                    "AddReference",
                    stage=new_prim.GetStage(),
                    prim_path=new_prim_path,
                    reference=Sdf.Reference(usd_path),
                )
            else:
                omni.kit.commands.execute(
                    "AddPayload",
                    stage=new_prim.GetStage(),
                    prim_path=new_prim_path,
                    payload=Sdf.Payload(usd_path),
                )

        for prim in new_prims:
            for variant in vset.GetVariantNames():
                self._select_variant(vset, variant)
                omni.kit.commands.execute(
                    "SetVariantEditorActiveVariant",
                    variant_path=root_path.AppendVariantSelection(vset_name, variant_name),
                )
                if prim.GetName() == variant:
                    value = "inherited"
                else:
                    value = "invisible"
                omni.kit.commands.execute(
                    "EditVariant",
                    prim_path=vset.GetPrim().GetPath().pathString,
                    variant_set_name=vset.GetName(),
                    cmd_name="ChangeProperty",
                    cmd_args={
                        "prop_path": prim.GetPath().AppendProperty("visibility"),
                        "value": value,
                        "prev": None,
                    },
                )

    # ================== Local Utility ==================
    # Clears All Lists

    def _clear_all(self):
        self._variant_specs.clear()
        self.active_variant = None
        self._target_prim_path = None

    # Updates USD Context and Stage
    def _update_context_and_stage(self, usd_context_name: str = ""):
        self._usd_context = omni.usd.get_context(usd_context_name)
        self._stage = self._usd_context.get_stage()
        self._custom_data_backup_layer = Sdf.Layer.CreateAnonymous()

    # Updates the root prim path
    def _update_root_prim_path(self, path):
        self._target_prim_path = path

    def _get_active_variant(self):
        return self._active_variant

    def _get_active_variant_set(self) -> str:
        var = self._active_variant
        if var:
            vset = Sdf.Path(var).GetVariantSelection()[0]
            return vset
        else:
            return None

    # Returns the root prim path
    def _get_root_prim_path(self) -> Sdf.Path:
        if self._target_prim_path is not None:
            return Sdf.Path(self._target_prim_path)
        else:
            return self._usd_context.get_stage().GetDefaultPrim().GetPath()

    # Get Authoring layer
    def _get_edit_target_layer(self):
        return self._stage.GetEditTarget().GetLayer()

    # Get Prim Spec
    def _get_prim_spec_from_path(self, path):
        return self._get_edit_target_layer().GetObjectAtPath(path)

    # Get variant sets from a given path
    def _get_variant_set_names_from_path(self, path):
        prim = self._stage.GetPrimAtPath(path)
        return prim.GetVariantSets().GetNames()

    # Get all variants from a given variant set
    def _get_variants_from_set(self, vset):
        if isinstance(vset, str):
            vset = self._get_variant_set_by_name(vset)
        elif isinstance(vset, Sdf.PrimSpec):
            return vset.variants
        return vset.GetVariantNames()

    def _get_variants_from_active_set(self):
        vset_name = Sdf.Path(self._active_variant).GetVariantSelection()[0]
        vset = self._get_variant_set_by_name(vset_name)
        return vset.GetVariantNames()

    # Get the layer that given variant is authored in
    def _get_variant_authored_layer(self, variant_path: Sdf.Path):
        for layer in self._stage.GetLayerStack():
            vspec_in_layer = layer.GetObjectAtPath(variant_path)
            if vspec_in_layer is not None:
                return layer

        return None

    # Get all variants from a given variant set spec
    def _get_variants_from_spec(self, spec):
        return spec.variants

    # Get Variant Sets from the Root Prim
    def _collect_variant_sets(self) -> list[str]:
        root_path = self._get_root_prim_path()
        variant_sets = self._get_variant_set_names_from_path(root_path)
        return variant_sets

    # Get all variant specs from a given spec and its children.
    # This information is used to populate the prim list and property list when selecting a variant.
    def _get_variant_specs(self, spec=None):
        layers = self._stage.GetLayerStack()
        layer = self._get_edit_target_layer()
        if not spec:
            self._variant_specs = set()
            spec = self._active_variant
        for layer in layers:
            if isinstance(spec, str):
                vspec = layer.GetObjectAtPath(Sdf.Path(spec))
            elif isinstance(spec, Sdf.Path):
                vspec = layer.GetObjectAtPath(spec)
            else:
                vspec = layer.GetObjectAtPath(Sdf.Path(spec.path))
            if vspec:
                if isinstance(vspec, Sdf.PrimSpec):
                    vPrimSpec = vspec
                elif isinstance(vspec, Sdf.VariantSpec):
                    self._variant_specs.update([vspec])
                    vPrimSpec = vspec.primSpec
                children = vPrimSpec.nameChildren
                if vPrimSpec:
                    if vPrimSpec.specifier == Sdf.SpecifierOver:
                        self._variant_specs.update([vspec])
                    if len(children) > 0:
                        for c in children:
                            self._variant_specs.update(self._get_variant_specs(c))
                    else:
                        continue
                else:
                    continue
            else:
                continue

        return self._variant_specs

    # Finds the strongest variant spec in prim stack
    def _find_variant_spec(self, vset_name, v_name):
        prim = self._stage.GetPrimAtPath(self._get_root_prim_path())
        for prim_spec in prim.GetPrimStack():
            if vset_name not in prim_spec.variantSets:
                continue

            vset_spec = prim_spec.variantSets[vset_name]
            for v_spec in vset_spec.variantList:
                if v_spec.name != v_name:
                    continue

                if self._stage.HasLocalLayer(v_spec.layer):
                    if self._stage.GetEditTarget().GetLayer() != v_spec.layer:
                        return

                return v_spec

    def find_spec_in_variant(self, spec_path):
        v_path = Sdf.Path(spec_path)
        while not v_path.IsAbsoluteRootPath() and v_path.GetParentPath() != self._get_root_prim_path():
            v_path = v_path.GetParentPath()

        vset_name, v_name = v_path.GetVariantSelection()
        v_spec = self._find_variant_spec(vset_name, v_name)
        if not v_spec:
            return None
        # To find a spec in variant in a referenced layer, we need to convert the path in the stage to path in that layer.
        spec_path = spec_path.ReplacePrefix(v_path, v_spec.path)

        return v_spec.layer.GetObjectAtPath(spec_path)

    # Collects prims with authored data in a variant
    def _check_specs_for_properties(self, v_path) -> Set[Sdf.Path]:
        vset_name, v_name = Sdf.Path(v_path).GetVariantSelection()
        v_spec = self._find_variant_spec(vset_name, v_name)
        if not v_spec:
            return set()

        prim_paths = set()

        # Collects prims added by users
        if self._stage.HasLocalLayer(v_spec.layer):
            added_prim_paths = v_spec.primSpec.customData.get("variantPrimPaths")
            if added_prim_paths:
                for relative_path in added_prim_paths:
                    stage_path = Sdf.Path(self._get_root_prim_path()).AppendPath(relative_path)
                    if self._stage.GetPrimAtPath(stage_path):
                        path = v_spec.path.AppendPath(relative_path).ReplacePrefix(
                            v_spec.owner.owner.path, self._get_root_prim_path()
                        )
                        prim_paths.add(path)
                    else:
                        self._remove_prim_path_from_metadata(v_spec.path, relative_path)

        # Collects prims with authored data
        def collect_prims(prim_spec):
            should_collect = False
            if (
                prim_spec.properties
                or prim_spec.payloadList.GetAddedOrExplicitItems()
                or prim_spec.referenceList.GetAddedOrExplicitItems()
            ):
                should_collect = True
            elif prim_spec.variantSelections:
                # If there are variant selections in the spec, make sure to ignore our own variant set
                for selection_set in prim_spec.variantSelections.keys():
                    if selection_set != vset_name:
                        should_collect = True

            if should_collect:
                path = prim_spec.path.ReplacePrefix(v_spec.owner.owner.path, self._get_root_prim_path())
                prim_paths.update([path])

            for child in prim_spec.nameChildren:
                collect_prims(child)

        collect_prims(v_spec.primSpec)

        return prim_paths

    # Find a specific variant set by name at the root prim path
    def _get_variant_set_by_name(self, name) -> Usd.VariantSet or None:
        prim = self._stage.GetPrimAtPath(self._get_root_prim_path())
        vsets = prim.GetVariantSets()
        if name:
            return vsets.GetVariantSet(name)
        else:
            return None

    # Get Reference Asset Path
    def _get_ref_path(self, prim):
        all_references = []
        for prim_spec in prim.GetPrimStack():
            if prim_spec.hasReferences:
                all_references.extend(prim_spec.referenceList.GetAddedOrExplicitItems())
        return all_references[0].assetPath

    # Helper Function to get the current Variant Edit Context
    def _get_variant_edit_context(self):
        vset_name = self._get_active_variant_set()
        vset = self._get_variant_set_by_name(vset_name)
        variantContext = vset.GetVariantEditContext()
        return variantContext

    # Asset Paths need to be anchored to the edit target for proper retargeting of references
    def anchor_reference_asset_path_to_layer(self, ref: Sdf.Reference, intro_layer: Sdf.Layer, anchor_layer: Sdf.Layer):
        asset_path = ref.assetPath
        if asset_path:
            asset_path = intro_layer.ComputeAbsolutePath(asset_path)
            if not anchor_layer.anonymous:
                asset_path = omni.client.make_relative_url(anchor_layer.identifier, asset_path)

            # make a copy as Reference is immutable
            ref = Sdf.Reference(
                assetPath=asset_path.replace("\\", "/"),
                primPath=ref.primPath,
                layerOffset=ref.layerOffset,
                customData=ref.customData,
            )
        return ref

    # Asset Paths need to be anchored to the edit target for proper retargeting of payloads
    def anchor_payload_asset_path_to_layer(self, ref: Sdf.Payload, intro_layer: Sdf.Layer, anchor_layer: Sdf.Layer):
        asset_path = ref.assetPath
        if asset_path:
            asset_path = intro_layer.ComputeAbsolutePath(asset_path)
            if not anchor_layer.anonymous:
                asset_path = omni.client.make_relative_url(anchor_layer.identifier, asset_path)

            # make a copy as Payload is immutable
            ref = Sdf.Payload(
                assetPath=asset_path.replace("\\", "/"),
                primPath=ref.primPath,
                layerOffset=ref.layerOffset,
            )
        return ref

    def _get_next_valid_variant_name(self, name: str, vset) -> str:
        pattern = r"_\d+$"
        match = re.search(pattern, name)
        if match:
            name = re.sub(match.group(), "", name)
        if self._is_variant_name_available(name, vset):
            return name

        for index in range(1, 1000):
            next = f"{name}_{index}"
            if self._is_variant_name_available(next, vset):
                return next
        else:
            return name

    def _is_variant_name_available(self, name, vset) -> bool:
        for existing_name in self._get_variants_from_set(vset):
            if existing_name == name:
                return False
        return True

    def _add_target_prim_metadata(self, variant_path: Sdf.Path, new_path: Sdf.Path):
        layer = self._get_edit_target_layer()
        v_spec = layer.GetObjectAtPath(variant_path)
        v_primspec = v_spec.primSpec
        custom_data = v_primspec.customData

        if custom_data.get("variantPrimPaths"):
            current_variant_prim_paths = set(custom_data.get("variantPrimPaths"))
        else:
            current_variant_prim_paths = set()

        vpp_len = len(current_variant_prim_paths)

        if isinstance(new_path, str):
            current_variant_prim_paths.add(new_path)
        elif isinstance(new_path, Sdf.Path):
            current_variant_prim_paths.add(new_path.pathString)
        custom_data["variantPrimPaths"] = Vt.StringArray(current_variant_prim_paths)
        if len(custom_data["variantPrimPaths"]) == vpp_len + 1:
            omni.kit.commands.execute(
                "ChangeMetadata",
                object_paths=[variant_path],
                key="customData",
                value=custom_data,
            )

    def _remove_prim_path_from_metadata(self, variant_path: Sdf.Path, removed_prim_path: Sdf.Path):
        layer = self._get_edit_target_layer()
        v_spec = layer.GetObjectAtPath(variant_path)
        if v_spec:
            v_primspec = v_spec.primSpec
            custom_data = v_primspec.customData

            if isinstance(removed_prim_path, str):
                if "}" in removed_prim_path:
                    meta_stem = removed_prim_path.split("}")[1]
                else:
                    meta_stem = removed_prim_path
            if isinstance(removed_prim_path, Sdf.Path):
                meta_stem = removed_prim_path
            if custom_data.get("variantPrimPaths"):
                current_variant_prim_paths = set(custom_data.get("variantPrimPaths"))
            else:
                current_variant_prim_paths = set()

            vpp_len = len(current_variant_prim_paths)

            if isinstance(meta_stem, str):
                if meta_stem in current_variant_prim_paths:
                    current_variant_prim_paths.remove(meta_stem)
            elif isinstance(meta_stem, Sdf.Path):
                if str(meta_stem) in current_variant_prim_paths:
                    current_variant_prim_paths.remove(str(meta_stem))

            if not list(current_variant_prim_paths):
                custom_data["variantPrimPaths"] = Vt.StringArray()

            custom_data["variantPrimPaths"] = Vt.StringArray(current_variant_prim_paths)

            if len(custom_data["variantPrimPaths"]) == vpp_len - 1:
                if len(custom_data["variantPrimPaths"]) == 0:
                    custom_data["variantPrimPaths"] = Vt.StringArray()
                omni.kit.commands.execute(
                    "ChangeMetadata",
                    object_paths=[variant_path],
                    key="customData",
                    value=custom_data,
                )
            if len(custom_data["variantPrimPaths"]) == vpp_len:
                # carb.log_warn(f"This prim path was not in the metadata, but that's okay.  It was probably populated from existing variant data")
                pass
        else:
            # carb.log_warn(f"no variant spec found at {variant_path}")
            pass

    def is_prim_path_in_metadata(self, path_to_check: str):
        all_primspecs_with_path = {}
        active_set_name = self._get_active_variant_set()
        if active_set_name:
            active_set = self._get_variant_set_by_name(active_set_name)
            variant_names = active_set.GetVariantNames()
            for name in variant_names:
                variant_path = Sdf.Path(self._target_prim_path).AppendVariantSelection(active_set_name, name)
                vspec = self.find_spec_in_variant(variant_path)
                if not vspec:
                    continue
                prim_spec = vspec.primSpec
                custom_data = prim_spec.customData
                metadata_prim_paths = custom_data.get("variantPrimPaths")
                if metadata_prim_paths:
                    for stem in metadata_prim_paths:
                        metadata_path = Sdf.Path(self._target_prim_path).AppendPath(stem)
                        if metadata_path == path_to_check:
                            all_primspecs_with_path[prim_spec] = stem
            if len(all_primspecs_with_path) > 0:
                return all_primspecs_with_path
            return False
        return False

    def _is_variant_set_name_available(self, vs_name):
        return vs_name not in self._collect_variant_sets()

    def save_property_metadata(self, prim: Usd.Prim):
        path = prim.GetPath().StripAllVariantSelections()
        if self._custom_data_backup_layer.GetPrimAtPath(path):
            return
        Sdf.CreatePrimInLayer(self._custom_data_backup_layer, path)
        for prim_spec in prim.GetPrimStack()[::-1]:
            for prop in prim_spec.properties:
                if prop.path.StripAllVariantSelections() != prop.path:
                    continue
                Sdf.CopySpec(prop.layer, prop.path, self._custom_data_backup_layer, prop.path)

    def get_property_display_name(self, path: Sdf.Path) -> str:
        prop = self._custom_data_backup_layer.GetPropertyAtPath(path.StripAllVariantSelections())
        if not prop:
            return None
        return prop.displayName

    async def process_prim(self, prim_path):
        prim = self._stage.GetPrimAtPath(Sdf.Path(prim_path).StripAllVariantSelections())
        if not prim:
            return

        if "Shader" == prim.GetTypeName():
            await omni.usd.get_context().load_mdl_parameters_for_prim_async(prim)
            self.save_property_metadata(prim)

    def check_prim_for_property(self, prim_path, property_name):
        prim = self._stage.GetPrimAtPath(prim_path)
        existing_prop_names = prim.GetPropertyNames()
        if property_name in existing_prop_names:
            return True
        if property_name == "material:binding" and omni.usd.is_prim_material_supported(prim):
            return True
        return False
