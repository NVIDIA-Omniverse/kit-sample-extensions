# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.

# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import asyncio
import gc
import random
import string
from enum import Enum
from functools import lru_cache, partial
from typing import List

import carb
import omni.ext
import omni.ui as ui
import omni.usd
from pxr import Sdf, Semantics, Usd, UsdSemantics

WINDOW_NAME = "Semantics Schema Editor"
MENU_PATH = f"Replicator/{WINDOW_NAME}"
LINE_STYLE = {"color": 0xFF9A9A9A}


class LabelWriteType(Enum):
    NEW = 0
    OVERWRITE = 1
    SKIP = 2


class SelectionType(Enum):
    STAGE = 0
    SELECTED = 1


def editor_log(level, message):
    if level == "info":
        carb.log_info(f"[semantics.schema.editor] {message}")
    if level == "warn":
        carb.log_warn(f"[semantics.schema.editor] {message}")
    if level == "error":
        carb.log_error(f"[semantics.schema.editor] {message}")


def id_generator(size=4, chars=string.ascii_uppercase + string.digits + string.ascii_lowercase):
    return "".join(random.choice(chars) for _ in range(size))


def get_unique_instance_name(prim):
    new_instance_name = f"Semantics_{id_generator()}"
    while prim.HasAPI(UsdSemantics.LabelsAPI):
        editor_log("info", "Generating new instance name due to collision!")
        new_instance_name = f"Semantics_{id_generator()}"
    return new_instance_name


@lru_cache()
def _ui_get_menu_delete_glyph():
    return omni.ui.get_custom_glyph_code("${glyphs}/menu_delete.svg")


def remove_string_prefixes(name, prefixes, apply_cumulatively):
    # Remove underscores from start
    while name.startswith("_"):
        name = name[1:]
    if apply_cumulatively:
        # Exhaustively try removing all prefixes
        prefixes_copy = prefixes.copy()
        i = 0
        while i < len(prefixes_copy):
            prefix = prefixes_copy[i]
            if name.startswith(prefix):
                name = name[len(prefix) :]
                del prefixes_copy[i]
                while name.startswith("_"):
                    name = name[1:]
                i = 0
            else:
                i = i + 1
    else:
        # Try removing each prefix once
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix) :]
                while name.startswith("_"):
                    name = name[1:]
    return name


def remove_string_numerical_ending(name):
    while name[-1].isnumeric() or name.endswith("_"):
        name = name[:-1]
    return name


def remove_string_suffixes(name, suffixes, apply_cumulatively):
    # Remove underscores from the end
    while name.endswith("_"):
        name = name[:-1]
    if apply_cumulatively:
        # Exhaustively try removing all suffixes
        suffixes_copy = suffixes.copy()
        i = 0
        while i < len(suffixes_copy):
            suffix = suffixes_copy[i]
            if name.endswith(suffix):
                name = name[: -len(suffix) - 1]
                del suffixes_copy[i]
                while name.endswith("_"):
                    name = name[:-1]
                i = 0
            else:
                i = i + 1
    else:
        # Try removing each suffix once
        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[: -len(suffix) - 1]
                while name.endswith("_"):
                    name = name[:-1]
    return name


def remove_string_separators(name):
    # Clear any remaining underscores
    name = name.replace("_", "")
    return name


def get_prim_auto_label(
    prim,
    prim_types=[],
    remove_numerical_ending=True,
    prefixes=[],
    suffixes=[],
    apply_cumulatively=True,
    remove_separators=True,
):
    name = ""
    if prim.GetTypeName() in prim_types or not prim_types:
        name = str(prim.GetPath()).split("/")[-1]
        if remove_numerical_ending:
            name = remove_string_numerical_ending(name)
        name = remove_string_prefixes(name, prefixes, apply_cumulatively)
        name = remove_string_suffixes(name, suffixes, apply_cumulatively)
        if remove_separators:
            name = remove_string_separators(name)
        if not name:
            carb.log_warn(f"Prim: '{prim.GetPath()}' results in empty label, will be skipped!")
    return name


def add_semantics(prim, semantic_type, semantic_value, mode: str):
    """
    Modifies the semantics labels for a given prim using the SDF API.

    Args:
        prim: The USD prim to modify.
        semantic_type: The type of the semantic label (used as the instance name).
        semantic_value: The value(s) to set for the semantic label. Can be a string or a list of strings.
        mode (str): The operation mode. Can be:
            - "add": Add the given semantic_value(s) to the existing labels.
            - "replace": Replace the existing labels with the given semantic_value(s).
            - "clear": Remove all existing labels and set to the given semantic_value(s).

    """
    stage = omni.usd.get_context().get_stage()

    # Ensure proper path
    if isinstance(prim, str):
        prim_path = Sdf.Path(prim)

    # Get the SdfPrimSpec for this prim
    layer = stage.GetEditTarget().GetLayer()
    prim_spec = layer.GetPrimAtPath(str(prim.GetPath()))
    if prim_spec is None:
        # Prim doesn't exist; create it as a Def
        prim_spec = Sdf.CreatePrimInLayer(layer, str(prim.GetPath()))
        prim_spec.specifier = Sdf.SpecifierDef

    api_schema_token = f"SemanticsLabelsAPI:{semantic_type}"

    # Apply schema while preserving existing API schemas
    apply_schemas(prim_spec, [api_schema_token])

    attr_name = f"semantics:labels:{semantic_type}"

    # Set semantic value
    # semantic_value should be a list of strings here
    if isinstance(semantic_value, str):
        semantic_value = [semantic_value]

    # Add attribute if it doesn't exist
    if attr_name not in prim_spec.attributes:
        Sdf.AttributeSpec(
            prim_spec,
            attr_name,
            Sdf.ValueTypeNames.StringArray,
        )

    labels_attr = prim_spec.attributes[attr_name]
    if mode in ["replace", "clear"]:
        labels_attr.default = semantic_value
    else:
        # Avoid duplicate labels when adding
        existing_labels = list(labels_attr.default) if labels_attr.default is not None else []
        merged_labels = existing_labels.copy()
        for val in semantic_value:
            if val not in merged_labels:
                merged_labels.append(val)
        labels_attr.default = merged_labels


