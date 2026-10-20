import functools
import weakref

import AnimationSchemaTools
import carb
import omni.anim.curve.core
import omni.kit.app
from omni.kit.widget.timeline import EditScope, WeakMethod
from pxr import Sdf, Tf, Usd, UsdUtils

from . import curve_editor_globals
from .curve_editor_globals import *
from .curve_editor_globals import _both_have_sample

# TODO - Better singleton class out there -- We have a Singleton class but it's not widely used
g_singleton = None


class _CurveTangent:
    def __init__(self):
        self._in_time_tick = 0
        self._out_time_tick = 0
        self._in_value = 0.0
        self._out_value = 0.0
        self._time_tick = 0
        self._selected = False

    def set_selected(self, selected: bool):
        self._selected = selected

    def set_time_tick(self, time_tick: int):
        self._time_tick = time_tick

    def set_in_time_tick(self, time_tick: int):
        self._in_time_tick = time_tick

    def set_in_value(self, value):
        self._in_value = value

    def set_out_time_tick(self, time_tick: int):
        self._out_time_tick = time_tick

    def set_out_value(self, value):
        self._out_value = value

    def set_from_tuber(self, key_tuber):
        self.set_time_tick(key_tuber.get_time_tick())
        self.set_in_time_tick(key_tuber.get_in_tangent_time_tick())
        self.set_in_value(key_tuber.get_in_tangent_value())
        self.set_out_time_tick(key_tuber.get_out_tangent_time_tick())
        self.set_out_value(key_tuber.get_out_tangent_value())

    def write_to_tuber(self, key_tuber):
        key_tuber.set_time_tick(self.get_time_tick())
        key_tuber.set_in_tangent_time_tick(self.get_in_time_tick())
        key_tuber.set_in_tangent_value(self.get_in_value())
        key_tuber.set_out_tangent_time_tick(self.get_out_time_tick())
        key_tuber.set_out_tangent_value(self.get_out_value())

    def get_selected(self):
        return self._selected

    def get_in_time_tick(self) -> int:
        return self._in_time_tick

    def get_in_time_code(self, time_codes_per_second) -> float:
        return time_tick_to_time_code(self.get_in_time_tick(), time_codes_per_second)

    def get_in_value(self):
        return self._in_value

    def get_out_time_tick(self) -> int:
        return self._out_time_tick

    def get_out_time_code(self, time_codes_per_second) -> float:
        return time_tick_to_time_code(self.get_out_time_tick(), time_codes_per_second)

    def get_out_value(self):
        return self._out_value

    def get_time_code(self, time_codes_per_second) -> float:
        return time_tick_to_time_code(self.get_time_tick(), time_codes_per_second)

    def get_time_tick(self) -> int:
        return self._time_tick


