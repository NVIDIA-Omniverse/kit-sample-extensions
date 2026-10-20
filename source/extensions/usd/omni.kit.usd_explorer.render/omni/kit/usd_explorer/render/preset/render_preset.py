import asyncio
import copy
import functools
import math
import queue

import carb
import omni.usd
from omni.kit.viewport.utility import get_active_viewport

g_singleton = None
SETTING_RESOLUTION_WIDTH = "/app/renderer/resolution/width"
SETTING_RESOLUTION_HEIGHT = "/app/renderer/resolution/height"

SETTING_SKIP_MOST_LIGHTS = "/rtx/scenedb/skipMostLights"


def singleton(cls):
    _instance = {}

    def inner(*args, **kargs):
        if cls not in _instance:
            _instance[cls] = cls(*args, **kargs)
        return _instance[cls]

    return inner()


class RenderSetItemData:
    def __init__(self, path, value):
        self.path = path
        self.value = value

    def set(self):
        setting = carb.settings.get_settings()
        setting.set(self.path, self.value)


# this work queue is used to avoid the hang by render mode switch
# there should only one switch task works in one time
class QueueManager:

    def __init__(self):
        self._stop_event = asyncio.Event()
        self._work_queue = asyncio.LifoQueue()
        self._is_working = False
        asyncio.ensure_future(self._run())

    def destroy(self):
        self._stop_event.set()
        self._work_queue.put_nowait(None)

    def put(self, obj):
        self._work_queue.put_nowait(obj)

    async def _run(self):
        while not self._stop_event.is_set():
            obj = await self._work_queue.get()
            if obj is not None:
                self._work_queue._init(20)
                await obj()


