# Copyright (c) 2021-2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["VisibilityEdit", "RefCountedUsdContextSub", "stage_has_prim_type"]

from pathlib import Path
from typing import Callable, Dict, Optional, Sequence, Union

import carb
import omni.usd
from pxr import Sdf, Usd, UsdGeom, UsdUtils


def _make_light_mode_setting_key(usd_context: omni.usd.UsdContext) -> str:
    # return f"/exts/omni.kit.viewport.menubar.lighting/lightingMode/{id(usd_context)}"
    stage_id = 0
    stage = usd_context.get_stage()
    if stage:
        stage_id = UsdUtils.StageCache.Get().GetId(stage).ToLongInt()
    # Get a unique path to this UsdContext as lighting modes will affect the stage itself
    return f"/exts/omni.kit.viewport.menubar.lighting/lightingMode/{stage_id}"


def _get_usd_rt_stage(stage: Usd.Stage):
    try:
        from pxr import UsdUtils
        from usdrt import Usd as UsdRtUsd

        stage_id = UsdUtils.StageCache.Get().GetId(stage).ToLongInt()
        fabric_active_for_stage = UsdRtUsd.Stage.StageWithHistoryExists(stage_id)
        if fabric_active_for_stage:
            rt_stage = UsdRtUsd.Stage.Attach(stage_id)
            # Kit 111's OVStage-backed USDRT (what production apps load) has no Fabric-only prim queries
            # (GetPrimsWithTypeName, GetPrimsWithAppliedAPIName): callers then traverse the USD stage.
            if rt_stage and all(
                hasattr(rt_stage, query) for query in ("GetPrimsWithTypeName", "GetPrimsWithAppliedAPIName")
            ):
                return rt_stage
    except (ImportError, ModuleNotFoundError):
        pass
    return None