class CurveEditorEventListener:
    def __init__(self, editor):
        self._owner_editor_wp = weakref.ref(editor)
        self._edit_scope = EditScope()
        self._curve_event_sub = curve_editor_globals.curve_plugin.get_event_stream().create_subscription_to_pop(
            functools.partial(__class__._on_curve_event, weakref.proxy(self))
        )
        self._stage_event_sub = (
            omni.usd.get_context()
            .get_stage_event_stream()
            .create_subscription_to_pop(functools.partial(__class__._on_stage_event, weakref.proxy(self)))
        )
        self._timeline_event_sub = (
            omni.timeline.get_timeline_interface()
            .get_timeline_event_stream()
            .create_subscription_to_pop(functools.partial(__class__._on_timeline_event, weakref.proxy(self)))
        )

    def _get_tracks_cache(self):
        return self._owner_editor_wp()._get_tracks_cache()

    def _get_retained_tracks_cache(self):
        return self._owner_editor_wp()._get_retained_tracks_cache()

    # only for auto fit when new track is added
    def _ui_raise_refit_and_update_flag(self):
        return self._owner_editor_wp()._ui_raise_refit_and_update_flag()

    # ui immediate removal of a track
    def _ui_remove_track(self, track):
        self._owner_editor_wp()._ui_remove_track(track)

    # _immediate_add_track, _immediate_update_track, _immediate_remove_track ensure that every entry in retained cache has
    # an corresponding entry in the main cache.

    # add in main cache and retained cache
    def _immediate_add_track(self, user_prim: str, attr_name: str, component_name: str):
        # if the user_prim is in the editing set, add the track in the retained cache
        if self._get_tracks_cache().has_user(user_prim):
            self._get_tracks_cache().add_track(user_prim, attr_name, component_name)
            self._get_retained_tracks_cache().add_track(user_prim, attr_name, component_name)
            # auto fit, when for example, the first key is added to an attribute.
            self._ui_raise_refit_and_update_flag()

    # keep the main cache, add in retained cache
    def _immediate_update_track(self, user_prim: str, attr_name: str, component_name: str):
        if self._get_tracks_cache().get_track(user_prim, attr_name, component_name):
            # add the track in the retained cache, but do NOT remove it from the main editing cache.
            # the selection status is perserved only in the main editing cache, after update
            self._get_retained_tracks_cache().add_track(user_prim, attr_name, component_name)
            # ui should remove the track until the next retained update
            self._ui_remove_track(CurveEditorTrack(user_prim, attr_name, component_name))

    # remove from main editing cache and retained cache
    def _immediate_remove_track(self, user_prim: str, attr_name: str, component_name: str):
        if self._get_tracks_cache().remove_track(user_prim, attr_name, component_name):
            self._get_retained_tracks_cache().remove_track(user_prim, attr_name, component_name)
            self._ui_remove_track(CurveEditorTrack(user_prim, attr_name, component_name))

    # remove all tracks of a prim from editing cache
    def _immediate_remove_user(self, user_prim_str: str):
        user_tracks = self._get_tracks_cache().get_user_tracks(user_prim_str)
        for track in user_tracks:
            self._immediate_remove_track(track.get_prim_path_str(), track.get_attr_name(), track.get_component_name())

    # add all tracks of a prim in editing cache
    def _immediate_add_user(self, user_prim_str: str):
        if len(self._get_tracks_cache().get_user_tracks(user_prim_str)):
            carb.log_warn(
                f"Unexpected code path in CurveEditorEventListener._immediate_add_user(), {user_prim_str} should not have historically cached animation."
            )
            # force clear. But a root cause should be found if this code path is met.
            self._immediate_remove_user(user_prim_str)

        for attr_name, component_name in get_track_attr_and_component_names_from_runtime(user_prim_str):
            self._immediate_add_track(user_prim_str, attr_name, component_name)

    # update all tracks of a prim in editing cache
    def _immediate_update_user(self, user_prim_str: str):
        user_tracks = self._get_tracks_cache().get_user_tracks(user_prim_str)
        for track in user_tracks:
            self._immediate_update_track(track.get_prim_path_str(), track.get_attr_name(), track.get_component_name())

    def _raise_stage_selection_changed_flag(self):
        self._owner_editor_wp()._raise_stage_selection_changed_flag()

    def _on_timeline_event(self, event):
        if event.type == int(omni.timeline.TimelineEventType.TIME_CODE_PER_SECOND_CHANGED):
            # update all animation components for all current users.
            for user in self._get_tracks_cache().get_users():
                self._immediate_update_user(user)

    def _on_stage_event(self, event):
        if event.type == int(omni.usd.StageEventType.SELECTION_CHANGED):
            self._raise_stage_selection_changed_flag()
        elif event.type == int(omni.usd.StageEventType.OPENED):
            # nop
            pass
        elif event.type == int(omni.usd.StageEventType.CLOSING):
            # on stage closing, the curve event system does not issue all prims remove event, so I have to manully do the removal.
            for user in self._get_tracks_cache().get_users():
                self._immediate_remove_user(user)

    def _on_curve_event(self, event):
        if event.type == omni.anim.curve.core.CurveEventType.KeySelectionChanged:
            # if edit scope is not occupied by internal operation.
            if self._edit_scope:
                # fine grained update is better if fine grained selection event is ready in the future
                # but now, update all animation components for all current users.
                for user in self._get_tracks_cache().get_users():
                    self._immediate_update_user(user)
            return

        paths_str = event.payload["paths"]
        for path_str in paths_str:
            component_char, attr_name, prim_path_str = get_component_and_attribute_name_and_prim(path_str)
            if attr_name == "":
                # the path is a prim path
                if event.type == omni.anim.curve.core.CurveEventType.Removed:
                    self._immediate_remove_user(prim_path_str)
                elif event.type == omni.anim.curve.core.CurveEventType.Added:
                    if len(self._get_tracks_cache().get_user_tracks(prim_path_str)):
                        carb.log_warn(
                            f"prim omni.anim.curve.core.CurveEventType.Added issued, but the prim {prim_path_str} previously has cached animation"
                        )
                    # this event means the prim has previously no animation, now it has 1 or multiple animation components
                    self._immediate_add_user(prim_path_str)
                elif event.type == omni.anim.curve.core.CurveEventType.Updated:
                    # update all animation components. I doubt if there is really a case this event is issued.
                    self._immediate_update_user(prim_path_str)
            elif component_char != "":
                # the path is a curve path
                if event.type == omni.anim.curve.core.CurveEventType.Added:
                    self._immediate_add_track(prim_path_str, attr_name, component_char)
                elif event.type == omni.anim.curve.core.CurveEventType.Updated:
                    # if edit scope is not occupied by internal operation.
                    if self._edit_scope:
                        self._immediate_update_track(prim_path_str, attr_name, component_char)
                elif event.type == omni.anim.curve.core.CurveEventType.Removed:
                    self._immediate_remove_track(prim_path_str, attr_name, component_char)


