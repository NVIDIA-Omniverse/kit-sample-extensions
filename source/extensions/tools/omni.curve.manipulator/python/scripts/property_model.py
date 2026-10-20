# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import math
from typing import List

import carb
import omni.kit
import omni.ui as ui
from omni.kit.property.usd.placeholder_attribute import PlaceholderAttribute
from omni.kit.property.usd.usd_attribute_model import UsdAttributeModel
from pxr import Gf, Sdf, Usd, UsdGeom

from . import utils


def default_get_interpolation_fn(stage, attribute_path, basis_curves):
    attribute = stage.GetAttributeAtPath(attribute_path)
    return UsdGeom.Primvar(attribute).GetInterpolation()


class UsdArrayElementAttributeModel(UsdAttributeModel):
    EDITABLE_INTERPOLATIONS = [UsdGeom.Tokens.constant, UsdGeom.Tokens.vertex]

    def __del__(self):
        self.destroy()

    def __init__(
        self,
        stage: Usd.Stage,
        attribute_paths: List[Sdf.Path],
        basis_curves: List[UsdGeom.BasisCurves],
        indices: List[int],
        self_refresh: bool,
        metadata: dict,
        change_on_edit_end: bool = False,
        create_default_element_fn=None,
        get_interpolation_fn=None,
        **kwargs,
    ):
        if not get_interpolation_fn:
            get_interpolation_fn = default_get_interpolation_fn
        min_length = min(len(attribute_paths), len(basis_curves), len(indices))
        super().__init__(
            stage=stage,
            attribute_paths=attribute_paths[:min_length],
            self_refresh=self_refresh,
            metadata=metadata,
            change_on_edit_end=change_on_edit_end,
            **kwargs,
        )
        self.__basis_curves = basis_curves[:min_length]
        self.__create_default_element_fn = create_default_element_fn
        self.__element_values = []
        self.__get_interpolation_fn = get_interpolation_fn
        self.__indices = indices[:min_length]
        self.__is_updating = False

    def _apply_value_to_element(self, element, value):
        element = value
        return element

    def _create_default_element(self):
        if self.__create_default_element_fn:
            return self.__create_default_element_fn()
        return None

    def _create_default_value(self):
        default_element = self._create_default_element()
        if default_element is not None:
            return self._extract_value_from_element(default_element)
        return None

    def _element_values_different(self, value):
        if value is not None:
            for element_value in self.__element_values:
                if element_value is not None and element_value != value:
                    return True
        return False

    def _extract_value_from_element(self, element):
        return element

    def _get_attributes_and_indices(self):
        attributes = []
        attribute_indices = []
        if self._stage:
            for index, path in enumerate(self._object_paths):
                prim = self._stage.GetPrimAtPath(path.GetPrimPath())
                if prim:
                    attr = prim.GetAttribute(path.name)
                    if not attr:
                        attr = PlaceholderAttribute(name=path.name, prim=prim, metadata=self._metadata)
                        attributes.append(attr)
                        attribute_indices.append(index)
                    elif not attr.IsHidden():
                        attributes.append(attr)
                        attribute_indices.append(index)
        return attributes, attribute_indices

    def _get_basis_curves(self, index):
        if index >= 0 and index < len(self.__basis_curves):
            return self.__basis_curves[index]
        return None

    def _get_interpolation_data(self, attribute_path, basis_curves, array_index):
        interpolation = self.__get_interpolation_fn(self._stage, attribute_path, basis_curves)
        if interpolation == UsdGeom.Tokens.constant:
            return 0, 0, 0.0, interpolation
        elif interpolation == UsdGeom.Tokens.varying:
            vertex_range_start, vertex_range_end = utils.get_array_index_range(basis_curves, array_index)
            if array_index >= vertex_range_start and array_index <= vertex_range_end:
                t = float(array_index - vertex_range_start) / float(vertex_range_end - vertex_range_start)
                max_index = len(self._value) - 1
                array_index_0 = math.floor(t * max_index)
                array_index_1 = math.ceil(t * max_index)
                return array_index_0, array_index_1, t, interpolation
        elif interpolation == UsdGeom.Tokens.vertex:
            return array_index, array_index, 0.0, interpolation
        return array_index, array_index, 0.0, ""

    def _get_valid_value(self, valid_value):
        value = self.get_value()
        if value is not None:
            return value
        return valid_value

    def _is_editing_attribute_element(self, attribute, array_index):
        attribute_path = attribute.GetPath()
        for i, check_attribute_path in enumerate(self._object_paths):
            check_array_index = self.__indices[i]
            if attribute_path == check_attribute_path and array_index == check_array_index:
                return True
        return False

    def _update_array_index(self, attribute, basis_curves, array_data, array_index, value):
        if array_index >= 0 and array_index < len(array_data):
            array_data[array_index] = self._apply_value_to_element(array_data[array_index], value)
            return True
        return False

    def _update_value(self, force=False):
        if (self._dirty or force) and self._stage:
            self.__is_updating = True
            super()._update_value(force)
            self.__is_updating = False
            self.__element_values = []
            if hasattr(self._value, "__len__"):
                for attribute_index, array_index in enumerate(self.__indices):
                    if attribute_index >= 0 and attribute_index < len(self._real_values):
                        real_values = self._real_values[attribute_index]
                        array_count = len(real_values)
                        array_index_0, array_index_1, t, _ = self._get_interpolation_data(
                            self._object_paths[attribute_index], self.__basis_curves[attribute_index], array_index
                        )
                        if array_index_0 < 0 or array_index_0 >= array_count:
                            self.__element_values.append(None)
                        elif array_index_1 < 0 and array_index_1 >= array_count:
                            self.__element_values.append(None)
                        else:
                            value = self._extract_value_from_element(real_values[array_index_0])
                            if t > 0.0:
                                value_1 = self._extract_value_from_element(real_values[array_index_1])
                                value = value + t * (value_1 - value)
                            self.__element_values.append(value)
            self._ambiguous = self._element_values_different(self.get_value())
            self._different_from_default = self._element_values_different(self._create_default_value())
            self.update_control_state()
            return True
        return False

    def destroy(self):
        self.clean()
        self.__basis_curves = None
        self.__create_default_element_fn = None
        self.__element_values = []
        self.__get_interpolation_fn = None
        self.__indices = None
        self.__is_updating = False

    def get_value(self):
        self._update_value()
        if len(self.__element_values) > 0:
            return self.__element_values[0]
        return None

    def get_value_as_bool(self) -> bool:
        return bool(self._get_valid_value(False))

    def get_value_as_float(self) -> float:
        return float(self._get_valid_value(0.0))

    def get_value_as_int(self) -> int:
        return int(self._get_valid_value(0))

    def get_value_as_string(self, elide_big_array=True) -> str:
        return str(self._get_valid_value(""))

    def is_editable(self) -> bool:
        for i, attribute_path in enumerate(self._object_paths):
            interpolation = self.__get_interpolation_fn(self._stage, attribute_path, self.__basis_curves[i])
            if interpolation not in UsdArrayElementAttributeModel.EDITABLE_INTERPOLATIONS:
                return False
        return True

    def set_default(self, *_):
        default_value = self._create_default_value()
        if self.is_different_from_default() and default_value is not None:
            self.set_value(default_value)

    def set_value(self, value):
        if self.is_locked():
            carb.log_warn("Setting locked attribute is not supported yet")
            self._update_value(True)
            return False
        if self._might_be_time_varying:
            carb.log_warn("Setting time varying attribute is not supported yet")
            self._update_value(True)
            return False
        attributes, attribute_indices = self._get_attributes_and_indices()
        if len(attributes) == 0:
            return False
        update_data_hash = {}
        for i, attribute in enumerate(attributes):
            attribute_index = attribute_indices[i]
            if attribute_index >= 0 and attribute_index < len(self._real_values):
                attribute_path = attribute.GetPath().pathString
                if attribute_path not in update_data_hash:
                    update_data_hash[attribute_path] = {
                        "array_data": [array_element for array_element in self._real_values[attribute_index]],
                        "attribute": attribute,
                    }
                array_index = self.__indices[attribute_index]
                basis_curves = self.__basis_curves[attribute_index]
                array_index, _, _, interpolation = self._get_interpolation_data(
                    attribute_path, basis_curves, array_index
                )
                if interpolation in UsdArrayElementAttributeModel.EDITABLE_INTERPOLATIONS:
                    array_data = update_data_hash[attribute_path]["array_data"]
                    if self._create_default_element() is not None:
                        while array_index >= len(array_data):
                            array_data.append(self._create_default_element())
                    if array_index < 0 or array_index >= len(array_data):
                        del update_data_hash[attribute_path]
                    elif not self._update_array_index(attribute, basis_curves, array_data, array_index, value):
                        del update_data_hash[attribute_path]
        with omni.kit.undo.group():
            self._ignore_notice = True
            for attribute_path in update_data_hash:
                update_data = update_data_hash[attribute_path]
                array_data = update_data["array_data"]
                attribute = update_data["attribute"]
                if not self._editing:
                    self._change_property(attribute.GetPath(), array_data, None)
                elif not self._change_on_edit_end:
                    attribute.Set(array_data)
            self._ignore_notice = False
        self._update_value(True)
        self._value_changed()
        return True

    def update_control_state(self):
        if not self.__is_updating:
            super().update_control_state()