def _remove_semantics_attributes(prim_spec, instance_name=""):
    """Remove semantics attributes from a prim spec.

    Args:
        prim_spec: The prim spec to modify
        instance_name: If specified, remove only this instance. If empty, remove all.
    """
    if instance_name:
        # Remove specific instance attribute
        attr_name = f"semantics:labels:{instance_name}"
        if attr_name in prim_spec.attributes:
            attr_spec = prim_spec.attributes[attr_name]
            del attr_spec.owner.properties[attr_name]
    else:
        # Remove all semantics attributes
        attr_names_to_delete = [
            name for name in list(prim_spec.attributes.keys()) if name.startswith("semantics:labels:")
        ]
        for attr_name in attr_names_to_delete:
            attr_spec = prim_spec.attributes[attr_name]
            del attr_spec.owner.properties[attr_name]


def _update_api_schemas(prim_spec, instance_name=""):
    """Update apiSchemas by filtering out SemanticsLabelsAPI tokens while preserving structure.

    Args:
        prim_spec: The prim spec to modify
        instance_name: If specified, remove only this instance. If empty, remove all.
    """
    existing_apis = prim_spec.GetInfo("apiSchemas")
    if not existing_apis:
        return

    # Define filter function based on whether we're removing a specific instance or all
    if instance_name:
        target_api = f"SemanticsLabelsAPI:{instance_name}"
        filter_func = lambda item: not (isinstance(item, str) and item == target_api)
    else:
        filter_func = lambda item: not (isinstance(item, str) and item.startswith("SemanticsLabelsAPI:"))

    modified = False

    # Filter each section while preserving structure
    for section_name in ["explicitItems", "prependedItems", "appendedItems"]:
        section_items = getattr(existing_apis, section_name, None)

        if section_items is None:
            continue

        original_items = list(section_items)
        filtered_items = [item for item in original_items if filter_func(item)]

        if len(filtered_items) != len(original_items):
            setattr(existing_apis, section_name, filtered_items)
            modified = True

    if modified:
        # Check if any items remain
        has_remaining_items = any(
            getattr(existing_apis, section, None) for section in ["explicitItems", "prependedItems", "appendedItems"]
        )

        if has_remaining_items:
            prim_spec.SetInfo("apiSchemas", existing_apis)
        else:
            # Remove metadata if no schemas remain
            prim_spec.ClearInfo("apiSchemas")


def clear_semantics(prim, instance_name=""):
    """Clear semantics labels and applied API tokens from a prim while preserving structure.

    Args:
        prim: The USD prim whose semantics will be cleared.
        instance_name: If specified, only clear this specific instance. If empty, clear all semantics.

    Notes:
        Performs removal by:
        - Deleting semantics:labels:* attributes
        - Filtering out SemanticsLabelsAPI:* tokens from apiSchemas
        - Preserving the original structure (explicit/prepended/appended)
    """
    stage = omni.usd.get_context().get_stage()
    if not stage:
        return ""

    layer = stage.GetEditTarget().GetLayer()
    prim_spec = layer.GetPrimAtPath(str(prim.GetPath()))
    if prim_spec is None:
        # Nothing authored for this prim in the current layer
        return ""

    # Remove semantics attributes
    _remove_semantics_attributes(prim_spec, instance_name)

    # Update apiSchemas
    _update_api_schemas(prim_spec, instance_name)


def clear_semantics_legacy(prim):
    """Remove all legacy SemanticsAPI schemas from a prim.

    Args:
        prim: The USD prim to clear legacy semantics from.
    """
    if prim.HasAPI(Semantics.SemanticsAPI):
        for schema in prim.GetAppliedSchemas():
            if schema.startswith("SemanticsAPI"):
                prim.RemoveAppliedSchema(schema)


def convert_legacy_semantics(prim, preserve_legacy=False):
    """Convert legacy SemanticsAPI instances to new SemanticsLabelsAPI format.

    Args:
        prim: The USD prim to convert.
        preserve_legacy: If True, keep the old schemas alongside new ones.

    Returns:
        Dict[str, List[str]]: Dictionary mapping semantic types to label lists.
    """
    legacy_semantics = {}

    if not prim.HasAPI(Semantics.SemanticsAPI):
        return legacy_semantics

    # Extract legacy semantics data
    for schema in prim.GetAppliedSchemas():
        if schema.startswith("SemanticsAPI:"):
            instance_name = schema.split(":", 1)[1]
            sem_old = Semantics.SemanticsAPI.Get(prim, instance_name)
            if sem_old:
                sem_type = sem_old.GetSemanticTypeAttr().Get()
                sem_data = sem_old.GetSemanticDataAttr().Get()

                # Only convert if we have valid data
                if sem_type and sem_data:
                    if sem_type not in legacy_semantics:
                        legacy_semantics[sem_type] = []
                    legacy_semantics[sem_type].append(sem_data)

    # Remove legacy schemas if not preserving
    if not preserve_legacy and legacy_semantics:
        clear_semantics_legacy(prim)

    return legacy_semantics


