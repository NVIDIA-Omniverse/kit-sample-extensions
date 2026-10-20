# SPDX-FileCopyrightText: Copyright (c) 2023-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import json
import math
import webbrowser
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Dict, List, Optional, Union

import omni.kit.app
from omni import ui
from pxr import UsdGeom

from .minimal_model import MinimalItem, MinimalModal
from .simple_double_model import SimpleDoubleModel
from .string_list_field_utils import parse_string_list_ui_text

__all__ = ["CadConverterOptionsBuilder", "OptionDef", "OptionType"]


class OptionType(Enum):
    """Types of UI options"""

    BOOL = "bool"
    BOOL_INVERTED = "bool_inverted"  # For "Convert Visible Only" which inverts convertHidden
    DOUBLE = "double"
    FLOAT = "float"
    INT = "int"
    COMBO = "combo"
    STRING = "string"
    STRING_LIST = "string_list"  # Comma-separated string in UI, List[str] on options model
    STRING_LIST_JSON = "string_list_json"  # JSON string in UI, complex list on options model


@dataclass
class OptionDef:
    """Definition for a single option"""

    attr: str  # Attribute name on options model
    label: str
    tooltip: str
    opt_type: OptionType
    combo_items: List[str] = None
    section: str = "main"  # "main", "advanced", "tessellation", or "text3d"
    min_value: float = None
    doc_url: str = None
    filter_names: List[str] = None  # If set, only show this option when the converter name is in the list
    # For COMBO: called as combo_setter(options_model, index) when the selection changes.
    # Use this when the options model needs special logic to convert a combo index to an enum value.
    # If None, the index is written directly via setattr.
    combo_setter: Optional[Callable] = None
    # For STRING_LIST_JSON: serialize(model_value) converts the stored value to a UI string.
    # deserialize(parsed_list) converts a parsed JSON list back to the model value.
    # If not provided, json.dumps/json.loads are used as-is.
    serialize: Optional[Callable] = None
    deserialize: Optional[Callable] = None
    # Most legacy combos store their selected row index. Some options instead
    # expose domain values (for example, unit scales), so keep the labels/indexes
    # in the UI model while mapping them to the values expected by the converter.
    combo_values: List = None


# Unit scale factors for the sceneOpMetersPerUnit combo. Index 0 means "use model units" (value=0).
_UNIT_SCALE_FACTORS = [
    0,
    UsdGeom.LinearUnits.meters,
    UsdGeom.LinearUnits.feet,
    UsdGeom.LinearUnits.inches,
    UsdGeom.LinearUnits.centimeters,
    UsdGeom.LinearUnits.millimeters,
    UsdGeom.LinearUnits.micrometers,
    UsdGeom.LinearUnits.nanometers,
]


COMMON_UI_OPTION_DEFINITIONS: List[OptionDef] = [
    # COMMON OPTIONS
    OptionDef(
        "sceneOpGenerateUVs",
        "Generate Projection UVs",
        "Generate Projection UVs -\nIf true, use Scene Optimizer to generate uvs for any Mesh prims that do not have them",
        OptionType.BOOL,
        section="advanced",
        doc_url="https://docs.omniverse.nvidia.com/extensions/latest/ext_scene-optimizer/operations.html#generate-projection-uvs",
    ),
    OptionDef(
        "sceneOpUpAxis",
        "Override Up-Axis",
        "Override Up-Axis - override the up-axis of the converted USD's stage to Y-up, Z-up, or default to the converter's up-axis setting.",
        OptionType.COMBO,
        combo_items=["File Default", "Y-Axis", "Z-Axis"],
        section="main",
    ),
    OptionDef(
        "sceneOpMetersPerUnit",
        "Unit",
        "Set the unit to use for the conversion.",
        OptionType.COMBO,
        combo_items=[
            "Use Model Units",
            "Meters",
            "Feet",
            "Inches",
            "Centimeters",
            "Millimeters",
            "Micrometers",
            "Nanometers",
        ],
        section="main",
        doc_url="https://docs.omniverse.nvidia.com/extensions/latest/ext_scene-optimizer/operations.html#edit-stage-metrics",
        combo_setter=lambda model, idx: setattr(model, "sceneOpMetersPerUnit", _UNIT_SCALE_FACTORS[idx]),
    ),
]


