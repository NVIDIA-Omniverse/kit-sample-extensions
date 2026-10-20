# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio
from numbers import Number
from typing import List, Optional

import carb
import carb.settings
import carb.tokens
import omni.client
import omni.kit.app
import omni.kit.commands
import omni.kit.undo
import omni.usd
from carb.eventdispatcher import get_eventdispatcher
from pxr import Gf, Sdf, Tf, Usd, UsdGeom, UsdShade, Vt

from ..constants import (
    ENVIRONMENT_MATERIALS_ROOT,
    ENVIRONMENT_PRIM_ROOT,
    GROUND_DEFAULT_SIZE,
    GROUND_PRIM_PATH,
    EnvironmentProperties,
    EnvironmentSettings,
    GroundSettings,
)
from ..models import PropertyValueModel, SettingModel, UsdModelBuilder
from ..scene_template import SceneTemplateHelper
from ..singleton import Singleton
from ..utils import get_subidentifier_from_mdl_async
from .commands import CreateGroundCommand


class GroundType:
    """Enumeration of ground display options in omni.kit.environment.core.

    This class defines string constants for configuring ground rendering modes. Use OFF to disable ground, ON to enable full ground, and SHADOWS to display ground with shadows only.
    """

    OFF = "Off"
    """str: Represents ground turned off."""
    ON = "On"
    """str: Represents ground fully active."""
    SHADOWS = "Shadows Only"
    """str: Represents ground with shadows only enabled."""