class RenderPreset(object):
    _instance = None

    def __init__(self):
        self._settings = carb.settings.get_settings()
        self._queue_manager = QueueManager()
        self._render_types = ["Draft", "Preview", "Photo", "Custom"]
        """
        When we go to "DRAFT MODE" we should set the following render settings by default:
        Render mode: RT
        Viewport Resolution 720p
        "/app/renderer/resolution/multiplier", 1
        "/app/renderer/resolution/width", 1920
        "/app/renderer/resolution/height", 1080
        "/app/renderer/gpuSynchronization": False
        Direct Lighting:
        "/rtx/shadows/denoiser/quarterRes": true
        Indirect Diffuse Light:
        "/rtx/sceneDb/ambientLightColor": 1.0, 1.0, 1.0
        "/rtx/sceneDb/ambientLightIntensity": 0.5
        "/rtx/ambientOcclusion/rayLength": 500
        Reflections:
        "/rtx/reflections/halfRes": TRUE
        Translucency:
        "/rtx/reflections/maxReflectionBounces": 5
        "/rtx/translucency/reflectionCutoff": 0.2


        Current Photo settings:
        rtx/pathtracing/MaxBounces = 12
        rtx/pathtracing/maxSpecularAndTransmissionBounces = 6
        rtx/pathtracing/totalSpp = 600
        Viewport Scaling 100%

        Preview mode is PT, but low settings on PT to be as fast as humanly possible.
        rtx/pathtracing/MaxBounces = 4
        rtx/pathtracing/maxSpecularAndTransmissionBounces = 6
        rtx/pathtracing/totalSpp = 50
        Viewport Scaling 66%
        """
        self._render_paths = [
            "/rtx/pathtracing/maxBounces",  # 0
            "/rtx/pathtracing/maxSpecularAndTransmissionBounces",  # 1
            "/rtx/pathtracing/totalSpp",  # 2
            "/rtx/rendermode",  # 3
            # "/rtx/ecoMode/enabled",
            # "/app/renderer/resolution/multiplier",  # 4
            # "/app/renderer/resolution/width",  # 5
            # "/app/renderer/resolution/height",  # 6
            # "/app/renderer/gpuSynchronization",  # 7
            # "/rtx/shadows/denoiser/quarterRes",  # 8
            # "/rtx/sceneDb/ambientLightColor",  # 9
            # "/rtx/sceneDb/ambientLightIntensity",  # 10
            # "/rtx/ambientOcclusion/rayLength",  # 11
            # "/rtx/reflections/halfRes",  # 12
            # "/rtx/reflections/maxReflectionBounces",  # 13
            # "/rtx/translucency/reflectionCutoff",  # 14
            # "/rtx/pathtracing/mgpu/enabled",  # 15
            # "/renderer/eco_mode_enable",  # 16
            # "/rtx/post/tonemap/op",  # 17
            # "/rtx/post/colorcorr/enabled",  # 18
            # "/rtx/post/colorcorr/outputMode",  # 19
            # "/rtx/post/colorgrad/enabled",  # 20
            #  "/rtx/post/colorgrad/outputMode",  # 21
            # "/rtx/reflections/enabled",  # 22
            # "/rtx/shadows/enabled",  # 23
            # "/rtx/translucency/enabled",  # 24
            # "/rtx/ambientOcclusion/enabled",  # 25
            # "/rtx/ambientOcclusion/temporalSqrtLength",  # 26
            # "/rtx/indirectDiffuse/enabled",  # 27
            # "/rtx/post/lensFlares/enabled",  # 28
            # "/rtx/post/lensFlares/flareScale",  # 29
            # "/rtx/post/chromaticAberration/enabled",  # 30
            # "/rtx/post/chromaticAberration/strengthR",  # 31
            # "/rtx/post/chromaticAberration/strengthG",  # 32
            # "/rtx/post/chromaticAberration/strengthB",  # 33
            # "/rtx/post/histogram/enabled",  # 34
            # "/rtx/domeLight/baking/resolution",  # 35
            # "/rtx/post/dof/enabled",  # 36
            # "/rtx/post/dof/overrideEnabled",  # 37
            # "/rtx/post/dof/viewUIEnabled",  # 38
            # "/rtx/post/aa/op",  # 39
            # "/rtx/directLighting/sampledLighting/enabled",  # 40
            # "/rtx/directLighting/sampledLighting/samplesPerPixel",  # 41
            # "/rtx/reflections/sampledLighting/enabled",  # 42
            # "/rtx/indirectDiffuse/enabled",  # 43
            # "/rtx/raytracing/cached/enabled",  # 44
            # "/rtx/reflections/halfRes",  # 45
        ]

        # OM-14757 need to also check on override camera DOF when we turn dof off
        # self._settings.set("/rtx/post/dof/viewUIEnabled", False)
        # Close "autoExposure" by default
        # self._settings.set("/rtx/post/histogram/enabled", False)

        # Setup "Custom"
        self._render_custom_group = {}
        # print("Render settings original value:")
        for path in self._render_paths:
            self._render_custom_group[path] = self._settings.get(path)
            # print(f"{path} = {self._render_custom_group[path]}")

        # Setup "Draft"
        self._render_draft_group = self._render_custom_group.copy()
        self._render_draft_group["/rtx/rendermode"] = "RaytracedLighting"

        # Setup "Preview"
        self._render_preview_group = self._render_custom_group.copy()
        self._render_preview_group["/rtx/pathtracing/maxBounces"] = 4
        self._render_preview_group["/rtx/pathtracing/maxSpecularAndTransmissionBounces"] = 6
        self._render_preview_group["/rtx/pathtracing/totalSpp"] = 100
        self._render_preview_group["/rtx/rendermode"] = "PathTracing"

        # Setup "Photo"
        self._render_photo_group = self._render_custom_group.copy()
        self._render_photo_group["/rtx/pathtracing/maxBounces"] = 12
        self._render_photo_group["/rtx/pathtracing/maxSpecularAndTransmissionBounces"] = 6
        self._render_photo_group["/rtx/pathtracing/totalSpp"] = 600
        self._render_photo_group["/rtx/rendermode"] = "PathTracing"

        self._groups = [
            self._render_draft_group,
            self._render_preview_group,
            self._render_photo_group,
            self._render_custom_group,
        ]

        self._original_groups = dict(zip(self._render_types, self._groups))

        # print("Each group original value:")
        # for render_type in self._render_types:
        #     group = self._original_groups[render_type]
        #         print(f"Render type: {render_type}")
        #         for path in group.keys():
        #             print(f"{path} = {group[path]}")

        self._preset_groups = copy.deepcopy(self._original_groups)
        self._setting_panel = None
        self._light_executor = None
        self._current_type = "Draft"
        # OM-14698 the value should set in config file, set value here wouldn't work after load another usd
        # OM-13060 Set common to all renderer settings
        # self._settings.set("/app/renderer/skipWhileMinimized", True)
        # self._settings.set("/rtx/raytracing/shadowBias", 0.1)
        global g_singleton
        g_singleton = RenderPreset._instance

    def destroy(self):
        self._queue_manager.destroy()

    # singleton model, to ensure set once , use in everywhere
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def update_menu_bar(self, menu_bar):
        self.set(self._current_type)

    def update_setting_panel(self, setting_panel):
        self._setting_panel = setting_panel
        self.set(self._current_type)

    def get_value(self, render_type, path):
        if render_type not in self._preset_groups:
            return None
        return self._preset_groups[render_type][path]

    def update_value(self, render_type, path, value):
        if render_type not in self._preset_groups:
            self.add_new_preset(render_type)
        self._preset_groups[render_type][path] = value

    def update_current_value(self, path, value):
        self.update_value(self._current_type, path, value)

    def update_draft_value(self, path, value):
        self.update_value("Draft", path, value)

    def update_preview_value(self, path, value):
        self.update_value("Preview", path, value)

    def update_photo_value(self, path, value):
        self.update_value("Photo", path, value)

    def update_custom_value(self, path, value):
        self.update_value("Custom", path, value)

    def add_new_preset(self, render_type):
        if render_type not in self._preset_groups:
            self._preset_groups[render_type] = {}

    def disable_lights(self):
        self._settings.set(SETTING_SKIP_MOST_LIGHTS, True)

    def restore_lights(self):
        self._settings.set(SETTING_SKIP_MOST_LIGHTS, False)

    def get_lights_status(self):
        return not self._settings.get(SETTING_SKIP_MOST_LIGHTS)

    # This interface should only called by menu bar and preset itself
    def set_value(self, render_type, is_reset=False, wait_frame=4):
        self._queue_manager.put(functools.partial(self.async_set_value, render_type, is_reset, wait_frame))

    async def async_set_value(self, render_type, is_reset=False, wait_frame=4):
        if render_type not in self._preset_groups:
            return

        if (not is_reset) and self._current_type == render_type:
            return

        viewport_api = get_active_viewport(omni.usd.get_context())

        self._current_type = render_type
        if self._settings.get("/rtx/renderpreset") != render_type:
            self._settings.set("/rtx/renderpreset", self._current_type)
        for path, value in self._preset_groups[render_type].items():
            self._settings.set(path, value)
            if path == "/rtx/rendermode":
                if value == "iray":
                    if viewport_api:
                        viewport_api.set_hd_engine("iray", "iray")
                    self._settings.set("/rtx/rendermode", "iray")
                    self._settings.set("/iray/rendermode", "iray")
                else:
                    self._settings.set("/rtx/rendermode", value)
                    if viewport_api:
                        viewport_api.set_hd_engine("rtx")

        # update render setting panel ui
        if self._setting_panel:
            self._setting_panel.rebuild()

        for i in range(wait_frame):
            await omni.kit.app.get_app().next_update_async()

    # This interface provide for other plugin expect menu bar
    def set(self, render_type):
        if render_type not in self._preset_groups:
            return
        self.set_value(render_type)

    def get_current_render(self):
        return self._current_type

    def reset(self):
        for render_type in self._render_types[0:3]:
            self._preset_groups[render_type] = copy.deepcopy(self._original_groups[render_type])
        self.set_value(self._current_type, True)


def get_instance():
    if g_singleton is None:
        RenderPreset()
    return g_singleton