class CadConverterOptionsBuilder:
    def __init__(self, options_model=None, option_definitions: List[OptionDef] = None, converter_name: str = None):
        self._options_model = options_model
        self._option_definitions = option_definitions
        self._converter_name = converter_name
        if self._option_definitions is None:
            raise ValueError("option_definitions parameter is required to build the options UI")

        # Storage for UI models and subscriptions
        self._models: Dict[str, Union[ui.AbstractValueModel, MinimalModal]] = {}
        self._subscriptions: Dict[str, object] = {}

        # Create models for all options
        self._create_models()

    def _get_initial_value(self, opt_def: OptionDef):
        """Get the initial value for a UI model from the options model"""
        if self._options_model is None:
            return None

        try:
            value = getattr(self._options_model, opt_def.attr)
            # For BOOL_INVERTED, the UI shows the opposite of the model value
            if opt_def.opt_type == OptionType.BOOL_INVERTED:
                return not value
            # For enum-typed combos, convert the enum to its integer index
            if value is not None and opt_def.attr in (
                "instancingStyle",
                "text3dConversionStyle",
                "meshConversionStyle",
                "curveConversionStyle",
            ):
                return int(value)
            if opt_def.opt_type == OptionType.COMBO and opt_def.combo_values:
                # The UI model needs a row index, while the options model holds
                # the corresponding domain value. Reverse the mapping on setup.
                for index, combo_value in enumerate(opt_def.combo_values):
                    if isinstance(value, (int, float)) and isinstance(combo_value, (int, float)):
                        # Unit-style values may have passed through text config,
                        # so tolerate harmless rounding. Zero is commonly a
                        # sentinel, however, and must only match exactly.
                        if value == 0.0 or combo_value == 0.0:
                            if value == combo_value:
                                return index
                        elif math.isclose(float(value), float(combo_value), rel_tol=1e-12, abs_tol=1e-15):
                            return index
                    elif value == combo_value:
                        return index
                return 0
            # For sceneOpMetersPerUnit, find the matching entry in the scale factors list
            if opt_def.attr == "sceneOpMetersPerUnit":
                if value is None or value == 0.0:
                    return 0  # "Use Model Units"
                try:
                    return _UNIT_SCALE_FACTORS.index(value)
                except ValueError:
                    return 0
            # For STRING_LIST, join list items into a comma-separated display string
            if opt_def.opt_type == OptionType.STRING_LIST:
                if isinstance(value, (list, tuple)):
                    return ", ".join(str(item) for item in value)
                return str(value) if value is not None else ""
            # For STRING_LIST_JSON, use serialize() if provided, else json.dumps
            if opt_def.opt_type == OptionType.STRING_LIST_JSON:
                if opt_def.serialize:
                    return opt_def.serialize(value)
                try:
                    return json.dumps(value) if value else ""
                except (TypeError, ValueError):
                    return ""
            return value
        except AttributeError:
            return None

    def _create_models(self):
        """Create UI models for all defined options"""
        for opt_def in self._option_definitions:
            if not self._has_option(opt_def.attr):
                continue

            if opt_def.opt_type in (OptionType.BOOL, OptionType.BOOL_INVERTED):
                initial_value = self._get_initial_value(opt_def)
                if initial_value is None:
                    initial_value = False
                model = ui.SimpleBoolModel(default_value=initial_value)
                self._models[opt_def.attr] = model
                inverted = opt_def.opt_type == OptionType.BOOL_INVERTED
                self._subscriptions[opt_def.attr] = model.subscribe_value_changed_fn(
                    lambda m, a=opt_def.attr, inv=inverted: self._on_bool_changed(m, a, inv)
                )

            elif opt_def.opt_type in (OptionType.DOUBLE, OptionType.FLOAT):
                initial_value = self._get_initial_value(opt_def)
                if initial_value is None:
                    initial_value = 0.0
                model = (
                    SimpleDoubleModel(default_value=initial_value)
                    if opt_def.opt_type == OptionType.DOUBLE
                    else ui.SimpleFloatModel(default_value=initial_value)
                )
                self._models[opt_def.attr] = model
                self._subscriptions[opt_def.attr] = model.subscribe_value_changed_fn(
                    lambda m, a=opt_def.attr, mv=opt_def.min_value: self._on_float_changed(m, a, mv)
                )

            elif opt_def.opt_type == OptionType.INT:
                initial_value = self._get_initial_value(opt_def)
                if initial_value is None:
                    initial_value = 0
                model = ui.SimpleIntModel(default_value=int(initial_value))
                self._models[opt_def.attr] = model
                self._subscriptions[opt_def.attr] = model.subscribe_value_changed_fn(
                    lambda m, a=opt_def.attr, mv=opt_def.min_value: self._on_int_changed(m, a, mv)
                )

            elif opt_def.opt_type in (OptionType.STRING, OptionType.STRING_LIST, OptionType.STRING_LIST_JSON):
                initial_value = self._get_initial_value(opt_def)
                if initial_value is None:
                    initial_value = ""
                model = ui.SimpleStringModel(initial_value)
                self._models[opt_def.attr] = model
                self._subscriptions[opt_def.attr] = model.subscribe_value_changed_fn(
                    lambda m, od=opt_def: self._on_string_type_changed(m, od)
                )

            elif opt_def.opt_type == OptionType.COMBO:
                initial_value = self._get_initial_value(opt_def)
                if initial_value is None:
                    initial_value = 0
                model = MinimalModal(
                    default_index=int(initial_value),
                    item_labels=opt_def.combo_items or [],
                )
                self._models[opt_def.attr] = model
                self._subscriptions[opt_def.attr] = model.subscribe_item_changed_fn(
                    lambda m, item, od=opt_def: self._on_combo_changed(m, od)
                )

    def _has_option(self, attr: str) -> bool:
        """Check if option exists on the model"""
        return self._options_model is not None and hasattr(self._options_model, attr)

    def _is_visible_for_converter(self, opt_def: OptionDef) -> bool:
        """Check if option should be visible for the current converter.

        If the option has no filter_names set, it is always visible.
        Otherwise, it is only visible when the converter name matches one in the list.
        """
        if opt_def.filter_names is None:
            return True
        return self._converter_name in opt_def.filter_names

    def _on_bool_changed(self, model: ui.SimpleBoolModel, attr: str, inverted: bool = False):
        """Generic handler for boolean option changes"""
        if self._has_option(attr):
            value = not model.as_bool if inverted else model.as_bool
            setattr(self._options_model, attr, value)

    def _on_float_changed(self, model: ui.AbstractValueModel, attr: str, min_value: float = None):
        """Generic handler for float option changes"""
        if self._has_option(attr):
            if min_value is not None and model.as_float < min_value:
                model.as_float = min_value
            setattr(self._options_model, attr, model.as_float)

    def _on_int_changed(self, model: ui.SimpleIntModel, attr: str, min_value: int = None):
        """Generic handler for int option changes"""
        if self._has_option(attr):
            if min_value is not None and model.as_int < min_value:
                model.as_int = int(min_value)
            setattr(self._options_model, attr, model.as_int)

    def _on_string_type_changed(self, model: ui.SimpleStringModel, opt_def: OptionDef):
        """Handler for STRING, STRING_LIST, and STRING_LIST_JSON option changes."""
        if not self._has_option(opt_def.attr):
            return
        raw = model.as_string
        if opt_def.opt_type == OptionType.STRING_LIST:
            setattr(self._options_model, opt_def.attr, parse_string_list_ui_text(raw))
        elif opt_def.opt_type == OptionType.STRING_LIST_JSON:
            raw = raw.strip()
            if not raw:
                setattr(self._options_model, opt_def.attr, [])
            else:
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, list):
                        value = opt_def.deserialize(parsed) if opt_def.deserialize else parsed
                        setattr(self._options_model, opt_def.attr, value)
                except (ValueError, TypeError):
                    pass  # Leave model unchanged while the user is still typing
        else:  # STRING
            setattr(self._options_model, opt_def.attr, raw)

    def _on_combo_changed(self, model: MinimalModal, opt_def: OptionDef):
        """Handler for combo box option changes."""
        if not self._has_option(opt_def.attr):
            return
        if opt_def.combo_setter:
            opt_def.combo_setter(self._options_model, model.current_index)
        elif opt_def.combo_values is not None:
            # Preserve the historical index behavior unless an option
            # explicitly declares that its rows represent domain values.
            if 0 <= model.current_index < len(opt_def.combo_values):
                setattr(self._options_model, opt_def.attr, opt_def.combo_values[model.current_index])
        else:
            setattr(self._options_model, opt_def.attr, model.current_index)

    def destroy(self) -> None:
        """Clean up subscriptions"""
        self._subscriptions.clear()
        self._models.clear()

    def _build_option_ui(self, opt_def: OptionDef) -> None:
        """Build UI for a single option"""
        if not self._has_option(opt_def.attr):
            return

        model = self._models.get(opt_def.attr)
        if model is None:
            return

        # Get tooltip
        tooltip = opt_def.tooltip

        with ui.HStack(width=0, spacing=4):
            if opt_def.opt_type in (OptionType.BOOL, OptionType.BOOL_INVERTED):
                if tooltip:
                    ui.CheckBox(model=model, identifier=f"check_{opt_def.attr}", tooltip=tooltip)
                else:
                    ui.CheckBox(model=model, identifier=f"check_{opt_def.attr}")
                ui.Label(opt_def.label)
            elif opt_def.opt_type in (OptionType.DOUBLE, OptionType.FLOAT):
                kwargs = {"model": model, "width": 80, "identifier": f"field_{opt_def.attr}"}
                if tooltip:
                    kwargs["tooltip"] = tooltip
                if opt_def.min_value is not None:
                    kwargs["min"] = opt_def.min_value
                ui.FloatField(**kwargs)
                ui.Label(opt_def.label)
            elif opt_def.opt_type == OptionType.INT:
                kwargs = {"model": model, "width": 80, "identifier": f"field_{opt_def.attr}"}
                if tooltip:
                    kwargs["tooltip"] = tooltip
                if opt_def.min_value is not None:
                    kwargs["min"] = int(opt_def.min_value)
                ui.IntField(**kwargs)
                ui.Label(opt_def.label)
            elif opt_def.opt_type == OptionType.STRING:
                kwargs = {"model": model, "width": 150, "identifier": f"field_{opt_def.attr}"}
                if tooltip:
                    kwargs["tooltip"] = tooltip
                ui.StringField(**kwargs)
                ui.Label(opt_def.label)
            elif opt_def.opt_type in (OptionType.STRING_LIST, OptionType.STRING_LIST_JSON):
                kwargs = {"model": model, "width": 220, "identifier": f"field_{opt_def.attr}"}
                if tooltip:
                    kwargs["tooltip"] = tooltip
                ui.StringField(**kwargs)
                ui.Label(opt_def.label)
            elif opt_def.opt_type == OptionType.COMBO:
                kwargs = {"width": 150, "identifier": f"combo_{opt_def.attr}"}
                if tooltip:
                    kwargs["tooltip"] = tooltip
                ui.ComboBox(model, **kwargs)
                ui.Label(opt_def.label)

            # Add help button if doc_url is specified
            if opt_def.doc_url:
                info_btn = ui.Button(height=12, width=12, text="?", tooltip="View documentation")
                info_btn.set_clicked_fn(lambda url=opt_def.doc_url: webbrowser.open(url))

    def _get_options_by_section(self, section: str) -> List[OptionDef]:
        """Get options that exist on the model for a given section, filtered by converter visibility"""
        return [
            opt
            for opt in self._option_definitions
            if opt.section == section and self._has_option(opt.attr) and self._is_visible_for_converter(opt)
        ]

    def _has_section_options(self, section: str) -> bool:
        """Check if any options exist for a section"""
        return len(self._get_options_by_section(section)) > 0

    def build_pane(self, asset_paths: List[str]) -> None:
        """Build the options pane UI"""
        with ui.VStack(height=0, spacing=4):
            # Build main options
            for opt_def in self._get_options_by_section("main"):
                # Special handling for up_axis - add section header
                if opt_def.attr == "sceneOpUpAxis":
                    # Check if we have sceneOpUpAxis or sceneOpMetersPerUnit to show the header
                    has_stage_metrics = self._has_option("sceneOpUpAxis") or self._has_option("sceneOpMetersPerUnit")
                    if has_stage_metrics:
                        with ui.HStack(width=0, spacing=4):
                            ui.Label("Edit Stage Metrics:")
                            info_btn = ui.Button(height=12, width=12, text="?", tooltip="View documentation")
                            info_btn.set_clicked_fn(
                                lambda: webbrowser.open(
                                    "https://docs.omniverse.nvidia.com/extensions/latest/ext_scene-optimizer/operations.html#edit-stage-metrics"
                                )
                            )
                self._build_option_ui(opt_def)

            # Build advanced options in collapsible frame
            if (
                self._has_section_options("advanced")
                or self._has_section_options("tessellation")
                or self._has_section_options("text3d")
            ):
                self._advanced_parameters_frame = ui.CollapsableFrame(
                    title="Advanced Parameters",
                    collapsed=True,
                    identifier="advanced_parameters_frame",
                )
                with self._advanced_parameters_frame:
                    with ui.VStack(height=0, spacing=4):
                        # Advanced options
                        for opt_def in self._get_options_by_section("advanced"):
                            self._build_option_ui(opt_def)

                        # Tessellation options
                        if self._has_section_options("tessellation"):
                            ui.Spacer(width=4)
                            ui.Label("Tessellation:")
                            for opt_def in self._get_options_by_section("tessellation"):
                                self._build_option_ui(opt_def)

                        # Text 3D options
                        if self._has_section_options("text3d"):
                            ui.Spacer(width=4)
                            ui.Label("Text 3D:")
                            for opt_def in self._get_options_by_section("text3d"):
                                self._build_option_ui(opt_def)

    def validate_json_fields(self) -> list:
        """Validate all STRING_LIST_JSON fields.

        Returns a list of (label, error_message) tuples for invalid fields.
        An empty list means all fields are valid.
        """
        errors = []
        for opt_def in self._option_definitions:
            if opt_def.opt_type != OptionType.STRING_LIST_JSON:
                continue
            model = self._models.get(opt_def.attr)
            if model is None:
                continue
            raw = model.as_string.strip()
            if not raw:
                continue
            try:
                parsed = json.loads(raw)
                if not isinstance(parsed, list):
                    errors.append(
                        (opt_def.label, f'Expected a JSON array (starting with "["), got: {type(parsed).__name__}')
                    )
            except (ValueError, TypeError) as exc:
                errors.append((opt_def.label, str(exc)))
        return errors

    def get_import_options(self):
        """Return the options model"""
        return self._options_model