class VisibilityEdit:
    def __init__(
        self,
        stage,
        types_to_show: Optional[Callable] = None,
        types_to_hide: Optional[Callable] = None,
        types_for_prune: Optional[Sequence[str]] = None,
        api_types_for_prune: Optional[Sequence[str]] = None,
    ):
        # Sdf.Path.FindLongestPrefix require Sdf.PathVector (i.e. list) so we cannot use a dict
        self.__path_to_change = {}
        self.__stage = stage
        self.__types_to_show = types_to_show
        self.__types_to_hide = types_to_hide
        self.__prim_types = types_for_prune
        self.__api_types = api_types_for_prune
        settings = carb.settings.get_settings()
        self.__skip_stage_window_hidden = settings.get(
            "/exts/omni.kit.viewport.menubar.lighting/stageWindow/skipHidden"
        )

    def run(self):
        if self.__gather_prims():
            self.__hide_prims()

    @property
    def predicate(self):
        return Usd.TraverseInstanceProxies(Usd.PrimDefaultPredicate)

    def __get_visibility(self, prim: Usd.Prim, prim_path: Sdf.Path):
        make_visible = self.__types_to_show(prim, prim_path) if self.__types_to_show else False
        make_invisible = self.__types_to_hide(prim, prim_path) if self.__types_to_hide else False
        return (make_visible, make_invisible)

    def __is_hidden_in_stage_window(self, usd_prim: Usd.Prim):
        return usd_prim.GetMetadata("hide_in_stage_window") if self.__skip_stage_window_hidden else False

    @carb.profiler.profile
    def __get_prim_iterator(self, predicate):
        # If UsdRt is available, use it to pre-prune the traversal to only given types
        if self.__prim_types or self.__api_types:
            rt_stage = _get_usd_rt_stage(self.__stage)
            if rt_stage:
                prims_hide_in_stage_window = set()

                def visible_in_stage_window(prim, prim_path):
                    if self.__is_hidden_in_stage_window(prim):
                        prims_hide_in_stage_window.add(prim_path)
                        return False
                    for hidden_path in prims_hide_in_stage_window:
                        if prim_path.GetCommonPrefix(hidden_path) == hidden_path:
                            return False
                    return True

                def yield_prim(container: dict):
                    for prim_type, prim_paths in container.items():
                        for prim_path in prim_paths:
                            prim = self.__stage.GetPrimAtPath(prim_path.GetString())
                            if prim and visible_in_stage_window(prim, prim.GetPath()):
                                yield prim

                prim_types, api_types = {}, {}
                if self.__prim_types:
                    for prim_type in self.__prim_types:
                        prim_types[prim_type] = rt_stage.GetPrimsWithTypeName(prim_type)
                if self.__api_types:
                    for api_type in self.__api_types:
                        api_types[api_type] = rt_stage.GetPrimsWithAppliedAPIName(api_type)

                for prim in yield_prim(prim_types):
                    yield prim
                for prim in yield_prim(api_types):
                    yield prim
                return

        iterator = iter(self.__stage.Traverse(predicate))
        for prim in iterator:
            # Prune anything that is hide_in_stage_window
            # Not sure why, but this matches legacy behavior
            if self.__is_hidden_in_stage_window(prim):
                iterator.PruneChildren()
                continue

            yield prim

    @carb.profiler.profile
    def __gather_prims(self):
        path_to_change = {}

        # Traverse the stage, gathering the prims that have requested a visibility change
        # This is a two-phase process to allow hiding leaves of instances by hiding the
        # top-most un-instanced parent whose leaves are all of a hideable type
        for prim in self.__get_prim_iterator(self.predicate):
            # Get the prim-type and check against DISPLAY_FLAG_TO_PRIM_TYPES
            prim_path = prim.GetPath()
            make_visible, make_invisible = self.__get_visibility(prim, prim_path)

            # If not making this type visible or invisible, then nothing to do
            if (make_visible is False) and (make_invisible is False):
                continue

            if prim.IsInstanceProxy():
                is_child = False
                for path in path_to_change.keys():
                    if path.GetCommonPrefix(prim_path) == path:
                        is_child = True
                        break
                if is_child:
                    continue

                parent = prim.GetParent()
                while parent and not parent.IsInstance():
                    parent = parent.GetParent()
                # Insert the parent now and validate all children in the second phase
                if parent:
                    path_to_change[parent.GetPath()] = True
            else:
                path_to_change[prim_path] = False

        self.__path_to_change = path_to_change
        return len(self.__path_to_change) != 0

    def __restored_visibility(self, prim: Usd.Prim, session_layers):
        # Value that will compose once the session override is removed
        attr = prim.GetAttribute(UsdGeom.Tokens.visibility)
        if attr:
            for prop_spec in attr.GetPropertyStack(Usd.TimeCode.Default()):
                if (prop_spec.layer not in session_layers) and (prop_spec.default is not None):
                    return prop_spec.default
        return UsdGeom.Tokens.inherited

    @carb.profiler.profile
    def __hide_prims(self):
        # Traverse the instanced prims, making sure that all children are of the proper type
        # or an allowed 'intermediate' type of Xform or Scope.
        # If all children pass that test, then the instance can safely be hidden, otherwise
        # it contains children that are not being requested as hidden, so the instance is left alone.

        predicate = self.predicate
        # UsdGeom.Imageabales that are acceptable intermediate children
        allowed_imageables = set(("Xform", "Scope"))
        # Setup the edit-context once, and batch all changes
        session_layer = self.__stage.GetSessionLayer()
        session_layers = set(self.__stage.GetLayerStack(True)) - set(self.__stage.GetLayerStack(False))
        restore_properties = []
        with Usd.EditContext(self.__stage, session_layer):
            with Sdf.ChangeBlock():
                for prim_path, is_instance in self.__path_to_change.items():
                    prim = self.__stage.GetPrimAtPath(prim_path)
                    if not prim:
                        continue
                    if prim.IsInstanceProxy():
                        carb.log_error(f"Unexpected instance in list of prims to toggle visibility: {prim.GetPath()}")
                        continue

                    # Assume success
                    toggle_error = None
                    visible = None

                    # If its an instance, traverse all children and make sure that
                    # they are of the right type, not a UsdImageable, or an allowed intermediate.
                    if is_instance:
                        for child_prim in prim.GetFilteredChildren(predicate):
                            child_type = child_prim.GetTypeName()
                            child_show, child_hide = self.__get_visibility(child_prim, child_prim.GetPath())
                            if (not child_show) and (not child_hide):
                                # If child is in neither list, than it must be an allowed intermediate type (or not an Imagaeable)
                                if (not UsdGeom.Imageable(child_prim)) or (child_type in allowed_imageables):
                                    continue
                                toggle_error = "it contains at least one child with a type not being requested to hide."
                                break
                            # First loop iteration, set visible to proper state
                            if visible is None:
                                visible = child_show
                            if child_show != visible:
                                toggle_error = "its hiearchy is too heterogeneous for this action."
                                break
                    else:
                        visible = self.__types_to_show(prim, prim_path) if self.__types_to_show else False

                    if toggle_error:
                        visible_verb = "show" if visible else "hide"
                        carb.log_warn(f"Will not {visible_verb} '{prim_path}', {toggle_error}")
                        continue

                    if visible:
                        # as the session layer overrides all other layers, remove the primSpec
                        prim_spec = session_layer.GetPrimAtPath(prim_path)
                        property = (
                            session_layer.GetPropertyAtPath(prim_path.AppendProperty(UsdGeom.Tokens.visibility))
                            if prim_spec
                            else None
                        )
                        if property:
                            # OMPE-99588: author the restored value so the renderer sees a value-change
                            restored = self.__restored_visibility(prim, session_layers)
                            if property.default != restored:
                                property.default = restored
                            restore_properties.append((prim_spec, property))
                    else:
                        imageable = UsdGeom.Imageable(prim)
                        if imageable:
                            imageable.GetVisibilityAttr().Set(UsdGeom.Tokens.invisible)

            # OMPE-99588: an active-metadata poke forces a prim resync; some RTX builds drop bare spec-removals
            if restore_properties:
                restored_prims = []
                with Sdf.ChangeBlock():
                    for prim_spec, property in restore_properties:
                        prim_path = prim_spec.path
                        # Capture any pre-existing session 'active' opinion so cleanup can restore it
                        had_active = prim_spec.HasActive()
                        prev_active = prim_spec.active if had_active else None
                        prim_spec.RemoveProperty(property)
                        prim = self.__stage.GetPrimAtPath(prim_path)
                        if prim:
                            # SetActive(True) is a no-op if active is already true; poke the opposite to force a resync
                            prim.SetActive((not prev_active) if had_active else True)
                            restored_prims.append((prim_path, had_active, prev_active))
                self.__schedule_active_cleanup(restored_prims)

    def __schedule_active_cleanup(self, restored_prims: Sequence[tuple]):
        # Deferred a frame: same-update author+clear would coalesce to a no-op (OMPE-99588)
        if not restored_prims:
            return

        import asyncio

        import omni.kit.app

        stage = self.__stage

        async def cleanup(stage: Usd.Stage, restored_prims: Sequence[tuple]):
            await omni.kit.app.get_app().next_update_async()
            try:
                with Usd.EditContext(stage, stage.GetSessionLayer()):
                    with Sdf.CleanupEnabler():
                        with Sdf.ChangeBlock():
                            for prim_path, had_active, prev_active in restored_prims:
                                prim = stage.GetPrimAtPath(prim_path)
                                if not prim:
                                    continue
                                if had_active:
                                    # Restore the captured session opinion instead of deleting it
                                    prim.SetActive(prev_active)
                                else:
                                    prim.ClearActive()
            except Exception:  # pragma: no cover - stage may have been closed
                import traceback

                carb.log_info(traceback.format_exc())

        asyncio.ensure_future(cleanup(stage, restored_prims))