class UsdTupleArrayElementAttributeModel(UsdArrayElementAttributeModel):
    def __init__(
        self,
        stage: Usd.Stage,
        attribute_paths: List[Sdf.Path],
        indices: List[int],
        component_index: int,
        self_refresh: bool,
        metadata: dict,
        change_on_edit_end=False,
        create_default_element_fn=None,
        **kwargs,
    ):
        super().__init__(
            stage=stage,
            attribute_paths=attribute_paths,
            indices=indices,
            self_refresh=self_refresh,
            metadata=metadata,
            change_on_edit_end=change_on_edit_end,
            create_default_element_fn=create_default_element_fn,
            **kwargs,
        )
        self.__component_index = component_index

    def _apply_value_to_element(self, element, value):
        if hasattr(element, "__len__"):
            if self.__component_index >= 0 and self.__component_index < len(element):
                element[self.__component_index] = value
        return element

    def _extract_value_from_element(self, element):
        if hasattr(element, "__len__"):
            if self.__component_index >= 0 and self.__component_index < len(element):
                return element[self.__component_index]
        return None


class CvAnchorElementAttributeModel(UsdTupleArrayElementAttributeModel):
    def __init__(
        self,
        stage: Usd.Stage,
        attribute_paths: List[Sdf.Path],
        indices: List[int],
        component_index: int,
        self_refresh: bool,
        metadata: dict,
        change_on_edit_end=False,
        create_default_element_fn=None,
        **kwargs,
    ):
        super().__init__(
            stage=stage,
            attribute_paths=attribute_paths,
            indices=indices,
            component_index=component_index,
            self_refresh=self_refresh,
            metadata=metadata,
            change_on_edit_end=change_on_edit_end,
            create_default_element_fn=create_default_element_fn,
            **kwargs,
        )

    def _calculate_tangent_offset(self, tangent, length, other_tangent, other_length, smooth, even):
        if smooth:
            tangent = -other_tangent
        if even:
            length = other_length
        return length * tangent

    def _get_periodic_anchor_index(self, array_index, basis_curves, array_index_start, array_index_end):
        if basis_curves.GetWrapAttr().Get() == UsdGeom.Tokens.periodic:
            if array_index == array_index_start:
                array_index = array_index_end
            elif array_index == array_index_end:
                array_index = array_index_start
        return array_index

    def _get_tangents(self, array_data, anchor_index, tangent_in_index, tangent_out_index):
        if tangent_in_index >= 0 and tangent_out_index < len(array_data):
            p0 = array_data[tangent_in_index]
            p1 = array_data[anchor_index]
            p2 = array_data[tangent_out_index]
            t0 = p0 - p1
            l0 = t0.Normalize()
            t1 = p2 - p1
            l1 = t1.Normalize()
            return (True, t0, l0, t1, l1)
        return (False, None, 0.0, None, 0.0)

    def _update_anchor(
        self,
        attribute,
        basis_curves,
        array_data,
        anchor_index,
        tangent_in_index,
        tangent_out_index,
        array_index_start,
        array_index_end,
        value,
        smooth,
        even,
    ):
        applied = True
        delta = value - self._extract_value_from_element(array_data[anchor_index])
        editing_tangent_in = self._is_editing_attribute_element(attribute, tangent_in_index)
        editing_tangent_out = self._is_editing_attribute_element(attribute, tangent_out_index)
        periodic_anchor_index = self._get_periodic_anchor_index(
            anchor_index, basis_curves, array_index_start, array_index_end
        )
        if super()._update_array_index(attribute, basis_curves, array_data, anchor_index, value):
            applied = True
        if anchor_index != periodic_anchor_index:
            if super()._update_array_index(attribute, basis_curves, array_data, periodic_anchor_index, value):
                applied = True
        if editing_tangent_in and editing_tangent_out:
            if super()._update_array_index(attribute, basis_curves, array_data, tangent_in_index, value):
                applied = True
            if super()._update_array_index(attribute, basis_curves, array_data, tangent_out_index, value):
                applied = True
        elif editing_tangent_in:
            if super()._update_array_index(attribute, basis_curves, array_data, tangent_in_index, value):
                applied = True
            if tangent_out_index is not None:
                tangent_out_value = self._extract_value_from_element(array_data[tangent_out_index]) + delta
                if super()._update_array_index(
                    attribute, basis_curves, array_data, tangent_out_index, tangent_out_value
                ):
                    applied = True
                self._update_tangent_out(
                    attribute, array_data, anchor_index, tangent_in_index, tangent_out_index, smooth, even
                )
        elif editing_tangent_out:
            if super()._update_array_index(attribute, basis_curves, array_data, tangent_out_index, value):
                applied = True
            if tangent_in_index is not None:
                tangent_in_value = self._extract_value_from_element(array_data[tangent_in_index]) + delta
                if super()._update_array_index(attribute, basis_curves, array_data, tangent_in_index, tangent_in_value):
                    applied = True
                self._update_tangent_in(
                    attribute, array_data, anchor_index, tangent_in_index, tangent_out_index, smooth, even
                )
        else:
            if tangent_in_index is not None:
                tangent_in_value = self._extract_value_from_element(array_data[tangent_in_index]) + delta
                if super()._update_array_index(attribute, basis_curves, array_data, tangent_in_index, tangent_in_value):
                    applied = True
            if tangent_out_index is not None:
                tangent_out_value = self._extract_value_from_element(array_data[tangent_out_index]) + delta
                if super()._update_array_index(
                    attribute, basis_curves, array_data, tangent_out_index, tangent_out_value
                ):
                    applied = True
        return applied

    def _update_array_index(self, attribute, basis_curves, array_data, array_index, value):
        if not utils.has_tangents(basis_curves):
            return super()._update_array_index(attribute, basis_curves, array_data, array_index, value)
        applied = False
        array_index_start, array_index_end = utils.get_array_index_range(basis_curves, array_index)
        smooth, even, tangent_in_index, anchor_index, tangent_out_index = utils.has_smooth_tangent(
            basis_curves, array_index
        )
        can_edit_tangents = not self._is_editing_attribute_element(attribute, anchor_index)
        if can_edit_tangents and array_index == tangent_in_index:
            if super()._update_array_index(attribute, basis_curves, array_data, array_index, value):
                applied = True
                self._update_tangent_out(
                    attribute, array_data, anchor_index, tangent_in_index, tangent_out_index, smooth, even
                )
        elif can_edit_tangents and array_index == tangent_out_index:
            if super()._update_array_index(attribute, basis_curves, array_data, array_index, value):
                applied = True
                self._update_tangent_in(
                    attribute, array_data, anchor_index, tangent_in_index, tangent_out_index, smooth, even
                )
        elif array_index == anchor_index:
            if self._update_anchor(
                attribute,
                basis_curves,
                array_data,
                anchor_index,
                tangent_in_index,
                tangent_out_index,
                array_index_start,
                array_index_end,
                value,
                smooth,
                even,
            ):
                applied = True
        return applied

    def _update_tangent_in(
        self, attribute, array_data, anchor_index, tangent_in_index, tangent_out_index, smooth, even
    ):
        if smooth or even:
            if not self._is_editing_attribute_element(attribute, tangent_in_index):
                valid, t0, l0, t1, l1 = self._get_tangents(
                    array_data, anchor_index, tangent_in_index, tangent_out_index
                )
                if valid:
                    offset = self._calculate_tangent_offset(t0, l0, t1, l1, smooth, even)
                    array_data[tangent_in_index] = array_data[anchor_index] + offset

    def _update_tangent_out(
        self, attribute, array_data, anchor_index, tangent_in_index, tangent_out_index, smooth, even
    ):
        if smooth or even:
            if not self._is_editing_attribute_element(attribute, tangent_out_index):
                valid, t0, l0, t1, l1 = self._get_tangents(
                    array_data, anchor_index, tangent_in_index, tangent_out_index
                )
                if valid:
                    offset = self._calculate_tangent_offset(t1, l1, t0, l0, smooth, even)
                    array_data[tangent_out_index] = array_data[anchor_index] + offset