def apply_schemas(prim_spec: Sdf.Spec, schemas: List[str]):
    """Applies USD schemas to a prim spec and creates their default attributes.

    Args:
        prim_spec: Prim spec to apply schemas to
        schemas: List of schema classes to apply
    """
    schema_registry = Usd.SchemaRegistry()

    for schema in schemas:
        if not isinstance(schema, str):
            raise ValueError(f"Encountered invalid schema {schema}. Schema must be defined as a string")
        # Check if this is a concrete/typed schema or an API schema
        concrete_def = schema_registry.FindConcretePrimDefinition(schema)
        # Split schema_name from schema_name:instance_name if schema is provided as a multi-apply schema
        schema_instance = schema.split(":")
        schema_name = schema_instance[0]
        instance_name = schema_instance[1] if len(schema_instance) == 2 else ""
        api_def = schema_registry.FindAppliedAPIPrimDefinition(schema_name)

        if not concrete_def and not api_def:
            raise ValueError(f"Schema {schema} not found")

        is_multiple_apply = schema_registry.IsMultipleApplyAPISchema(schema_name)

        if concrete_def:
            prim_spec.typeName = schema
        elif api_def:
            # This is an API schema
            # Get the current apiSchemas metadata. Avoid forcing an explicit list-op,
            # which can mask weaker layer opinions (e.g., physics API schemas).
            api_schemas = prim_spec.GetInfo("apiSchemas") or Sdf.TokenListOp()

            # Helper: determine if schema token is already present in this layer's list-op
            def _op_contains(op, token: str) -> bool:
                lists = []
                if getattr(op, "explicitItems", None):
                    lists.append(op.explicitItems)
                if getattr(op, "prependedItems", None):
                    lists.append(op.prependedItems)
                if getattr(op, "appendedItems", None):
                    lists.append(op.appendedItems)
                return any(token in lst for lst in lists)

            if _op_contains(api_schemas, schema):
                continue

            # Prefer updating explicit items only if explicit is already used in this layer;
            # otherwise append to appendedItems to preserve weaker opinions.
            if getattr(api_schemas, "explicitItems", None):
                new_explicit = list(api_schemas.explicitItems)
                if schema not in new_explicit:
                    new_explicit.append(schema)
                api_schemas.explicitItems = new_explicit
            else:
                new_appended = list(api_schemas.appendedItems or [])
                if schema not in new_appended:
                    new_appended.append(schema)
                api_schemas.appendedItems = new_appended

            prim_spec.SetInfo("apiSchemas", api_schemas)

            # Apply schema attributes
            for prop_name in api_def.GetPropertyNames():
                prop_spec = api_def.GetSchemaPropertySpec(prop_name)

                # Replace __INSTANCE_NAME__ with the actual instance name
                if instance_name and is_multiple_apply:
                    prop_name = prop_name.replace("__INSTANCE_NAME__", instance_name)

                # Skip if property already exists
                if prop_name in prim_spec.properties:
                    continue

                # Create the property on the prim spec
                if isinstance(prop_spec, Sdf.AttributeSpec):
                    attr_spec = Sdf.AttributeSpec(
                        prim_spec, prop_name, prop_spec.typeName, variability=prop_spec.variability
                    )

                    # Copy default value if it exists
                    if hasattr(prop_spec, "default") and prop_spec.default is not None:
                        attr_spec.default = prop_spec.default


def add_prim_semantics(
    prims, data, instance="class", write_type=LabelWriteType.NEW, preview=False, auto_convert_legacy=True
):
    """Add semantic labels to one or more prims.

    Args:
        prims: Single prim or list of prims to modify.
        data: Semantic data - can be string, list of strings, or dict mapping instances to labels.
        instance: Default instance name to use.
        write_type: How to handle existing data (NEW, OVERWRITE, SKIP).
        preview: If True, only show what would be done without making changes.
        auto_convert_legacy: If True, automatically convert legacy SemanticsAPI to new format.

    Returns:
        str: Output log of operations performed.
    """
    # Normalize inputs - support both single prim and list of prims
    if not isinstance(prims, list):
        prims = [prims]

    preview_flag = "" if not preview else "[PREVIEW]"
    output_str = ""

    for prim in prims:
        # Handle legacy conversion if requested
        legacy_semantics = {}
        if auto_convert_legacy:
            legacy_semantics = convert_legacy_semantics(prim, preserve_legacy=False)
            if legacy_semantics:
                output_str += f"{preview_flag}[LEGACY_CONVERTED]: '{prim.GetPath()}' --> {legacy_semantics}\n"

        # Handle different data formats
        semantic_data = {}
        if isinstance(data, dict):
            semantic_data = data
        elif isinstance(data, (list, str)):
            semantic_data = {instance: data if isinstance(data, list) else [data]}
        else:
            output_str += f"{preview_flag}[ERROR]: Invalid data format for '{prim.GetPath()}'\n"
            continue

        # Process each semantic type/instance
        for sem_instance, sem_values in semantic_data.items():
            if isinstance(sem_values, str):
                sem_values = [sem_values]

            # Merge with legacy semantics if available
            if legacy_semantics and sem_instance in legacy_semantics:
                # Combine legacy and new values, avoiding duplicates
                combined_values = legacy_semantics[sem_instance].copy()
                for val in sem_values:
                    if val not in combined_values:
                        combined_values.append(val)
                sem_values = combined_values

            # Check if the prim already has the UsdSemantics.LabelsAPI with the given instance
            existing_instance_found = False
            if prim.HasAPI(UsdSemantics.LabelsAPI) and write_type is not LabelWriteType.NEW:
                for schema in prim.GetAppliedSchemas():
                    if "SemanticsLabelsAPI" in schema:
                        existing_instance = schema.split(":")[1]
                        if existing_instance == sem_instance:
                            existing_instance_found = True
                            if write_type is LabelWriteType.SKIP:
                                # Skip writing in case of existing data
                                output_str += f"{preview_flag}[{write_type.name}]: '{prim.GetPath()}' --> '{sem_instance}':'{sem_values}'\n"
                                break
                            elif write_type is LabelWriteType.OVERWRITE:
                                # Overwrite existing data
                                if not preview:
                                    with Sdf.ChangeBlock():
                                        add_semantics(prim, existing_instance, sem_values, "replace")
                                output_str += f"{preview_flag}[{write_type.name}]: '{prim.GetPath()}' --> '{sem_instance}':'{sem_values}'\n"
                                break

            # Add new semantic data only if not skipped
            if not existing_instance_found or write_type is LabelWriteType.NEW:
                if not preview:
                    # Use the default instance name "class" if not specified
                    instance_name = sem_instance if sem_instance else "class"
                    with Sdf.ChangeBlock():
                        add_semantics(prim, instance_name, sem_values, "add")

                output_str += (
                    f"{preview_flag}[{write_type.name}]: '{prim.GetPath()}' --> '{sem_instance}':'{sem_values}'\n"
                )

    return output_str