# Kit 111's Runtime Core authors a fallback DistantLight (/OVRuntimeDefaultLight) on its own scaffold layer while the
# stage has no light of its own, and removes it once the stage gets one. It marks it with this customData key
# (omni.runtime.core.FALLBACK_LIGHT_CUSTOM_DATA_KEY); it is not one of the stage's lights. Read the key directly so this
# also runs without omni.runtime.core (Kit 110).
_RUNTIME_FALLBACK_LIGHT_KEY = "omni:runtime:fallbackLight"


def _is_runtime_fallback_light(prim) -> bool:
    return bool(prim) and bool(prim.GetCustomDataByKey(_RUNTIME_FALLBACK_LIGHT_KEY))


@carb.profiler.profile
def stage_has_api_type(stage: Usd.Stage, api_type, search_from_default_prim: bool = False) -> bool:
    """Return if the stage has any Usd.Prims of type given"""
    if not stage:
        return False

    root = None
    if search_from_default_prim:
        root = stage.GetDefaultPrim()
    if not root:
        root = stage.GetPseudoRoot()

    # If UsdRt is available, do a fast-query of the prim type, then compare
    # results for anythng properly underneath root-path
    rt_stage = _get_usd_rt_stage(stage)
    if rt_stage:
        root = root.GetPath()
        for prim_path in rt_stage.GetPrimsWithAppliedAPIName(api_type.__name__):
            if root.GetCommonPrefix(prim_path.GetString()) == root and not _is_runtime_fallback_light(
                stage.GetPrimAtPath(prim_path.GetString())
            ):
                return True
        return False

    # Breadth-first search because its likely a light wont be deeply nested in a hierarchy
    # that a model might have and would more likely appear in a shallow hierachy off of the root.
    def iterate_children(children_lists, api_type):
        child_children = []
        for children in children_lists:
            if not children:
                continue
            for child in children:
                if child.HasAPI(api_type) and not _is_runtime_fallback_light(child):
                    return True
                child_children.append(child.GetChildren())

        if child_children:
            return iterate_children(child_children, api_type)
        return False

    return iterate_children([root.GetChildren()], api_type)


