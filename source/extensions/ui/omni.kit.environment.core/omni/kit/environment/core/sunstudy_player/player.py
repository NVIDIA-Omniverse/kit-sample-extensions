# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import math
from datetime import date, datetime
from typing import Any, Optional

import carb
import carb.events
import carb.settings
import omni.kit.app
import omni.usd
from carb.eventdispatcher import Event, get_eventdispatcher
from pxr import Gf, Sdf, Usd, UsdGeom, UsdLux

from ..constants import ENVIRONMENT_PRIM_ROOT, SKY_PRIM_PATH, EnvironmentProperties, PlaySettings
from ..models import PropertyValueModel, SettingModel, UsdModelBuilder

DEBUG_MODE = False
PERSISTENT_SETTING_NORTHORIENTATION = "/persistent/app/stage/northOrientation"


class SunstudySkyType:
    """A class for specifying the sky configuration mode for sun study environments.

    This class provides string constants that define the available sky types. Use these constants to indicate the current sky state when configuring sun study features in the omni.kit.environment.core extension.

    Constants:
        NONE: Indicates that no sky is configured.
        DYNAMIC: Indicates a dynamic sky that changes over time.
        STATIC: Indicates a static sky.
    """

    NONE = "None"
    """str: 'None' value indicating no sky configuration is used."""
    DYNAMIC = "Dynamic"
    """str: 'Dynamic' value representing a sky with dynamic properties."""
    STATIC = "Static"
    """str: 'Static' value representing a sky with fixed lighting setup."""