def remove_prim_semantics(prim, instance_name="", prim_types=[], preview=False):
    preview_flag = "" if not preview else "[PREVIEW]"
    output_str = ""
    if prim.GetTypeName() in prim_types or not prim_types:
        if prim.HasAPI(UsdSemantics.LabelsAPI):
            for schema in prim.GetAppliedSchemas():
                if "SemanticsLabelsAPI" in schema:
                    current_instance = schema.split(":")[1]
                    if instance_name == "" or current_instance == instance_name:
                        sem = UsdSemantics.LabelsAPI(prim, current_instance)
                        labels = sem.GetLabelsAttr().Get()
                        if labels:
                            output_str += (
                                f"{preview_flag}[REMOVE]: '{prim.GetPath()}' --> '{current_instance}':'{labels}'\n"
                            )
                            if not preview:
                                with Sdf.ChangeBlock():
                                    clear_semantics(prim, current_instance)
    return output_str


class PrimSemanticData:
    def __init__(self, prim) -> None:
        self._prim = prim
        self._current_data_v1 = []
        self._current_data_v2 = []
        self.update_ui_func = None

        self._get_current_semantics()

    def _get_current_semantics(self):
        # [OM-96866] If prim doesn't have the semanticsAPI, don't build entry
        if not self._prim.HasAPI("SemanticsLabelsAPI") and not self._prim.HasAPI("SemanticsAPI"):
            return

        # Get all the semantic instance names that currently exist
        semantic_instance_names = []
        for schema in self._prim.GetAppliedSchemas():
            if "SemanticsLabelsAPI" in schema:
                semantic = (schema.split(":")[1], "SemanticsLabelsAPI")
                semantic_instance_names.append(semantic)
            # Also support the old semantics API
            elif "SemanticsAPI" in schema:
                semantic = (schema.split(":")[1], "SemanticsAPI")
                semantic_instance_names.append(semantic)

        # Get all the semantic info for each semantic instance
        if not len(semantic_instance_names) == 0:
            for instance_name in semantic_instance_names:
                data = {}
                if instance_name[1] == "SemanticsLabelsAPI":
                    data["api"] = "SemanticsLabelsAPI"
                    sem = UsdSemantics.LabelsAPI(self._prim, instance_name[0])
                    data["name"] = instance_name[0]
                    data["labels"] = sem.GetLabelsAttr().Get()
                    if sem.GetLabelsAttr().Get() == None:
                        data["ui_hide"] = True
                    else:
                        data["ui_hide"] = False
                    self._current_data_v2.append(data)
                elif instance_name[1] == "SemanticsAPI":
                    data["api"] = "SemanticsAPI"
                    data["name"] = instance_name[0]
                    sem = Semantics.SemanticsAPI
                    p_sem = sem.Get(self._prim, instance_name[0])
                    data["type"] = p_sem.GetSemanticTypeAttr().Get()
                    data["data"] = p_sem.GetSemanticDataAttr().Get()
                    if p_sem.GetSemanticTypeAttr().Get() == "" and p_sem.GetSemanticDataAttr().Get() == "":
                        data["ui_hide"] = True
                    else:
                        data["ui_hide"] = False
                    self._current_data_v1.append(data)

    def add_entry(self, inst="", labels=""):
        if inst == "" and labels == "":
            editor_log("error", f"Instance and labels fields are empty!")
            return
        if inst == "":
            editor_log("warn", "Instance entry is empty!")
        if labels == "":
            editor_log("warn", "Labels entry is empty!")

        labels = labels.split(",")

        # Add semantic labels (will merge with existing labels if instance already exists)
        with Sdf.ChangeBlock():
            add_semantics(self._prim, inst, labels, "add")

        editor_log("info", f"Add {inst} semantic to {self._prim.GetPath()} with labels: {labels}")

        if self.update_ui_func is not None:
            asyncio.ensure_future(self.update_ui_func())

    def _update_single_entry(self, name, new_type="", new_data=""):
        sem = Semantics.SemanticsAPI.Apply(self._prim, name)
        sem.CreateSemanticTypeAttr()
        sem.CreateSemanticDataAttr()

        typeAttr = sem.GetSemanticTypeAttr()
        dataAttr = sem.GetSemanticDataAttr()
        typeAttr.Set(new_type)
        dataAttr.Set(new_data)

        if self.update_ui_func is not None:
            asyncio.ensure_future(self.update_ui_func())

    def _update_single_label(self, inst, label, new_label):
        if inst == "":
            editor_log("error", "Instance entry is empty!")
            return

        if new_label == "":
            editor_log("error", "New label entry is empty!")
            return

        if new_label == label:
            editor_log("error", "New label entry is the same as the old label!")
            return

        if ":" in new_label:
            editor_log("error", "New label entry cannot contain ':'!")
            return

        with Sdf.ChangeBlock():
            add_semantics(self._prim, inst, [new_label], "replace")

        if self.update_ui_func is not None:
            asyncio.ensure_future(self.update_ui_func())

    def _remove_single_label(self, inst, label):
        schemas = [s.split(":")[1] for s in self._prim.GetAppliedSchemas() if "SemanticsLabelsAPI" in s]

        if inst not in schemas:
            editor_log("error", f"Instance {inst} not found on {self._prim.GetPath()}")
            return

        # Get current labels for this instance
        sem = UsdSemantics.LabelsAPI(self._prim, inst)
        current_labels = sem.GetLabelsAttr().Get() or []

        # Remove the specific label
        if label in current_labels:
            remaining_labels = [l for l in current_labels if l != label]

            with Sdf.ChangeBlock():
                if remaining_labels:
                    # Update with remaining labels
                    add_semantics(self._prim, inst, remaining_labels, "replace")
                else:
                    # No labels left, remove the entire instance
                    clear_semantics(self._prim, inst)

            editor_log("info", f"Removed label '{label}' from instance '{inst}' on {self._prim.GetPath()}")
        else:
            editor_log("warn", f"Label '{label}' not found in instance '{inst}' on {self._prim.GetPath()}")

        if self.update_ui_func is not None:
            asyncio.ensure_future(self.update_ui_func())

    def _remove_single_entry(self, inst):
        schemas = [s.split(":")[1] for s in self._prim.GetAppliedSchemas() if "SemanticsLabelsAPI" in s]

        if inst not in schemas:
            raise ValueError(f"Instance {inst} not found on {self._prim.GetPath()}")

        with Sdf.ChangeBlock():
            clear_semantics(self._prim, inst)

        if self.update_ui_func is not None:
            asyncio.ensure_future(self.update_ui_func())

    def _remove_single_old_entry(self, name):
        # Validate that the requested instance actually exists on the prim
        applied_instances = [s.split(":")[1] for s in self._prim.GetAppliedSchemas() if "SemanticsAPI" in s]
        if name not in applied_instances:
            raise ValueError(f"Instance {name} not found on {self._prim.GetPath()}")

        sem = Semantics.SemanticsAPI.Get(self._prim, name)
        if not sem:
            raise ValueError(f"Instance {name} not found on {self._prim.GetPath()}")

        typeAttr = sem.GetSemanticTypeAttr()
        dataAttr = sem.GetSemanticDataAttr()

        if not self._prim.RemoveProperty(typeAttr.GetName()):
            editor_log("warn", f"could not remove SemanticType for {name} from {self._prim.GetPath()}")
        if not self._prim.RemoveProperty(dataAttr.GetName()):
            editor_log("warn", f"could not remove SemanticData for {name} from {self._prim.GetPath()}")

        if self._prim.RemoveAPI(Semantics.SemanticsAPI, name):
            editor_log("info", f"Removed {name} semantic instance from {self._prim.GetPath()}")

        if self.update_ui_func is not None:
            asyncio.ensure_future(self.update_ui_func())

    def create_prim_entry_ui(self, update_func, instance_model, labels_model) -> None:
        """Used for creating each selected item's semantic data ui"""
        self.update_ui_func = update_func
        with ui.CollapsableFrame(self._prim.GetPath().pathString, height=ui.Pixel(10), collapsed=False):
            with ui.VStack(spacing=5):
                if len(self._current_data_v2) > 0 and len(self._current_data_v2) > sum(
                    x["ui_hide"] == True for x in self._current_data_v2
                ):
                    with ui.VStack(spacing=5):
                        with ui.HStack(spacing=5):
                            ui.Label("Semantic Name", width=ui.Percent(30))
                            ui.Label("Semantic Labels")
                        visible_items = [i for i in self._current_data_v2 if not i["ui_hide"]]
                        for idx, i in enumerate(visible_items):
                            with ui.HStack(spacing=5):
                                ui.Label(i["name"], width=ui.Percent(30))
                                with ui.VStack(spacing=5):
                                    for label in i["labels"]:
                                        with ui.HStack(spacing=5):
                                            m_label = ui.StringField(width=ui.Percent(70)).model
                                            m_label.set_value(label)
                                            ui.Button(
                                                "Update",
                                                clicked_fn=lambda n=i[
                                                    "name"
                                                ], c=label, l=m_label: self._update_single_label(n, c, l.as_string),
                                            )
                                            ui.Button(
                                                f"{_ui_get_menu_delete_glyph()}",
                                                width=30,
                                                clicked_fn=lambda n=i["name"], l=m_label: self._remove_single_label(
                                                    n, l.as_string
                                                ),
                                                tooltip="Removes label from semantic instance",
                                            )
                            if idx < len(visible_items) - 1:
                                ui.Line(style=LINE_STYLE)
                else:
                    ui.Label("This prim has no semantic data.", height=10)
                ui.Button(
                    "Add New Value",
                    height=30,
                    clicked_fn=lambda: self.add_entry(instance_model.as_string, labels_model.as_string),
                )

                if len(self._current_data_v1) > 0 and len(self._current_data_v1) > sum(
                    x["ui_hide"] == True for x in self._current_data_v1
                ):
                    with ui.VStack(spacing=5):
                        ui.Label(
                            "This prim contains an old semantic schema that will be deprecated in the future.",
                            height=10,
                            style={"color": 0xFFFFFF00, "alignment": ui.Alignment.CENTER},
                        )
                        with ui.HStack(spacing=5):
                            ui.Label("Instance Name")
                            ui.Label("Semantic Type")
                            ui.Label("Semantic Data")
                            ui.Label("")  # Dummy for spacing
                        for i in self._current_data_v1:
                            if not i["ui_hide"]:
                                with ui.HStack(spacing=5):
                                    ui.Label(i["name"])
                                    m_type = ui.StringField().model
                                    m_type.set_value(i["type"])
                                    m_data = ui.StringField().model
                                    m_data.set_value(i["data"])
                                    with ui.HStack():
                                        ui.Button(
                                            "Update",
                                            clicked_fn=lambda n=i[
                                                "name"
                                            ], t=m_type, d=m_data: self._update_single_entry(
                                                n, t.as_string, d.as_string
                                            ),
                                        )
                                        ui.Button(
                                            f"{_ui_get_menu_delete_glyph()}",
                                            width=30,
                                            clicked_fn=lambda n=i["name"]: self._remove_single_old_entry(n),
                                            tooltip="Removes semantic instance from prim",
                                        )
                        ui.Spacer()