class RefCountedUsdContextSub:
    """Create a single stage-open callback for multiple instance attaching to a single omni.usd.USdContext"""

    __g_usd_stage_subs: Dict[str, tuple] = {}

    def __init__(
        self,
        usd_context_name: Optional[str] = None,
        usd_context_opened: Optional[Callable] = None,
        setting_path: Optional[str] = None,
        setting_changed: Optional[Callable] = None,
    ):
        if setting_path is None:
            setting_path = _make_light_mode_setting_key(omni.usd.get_context(usd_context_name))
        # Inspect teh dict for current value or set it to empty
        sub_tuple = self.__g_usd_stage_subs.get(usd_context_name)
        first_sub = sub_tuple is None
        # If no sub, then create one now
        if first_sub:

            def on_setting_changed(item: carb.dictionary.Item, event_type: carb.settings.ChangeEventType):
                if event_type == carb.settings.ChangeEventType.CHANGED:
                    setting_changed_fn = RefCountedUsdContextSub.__g_usd_stage_subs.get(usd_context_name)[4]
                    setting_changed_fn(
                        omni.usd.get_context(usd_context_name), carb.settings.get_settings().get(setting_path)
                    )

            def on_stage_opened(*args, **kwargs):
                nonlocal setting_path
                settings = carb.settings.get_settings()
                prev_value = settings.get(setting_path) if setting_path else None
                setting_path = _make_light_mode_setting_key(omni.usd.get_context(usd_context_name))
                sub_tuple = RefCountedUsdContextSub.__g_usd_stage_subs.get(usd_context_name)
                sub_tuple = (
                    sub_tuple[0],
                    settings.subscribe_to_node_change_events(setting_path, on_setting_changed),
                    sub_tuple[2],
                    sub_tuple[3],
                    sub_tuple[4],
                )
                RefCountedUsdContextSub.__g_usd_stage_subs[usd_context_name] = sub_tuple
                usd_context_opened_fn = sub_tuple[3]
                usd_context_opened_fn(usd_context_name, omni.usd.get_context(usd_context_name), prev_value)

            usd_context = omni.usd.get_context(usd_context_name)
            sub_tuple = (
                (
                    carb.eventdispatcher.get_eventdispatcher().observe_event(
                        observer_name=f"omni.kit.viewport.menubar.lighting.RefCountedUsdContextSub.{usd_context}",
                        event_name=usd_context.stage_event_name(omni.usd.StageEventType.OPENED),
                        on_event=on_stage_opened,
                    )
                    if usd_context_opened
                    else None
                ),
                (
                    carb.settings.get_settings().subscribe_to_node_change_events(setting_path, on_setting_changed)
                    if setting_path
                    else None
                ),
                0,
            )

        self.__usd_context_name: Optional[str] = usd_context_name
        self.__g_usd_stage_subs[usd_context_name] = (
            # Store back the existing or created subscriptions and increment the refcount
            sub_tuple[0],
            sub_tuple[1],
            sub_tuple[2] + 1,
            # Store the last callbacks registered into the state
            usd_context_opened,
            setting_changed,
        )

        # Call the callback if the stage is already completely opened and this is the first sub
        # Done last so that all members are constructed
        if first_sub:
            if usd_context.get_stage_state() == omni.usd.StageState.OPENED:
                try:
                    usd_context_opened(usd_context_name, usd_context, carb.settings.get_settings().get(setting_path))
                except Exception:
                    import traceback

                    carb.log_error(traceback.format_exc())

    def __del__(self):
        self.destroy()

    def destroy(self):
        usd_context_name, self.__usd_context_name = self.__usd_context_name, None
        if usd_context_name is None:
            return

        sub_tuple = self.__g_usd_stage_subs[usd_context_name]
        ref_count = sub_tuple[2] - 1
        if ref_count:
            self.__g_usd_stage_subs[usd_context_name] = (
                sub_tuple[0],
                sub_tuple[1],
                ref_count,
                sub_tuple[3],
                sub_tuple[4],
            )
        else:
            if sub_tuple[1]:
                carb.settings.get_settings().unsubscribe_to_change_events(sub_tuple[1])
            del self.__g_usd_stage_subs[usd_context_name]


