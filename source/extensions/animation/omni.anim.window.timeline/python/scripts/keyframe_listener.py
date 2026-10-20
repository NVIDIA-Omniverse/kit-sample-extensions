import functools
import weakref

import carb.settings
import omni.anim.curve.core
import omni.timeline
import omni.usd
from pxr import Sdf


# listen the prims keyframe events and update to timeline
class KeyFrameListener:
    _keyframelistener_instance = None

    def __init__(self):
        self._listen_prim_paths = []

        self._on_curve_evt_fn = []
        self._prim_proxys = []

        self._usd_context = omni.usd.get_context()
        self._settings = carb.settings.get_settings()
        self._timeline = omni.timeline.get_timeline_interface()

        self._animcurve = omni.anim.curve.core.acquire_interface()
        self._curve_event_sub = self._animcurve.get_event_stream().create_subscription_to_pop(
            functools.partial(__class__._on_curve_event, weakref.proxy(self))
        )

        KeyFrameListener._keyframelistener_instance = self

    def __del__(self):
        self._listen_prim_paths.clear()
        self._curve_event_sub = None
        self._on_curve_evt_fn.clear()
        self._prim_proxys.clear()
        self._animcurve = None
        self._timeline = None

    @staticmethod
    def get_instance():
        if KeyFrameListener._keyframelistener_instance is None:
            KeyFrameListener._keyframelistener_instance = KeyFrameListener()
        return KeyFrameListener._keyframelistener_instance

    @staticmethod
    def destroy():
        KeyFrameListener._keyframelistener_instance = None

    def add_prim_proxy_fn(self, prim_fn):
        self._prim_proxys.append(prim_fn)

    def add_curve_update_fn(self, on_evt_fn):
        self._on_curve_evt_fn.append(on_evt_fn)

    def _on_curve_event(self, event):
        paths = event.payload["paths"]
        sdf_paths = [Sdf.Path(path) for path in paths]
        prim_paths = [str(sdf_path.GetPrimPath()) for sdf_path in sdf_paths if sdf_path.GetPrimPath() is not None]

        for prim_path in prim_paths:
            if prim_path in self._listen_prim_paths:
                for curv_evt_fn in self._on_curve_evt_fn:
                    curv_evt_fn(prim_path)

    def get_keyframes(self, prim_paths: list, start_second: float, end_second: float):
        filter_keyframes = set()
        self._listen_prim_paths.clear()

        if start_second >= end_second:
            return filter_keyframes

        if len(prim_paths) == 0:
            return filter_keyframes

        tps = self._animcurve.get_ticks_per_second()
        start_ticks = start_second * tps
        end_ticks = end_second * tps

        new_paths = prim_paths
        for prim_proxy in self._prim_proxys:
            new_paths = prim_proxy(new_paths)

        for prim_path in new_paths:
            curves = self._animcurve.get_curves(prim_path)
            for curve in curves.values():
                for key in curve.keys:
                    if key.time >= start_ticks and key.time <= end_ticks:
                        filter_keyframes.add(key.time)

        self._listen_prim_paths = new_paths
        return sorted(filter_keyframes)

    def get_listen_prims(self):
        return self._listen_prim_paths

    def is_listen_path(self, path):
        prim_path = path.GetPrimPath() if path.IsPropertyPath() else path

        for listen_path in self._listen_prim_paths:
            if Sdf.Path(listen_path).HasPrefix(prim_path):
                return True

        return False