def upgrade_prim_semantics(prim: Usd.Prim, preview: bool = False) -> tuple[str, int]:
    """Converts old SemanticsAPI instances on a prim to UsdSemantics.LabelsAPI.

    Args:
        prim: The USD prim to upgrade.
        preview: If True, only calculate changes without modifying the prim.

    Returns:
        A tuple containing (output log string, upgraded count).
    """
    output_str = ""
    upgraded_count = 0
    preview_flag = "[PREVIEW] " if preview else ""

    # Find all old semantic API instances on this prim
    old_api_instances = [
        schema_name.split(":", 1)[1]
        for schema_name in prim.GetAppliedSchemas()
        if schema_name.startswith("SemanticsAPI:")
    ]

    if not old_api_instances:
        return "", 0

    for old_instance_name in old_api_instances:
        try:
            sem_old = Semantics.SemanticsAPI.Get(prim, old_instance_name)
            if not sem_old:
                continue

            old_type = sem_old.GetSemanticTypeAttr().Get()
            old_data = sem_old.GetSemanticDataAttr().Get()

            # Skip if no meaningful data to migrate
            if not old_type or not old_data:
                output_str += (
                    f"{preview_flag}[SKIP - Empty Type/Data]: '{prim.GetPath()}' OldInstance:'{old_instance_name}'\n"
                )
                continue

            new_instance_name = old_type
            new_label = old_data
            new_schema_name = f"SemanticsLabelsAPI:{new_instance_name}"

            output_str += f"{preview_flag}[UPGRADE]: '{prim.GetPath()}' From:'{old_instance_name}'(type='{old_type}', data='{old_data}') To:'{new_instance_name}'(labels=['{new_label}'])\n"

            # Only apply changes if not in preview mode
            if not preview:
                with Sdf.ChangeBlock():
                    # Apply new schema with label
                    add_semantics(prim, new_instance_name, [new_label], "add")

                    # Remove old schema properties and API
                    sem_old_for_removal = Semantics.SemanticsAPI.Get(prim, old_instance_name)
                    if sem_old_for_removal:
                        typeAttr = sem_old_for_removal.GetSemanticTypeAttr()
                        dataAttr = sem_old_for_removal.GetSemanticDataAttr()

                        if typeAttr:
                            prim.RemoveProperty(typeAttr.GetName())
                        if dataAttr:
                            prim.RemoveProperty(dataAttr.GetName())

                        if not prim.RemoveAPI(Semantics.SemanticsAPI, old_instance_name):
                            output_str += (
                                f"{preview_flag}  [WARN]: Failed to remove old API schema '{old_instance_name}'.\n"
                            )

            upgraded_count += 1

        except Exception as e:
            error_msg = f"Error processing '{old_instance_name}' on '{prim.GetPath()}': {e}"
            editor_log("error", error_msg)
            output_str += f"{preview_flag}[ERROR]: {error_msg}\n"

    return output_str, upgraded_count