class CurveEditorTrack:
    def __init__(self, user_prim: str, attr_name: str, component_name: str):
        self._prim_path_str = user_prim
        self._attr_name = attr_name
        self._component_name = component_name
        self._attr_path_str = user_prim + "." + self._attr_name
        self._data_attr_name = attr_name + ":" + component_name
        self._track_name = user_prim + "." + self._data_attr_name

    def get_track_name(self):
        return self._track_name

    def get_prim_path_str(self):
        return self._prim_path_str

    def get_attr_name(self):
        return self._attr_name

    def get_component_name(self):
        return self._component_name

    def get_attr_path_str(self):
        return self._attr_path_str

    def get_data_attr_name(self):
        return self._data_attr_name


class TracksCache:
    def __init__(self):
        self._cache = {}

    def clear(self):
        self._cache.clear()

    def has_user(self, user_prim: str):
        return self._cache.__contains__(user_prim)

    # user_prim has full path string. cached prim can have no curve for sometime or even for ever.
    def add_user(self, user_prim: str):
        if not self._cache.__contains__(user_prim):
            self._cache[user_prim] = {}
        else:
            carb.log_warn("Unexpected code path in TracksCache.add_user()")

    # user_prim has full path string, user_attr_name has no path, component_name is "x" or "y" or "z" or "w".
    # return the added track for convenience
    def add_track(self, user_prim: str, attr_name: str, component_name: str):
        if not self._cache.__contains__(user_prim):
            self._cache[user_prim] = {}
        if not self._cache[user_prim].__contains__(attr_name):
            self._cache[user_prim][attr_name] = {}

        added_track = CurveEditorTrack(user_prim, attr_name, component_name)
        self._cache[user_prim][attr_name][component_name] = added_track
        return added_track

    # delete the user_prim entry.
    def remove_user(self, user_prim: str) -> bool:
        if self._cache.__contains__(user_prim):
            found = True
            self._cache.pop(user_prim)
        else:
            found = False

        return found

    # delete the track entry. it will not delete user_prim entry even if it is empty.
    def remove_track(self, user_prim: str, attr_name: str, component_name: str):
        track = None
        if self._cache.__contains__(user_prim):
            if self._cache[user_prim].__contains__(attr_name):
                if self._cache[user_prim][attr_name].__contains__(component_name):
                    track = self._cache[user_prim][attr_name][component_name]
                    self._cache[user_prim][attr_name].pop(component_name)

                    if len(self._cache[user_prim][attr_name]) == 0:
                        self._cache[user_prim].pop(attr_name)
                        # here, do not pop user_prim even if self._cache[user_prim] is empty.
                        # because the self._cache[user_prim] represent UI selected prim, even if it has no curve.

        return track

    def get_track(self, user_prim: str, attr_name: str, component_name: str):
        if self._cache.__contains__(user_prim):
            if self._cache[user_prim].__contains__(attr_name):
                if self._cache[user_prim][attr_name].__contains__(component_name):
                    return self._cache[user_prim][attr_name][component_name]

        return None

    # return None if user_prim entry is not available.
    def get_user_tracks(self, user_prim: str):
        track_list = []
        if self._cache.__contains__(user_prim):
            for attr_name, attr_tracks in self._cache[user_prim].items():
                for component_name, track in attr_tracks.items():
                    track_list.append(track)
        return track_list

    def get_tracks(self):
        track_list = []
        for user_prim, prim_tracks in self._cache.items():
            for attr_name, attr_tracks in prim_tracks.items():
                for component_name, track in attr_tracks.items():
                    track_list.append(track)

        return track_list

    def get_users(self):
        user_list = []
        for user_prim, prim_tracks in self._cache.items():
            user_list.append(user_prim)

        return user_list


