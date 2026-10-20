import copy
import weakref
from typing import Dict, List, Tuple

from pxr import Sdf

from ..bindings._animcurve import *
from . import utils


class KeySelectionState:
    class SelectFlag:
        def __init__(self, key: bool, in_tangent: bool, out_tangent: bool):
            self.key = key
            self.in_tangent = in_tangent
            self.out_tangent = out_tangent

    _instances = []
    _curve_event_sub = None
    global_instance = None
    ignore_curve_event = False

    def __init__(self, curve_path: str = None, keys: Dict[int, SelectFlag] = None):
        self._instances.append(weakref.proxy(self))
        self.curves = {}
        if curve_path and keys:
            self.curves = {curve_path: keys}

    def __del__(self):
        self._instances.remove(self)

    def on_keys_changed(curve_path: str, moved: List[Tuple[int, int]], removed: List[int]):
        for self in __class__._instances:
            keys = self.curves.get(curve_path)
            if keys is None:
                continue

            for time in removed:
                keys.pop(time, None)

            if not keys:
                del self.curves[curve_path]
                continue

            moved_keys = {}
            for old, new in moved:
                key = keys.get(old)
                if key is None:
                    continue

                moved_keys[new] = key
                del keys[old]

            for time, key in moved_keys.items():
                keys[time] = key

    def replace(self, selection_state: "__class__"):
        self.curves = copy.deepcopy(selection_state.curves)

    def add(self, selection_state: "__class__"):
        for curve_path, keys in selection_state.curves.items():
            if curve_path in self.curves:
                this_keys = self.curves[curve_path]
                for time, flag in keys.items():
                    if time in this_keys:
                        this_flag = this_keys[time]

                        this_flag.key = this_flag.key or flag.key
                        this_flag.in_tangent = this_flag.in_tangent or flag.in_tangent
                        this_flag.out_tangent = this_flag.out_tangent or flag.out_tangent
                    else:
                        this_keys[time] = flag
            else:
                self.curves[curve_path] = keys

    def remove(self, selection_state: "__class__"):
        invalid_curves = []

        for curve_path, keys in selection_state.curves.items():
            this_keys = self.curves.get(curve_path)
            if this_keys is None:
                continue

            invalid_times = []

            for time, flag in this_keys.items():
                that_flag = keys.get(time)
                if that_flag is None:
                    continue

                if that_flag.key:
                    flag.key = False
                if that_flag.in_tangent:
                    flag.in_tangent = False
                if that_flag.out_tangent:
                    flag.out_tangent = False

                if not (flag.key or flag.in_tangent or flag.out_tangent):
                    invalid_times.append(time)

            for time in invalid_times:
                del this_keys[time]

            if not this_keys:
                invalid_curves.append(curve_path)

        for curve in invalid_curves:
            del self.curves[curve]

    def _on_curve_event(event):
        if __class__.ignore_curve_event:
            return

        if event.type not in [CurveEventType.Added, CurveEventType.Removed, CurveEventType.Updated]:
            return

        paths = event.payload["paths"]
        update_infos = event.payload["updateInfos"]
        for self in __class__._instances:
            for curve_path in list(self.curves.keys()):
                for i in range(0, len(paths)):
                    path = paths[i]

                    if not Sdf.Path(curve_path).HasPrefix(path):
                        continue

                    if update_infos is not None:
                        update_info = update_infos[i]
                        if len(update_info) > 0:
                            break

                    del self.curves[curve_path]
                    break

    def _startup():
        event_stream = utils.curve_plugin.get_event_stream()
        __class__._curve_event_sub = event_stream.create_subscription_to_pop(__class__._on_curve_event)

        __class__.global_instance = KeySelectionState()

    def _shutdown():
        __class__.global_instance = None
        __class__._curve_event_sub = None