class SunstudyPlayer:
    """A class for controlling sun study playback in a USD stage environment.

    This class manages dynamic sky simulation by configuring and updating various environment parameters, such as time, date, and geographic location. It is designed to handle play settings including play rate, looping, and current time updates, and it synchronizes changes to sky attributes like sun position and related lighting parameters.

    Users can start and stop playback, update timezone adjustments for predefined city locations, and implicitly manage property changes for latitude, longitude, north orientation, and time controls. The class integrates with USD stage events and settings to reload and refresh sky data when needed, ensuring that the environment remains consistent with artist and simulation inputs.

    It provides a straightforward interface, where starting the simulation prepares the dynamic sky based on current settings and middleware events, and stopping halts active updates to allow for further configuration or cleanup.
    """

    def __init__(self):
        self._fixtimezone = True

        self._usd_context = omni.usd.get_context()
        self._stage: Optional[Usd.Stage] = None
        self._settings = carb.settings.get_settings()

        # Play setting
        self._play_rate_model = SettingModel(PlaySettings.RATE)
        self._play_loop_model = SettingModel(PlaySettings.LOOP)
        self._playing_model = SettingModel(PlaySettings.PLAYING)
        self._current_sky_model = SettingModel(PlaySettings.CURRENT_SKY_PATH)
        self._current_sky_type_model = SettingModel(PlaySettings.CURRENT_SKY_TYPE)

        # Datetime Properties
        self._date_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.DATE, value_type=Sdf.ValueTypeNames.String, default="2021-11-24", default_prim_type=""
        )
        self._date_model.add_value_changed_fn(self._on_date_changed)
        self._start_time_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.TIME_START, value_type=Sdf.ValueTypeNames.Float, default=6.0, default_prim_type=""
        )
        self._start_time_model.add_value_changed_fn(self._on_start_time_changed)
        self._end_time_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.TIME_END, value_type=Sdf.ValueTypeNames.Float, default=18.0, default_prim_type=""
        )
        self._end_time_model.add_value_changed_fn(self._on_end_time_changed)
        self._current_time_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.TIME_CURRENT, value_type=Sdf.ValueTypeNames.Float, default=6.0, default_prim_type=""
        )
        self._current_time_model.add_value_changed_fn(self._on_current_time_changed)

        # Location properties
        self._longitude_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.LONGITUDE,
            value_type=Sdf.ValueTypeNames.Double,
            default=0.0,
            min=-180,
            max=180,
            default_prim_type="",
        )
        self._longitude_model.add_value_changed_fn(self._on_longitude_changed)
        self._latitude_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.LATITUDE,
            value_type=Sdf.ValueTypeNames.Double,
            default=0.0,
            min=-90,
            max=90,
            default_prim_type="",
        )
        self._latitude_model.add_value_changed_fn(self._on_latitude_changed)
        self._north_orientation_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.NORTH_ORIENTATION,
            value_type=Sdf.ValueTypeNames.Double,
            default=0.0,
            min=0,
            max=360,
            default_prim_type="",
        )
        self._north_orientation_model.add_value_changed_fn(self._on_north_orientation_changed)

        # Weather properties
        self._cumulus_enabled_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.CUMULUS_ENABLED,
            value_type=Sdf.ValueTypeNames.Bool,
            default=False,
        )
        self._cumulus_enabled_model.add_value_changed_fn(self._on_cumulus_enabled_changed)

        self._cloud_coverage_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.CLOUD_COVERAGE,
            value_type=Sdf.ValueTypeNames.Float,
            default=0.0,
            min=-0.5,
            max=0.5,
            default_prim_type="",
        )
        self._cloud_coverage_model.add_value_changed_fn(self._on_cloud_coverage_changed)

        self._haze_model = UsdModelBuilder().create_property_value_model(
            EnvironmentProperties.HAZE,
            value_type=Sdf.ValueTypeNames.Float,
            default=0.0,
            min=0.0,
            max=1.0,
            default_prim_type="",
        )
        self._haze_model.add_value_changed_fn(self._on_haze_changed)

        self._SKY_ATTRIBUTES = {
            "Year": None,
            "TimeOfDay": self._current_time_model,
            "DayOfYear": None,
            "StartTOD": self._start_time_model,
            "EndTOD": self._end_time_model,
            "Latitude": self._latitude_model,
            "Longitude": self._longitude_model,
            "NorthOrientation": self._north_orientation_model,
            "CumulusEnabled": self._cumulus_enabled_model,
            "CloudCoverage": self._cloud_coverage_model,
            "haze": self._haze_model,
        }

        self._update_sub = None
        self._stage_event_subs = [
            get_eventdispatcher().observe_event(
                observer_name="omni.kit.environment.core.SunStudyPlayer",
                event_name=self._usd_context.stage_event_name(e),
                on_event=trigger_fn,
            )
            for e, trigger_fn in [
                (omni.usd.StageEventType.OPENED, self._on_stage_opened),
                (omni.usd.StageEventType.CLOSING, self._on_stage_closing),
                (omni.usd.StageEventType.CLOSED, self._on_stage_closed),
                (omni.usd.StageEventType.ASSETS_LOADED, self._on_stage_assets_loaded),
            ]
        ]
        UsdModelBuilder().register_prim_callback(SKY_PRIM_PATH, self._on_sky_changed)

        self.sky_type = SunstudySkyType.NONE
        self._current_sky_type_model.set_value(SunstudySkyType.NONE)
        self._reload_sky()

    def destroy(self):
        """Destroys the SunstudyPlayer by releasing event subscriptions and destroying property models for play rate, loop, playing, sky settings, time, date, and location."""
        self._update_sub = None
        if self._stage_event_subs:
            self._stage_event_subs.clear()
            self._stage_event_subs = None
        self._play_rate_model.destroy()
        self._play_loop_model.destroy()
        self._playing_model.destroy()
        self._current_sky_model.destroy()
        self._current_sky_type_model.destroy()
        self._start_time_model.destroy()
        self._end_time_model.destroy()
        self._current_time_model.destroy()
        self._date_model.destroy()
        self._longitude_model.destroy()
        self._latitude_model.destroy()
        self._north_orientation_model.destroy()

    @property
    def latitude(self) -> float:
        """Gets the current latitude value used for sun position calculations.

        Returns:
            float: Current latitude retrieved from the latitude model.
        """
        return self._latitude_model.as_float

    @latitude.setter
    def latitude(self, value: float) -> None:
        """Sets the latitude value used for sun position calculations.

        Args:
            value (float): New latitude value.
        """
        self._latitude_model.set_value(value)

    @property
    def longitude(self) -> float:
        """Gets the current longitude value used for sun position calculations.

        Returns:
            float: Current longitude retrieved from the longitude model.
        """
        return self._longitude_model.as_float

    @longitude.setter
    def longitude(self, value: float) -> None:
        """Sets the longitude value used for sun position calculations.

        Args:
            value (float): New longitude value.
        """
        self._longitude_model.set_value(value)

    @property
    def north_orientation(self) -> float:
        """Gets the current north orientation value used to adjust directional alignment.

        Returns:
            float: Current north orientation retrieved from the north orientation model.
        """
        return self._north_orientation_model.as_float

    @north_orientation.setter
    def north_orientation(self, value: float) -> None:
        """Sets the north orientation value used to adjust directional alignment.

        Args:
            value (float): New north orientation value.
        """
        self._north_orientation_model.set_value(value)

    @property
    def current_time(self) -> float:
        """Time in hours"""
        return self._current_time_model.as_float

    @current_time.setter
    def current_time(self, value: float) -> None:
        """Sets the current time in hours for scene animation.

        Args:
            value (float): New current time value in hours.
        """
        self._current_time_model.set_value(value)

    @property
    def start_time(self) -> float:
        """Time in hours"""
        return self._start_time_model.as_float

    @start_time.setter
    def start_time(self, value: float) -> None:
        """Sets the start time in hours to define the animation range.

        Args:
            value (float): New start time value in hours.
        """
        self._start_time_model.set_value(value)

    @property
    def end_time(self) -> float:
        """Time in hours"""
        return self._end_time_model.as_float

    @end_time.setter
    def end_time(self, value: float) -> None:
        """Sets the end time in hours to define the animation range.

        Args:
            value (float): New end time value in hours.
        """
        self._end_time_model.set_value(value)

    @property
    def current_date(self) -> str:
        """Date in year-month-day"""
        current_date = date.fromordinal(
            date(int(self._skydata["Year"]), 1, 1).toordinal() + int(self._skydata["DayOfYear"]) - 1
        )
        return "{}-{:02d}-{:02d}".format(current_date.year, current_date.month, current_date.day)

    @current_date.setter
    def current_date(self, value: str) -> None:
        """Sets the current date in year-month-day format.

        Args:
            value (str): New current date value in YYYY-MM-DD format.
        """
        self._date_model.set_value(value)

    def start(self) -> bool:
        """Start playing. If no sky is present, logs a warning and returns False. Resets current time if it is near the end time, subscribes to update events, and enables playing.

        Returns:
            bool: True if playing started successfully, False otherwise.
        """
        if self._sky_root is None:
            carb.log_warn("Sunstudy cannot work since no sky!")
            return False

        if self.current_time + 0.01 >= self.end_time:
            self._current_time_model.set_value(self.start_time)

        if self._update_sub is None:
            self._update_sub = carb.eventdispatcher.get_eventdispatcher().observe_event(
                observer_name="omni.kit.environment.core.SunStudyPlayer",
                event_name=omni.kit.app.GLOBAL_EVENT_UPDATE,
                on_event=self._on_update,
            )

        self._playing_model.set_value(True)

        return True

    def stop(self) -> None:
        """Stops playing by setting the playing flag to False and clearing the update subscription."""
        self._playing_model.set_value(False)
        self._update_sub = None

    def update_fix_timezone(self, need_fix_timezone: bool):
        """Updates the timezone fix flag based on the predefined city location setting.

        Args:
            need_fix_timezone (bool): Flag to fix timezone if using predefined city location.
        """
        # If using predefined city location, fix timezone. Otherwise not
        self._fixtimezone = need_fix_timezone

    def _find_sky_root(self) -> bool:
        """Find sky prim with materials, lights"""
        self.sky_type = SunstudySkyType.NONE
        self._current_sky_type_model.set_value(SunstudySkyType.NONE)
        env_prim = self._stage.GetPrimAtPath(ENVIRONMENT_PRIM_ROOT)
        if not env_prim:
            return False

        for prim in env_prim.GetAllChildren():
            path = prim.GetPath().pathString
            if path.startswith(SKY_PRIM_PATH):
                self._current_sky_model.set_value(path)
                if self._is_dynamic_sky(path):
                    carb.log_info(f"[SunstudyPlayer] Found {self.sky_type} sky: {path}")
                    return True
        if self.sky_type == SunstudySkyType.NONE:
            self._current_sky_model.set_value("")
        return False

    def _is_dynamic_sky(self, path: str) -> bool:
        # Sky material
        sky_material_path = path + "/Looks/SkyMaterial"
        sky_material = self._stage.GetPrimAtPath(sky_material_path)
        if sky_material:
            self._sky_material = (
                sky_material_path if self._is_mdl_material(sky_material_path) else (sky_material_path + "/Shader")
            )
        else:
            # carb.log_warn("Sky material not found!")
            self.sky_type = SunstudySkyType.STATIC
            self._current_sky_type_model.set_value(SunstudySkyType.STATIC)
            return False

        sun_light = self._stage.GetPrimAtPath(path + "/AxisNorth/AxisLatitude/AxisSHA/AxisDeclination/DistantLight")
        if sun_light:
            self._sky_root = path
            self.sky_type = SunstudySkyType.DYNAMIC
            self._current_sky_type_model.set_value(SunstudySkyType.DYNAMIC)
            return True
        else:
            carb.log_warn("Sun light not found!")
            self.sky_type = SunstudySkyType.STATIC
            self._current_sky_type_model.set_value(SunstudySkyType.STATIC)
            return False

    def _find_data_root(self) -> bool:
        """Find data (time and location) prim with play parameters"""
        if self._stage is not None:
            # OM-80044: Now only check prims under Environment root for better scene load time
            env_prim = self._stage.GetPrimAtPath(ENVIRONMENT_PRIM_ROOT)
            if env_prim:
                for prim in env_prim.GetAllChildren():
                    match = 0
                    for k in self._SKY_ATTRIBUTES:
                        if prim.HasAttribute(k):
                            match += 1
                    if match >= len(self._SKY_ATTRIBUTES) - 3:
                        self._data_root = str(prim.GetPath())
                        return True
        self._data_root = self._sky_root
        return False

    def _on_update(self, event: Event):
        delta = event["dt"] * self._play_rate_model.as_int
        current_time = self.current_time + delta

        stop = False
        if current_time > self.end_time:
            if self._play_loop_model.as_bool:
                current_time = self.start_time
            else:
                current_time = self.end_time
                stop = True

        if current_time < self.start_time:
            current_time = self.start_time

        self._current_time_model.set_value(current_time)
        self._update_sky_data()

        if stop:
            self.stop()

    # OM-21262  SunStudy should work with new mdl schema
    def _is_mdl_material(self, material_path: str):
        names = (
            "Latitude",
            "Longitude",
            "TimeOfDay",
            "DayOfYear",
            "NorthOrientation",
            "Declination",
            "SHA",
            "Azimuth",
            "Elevation",
        )
        if not material_path:
            return False
        prim = self._stage.GetPrimAtPath(material_path)
        for k in names:
            name = "inputs:" + k
            if not prim.HasAttribute(name):
                return False
        return True

    def _update_sky_data(self):
        if not (self._stage and self._sky_root):
            return

        prim = self._stage.GetPrimAtPath(self._sky_root)
        if prim.IsValid():
            sundata = self._get_sun_position(
                self._latitude_model.as_float,
                self._longitude_model.as_float,
                self._current_time_model.as_float,
                self._skydata["DayOfYear"],
                self._fixtimezone,
            )
            for k, v in sundata.items():
                self._skydata[k] = v
            self._write_sky_params()
            self._update_fog()

    def _write_sky_params(self):
        stage = self._stage
        sha = -self._skydata["SHA"] + 180
        lat = self._latitude_model.as_float
        dec = self._skydata["Declination"]
        nor = self._north_orientation_model.as_float

        self._set_rotation(stage.GetPrimAtPath(self._sky_root + "/AxisNorth/AxisLatitude"), Gf.Vec3d(0, 0, lat))
        self._set_rotation(stage.GetPrimAtPath(self._sky_root + "/AxisNorth/AxisLatitude/AxisSHA"), Gf.Vec3d(sha, 0, 0))
        self._set_rotation(
            stage.GetPrimAtPath(self._sky_root + "/AxisNorth/AxisLatitude/AxisSHA/AxisDeclination"), Gf.Vec3d(0, 0, dec)
        )
        prim_az = stage.GetPrimAtPath(self._sky_root + "/AxisNorth/AxisAzimuth")
        prim_el = stage.GetPrimAtPath(self._sky_root + "/AxisNorth/AxisAzimuth/AxisElevation")
        if prim_az.IsValid() and prim_el.IsValid():
            self._set_rotation(prim_az, Gf.Vec3d(0, self._skydata["Azimuth"], 0))
            self._set_rotation(prim_el, Gf.Vec3d(0, 0, self._skydata["Elevation"]))

        self._set_rotation(stage.GetPrimAtPath(self._sky_root + "/AxisNorth"), Gf.Vec3d(0, nor, 0))
        self._set_rotation(stage.GetPrimAtPath(self._sky_root + "/DomeLight"), Gf.Vec3d(270, 0, nor))

        self._set_mdl_param_list(self._sky_material, self._skydata)

    def _load_sky_data(self):
        prim = self._stage.GetPrimAtPath(self._data_root)
        if prim:
            for name in self._SKY_ATTRIBUTES:
                if prim.HasAttribute(name) is True:
                    attr = prim.GetAttribute(name)
                    value = attr.Get()
                    self._skydata[name] = attr.Get()
                    if self._SKY_ATTRIBUTES[name]:
                        self._SKY_ATTRIBUTES[name].set_default(value)
                    else:
                        if name == "Year" or name == "DayOfYear":
                            self._date_model.set_default(self.current_date)

        self._settings.set(PERSISTENT_SETTING_NORTHORIENTATION, self._north_orientation_model.as_float)

    def _load_sky_settings(self):
        # Set to default value
        self._skysettings = {
            "SunColorA": Gf.Vec3f(1.0, 0.98, 0.95),
            "SunColorB": Gf.Vec3f(0.5, 0.3, 0.1),
            "GlobalIntensity": 1.0,
            "AmbientColorA": Gf.Vec3f(0.5, 0.68, 1.0),
            "AmbientColorB": Gf.Vec3f(0.25, 0.2, 0.12),
            "AmbientColorC": Gf.Vec3f(0.075, 0.092, 0.111),
            "AmbientElevationA": 6.0,
            "AmbientElevationC": -2.0,
            "AmbientIntensity": 0.1,
            "DomeColorA": Gf.Vec3f(1.0, 1.0, 1.0),
            "DomeColorB": Gf.Vec3f(1.0, 1.0, 1.0),
            "DomeColorC": Gf.Vec3f(1.0, 1.0, 1.0),
            "DomeElevationA": 6.0,
            "DomeElevationC": -6.0,
            "DomeEnabled": True,
            "DomeIntensity": 1.0,
            "FogColorA": Gf.Vec3f(0.192, 0.28, 0.376),
            "FogColorB": Gf.Vec3f(0.772, 0.2, 0.007),
            "FogColorC": Gf.Vec3f(0.002, 0.002, 0.003),
            "FogColorIntensity": 10.0,
            "FogDensityA": 0.1,
            "FogDensityB": 0.03,
            "FogElevationA": 8.0,
            "FogElevationB": -3.0,
            "FogFactorDistance": 0.0,
            "FogFactorHeight": 0.16,
            "SunColorC": Gf.Vec3f(0.25, 0.013, 0.0),
            "SunColorElevationA": 20.0,
            "SunColorElevationB": -0.5,
            "SunIntensity": 5000.0,
        }

        prim = self._stage.GetPrimAtPath(self._sky_root)
        if prim and prim.IsValid():
            for p in prim.GetPropertiesInNamespace("settings:"):
                self._skysettings[p.GetBaseName()] = p.Get()

    def _set_mdl_param(self, mat, param: str, val: Any, create_value_type: Optional[Sdf.ValueTypeNames] = None):
        if not mat:
            return
        if not self._stage:
            return
        prim = self._stage.GetPrimAtPath(mat)
        if not prim:
            return
        name = "inputs:" + param
        if prim.HasAttribute(name):
            prim.GetAttribute(name).Set(val)
        elif create_value_type:
            prim.CreateAttribute(name, create_value_type).Set(val)

    def _get_mdl_param(self, mat, param):
        name = "inputs:" + param
        if not mat:
            return
        prim = self._stage.GetPrimAtPath(mat)
        if prim.HasAttribute(name):
            return prim.GetAttribute(name).Get()
        return 0

    def _set_mdl_param_list(self, mat, paramlist):
        if not mat:
            return
        prim = self._stage.GetPrimAtPath(mat)
        for k, v in self._skydata.items():
            name = "inputs:" + k
            if prim.HasAttribute(name):
                prim.GetAttribute(name).Set(v)

    def _init_fog(self, value=0):
        settings = carb.settings.get_settings()
        settings.set("/rtx/fog/enabled", True)
        settings.set("/rtx/fog/fogDistanceBased/enabled", True)
        settings.set("/rtx/fog/fogStartDist", 0)
        settings.set("/rtx/fog/fogEndDist", 800000)
        settings.set("/rtx/fog/fogStartHeight", 20000)
        settings.set("/rtx/fog/fogHeightFalloff", 1)
        settings.set("/rtx/fogZup/enabled", True)

    def _update_fog(self):
        skymat = self._sky_material
        elevation = self._skydata["Elevation"]
        # settings = carb.settings.get_settings()
        stage = self._stage

        global_intensity = self._skysettings["GlobalIntensity"]
        self._set_mdl_param(skymat, "GlobalIntensity", global_intensity)

        col_a = self._skysettings["SunColorA"]
        col_b = self._skysettings["SunColorB"]
        sun_fader = self._elevation_fader(
            self._skysettings["SunColorElevationA"], self._skysettings["SunColorElevationB"], elevation
        )
        if "SunColorC" in self._skysettings:
            col_c = self._skysettings["SunColorC"]
            sun_col = self._lerpcolor(
                self._lerpcolor(col_a, col_b, min(1.0, sun_fader * 2)), col_c, max(0.0, sun_fader * 2 - 1)
            )
        else:
            sun_col = self._lerpcolor(col_a, col_b, sun_fader)

        # OM-96740: Prevents _update_fog() from throwing an exception for a missing texture.
        try:
            distant_light = UsdLux.DistantLight.Get(
                stage, self._sky_root + "/AxisNorth/AxisLatitude/AxisSHA/AxisDeclination/DistantLight"
            )
        except TypeError:
            distant_light = None

        if distant_light and distant_light.GetPath() and stage.GetPrimAtPath(distant_light.GetPath()).IsValid():

            angle = distant_light.GetAngleAttr().Get()
            if angle is None:
                angle = 0.0
            hs = elevation > -0.5 * angle
            hf = hs * self._elevation_fader(-0.5 * angle, angle, elevation)
            distant_light.GetColorAttr().Set(sun_col)
            distant_light.GetIntensityAttr().Set(global_intensity * self._skysettings["SunIntensity"] * hf)

            # self._set_mdl_param(skymat, "SunSize", angle)
            self._set_mdl_param(skymat, "SunColor", sun_col)
            self._set_mdl_param(skymat, "SunIntensity", self._skysettings["SunIntensity"] * hs)

    def _lerpcolor(self, a, b, x):
        return (a[0] * (1 - x) + b[0] * x, a[1] * (1 - x) + b[1] * x, a[2] * (1 - x) + b[2] * x)

    def _elevation_fader(self, start, end, elevation):
        if end - start == 0:
            return 0
        return max(0, min(1, (elevation - start) / (end - start)))

    def _get_rotation(self, prim):
        properties = prim.GetPropertyNames()
        if "xformOp:rotateXYZ" in properties:
            return prim.GetAttribute("xformOp:rotateXYZ").Get()
        elif "xformOp:rotateZYX" in properties:
            return prim.GetAttribute("xformOp:rotateZYX").Get()
        else:
            self._set_rotation(prim, Gf.Vec3d(0, 0, 0))
            return prim.GetAttribute("xformOp:rotateXYZ").Get()

    def _set_rotation(self, prim, rot):
        properties = prim.GetPropertyNames()
        if "xformOp:rotateXYZ" in properties:
            rotation = prim.GetAttribute("xformOp:rotateXYZ")
            rotation.Set(rot)
        elif "xformOp:rotateZYX" in properties:
            rotation = prim.GetAttribute("xformOp:rotateZYX")
            rotation.Set(rot)
        elif "xformOp:transform" in properties:
            carb.log_info("Object missing rotation op. Adding it.")
            xform = UsdGeom.Xformable(prim)
            xform_op = xform.AddXformOp(UsdGeom.XformOp.TypeRotateXYZ, UsdGeom.XformOp.PrecisionDouble, "")
            rotate = Gf.Vec3d(rot[0], rot[1], rot[2])
            xform_op.Set(rotate)

    def _get_scale(self, prim):
        properties = prim.GetPropertyNames()
        if "xformOp:scale" not in properties:
            self._set_scale(prim, Gf.Vec3d(1, 1, 1))
        return prim.GetAttribute("xformOp:scale").Get()

    def _set_scale(self, prim, new_scale):
        properties = prim.GetPropertyNames()
        if "xformOp:scale" not in properties:
            carb.log_info("Object missing scale op. Adding it.")
            xform = UsdGeom.Xformable(prim)
            xform.AddXformOp(UsdGeom.XformOp.TypeScale, UsdGeom.XformOp.PrecisionDouble, "")
        scale = prim.GetAttribute("xformOp:scale")
        scale.Set(new_scale)

    def _get_sun_position(self, latitude, longitude, ToD, DoY, fixtimezone=False):
        if abs(latitude) == 90:
            latitude *= 0.999999

        time_of_day = ToD
        day_of_year = math.floor(DoY)

        declination_lock = False
        # Spencer formula
        T = math.radians((360 / 365.25) * (day_of_year + declination_lock * time_of_day / 24))
        D = (
            0.006918
            - 0.399912 * math.cos(T)
            + 0.070257 * math.sin(T)
            - 0.006758 * math.cos(2 * T)
            + 0.000907 * math.sin(2 * T)
            - 0.002697 * math.cos(3 * T)
            + 0.001480 * math.sin(3 * T)
        )
        E = (
            0.0000075
            + 0.001868 * math.cos(T)
            - 0.032077 * math.sin(T)
            - 0.014615 * math.cos(2 * T)
            - 0.040849 * math.sin(2 * T)
        )
        # Basic formula
        # D = math.radians(-23.45*math.cos(T+math.radians(10)))
        # E = 0

        SHA = (time_of_day - 12) * 360 / 24 + longitude + math.degrees(E)

        # Temp fix for timezone offset = ignoring the longitude
        if fixtimezone:
            SHA -= longitude

        SV = Gf.Vec3d(0, -1, 0)
        rotDEC = Gf.Rotation(Gf.Vec3d(0, 0, 1), math.degrees(D))
        rotSHA = Gf.Rotation(Gf.Vec3d(1, 0, 0), 180 - SHA)
        rotLAT = Gf.Rotation(Gf.Vec3d(0, 0, 1), latitude)
        SV = rotDEC.TransformDir(SV)
        SV = rotSHA.TransformDir(SV)
        SV = rotLAT.TransformDir(SV)

        SEA = math.degrees(math.asin(SV[1]))
        AZ = math.degrees(-math.atan2(SV[2], SV[0]))

        sundata = {"Declination": math.degrees(D), "SHA": SHA, "Azimuth": AZ, "Elevation": SEA}
        return sundata

    def _clean(self):
        self.sky_type = SunstudySkyType.NONE
        self._current_sky_type_model.set_value(SunstudySkyType.NONE)
        self._sky_material = ""
        self._skysettings = {}
        self._sky_root = None
        self._data_root = ""

        now = datetime.now()

        self._latitude_model.set_default(51.426)
        self._longitude_model.set_default(-0.985)
        self._north_orientation_model.set_default(0.0)
        self._start_time_model.set_default(6)
        self._end_time_model.set_default(18)
        self._current_time_model.set_default((now.hour * 3600 + now.minute * 60 + now.second) / 3600.0)

        self._skydata = {
            "Year": now.year,
            "Latitude": self._latitude_model.as_float,
            "Longitude": self._longitude_model.as_float,
            "TimeOfDay": self._current_time_model.as_float,
            "DayOfYear": now.date().timetuple().tm_yday,
            "NorthOrientation": self._north_orientation_model.as_float,
            "Declination": 0,
            "SHA": 0,
            "Azimuth": 0,
            "Elevation": 0,
            "StartTOD": self._start_time_model.as_float,
            "EndTOD": self._end_time_model.as_float,
        }

        self._date_model.set_default(self.current_date)

    def _reload_sky(self) -> bool:
        self._clean()

        self._stage = self._usd_context.get_stage()
        self._sky_root = None
        if not self._stage:
            return False

        if not self._find_sky_root():
            return False
        self._find_data_root()
        self._load_sky_data()
        self._load_sky_settings()

        return True

    def _on_sky_changed(self, stage: Usd.Stage, path: str) -> None:
        if stage.GetPrimAtPath(path):
            # Sky created
            self._reload_sky()
        else:
            # Sky Removed
            if path == self._sky_root:
                self.stop()
                self._clean()

    def _on_stage_closing(self, _):
        # OM-84062: Listen to USD close, stop playing when USD is closing
        if self._playing_model.get_value_as_bool():
            self.stop()

    def _on_stage_opened(self, _):
        self._reload_sky()

        # OM-53986: If open a large scene, env params are set before sky loaded
        # Need to refresh sky data to make sure env params are correctly configured
        self._update_sky_data()

        # OM-79609: Do not make stage dirty
        omni.usd.get_context().set_pending_edit(False)

    def _on_stage_assets_loaded(self, _):
        if self._settings.get("/exts/omni.kit.environment.core/extraMdlParam"):
            self._extra_mdl_param()

    def _on_stage_closed(self, _):
        self._stage = None

    def _on_latitude_changed(self, model: PropertyValueModel) -> None:
        self._skydata["Latitude"] = model.as_float
        if self._update_sub is None:
            self._update_sky_data()

    def _on_longitude_changed(self, model: PropertyValueModel) -> None:
        self._skydata["Longitude"] = model.as_float
        if self._update_sub is None:
            self._update_sky_data()

    def _on_north_orientation_changed(self, model: PropertyValueModel) -> None:
        self._skydata["NorthOrientation"] = model.as_float
        self._settings.set(PERSISTENT_SETTING_NORTHORIENTATION, model.as_float)
        if self._update_sub is None:
            self._update_sky_data()

    def _on_current_time_changed(self, model: PropertyValueModel) -> None:
        self._skydata["TimeOfDay"] = model.as_float
        if self._update_sub is None:
            self._update_sky_data()

    def _on_start_time_changed(self, model: PropertyValueModel) -> None:
        self._skydata["StartTOD"] = model.as_float

    def _on_end_time_changed(self, model: PropertyValueModel) -> None:
        self._skydata["EndTOD"] = model.as_float

    def _on_date_changed(self, model: PropertyValueModel) -> None:
        year, month, day = model.as_string.split("-")
        current_date = date(int(year), int(month), int(day))
        self._skydata["Year"] = int(year)
        self._skydata["DayOfYear"] = current_date.timetuple().tm_yday

    def _extra_mdl_param(self):
        if self.sky_type == SunstudySkyType.DYNAMIC:
            # poke one of sky mat parameters
            self._set_mdl_param(self._sky_material, "GlobalIntensity", 1.001)
            self._set_mdl_param(self._sky_material, "GlobalIntensity", 1)

    def _on_cumulus_enabled_changed(self, model: PropertyValueModel) -> None:
        self._set_mdl_param(
            self._sky_material, "CumulusEnabled", model.as_float, create_value_type=Sdf.ValueTypeNames.Bool
        )

    def _on_cloud_coverage_changed(self, model: PropertyValueModel) -> None:
        self._set_mdl_param(
            self._sky_material, "CloudCoverage", model.as_float, create_value_type=Sdf.ValueTypeNames.Float
        )

    def _on_haze_changed(self, model: PropertyValueModel) -> None:
        self._set_mdl_param(self._sky_material, "haze", model.as_float, create_value_type=Sdf.ValueTypeNames.Float)