class InterpolationsModel(ui.AbstractItemModel):
    INTERPOLATIONS = [UsdGeom.Tokens.constant, UsdGeom.Tokens.varying, UsdGeom.Tokens.vertex]

    class Item(ui.AbstractItem):
        def __init__(self, text: str):
            super().__init__()
            self.model = ui.SimpleStringModel(text)

        def destroy(self):
            self.model = None

    def __init__(
        self,
        stage: Usd.Stage,
        attribute_paths: List[Sdf.Path],
        basis_curves: List[UsdGeom.BasisCurves],
        create_default_element_fn=None,
        get_interpolation_fn=None,
    ):
        super().__init__()
        current_index = -1
        count = min(len(attribute_paths), len(basis_curves))
        if not get_interpolation_fn:
            get_interpolation_fn = default_get_interpolation_fn
        if stage:
            current_value = ""
            if count > 0:
                current_value = get_interpolation_fn(stage, attribute_paths[0], basis_curves[0])
            if current_value in InterpolationsModel.INTERPOLATIONS:
                current_index = InterpolationsModel.INTERPOLATIONS.index(current_value)
        self._attribute_paths = attribute_paths
        self.__basis_curves = basis_curves
        self._combobox_items = [InterpolationsModel.Item(i) for i in InterpolationsModel.INTERPOLATIONS]
        self._create_default_element_fn = create_default_element_fn
        self._current_index = self._current_index = ui.SimpleIntModel(current_index)
        self._current_index.add_value_changed_fn(self._on_index_changed)
        self._get_interpolation_fn = get_interpolation_fn
        self._stage = stage

    def _create_default_element(self):
        if self._create_default_element_fn:
            return self._create_default_element_fn()
        return None

    def _get_anchor_point_count(self, basis_curves):
        anchor_point_count = 0
        has_tangents = utils.has_tangents(basis_curves)
        for vertex_count in basis_curves.GetCurveVertexCountsAttr().Get():
            if has_tangents:
                anchor_point_count = anchor_point_count + math.ceil(float(vertex_count) / 3.0)
            else:
                anchor_point_count = anchor_point_count + vertex_count
        return anchor_point_count

    def destroy(self):
        self._attribute_paths = []
        self.__basis_curves = []
        self._combobox_items = []
        self._create_default_element_fn = None
        self._current_index = None
        self._get_interpolation_fn = None
        self._stage = None

    def get_attribute_paths(self):
        return self._attribute_paths

    def get_current_index(self):
        return self._current_index.get_value_as_int()

    def get_current_value(self):
        current_index = self.get_current_index()
        if current_index >= 0 and current_index < len(self._combobox_items):
            return self._combobox_items[current_index].model.get_value_as_string()
        return None

    def get_item_children(self, _):
        return self._combobox_items

    def get_item_value_model(self, item, _):
        if item is None:
            return self._current_index
        return item.model

    def _on_index_changed(self, index_model: ui.SimpleIntModel):
        index = index_model.get_value_as_int()
        if index >= 0 and index < len(InterpolationsModel.INTERPOLATIONS) and self._stage:
            interpolation = InterpolationsModel.INTERPOLATIONS[index]
            update_data_hash = {}
            for i, attribute_path in enumerate(self._attribute_paths):
                attribute = self._stage.GetAttributeAtPath(attribute_path)
                basis_curves = self.__basis_curves[i]
                default_element = self._create_default_element()
                new_value = []
                old_interpolation = self._get_interpolation_fn(self._stage, attribute_path, basis_curves)
                old_value = attribute.Get()
                old_value_array = old_value
                if old_value is None:
                    old_value_array = []
                if interpolation == UsdGeom.Tokens.constant:
                    if len(old_value_array) > 0:
                        new_value.append(old_value_array[0])
                    else:
                        new_value.append(default_element)
                elif interpolation == UsdGeom.Tokens.varying or interpolation == UsdGeom.Tokens.vertex:
                    new_count = len(basis_curves.GetPointsAttr().Get())
                    old_count = len(old_value_array)
                    if interpolation == UsdGeom.Tokens.varying:
                        new_count = self._get_anchor_point_count(basis_curves)
                    if old_interpolation == UsdGeom.Tokens.constant:
                        old_count = min(old_count, 1)
                    if old_count > 0:
                        index_scale = 1.0
                        if new_count > 1:
                            index_scale = 1.0 / float(new_count - 1)
                        for new_index in range(new_count):
                            old_index = index_scale * float(new_index) * (old_count - 1)
                            old_index_a = int(max(0, min(math.floor(old_index), old_count - 1)))
                            old_index_b = int(max(0, min(old_index_a + 1, old_count - 1)))
                            old_index_t = old_index - float(old_index_a)
                            value_a = old_value_array[old_index_a]
                            value_b = old_value_array[old_index_b]
                            value = value_a + old_index_t * (value_b - value_a)
                            new_value.append(value)
                    else:
                        while len(new_value) < new_count:
                            new_value.append(default_element)
                elif interpolation == UsdGeom.Tokens.vertex:
                    new_count = len(basis_curves.GetPointsAttr().Get())
                    if new_count > 0:
                        for value in old_value_array:
                            new_value.append(value)
                        if len(new_value) > 0:
                            default_element = new_value[-1]
                        while len(new_value) < new_count:
                            new_value.append(default_element)
                        new_value = new_value[:new_count]
                else:
                    new_value = old_value
                update_data_hash[attribute_path] = {
                    "interpolation": interpolation,
                    "new_value": new_value,
                    "old_value": old_value,
                }
            with omni.kit.undo.group():
                for attribute_path in update_data_hash:
                    update_data = update_data_hash[attribute_path]
                    omni.kit.commands.execute(
                        "SetPrimvarInterpolationCommand",
                        primvar_path=attribute_path,
                        interpolation=update_data["interpolation"],
                    )
                    omni.kit.commands.execute(
                        "ChangeProperty",
                        prop_path=attribute_path,
                        value=update_data["new_value"],
                        prev=update_data["old_value"],
                    )
            self._item_changed(None)