# Default rig name transformation: "snake_case_file.ext" => "Snake Case File"
def _get_rig_name(light_rig: Union[Path, str]):
    import string

    # Get the filename without extension
    rig_name = Path(light_rig).stem
    # Transform file_name_1 => File Name 1
    return string.capwords(rig_name.replace("_", " "))


# Default rig list sorting: alphabetical and case insensitive
def _sort_rigs_paths(light_rigs: Sequence[Path]) -> Sequence[Path]:
    return sorted(light_rigs, key=lambda p: p.stem.lower())


# Function to get the setting-key that stores the rig directory path
def _get_light_rig_setting_key(extension_id: str):
    return f"/exts/{extension_id}/rigs"


def _get_rig_names_and_paths(extension_id: str):
    # Get the rig directory setting value
    rig_path = carb.settings.get_settings().get(_get_light_rig_setting_key(extension_id))
    if not rig_path:
        return None

    # From the rig directory setting value, resolve any carb-tokens
    rig_path = carb.tokens.get_tokens_interface().resolve(rig_path)
    if not rig_path:
        return None

    # Finally, from the rig directory setting value, resolve to a fully formed path
    rig_path = Path(rig_path).absolute()
    # Get a sorted list a the usd* files in that directory
    light_rigs = _sort_rigs_paths(Path(rig_path).absolute().rglob("*.usd*"))
    if not light_rigs:
        return None

    # Return a name, path pair from the list of rigs
    for light_rig in light_rigs:
        yield _get_rig_name(light_rig), light_rig