def upgrade_stage_semantics(preview=False):
    """Upgrade all old SemanticsAPI instances on the stage to the new UsdSemantics.LabelsAPI format."""
    output_str = ""
    stage = omni.usd.get_context().get_stage()
    if not stage:
        editor_log("warn", "No stage open.")
        return

    preview_flag = "[PREVIEW]" if preview else ""
    total_upgraded = 0

    # Traverse the stage to upgrade semantics
    for prim in stage.Traverse():
        prim_output, prim_upgraded = upgrade_prim_semantics(prim, preview)
        output_str += prim_output
        total_upgraded += prim_upgraded

    summary = f"\n{preview_flag} Upgrade Summary: Processed {total_upgraded} old API instances."
    output_str += summary

    return output_str


class Extension(omni.ext.IExt):
    def on_startup(self) -> None:
        """Called to load the extension"""
        editor_log("info", "Extension startup!")

        show_window_on_startup = not carb.settings.get_settings().get_as_bool(
            "/exts/semantics_schema_editor/hideWindowOnStartup"
        )
        self._window = ui.Window(
            WINDOW_NAME, dockPreference=ui.DockPreference.RIGHT_BOTTOM, visible=show_window_on_startup
        )

        self._window.deferred_dock_in("Property", omni.ui.DockPolicy.DO_NOTHING)
        self._window.set_visibility_changed_fn(self._on_visibility_changed)

        self._semantic_instance = "class"
        self._label_write_type = LabelWriteType.NEW
        self._prim_types_filter = "Mesh, Material, Skeleton"
        self._prefixes_to_remove = "SM, MI, Mat"
        self._remove_numerical_endings = True
        self._suffixes_to_remove = "Mat, 6M"
        self._apply_cumulatively = True
        self._remove_underscore_separators = True
        self._preview_changes = False
        self._selection_type = SelectionType.STAGE
        self._output_str = ""

        self._selection_frame_collapsed = False
        self._auto_frame_collapsed = False
        self._output_frame_collapsed = True
        self._utilities_frame_collapsed = True

        self._context = omni.usd.get_context()
        self._selected_prim_paths = []

        self._instance_cache = ""
        self._labels_cache = ""

        self._selection_sub = self._context.get_stage_event_stream().create_subscription_to_pop(
            self.on_stage_event, name="semantics_ui stage update"
        )
        self._selection = self._context.get_selection()

        self._build_window_ui()
        self._register_actions()
        self._create_menu()

    def _toggle_window_visibility(self):
        if "_window" not in dir(self):
            return
        self._window.visible = not self._window.visible

    def _is_visible(self):
        if "_window" not in dir(self):
            return False
        return self._window.visible if self._window else False

    def _on_visibility_changed(self, visible):
        omni.kit.menu.utils.refresh_menu_items("Replicator")

    def on_shutdown(self) -> None:
        """Called when the extesion is unloaded"""
        editor_log("info", f"Extension shutdown!")
        self._deregister_actions()
        self._window = None
        self._selection_sub = None
        gc.collect()

    def apply_semantics_automated(self, prim, semantic_instance, semantic_labels):
        PrimSemanticData(prim)._update_single_entry("Semantics", semantic_instance, semantic_labels)

    def on_stage_event(self, event):
        if event.type == int(omni.usd.StageEventType.SELECTION_CHANGED):
            self._selected_prim_paths.clear()
            selected = self._selection.get_selected_prim_paths()
            for prim_path in selected:
                self._selected_prim_paths.append(prim_path)
            self._build_window_ui()

    def _add_to_all_entries(self, entries):
        n_instance = self.new_instance.as_string
        n_labels = self.new_labels.as_string
        for e in entries:
            e.add_entry(n_instance, n_labels)

    def _cache_values(self):
        self._instance_cache = self.new_instance.as_string
        self._labels_cache = self.new_labels.as_string

    def _add_auto_semantics(self):
        self._output_str = ""
        # Create list of the comma separated values and make sure no empty string ends up in the list
        prim_types = [prim_type for prim_type in self._prim_types_filter.replace(" ", "").split(",") if prim_type]
        prefixes = [prefix for prefix in self._prefixes_to_remove.replace(" ", "").split(",") if prefix]
        suffixes = [suffix for suffix in self._suffixes_to_remove.replace(" ", "").split(",") if suffix]

        get_prim_data = partial(
            get_prim_auto_label,
            prim_types=prim_types,
            remove_numerical_ending=self._remove_numerical_endings,
            prefixes=prefixes,
            suffixes=suffixes,
            apply_cumulatively=self._apply_cumulatively,
            remove_separators=self._remove_underscore_separators,
        )
        add_prim_data = partial(
            add_prim_semantics,
            instance=self._semantic_instance,
            write_type=self._label_write_type,
            preview=self._preview_changes,
        )
        if self._selection_type is SelectionType.STAGE:
            for prim in self._context.get_stage().Traverse():
                label = get_prim_data(prim)
                if label:
                    self._output_str += add_prim_data(prim, data=label)
        elif self._selection_type is SelectionType.SELECTED:
            for path in self._selected_prim_paths:
                prim = self._context.get_stage().GetPrimAtPath(path)
                label = get_prim_data(prim)
                if label:
                    self._output_str += add_prim_data(prim, data=label)
        # Rebuild ui so the semantic property changes are visible
        asyncio.ensure_future(self._build_window_ui_async())

    def _remove_semantics(self, instance_name="", prim_types=[]):
        self._output_str = ""
        if self._selection_type is SelectionType.STAGE:
            for prim in self._context.get_stage().Traverse():
                self._output_str += remove_prim_semantics(
                    prim, instance_name=instance_name, prim_types=prim_types, preview=self._preview_changes
                )
        elif self._selection_type is SelectionType.SELECTED:
            for path in self._selected_prim_paths:
                prim = self._context.get_stage().GetPrimAtPath(path)
                self._output_str += remove_prim_semantics(
                    prim, instance_name=instance_name, prim_types=prim_types, preview=self._preview_changes
                )
        # Rebuild ui so the semantic property changes are visible
        asyncio.ensure_future(self._build_window_ui_async())

    def _remove_type_semantics(self):
        # Create list of the comma separated values and make sure no empty string ends up in the list
        prim_types = [prim_type for prim_type in self._prim_types_filter.replace(" ", "").split(",") if prim_type]
        self._remove_semantics(instance_name=self._semantic_instance, prim_types=prim_types)

    def _remove_all_semantics(self):
        self._remove_semantics()

    def _build_selection_ui(self):
        with ui.VStack(spacing=5):
            with ui.HStack(spacing=5):
                ui.Label("New Semantic Instance")
                ui.Label("New Semantic Labels")
            with ui.HStack(spacing=5):
                self.new_instance = ui.StringField(height=20).model
                self.new_instance.set_value(self._instance_cache)
                self.new_instance.add_value_changed_fn(lambda _: self._cache_values())
                self.new_labels = ui.StringField(
                    height=20, tooltip="Enter the semantic labels separated by commas"
                ).model
                self.new_labels.set_value(self._labels_cache)
                self.new_labels.add_value_changed_fn(lambda _: self._cache_values())
            if not len(self._selected_prim_paths) == 0:
                entries = []
                ui.Button(
                    "Add Entry On All Selected Prims", height=30, clicked_fn=lambda: self._add_to_all_entries(entries)
                )
                for p in self._selected_prim_paths:
                    prim = self._context.get_stage().GetPrimAtPath(p)
                    prim_entry = PrimSemanticData(prim)
                    prim_entry.create_prim_entry_ui(self._build_window_ui_async, self.new_instance, self.new_labels)
                    entries.append(prim_entry)
            else:
                ui.Label("Select an object to display and edit the semantic data.", height=30)

    def _build_output_frame_ui(self):
        output_frame = ui.CollapsableFrame("Output", height=ui.Pixel(10), collapsed=self._output_frame_collapsed)
        with output_frame:

            def on_collapsed_changed(collapsed):
                self._output_frame_collapsed = collapsed

            output_frame.set_collapsed_changed_fn(on_collapsed_changed)
            output_field_model = ui.StringField(read_only=True, multiline=True, height=150).model
            output_field_model.set_value(self._output_str)

    def _build_auto_annotator_ui(self):
        with ui.VStack(spacing=5):
            with ui.HStack(spacing=5):
                ui.Spacer(width=5)
                ui.Label("Semantics Instance")
                semantic_instance_model = ui.StringField(height=20).model
                semantic_instance_model.set_value(self._semantic_instance)

                def semantic_instance_changed(model):
                    self._semantic_instance = model.as_string

                semantic_instance_model.add_value_changed_fn(semantic_instance_changed)

                write_collection = ui.RadioCollection()
                write_collection.model.set_value(self._label_write_type.value)

                def label_collection_changed(model):
                    self._label_write_type = LabelWriteType(model.as_int)

                write_collection.model.add_value_changed_fn(label_collection_changed)

                ui.RadioButton(
                    text="New", radio_collection=write_collection, tooltip="Create new if instance already exists"
                )
                ui.RadioButton(
                    text="Overwrite", radio_collection=write_collection, tooltip="Overwrite if instance already exists"
                )
                ui.RadioButton(
                    text="Skip", radio_collection=write_collection, tooltip="Skip creation if instance already exists"
                )

            with ui.HStack(spacing=5):
                ui.Spacer(width=5)
                ui.Label("Prim types filter")
                types_filter_model = ui.StringField(height=20).model
                types_filter_model.set_value(self._prim_types_filter)

                def class_filter_changed(model):
                    self._prim_types_filter = model.as_string

                types_filter_model.add_value_changed_fn(class_filter_changed)

            with ui.HStack(spacing=5):
                ui.Spacer(width=5)
                ui.Label("Remove numerical ending", tooltip="Remove numerical ending")
                numerical_endings_model = ui.CheckBox().model
                numerical_endings_model.set_value(self._remove_numerical_endings)

                def remove_numerical_ending_changed(model):
                    self._remove_numerical_endings = model.as_bool

                numerical_endings_model.add_value_changed_fn(remove_numerical_ending_changed)

            with ui.HStack(spacing=5):
                ui.Spacer(width=5)
                ui.Label("Remove prefixes")
                prefixes_model = ui.StringField(height=20).model
                prefixes_model.set_value(self._prefixes_to_remove)

                def remove_prefixes_change(model):
                    self._prefixes_to_remove = model.as_string

                prefixes_model.add_value_changed_fn(remove_prefixes_change)

            with ui.HStack(spacing=5):
                ui.Spacer(width=5)
                ui.Label("Remove suffixes")
                suffixes_model = ui.StringField(height=20).model
                suffixes_model.set_value(self._suffixes_to_remove)

                def remove_suffixes_changed(model):
                    self._suffixes_to_remove = model.as_string

                suffixes_model.add_value_changed_fn(remove_suffixes_changed)

            with ui.HStack(spacing=5):
                ui.Spacer(width=5)
                ui.Label("Apply cumulatively", tooltip="Remove all prefixes and suffixes cumulatively")
                remove_cumulatively_model = ui.CheckBox().model
                remove_cumulatively_model.set_value(self._apply_cumulatively)

                def apply_cumulatively_changed(model):
                    self._apply_cumulatively = model.as_bool

                remove_cumulatively_model.add_value_changed_fn(apply_cumulatively_changed)

            with ui.HStack(spacing=5):
                ui.Spacer(width=5)
                ui.Label("Remove separators", tooltip="Remove remaining underscore separators")
                remove_separators_model = ui.CheckBox(height=20).model
                remove_separators_model.set_value(self._remove_underscore_separators)

                def remove_separators_changed(model):
                    self._remove_underscore_separators = model.as_bool

                remove_separators_model.add_value_changed_fn(remove_separators_changed)

            with ui.HStack(spacing=5):
                ui.Spacer(width=5)
                ui.Label("Preview", tooltip="Changes will not be applied")
                preview_model = ui.CheckBox().model
                preview_model.set_value(self._preview_changes)

                def display_results_changed(model):
                    self._preview_changes = model.as_bool

                preview_model.add_value_changed_fn(display_results_changed)

            with ui.HStack(spacing=5):
                ui.Spacer(width=5)
                ui.Label("Apply to")
                selection_collection = ui.RadioCollection()
                selection_collection.model.set_value(self._selection_type.value)

                def selection_collection_change(model):
                    self._selection_type = SelectionType(model.as_int)

                selection_collection.model.add_value_changed_fn(selection_collection_change)
                ui.RadioButton(text="Stage", radio_collection=selection_collection)
                ui.RadioButton(text="Selected", radio_collection=selection_collection)

            with ui.HStack(spacing=5):
                ui.Button(
                    "Add",
                    height=30,
                    tooltip="Automatically generate semantic labels",
                    clicked_fn=lambda: self._add_auto_semantics(),
                )
                ui.Button(
                    "Remove",
                    height=30,
                    tooltip="Remove semantic data of the selected instance and prim types",
                    clicked_fn=lambda: self._remove_type_semantics(),
                )
                ui.Button(
                    "Remove All",
                    height=30,
                    tooltip="Remove all semantic data from all prim types, equivalent to 'Remove' with empty 'Semantics Instance' and 'Prim types filter' fields",
                    clicked_fn=lambda: self._remove_all_semantics(),
                )
            utils_frame = ui.CollapsableFrame(
                "Utilities", height=ui.Pixel(10), collapsed=self._utilities_frame_collapsed
            )
            with utils_frame:

                def on_utils_collapsed_changed(collapsed):
                    self._utilities_frame_collapsed = collapsed

                utils_frame.set_collapsed_changed_fn(on_utils_collapsed_changed)

                with ui.HStack(spacing=5):
                    ui.Button(
                        "Upgrade Stage to New Semantics API",
                        height=30,
                        tooltip="Upgrade prims in stage from old SemanticsAPI to new UsdSemantics.LabelsAPI (use 'Preview' to check results first)",
                        clicked_fn=self._on_upgrade_stage_semantics,
                    )

            self._build_output_frame_ui()
            ui.Spacer(height=15)

    def _on_upgrade_stage_semantics(self):
        self._output_str = upgrade_stage_semantics(preview=self._preview_changes)
        asyncio.ensure_future(self._build_window_ui_async())

    def _build_window_ui(self):
        with self._window.frame:
            with ui.ScrollingFrame():
                with ui.VStack(spacing=5):
                    selection_frame = ui.CollapsableFrame(
                        "Apply semantic data on selected objects",
                        height=ui.Pixel(10),
                        collapsed=self._selection_frame_collapsed,
                    )
                    with selection_frame:

                        def on_collapsed_changed(collapsed):
                            self._selection_frame_collapsed = collapsed

                        selection_frame.set_collapsed_changed_fn(on_collapsed_changed)
                        self._build_selection_ui()

                    auto_frame = ui.CollapsableFrame(
                        "Apply semantic data using prim names",
                        height=ui.Pixel(10),
                        collapsed=self._auto_frame_collapsed,
                    )
                    with auto_frame:

                        def on_collapsed_changed(collapsed):
                            self._auto_frame_collapsed = collapsed

                        auto_frame.set_collapsed_changed_fn(on_collapsed_changed)
                        self._build_auto_annotator_ui()

    async def _build_window_ui_async(self):
        self._build_window_ui()

    def _register_actions(self):
        action_registry = omni.kit.actions.core.get_action_registry()
        actions_tag = "Semantics Schema Editor Menu Actions"
        extension_id = "semantics.schema.editor"

        action_registry.register_action(
            extension_id,
            "toggle window visibility",
            self._toggle_window_visibility,
            display_name="Replicator->Semantics Schema Editor",
            description="Show/Hide the Semantics Schema Editor Window",
            tag=actions_tag,
        )

    def _deregister_actions(self):
        extension_id = "semantics.schema.editor"
        action_registry = omni.kit.actions.core.get_action_registry()
        action_registry.deregister_all_actions_for_extension(extension_id)

    def _create_menu(self):
        menu = omni.kit.menu.utils
        menu_items = [menu.MenuItemDescription()]
        extension_id = "semantics.schema.editor"

        menu_items.append(
            menu.MenuItemDescription(
                name=WINDOW_NAME,
                ticked=True,
                ticked_fn=self._is_visible,
                onclick_action=(extension_id, "toggle window visibility"),
            )
        )
        menu.add_menu_items(menu_items, "Replicator")
        return menu_items