class SingletonCurveEditor:

    def __init__(self):
        global g_singleton
        if g_singleton:
            carb.log_error("Unexpected code path in SingletonCurveEditor.__init__()")

        self._tracks_cache = TracksCache()
        self._retained_tracks_cache = TracksCache()
        self._listener = CurveEditorEventListener(self)
        self._ui_worker = None

        # self._stage is designed to be only managed in _stage_update_sub functions directly.
        self._stage = None
        self._stage_update_sub = omni.stageupdate.get_stage_update_interface().create_stage_update_node(
            "SingletonCurveEditor",
            WeakMethod(self._on_stage_attach),
            WeakMethod(self._on_stage_detach),
            WeakMethod(self._on_stage_update),
            None,
            None,
            None,
        )
        self._stage_selection_changed_flag = True  # force to do at least one first _retained_update.
        self._selection = omni.usd.get_context().get_selection()

    def usd_edit_scope(self):
        return self._listener._edit_scope

    def _raise_stage_selection_changed_flag(self):
        self._stage_selection_changed_flag = True

    def _take_stage_selection_changed_flag(self) -> bool:
        take = self._stage_selection_changed_flag
        self._stage_selection_changed_flag = False
        return take

    def set_ui_worker(self, ui_worker):
        self._ui_worker = ui_worker

    def _get_tracks_cache(self):
        return self._tracks_cache

    def _get_retained_tracks_cache(self):
        return self._retained_tracks_cache

    def get_tracks(self):
        return self._get_tracks_cache().get_tracks()

    def get_track(self, user_prim: str, attr_name: str, component_name: str):
        return self._get_tracks_cache().get_track(user_prim, attr_name, component_name)

    def _on_stage_attach(self, stage_id, meters_per_unit):
        if self._stage:
            # I guess at most one stage is attached at the same time. That should the omni.usd.get_context().get_stage(). If not, that is really a disaster.
            carb.log_error("Unexpected code path in SingletonCurveEditor._on_stage_attach()")
            return

        cache = UsdUtils.StageCache.Get()
        self._stage = cache.Find(Usd.StageCache.Id.FromLongInt(stage_id))

    def _on_stage_detach(self):
        self._stage = None

    def _on_stage_update(self, t, dt):
        self._retained_update(self._stage)

    # return 3 sets : no_longer_selected, all_still_selected, new_selected
    def _split_selected_prim_paths(self):
        current_selected = set()
        current_selected.update([str(p) for p in self._selection.get_selected_prim_paths()])

        previous_selected = set()
        previous_selected.update(self._tracks_cache.get_users())

        no_longer_selected = set()
        all_still_selected = set()
        new_selected = set()
        all_still_selected.update(current_selected & previous_selected)
        no_longer_selected.update(previous_selected - all_still_selected)
        new_selected.update(current_selected - all_still_selected)

        return no_longer_selected, all_still_selected, new_selected

    # remove no_longer_selected user from the main editing cache and retained cache
    def _cache_remove_no_longer_selected_users(self, no_longer_selected):
        for user in no_longer_selected:
            self._tracks_cache.remove_user(user)
            self._retained_tracks_cache.remove_user(user)

    # for the latest new selected prims, found their curves and add in the immediate cache
    def _cache_add_new_selected_users(self, stage, new_selected):
        for user_prim_path_str in new_selected:
            if self._tracks_cache.has_user(user_prim_path_str):
                carb.log_error("Unexpected code path in SingletonCurveEditor._cache_add_new_selected_users()")
                # there is definitely something wrong. To avoid further mess, clear the entry.
                self._tracks_cache.remove_user(user_prim_path_str)
            self._tracks_cache.add_user(user_prim_path_str)
            # for every user's animatable component, do self._tracks_cache.add_track(user_prim_path_str, *, *)
            for attr_name, component_name in get_track_attr_and_component_names_from_runtime(user_prim_path_str):
                self._tracks_cache.add_track(user_prim_path_str, attr_name, component_name)

    def _ui_remove_no_longer_selected_users(self, no_longer_selected):
        for user in no_longer_selected:
            user_tracks = self._get_tracks_cache().get_user_tracks(user)
            for track in user_tracks:
                self._ui_remove_track(track)

    def _ui_update_still_selected_users(self, stage, still_selected):
        for user in still_selected:
            user_tracks = self._get_retained_tracks_cache().get_user_tracks(user)
            for track in user_tracks:
                self._ui_add_track(stage, track)

    def _ui_add_new_selected_users(self, stage, new_selected):
        for user in new_selected:
            user_tracks = self._get_tracks_cache().get_user_tracks(user)
            for track in user_tracks:
                self._ui_add_track(stage, track)

    def _ui_raise_refit_and_update_flag(self):
        self._ui_worker._ui_raise_refit_and_update_flag()

    # this should only be called in retained phase.
    def _ui_add_track(self, stage, track):
        self._ui_worker._ui_add_track(stage, track)

    def _ui_remove_track(self, track):
        self._ui_worker._ui_remove_track(track)

    def _retained_remove_no_longer_selected_users(self, no_longer_selected):
        # do ui remove first and then cache remove, because of cache dependency
        self._ui_remove_no_longer_selected_users(no_longer_selected)
        self._cache_remove_no_longer_selected_users(no_longer_selected)

    def _retained_update_still_selected_users(self, stage, still_selected):
        # if there is something to update
        if len(self._retained_tracks_cache.get_users()):
            # do ui update and before _retained_tracks_cache clear, the main cache is not changed here.
            self._ui_update_still_selected_users(stage, still_selected)

            # self._retained_tracks_cache is used in retained update once a frame. reset self._retained_tracks_cache.
            self._retained_tracks_cache.clear()

    def _retained_add_new_selected_users(self, stage, new_selected):
        # do cache add first and then ui add, because of cache dependency
        self._cache_add_new_selected_users(stage, new_selected)
        self._ui_add_new_selected_users(stage, new_selected)

    # tracks add can only happen in retained update here, while tracks removal can be instant.
    def _retained_update(self, stage):
        if self._take_stage_selection_changed_flag():
            no_longer_selected, all_still_selected, new_selected = self._split_selected_prim_paths()
            self._retained_remove_no_longer_selected_users(no_longer_selected)
            self._retained_update_still_selected_users(stage, all_still_selected)
            self._retained_add_new_selected_users(stage, new_selected)

            # auto fit when prim selection set changes
            self._ui_raise_refit_and_update_flag()

            # this is a hack for timeline_node_mode only
            self._ui_worker._update_with_timeline_node_mode()
        else:
            self._retained_update_still_selected_users(stage, self._retained_tracks_cache.get_users())

        self._ui_worker._retained_update(stage)

    def set_track_is_visible(self, track, is_visible: bool):
        self._ui_worker._ui_update_track_visibility(track, is_visible)

    # -----------------------------------------
    @staticmethod
    def get_instance():
        global g_singleton
        if g_singleton == None:
            g_singleton = SingletonCurveEditor()
        return weakref.proxy(g_singleton)

    @staticmethod
    def get_instance_ref():
        global g_singleton
        if g_singleton == None:
            g_singleton = SingletonCurveEditor()
        return weakref.ref(g_singleton)

    # must call before extension unload GC
    @staticmethod
    def destroy():
        global g_singleton
        g_singleton = None