@Singleton
class GroundHelper:
    """
    Helper to manager ground, for example, create, hide/show, set size
    """

    def __init__(self):
        self._settings = carb.settings.get_settings()

        self._ground_prim: Optional[Usd.Prim] = None
        self._ground_type_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.GROUND_TYPE, value_type=Sdf.ValueTypeNames.String, default=GroundType.OFF
        )
        self._ground_type_model.add_value_changed_fn(self._on_ground_type_changed)
        self._ground_size_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.GROUND_SIZE, value_type=Sdf.ValueTypeNames.Int, default=GROUND_DEFAULT_SIZE
        )
        self._ground_size_model.add_value_changed_fn(self._on_ground_size_changed)

        self._ground_material_model = None

        UsdModelBuilder().register_prim_callback(GROUND_PRIM_PATH, self._on_ground_prim_changed)

        context = omni.usd.get_context()
        self._stage_event_subs = [
            get_eventdispatcher().observe_event(
                observer_name="omni.kit.environment.core.GroundHelper",
                event_name=context.stage_event_name(e),
                on_event=trigger_fn,
            )
            for e, trigger_fn in [
                (omni.usd.StageEventType.OPENED, self._on_stage_opened),
                (omni.usd.StageEventType.CLOSED, self._on_stage_closed),
            ]
        ]

        self._stage = omni.usd.get_context().get_stage()
        if self._stage:
            self._on_stage_opened()

        self._scene_template_helper = SceneTemplateHelper()

    def destroy(self):
        """Destroys the ground helper subscription.

        Releases the stage event subscription by setting it to None.
        """
        self._stage_event_subs.clear()
        self._stage_event_subs = None

    def find_ground(self, root_path: str = ENVIRONMENT_PRIM_ROOT) -> Optional[Usd.Prim]:
        """Finds the ground prim using the provided root prim path.

        Args:
            root_path (str): Root prim path to search for the ground prim.

        Returns:
            Optional[Usd.Prim]: The ground prim if found, otherwise None.
        """
        stage = omni.usd.get_context().get_stage()
        if not stage:
            return None
        env_root_prim = stage.GetPrimAtPath(root_path)
        if not env_root_prim:
            return None
        children = env_root_prim.GetChildren()
        for prim in children:
            prim_path = prim.GetPath().pathString
            if prim_path.split("/")[-1].startswith("ground") and prim.GetTypeName() == "Mesh":
                return prim
        else:
            return None

    @property
    def ground_prim(self) -> Optional[Usd.Prim]:
        """Gets the current ground prim.

        Returns:
            Optional[Usd.Prim]: The current ground prim, or None.
        """
        return self._ground_prim

    @ground_prim.setter
    def ground_prim(self, prim: Optional[Usd.Prim]):
        """Sets the ground prim and updates the ground material model binding if a valid prim is provided.

        Args:
            prim (Optional[Usd.Prim]): The new ground prim to set.
        """
        carb.log_info(f"Ground found: {prim}")

        self._ground_prim = prim
        self._settings.set(GroundSettings.PATH, prim.GetPath().pathString if prim else "")
        if prim:
            self._ground_material_model = UsdModelBuilder().create_property_value_model(
                f"{prim.GetPath().pathString}.material:binding", value_type=Sdf.ValueTypeNames.String, default=""
            )

    @property
    def ground_material(self) -> Optional[str]:
        """Gets the bound ground material string if available.

        Returns:
            Optional[str]: The ground material string if available, otherwise None.
        """
        if self._ground_material_model:
            return self._ground_material_model.as_string
        else:
            return None

    def _on_stage_closed(self, _):
        self._ground_type_model.set_default(GroundType.OFF, save=False)
        self._stage = None

    def _on_stage_opened(self, _):
        self._stage = omni.usd.get_context().get_stage()
        self.ground_prim = self.find_ground()
        if self._settings.get(EnvironmentSettings.GROUND_ENABLE):
            if self._ground_prim is None:
                self._create_default_ground()
        else:
            self._load_ground_type(save=False)
            # OM-79422: no usd notification when ground size property created, set size here
            if self._stage.GetPropertyAtPath(EnvironmentProperties.GROUND_SIZE):
                self._set_ground_size(self._ground_size_model.as_float)

    def _load_ground_type(self, save=True):
        if self._ground_prim is None:
            self._ground_type_model.set_default(GroundType.OFF, save=save)
        else:
            if not self._is_ground_visible():
                self._ground_type_model.set_default(GroundType.OFF, save=save)
            elif self._is_ground_matte_object():
                self._ground_type_model.set_default(GroundType.SHADOWS, save=save)
            else:
                self._ground_type_model.set_default(GroundType.ON, save=save)

    def _create_default_ground(self, ground_type: GroundType = GroundType.ON):
        # Create ground plane
        omni.kit.commands.execute("CreateGroundCommand", u_patches=1, v_patches=1)
        self.ground_prim = self.find_ground()

        # Set ground size
        self._set_ground_size(self._ground_size_model.as_float)

        async def __bind_material_async():
            # Bind default ground material
            default_material_asset = self._settings.get(EnvironmentSettings.GROUND_MATERIAL)
            if default_material_asset:
                default_material_asset = carb.tokens.get_tokens_interface().resolve(default_material_asset)
                result, list_entry = omni.client.stat(default_material_asset)
                if result == omni.client.Result.OK:
                    omni.kit.undo.begin_group()
                    default_material_sub_id = self._settings.get(EnvironmentSettings.GROUND_SUB_MATERIAL)
                    if default_material_sub_id:
                        sub_ids = await get_subidentifier_from_mdl_async(default_material_asset)
                        if not sub_ids or default_material_sub_id not in sub_ids:
                            default_material_sub_id = ""
                    material_prim_path = self._create_material(default_material_asset, default_material_sub_id)
                    self._bind_material(material_prim_path, GROUND_PRIM_PATH)
                    omni.kit.undo.end_group()
                else:
                    carb.log_error(f"Failed to create ground material: {default_material_asset} {result}")

        asyncio.ensure_future(__bind_material_async())

        self._ground_type_model.set_default(ground_type)

    def _set_ground_size(self, size: float):
        stage = omni.usd.get_context().get_stage()
        if stage and self._ground_prim:
            ground_prim_path = self._ground_prim.GetPath().pathString
            # Calculate from plane
            prop_points = stage.GetPropertyAtPath(ground_prim_path + ".points")
            prop_extent = stage.GetPropertyAtPath(ground_prim_path + ".extent")
            mesh = UsdGeom.Mesh.Get(omni.usd.get_context().get_stage(), ground_prim_path)
            if mesh:
                if hasattr(mesh, "GetPrimvar"):
                    st = mesh.GetPrimvar("st")
                else:
                    st = UsdGeom.PrimvarsAPI(mesh).GetPrimvar("st")
            else:
                st = None
            if prop_points and st:
                # Set point size for 1 meter
                points = prop_points.Get()
                scale = float(size) / 2 / abs(points[0][0])

                up_axis = UsdGeom.GetStageUpAxis(stage)
                # if up_axis == "Z":
                if True:
                    new_points = []
                    for point in points:
                        for i in range(3):
                            point[i] *= scale
                        new_points.append(point)
                    prop_points.Set(new_points)
                    new_st = []
                    base = None
                    for index, st_point in enumerate(st.Get()):
                        if index == 0:
                            new_st.append(st_point)
                            base = st_point
                        else:
                            new_point = (st_point - base) * scale + base
                            new_st.append(new_point)
                    st.Set(new_st)

                    prop_extent.Set([(-size, -size, 0), (size, size, 0)])

    def _create_material(self, material_url: str, material_sub_id: str, context_name: str = "") -> str:
        """
        Create material. Return path of created material prim.
        Args:
            material_url (str): Material url to create material.
            material_sub_id (str): Sub Identifier of material.
            context_name (str): Name of usd context to create material in.
        """
        # Comes from material browser
        usd_context = omni.usd.get_context(context_name)
        stage = usd_context.get_stage()

        name = material_url.split("/")[-1]
        material_name = material_sub_id if material_sub_id else name[:-4]
        material_prim_path = omni.usd.get_stage_next_free_path(
            stage, f"{ENVIRONMENT_MATERIALS_ROOT}/{Tf.MakeValidIdentifier(material_name)}", False
        )

        if name.endswith("mdl"):
            omni.kit.commands.execute(
                "CreateMdlMaterialPrimCommand",
                mtl_url=material_url,
                mtl_name=material_name,
                mtl_path=material_prim_path,
            )
        else:
            omni.kit.commands.execute(
                "CreateReferenceCommand",
                path_to=material_prim_path,
                asset_path=material_url,
                prim_path=None,
                usd_context=usd_context,
            )
        return material_prim_path

    def _bind_material(
        self, material_prim_path: str, target_path: str, strength=UsdShade.Tokens.strongerThanDescendants
    ) -> None:
        """
        Bind material to target prims.
        Args:
            material_prim_path (str): Url of material prim.
            target_path (str): Target paths.
        """
        omni.kit.commands.execute(
            "BindMaterial", prim_path=target_path, material_path=material_prim_path, strength=strength
        )

    def _on_ground_size_changed(self, model: PropertyValueModel) -> None:
        if not self._stage:
            return
        if model.as_float > 0:
            self._set_ground_size(model.as_float)

    def _is_ground_matte_object(self) -> bool:
        if self._ground_prim:
            primvars_api = UsdGeom.PrimvarsAPI(self._ground_prim)
            value = primvars_api.GetPrimvar("isMatteObject")
            if value:
                return value.Get()
            else:
                return False
        else:
            return False

    def _set_ground_matte_object(self, enable) -> None:
        if self._ground_prim:
            if enable:
                self._clean_ground_material()
            primvars_api = UsdGeom.PrimvarsAPI(self._ground_prim)
            value = primvars_api.GetPrimvar("isMatteObject")
            if value:
                value.Set(enable)
            else:
                primvars_api.CreatePrimvar("isMatteObject", Sdf.ValueTypeNames.Bool).Set(enable)

    def _is_ground_visible(self) -> bool:
        if self._ground_prim:
            visible_attr_path = self._ground_prim.GetPath().pathString + ".visibility"
            visible_attr = self._ground_prim.GetAttributeAtPath(visible_attr_path)
            if visible_attr:
                return visible_attr.Get() != "invisible"
            else:
                return True
        else:
            return False

    def _set_ground_visible(self, visible: bool) -> None:
        value = "inherited" if visible else "invisible"
        if self._ground_prim:
            visible_attr_path = self._ground_prim.GetPath().pathString + ".visibility"
            visible_attr = self._ground_prim.GetAttributeAtPath(visible_attr_path)
            if visible_attr:
                return visible_attr.Set(value)
            else:
                self._ground_prim.CreateAttribute(visible_attr_path, Sdf.ValueTypeNames.String, value)

    def _on_ground_type_changed(self, model: PropertyValueModel) -> None:
        if not self._stage:
            return

        # OM-104065: Do nothing if ENVIRONMENT_PRIM_ROOT becomes inactive
        if self._is_environment_inactive():
            return

        if model.as_string != GroundType.SHADOWS:
            self._restore_ground_material()
        if model.as_string == GroundType.OFF:
            self._set_ground_visible(False)
        else:
            if self._ground_prim is None:
                # Check ground again to fix issue when applying template
                self.ground_prim = self.find_ground()
                if self._ground_prim is None:
                    self._create_default_ground(ground_type=model.as_string)
            else:
                self._set_ground_visible(True)
                if model.as_string == GroundType.ON:
                    self._set_ground_matte_object(False)
                if model.as_string == GroundType.SHADOWS:
                    self._set_ground_matte_object(True)

    def _on_ground_prim_changed(self, stage: Usd.Stage, path: str) -> None:
        self.ground_prim = self.find_ground()
        carb.log_info(f"Ground changed to: {self.ground_prim}")

        async def __load():
            await omni.kit.app.get_app().next_update_async()
            self._load_ground_type(save=False)

        asyncio.ensure_future(__load())

    def update_ground_material(self, material_path: str) -> None:
        """Updates the ground material by copying it from the provided material path. The method creates a copy under the environment materials root and rebinds it to the ground prim.

        Args:
            material_path (str): Path of the source ground material to copy.
        """
        if material_path and not material_path.startswith(ENVIRONMENT_MATERIALS_ROOT):
            material_name = material_path.split("/")[-1]
            stage = omni.usd.get_context().get_stage()
            materials_root = stage.GetPrimAtPath(ENVIRONMENT_MATERIALS_ROOT)
            if not materials_root:
                stage.DefinePrim(ENVIRONMENT_MATERIALS_ROOT, "Scope")
            new_material_path = omni.usd.get_stage_next_free_path(
                stage, ENVIRONMENT_MATERIALS_ROOT + "/" + material_name, False
            )
            carb.log_info(f"Copy ground material from {material_path} to {new_material_path}")
            omni.kit.commands.execute(
                "CopyPrimCommand", path_from=material_path, path_to=new_material_path, combine_layers=True
            )
            # OM-97507: If binding in session layer, must update binding in session layer too. Otherwise it takes no effect
            target_layer, _ = omni.usd.find_spec_on_session_or_its_sublayers(
                self._stage, self._ground_material_model.property_path
            )
            with Usd.EditContext(stage, target_layer):
                self._bind_material(new_material_path, self._ground_prim.GetPath().pathString)

    def _clean_ground_material(self):
        if self.ground_material:
            stage = omni.usd.get_context().get_stage()

            # Save current ground material
            self._save_property(EnvironmentProperties.GROUND_MATERIAL_PATH, self.ground_material)

            strength = self._get_material_strength()
            self._save_property(EnvironmentProperties.GROUND_MATERIAL_STRENGTH, strength)

            # unbind material
            self._bind_material("", self._ground_prim.GetPath().pathString)

    def _restore_ground_material(self):
        if not self._ground_prim:
            return
        stage = omni.usd.get_context().get_stage()
        ground_material_path = self._laod_property(EnvironmentProperties.GROUND_MATERIAL_PATH)
        ground_material_strength = self._laod_property(EnvironmentProperties.GROUND_MATERIAL_STRENGTH)
        if ground_material_path:
            self._bind_material(
                ground_material_path, self._ground_prim.GetPath().pathString, strength=ground_material_strength
            )

    def _get_material_strength(self):
        if not self._ground_prim:
            return None

        strength = None
        material, relationship = UsdShade.MaterialBindingAPI(self._ground_prim).ComputeBoundMaterial()
        if relationship:
            strength = UsdShade.MaterialBindingAPI.GetMaterialBindingStrength(relationship)
        return strength

    def _save_property(self, property_path: str, value: str) -> None:
        stage = omni.usd.get_context().get_stage()

        # Save current ground material
        prop = stage.GetPropertyAtPath(property_path)
        if prop:
            prop.Set(value)
        else:
            # Create attribute
            prim_path, attr_name = property_path.split(".")
            prim = stage.GetPrimAtPath(prim_path)
            if prim:
                prim.CreateAttribute(attr_name, Sdf.ValueTypeNames.String).Set(value)

    def _laod_property(self, property_path: str, default=None):
        stage = omni.usd.get_context().get_stage()
        prop = stage.GetPropertyAtPath(property_path)
        if prop:
            return prop.Get()
        else:
            return default

    def _is_environment_inactive(self) -> bool:
        if not self._stage:
            return False
        env_prim = self._stage.GetPrimAtPath(ENVIRONMENT_PRIM_ROOT)
        if env_prim and not env_prim.IsActive():
            return True
        return False
