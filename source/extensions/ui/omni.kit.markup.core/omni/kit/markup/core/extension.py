# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import weakref
from copy import deepcopy
from typing import Callable, Dict, List, Optional, cast

import carb
import carb.eventdispatcher
import carb.events
import carb.settings
import omni.ext
import omni.kit.app
import omni.kit.commands
import omni.kit.prim.icon
import omni.kit.undo
import omni.kit.usd.layers as usd_layers
import omni.timeline
import omni.ui as ui
import omni.usd
from carb.eventdispatcher import get_eventdispatcher
from omni.kit.async_engine import run_coroutine
from omni.kit.stage.copypaste import get_prim_as_text, text_to_stage
from omni.kit.viewport.utility import get_active_viewport

try:
    from omni.usd_presenter.sidecar import deregister_data, register_data
except ImportError:
    register_data = deregister_data = lambda *x: None

from pxr import Sdf, Tf, Trace, Usd, UsdGeom

from .common import (
    APPLICATION_MODE,
    MARKUP_ROOT_PRIM_PATH,
    SETTINGS_MARKUP_ACTIVE,
    SETTINGS_MARKUP_EDITING,
    SETTINGS_MARKUP_ROOT,
)
from .markup_usd import MarkupUsd
from .viewport_markup import ViewportMarkup

LOCK_CAMERA_ATTR = "omni:kit:cameraLock"
LOCK_EDIT_ATTR = "omni:LiveEditLock"

SETTINGS_VIEWPORT_RECT = SETTINGS_MARKUP_ROOT + "viewport_rect"
SETTINGS_MARKUP_SHOW_ICONS = SETTINGS_MARKUP_ROOT + "show_icons"

SETTINGS_MARKUP_ENABLE_HOTKEYS = SETTINGS_MARKUP_ROOT + "enable_hotkeys"
SETTINGS_MARKUP_CREATE_HOTKEY = SETTINGS_MARKUP_ROOT + "hotkeys/create"
SETTINGS_MARKUP_NEXT_HOTKEY = SETTINGS_MARKUP_ROOT + "hotkeys/next"
SETTINGS_MARKUP_PREVIOUS_HOTKEY = SETTINGS_MARKUP_ROOT + "hotkeys/previous"
SETTINGS_MARKUP_APPLY_HOTKEY = SETTINGS_MARKUP_ROOT + "hotkeys/apply"
SETTINGS_MARKUP_CANCEL_HOTKEY = SETTINGS_MARKUP_ROOT + "hotkeys/cancel"
SETTINGS_MARKUP_DELETE_HOTKEY = SETTINGS_MARKUP_ROOT + "hotkeys/delete"
SETTINGS_MARKUP_NEXT_TOOL_HOTKEY = SETTINGS_MARKUP_ROOT + "hotkeys/next_tool"
SETTINGS_MARKUP_PREVIOUS_TOOL_HOTKEY = SETTINGS_MARKUP_ROOT + "hotkeys/previous_tool"

SETTINGS_MARKUP_CURRENT_TOOL = "/persistent/exts/omni.kit.tool.markup/tool_default"
MARKUP_TOOL_ORDER = ["comment", "draw", "arrow", "line", "shapes"]

MARKUP_WINDOW_FOCUS_CONTEXT = "omni.kit.markup.core-window-focused"
MARKUP_EDIT_CONTEXT = "omni.kit.markup.core-window-edit"

MARKUP_ICON_URL = "${omni.kit.markup.core}/icons/MarkUp_Viewport.png"
NAV_OP_PATHS = [
    "/exts/omni.kit.tool.navigation/activeOperation",
    "/exts/omni.kit.viewport.navigation.core/activeOperation",
]
NAV_AUTO_CENTER = "/exts/omni.kit.viewport.navigation.camera_manipulator/orbitAutoCenter"
NAV_IS_VISIBLE = "/exts/omni.kit.viewport.navigation.core/isVisible"
g_singleton = None


def get_instance() -> Optional["MarkupCore"]:
    global g_singleton
    return g_singleton


class MarkupChangeCallbacks:
    def __dummy(*_) -> None:  # pragma: no cover
        pass

    def __init__(
        self,
        on_markup_created: Callable = __dummy,
        on_markup_deleted: Callable = __dummy,
        on_markup_changed: Callable = __dummy,
        on_reset: Callable = __dummy,
    ) -> None:
        self.on_markup_created = on_markup_created
        self.on_markup_deleted = on_markup_deleted
        self.on_markup_changed = on_markup_changed
        self.on_reset = on_reset


class MarkupExtension(omni.ext.IExt):
    def on_startup(self, _ext_id) -> None:
        self._markup = MarkupCore()
        self._markup.on_startup(_ext_id)

    def on_shutdown(self) -> None:
        self._markup.on_shutdown()


class MarkupCore:
    _stage: Usd.Stage

    # ext_id is current extension id. It can be used with extension manager to query additional information, like where
    # this extension is located on filesystem.
    def on_startup(self, _ext_id) -> None:
        sections = _ext_id.split("-")
        self._same_layer = None
        self._ext_name = sections[0]
        self.__sidecar_data = register_data("Markup")
        self._prim_icon = omni.kit.prim.icon.get_prim_icon_interface()
        self._markups: Dict[str, ViewportMarkup] = {}
        self._notifications: List[MarkupChangeCallbacks] = []

        self._current_markup: Optional[ViewportMarkup] = None
        self._editing_markup: Optional[ViewportMarkup] = None
        # Navbar visibility captured on edit-entry, restored (and cleared) on edit-exit.
        # None means "nothing captured", so restore is a no-op outside an edit session.
        self._nav_is_visible_captured: Optional[bool] = None
        self._markup_usd = None
        self._open_callback = None
        self._opened_markup_name = ""
        self._edit_state_change_fn: Optional[Callable] = None
        self._edit_end_fn: Optional[Callable] = None
        self._export_fn: Optional[Callable] = None
        self._prim_icon = omni.kit.prim.icon.get_prim_icon_interface()

        self._app = omni.kit.app.get_app_interface()
        self._timeline = omni.timeline.get_timeline_interface()
        self._update_sub = None
        self._settings = carb.settings.get_settings()

        self._usd_context = omni.usd.get_context()
        self._usd_selection = self._usd_context.get_selection()
        self._selected_prim_paths: List[str] = []
        self._stage = self._usd_context.get_stage()
        self._stage_event_observers = [
            get_eventdispatcher().observe_event(
                observer_name="omni.kit.markup.core:extension",
                event_name=event,
                on_event=func,
            )
            for event, func in (
                (self._usd_context.stage_event_name(omni.usd.StageEventType.OPENED), lambda _: self._on_stage_opened()),
                (self._usd_context.stage_event_name(omni.usd.StageEventType.CLOSED), lambda _: self._on_stage_closed()),
                (
                    self._usd_context.stage_event_name(omni.usd.StageEventType.CLOSING),
                    lambda _: self._on_stage_closing(),
                ),
            )
        ]
        if self._usd_context.get_stage_state() == omni.usd.StageState.OPENED:  # pragma: no cover
            self.current_markup = None
            self._refresh_markups()

        self._update_setting_sub = omni.kit.app.SettingChangeSubscription(
            SETTINGS_MARKUP_SHOW_ICONS, lambda *_: self._on_visibility_setting_changed()
        )
        if not self._is_markup_icon_visible():
            self._hide_markup_icons()
        self._prim_icon = omni.kit.prim.icon.get_prim_icon_interface()

        self._locked_camera_path = ""
        self._old_edit_data = ""
        self.__register_display_setting()
        self._handle_change_task = None

        self._selection_command = None

        def application_mode_changed(*args, _self=weakref.ref(self)):  # pragma: no cover
            self = _self()
            if self:
                if self._settings.get(APPLICATION_MODE) not in ("review", "approve"):
                    self.current_markup = None

        self._application_mode_changed_id = self._settings.subscribe_to_node_change_events(
            APPLICATION_MODE, application_mode_changed
        )
        self.__layers_event_subscriptions = []
        self.__layers = cast(usd_layers.Layers, usd_layers.get_layers(self._usd_context))
        if self.__layers:
            self.__register_stage_update()

        self.__init_hotkeys()
        self._enable_hotkeys_sub = self._settings.subscribe_to_node_change_events(
            SETTINGS_MARKUP_ENABLE_HOTKEYS,
            self._on_hotkeys_enabled_changed,
        )

        global g_singleton
        g_singleton = self
        self.__dirty_paths: "set[Sdf.Path]" = set()
        run_coroutine(self.deferred_startup())

    def __init_hotkeys(self):
        self._hotkey_reg = None
        self._hotkey_context = None
        self._action_reg = None
        self._actions = {}
        self._hotkeys = {}
        self._register_hotkeys()

    def __register_stage_update(self):
        self.__stage_listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_objects_changed, self._stage)
        if not hasattr(usd_layers, "layer_event_name"):
            self.__layers_event_subscription = self.__layers.get_event_stream().create_subscription_to_pop(
                self.__on_layers_event, name="omni.kit.markup.core"
            )
        else:
            for event_type in (
                usd_layers.LayerEventType.PRIM_SPECS_CHANGED,
                usd_layers.LayerEventType.LIVE_SESSION_STATE_CHANGED,
                usd_layers.LayerEventType.SUBLAYERS_CHANGED,
                usd_layers.LayerEventType.MUTENESS_SCOPE_CHANGED,
                usd_layers.LayerEventType.MUTENESS_STATE_CHANGED,
            ):
                event_name = usd_layers.layer_event_name(event_type)
                sub = get_eventdispatcher().observe_event(
                    observer_name=f"omni.kit.markup.core:extension-{event_name}",
                    event_name=event_name,
                    on_event=self.__on_layers_event,
                )
                self.__layers_event_subscriptions.append(sub)

    def __deregister_stage_update(self):
        self.__stage_listener = None
        self.__layers_event_subscription = None
        self.__layers_event_subscriptions.clear()

    async def deferred_startup(self):
        # Not sure why, but commands need to be registered with a slight delay.
        # My guess is some kind of circular import problem that isn't raising a proper traceback. -Bob
        import omni.kit.app
        import omni.kit.commands

        await omni.kit.app.get_app().post_update_async()
        try:
            import omni.kit.markup.core.commands
        except ImportError as e:  # pragma: no cover
            carb.log_error(e.msg)
        else:
            omni.kit.commands.register_all_commands_in_module("omni.kit.markup.core.commands")

    @property
    def edit_state_change_fn(self) -> Optional[Callable]:
        return self._edit_state_change_fn

    @edit_state_change_fn.setter
    def edit_state_change_fn(self, val: Optional[Callable]) -> None:
        self._edit_state_change_fn = val

    @property
    def edit_end_fn(self) -> Optional[Callable]:
        return self._edit_end_fn

    @edit_end_fn.setter
    def edit_end_fn(self, val: Optional[Callable]) -> None:
        self._edit_end_fn = val

    @property
    def export_fn(self) -> Optional[Callable]:
        return self._export_fn

    @export_fn.setter
    def export_fn(self, val: Optional[Callable]) -> None:
        self._export_fn = val

    def on_shutdown(self) -> None:  # pragma: no cover
        global g_singleton
        g_singleton = None

        self._remove_markup_edit_hotkeys()
        self._deregister_all_hotkeys()
        self._action_reg = None
        self._hotkey_reg = None
        self._hotkey_context = None

        if self._enable_hotkeys_sub:
            self._settings.unsubscribe_to_change_events(self._enable_hotkeys_sub)
            self._enable_hotkeys_sub = None

        self._app = None
        self.editing_markup = None
        self.current_markup = None
        self._notifications.clear()
        self._update_setting_sub = None
        # self._stage_event_sub = None
        self._stage = None
        self._usd_context = None

        self._hide_markup_icons()
        deregister_data("Markup")
        self.__sidecar_data = None

        omni.kit.commands.unregister_module_commands("omni.kit.markup.core.commands")
        self.__deregister_display_setting()
        self.__deregister_stage_update()
        if self._handle_change_task and not self._handle_change_task.done():
            self._handle_change_task.cancel()

    def __on_layers_event(self, event: carb.events.IEvent | carb.eventdispatcher.Event):
        payload = usd_layers.get_layer_event_payload(event)
        if not payload:  # pragma: no cover
            return
        if payload.event_type == usd_layers.LayerEventType.PRIM_SPECS_CHANGED:
            for _layer, specs in payload.layer_spec_paths.items():
                self.__dirty_paths.update({Sdf.Path(spec) for spec in specs if spec.startswith(MARKUP_ROOT_PRIM_PATH)})
        elif payload.event_type in (
            usd_layers.LayerEventType.LIVE_SESSION_STATE_CHANGED,
            usd_layers.LayerEventType.SUBLAYERS_CHANGED,
            usd_layers.LayerEventType.MUTENESS_SCOPE_CHANGED,
            usd_layers.LayerEventType.MUTENESS_STATE_CHANGED,
        ):  # pragma: no cover
            self._refresh_markups()
            return
        else:
            return

        if not self.__dirty_paths:
            return

        if self._handle_change_task is None or self._handle_change_task.done():
            self._handle_change_task = run_coroutine(self._handle_changes())

    @Trace.TraceFunction
    def _on_objects_changed(self, notice: Usd.Notice.ObjectsChanged, stage: Usd.Stage):  # pragma: no cover
        if not stage or stage != self._stage:
            return
        if not self.__layers.get_live_syncing().is_stage_in_live_session():
            return

        paths: "list[Sdf.Path]" = cast("list[Sdf.Path]", notice.GetResyncedPaths())
        paths.extend(cast("list[Sdf.Path]", notice.GetChangedInfoOnlyPaths()))
        self.__dirty_paths.update(pth for pth in paths if pth.HasPrefix(MARKUP_ROOT_PRIM_PATH))

        if not self.__dirty_paths:
            return

        if self._handle_change_task is None or self._handle_change_task.done():
            self._handle_change_task = run_coroutine(self._handle_changes())

    async def _handle_changes(self):
        for _ in range(5):
            await omni.kit.app.get_app().next_update_async()
        self.__process_dirty(self.__dirty_paths.copy())
        self.__dirty_paths.clear()
        self._handle_change_task = None

    def __process_dirty(self, paths: "set[Sdf.Path]"):
        if self.editing_markup:
            return

        if not omni.usd.get_context().get_stage():
            # clear markups when the stage is changed/closed
            # copy the dict, as this iteration can happen while something else is modifying self._markups apparently
            markups = self._markups.copy()
            for name, markup in markups.items():
                self.delete_markup(markup)
            return

        for path in paths:
            if path.IsAbsoluteRootPath() or path == MARKUP_ROOT_PRIM_PATH:
                break
            prim_path: Sdf.Path = cast(Sdf.Path, path.GetPrimPath() if path.IsPrimPropertyPath() else path)
            new_path: Sdf.Path = cast(Sdf.Path, prim_path)
            while cast(Sdf.Path, new_path.GetParentPath()) != MARKUP_ROOT_PRIM_PATH:
                new_path: Sdf.Path = cast(Sdf.Path, new_path.GetParentPath())
            if self._stage is not None and bool(self._stage):
                prim: Usd.Prim = cast(Usd.Prim, self._stage.GetPrimAtPath(cast(Sdf.Path, new_path)))
            else:
                prim = None
            if prim and prim.IsValid():
                markup = self.get_markup_from_prim_path(cast(str, new_path.pathString))
                if not markup:
                    markup = ViewportMarkup("", sidecar_data=self.__sidecar_data)

                if markup.create_from_prim(prim):
                    self._markups[markup.name] = markup
            else:
                markup = self.get_markup_from_prim_path(cast(str, path.pathString))
                if markup:  # pragma: no cover
                    self.delete_markup(markup)
        self._refresh_markups()

    @property
    def edit_context(self) -> Usd.EditContext:
        return (
            self.__sidecar_data.edit_context
            if self.__sidecar_data
            else Usd.EditContext(self._stage, Usd.EditTarget(None))
        )

    @property
    def current_markup(self) -> Optional[ViewportMarkup]:
        return self._current_markup

    @current_markup.setter
    def current_markup(self, markup: Optional[ViewportMarkup]) -> None:
        self._current_markup = markup
        if self._current_markup is None:
            if self.editing_markup is not None:
                self.editing_markup = None
            self._settings.set_string(SETTINGS_MARKUP_ACTIVE, "")
            if hasattr(self, "_auto_center"):
                self._settings.set(NAV_AUTO_CENTER, self._auto_center)
            self._set_markup_icon_visibility()
        else:
            for NAV_OP_PATH in NAV_OP_PATHS:
                self._settings.set_string(NAV_OP_PATH, "none")
            self._auto_center = self._settings.get_as_bool(NAV_AUTO_CENTER)
            self._settings.set_bool(NAV_AUTO_CENTER, False)
            self._selected_prim_paths = self._usd_selection.get_selected_prim_paths()
            self._usd_selection.clear_selected_prim_paths()
            self._settings.set_string(SETTINGS_MARKUP_ACTIVE, self._current_markup.name)
            self._hide_markup_icons()

    @property
    def editing_markup(self) -> Optional[ViewportMarkup]:
        return self._editing_markup

    @editing_markup.setter
    def editing_markup(self, markup: Optional[ViewportMarkup]) -> None:

        if markup is None:
            # If we're setting editing_markup to None, there are two cases to consider:
            if self._editing_markup is None:
                # If self._editing_markup was already None, we want to exit early.
                # Importantly, not exiting here can lead to invalid behavior -- e.g.,
                # during a live session, one user adding a markup will case the markup list window
                # to appear in other users' sessions, even if they are not in markup mode.
                # This is because the list window's visibility is keyed off changes to SETTINGS_MARKUP_EDITING,
                # and is one of the bugs observed in OMFP-2778.
                return
            else:
                # Otherwise, we want to clear the lock attribute on the markup we've finished editing.
                # TODO: should this be done unconditionally, and not just when markup == None?
                if self._stage is not None and bool(self._stage):
                    prim = self._stage.GetPrimAtPath(self._editing_markup.get_usd_prim_path())
                    if prim and prim.IsValid() and prim.HasAttribute(LOCK_EDIT_ATTR):
                        prim.RemoveProperty(LOCK_EDIT_ATTR)

        self._editing_markup = markup
        if self._editing_markup is None:
            self._settings.set(SETTINGS_MARKUP_EDITING, "")
            self._restore_navbar()
        else:
            self._settings.set(SETTINGS_MARKUP_EDITING, self._editing_markup.name)
            self._capture_and_hide_navbar()
            # In edit mode, never check markup changes, keep current markup
            self.recall_markup(markup)

    def _capture_and_hide_navbar(self) -> None:
        # Capture the navbar visibility once per edit session and hide it while editing.
        # Guarded so re-entrant edit-entry doesn't overwrite the captured value with the
        # already-hidden state.
        if self._nav_is_visible_captured is None:
            self._nav_is_visible_captured = self._settings.get_as_bool(NAV_IS_VISIBLE)
            self._settings.set_bool(NAV_IS_VISIBLE, False)

    def _restore_navbar(self) -> None:
        # Restore the navbar to its pre-edit visibility and clear the capture so the value
        # is never reused on a subsequent, unrelated edit-exit path.
        if self._nav_is_visible_captured is not None:
            self._settings.set_bool(NAV_IS_VISIBLE, self._nav_is_visible_captured)
            self._nav_is_visible_captured = None

    @property
    def opened_markup_name(self) -> str:
        return self._opened_markup_name

    @opened_markup_name.setter
    def opened_markup_name(self, name: str) -> None:
        self._opened_markup_name = name

    def register_callback(self, notification: MarkupChangeCallbacks) -> None:
        self._notifications.append(notification)

    def deregister_callback(self, notification: MarkupChangeCallbacks) -> None:
        if notification in self._notifications:
            self._notifications.remove(notification)

    def is_markup_prim(self, prim_path: str) -> bool:
        if str(prim_path).startswith(MARKUP_ROOT_PRIM_PATH + "/"):
            return True
        return False

    def load_markups(self) -> None:
        self._refresh_markups()

    def create_markup(
        self,
        new_markup_path: str = "",
        icon_url: str = MARKUP_ICON_URL,
        icon_click: Optional[Callable[[str], None]] = None,
    ) -> None:
        if self.__sidecar_data and self.__sidecar_data.read_only:  # pragma: no cover
            self.__sidecar_data.notify_read_only("Create Markup")
            return

        # OM-51837 - Storing selected prim paths and clearing selection so the thumbnail camera doesn't do
        # a fit-to-selected before capturing the thumbnail.
        self._selected_prim_paths = self._usd_selection.get_selected_prim_paths()
        self._usd_selection.clear_selected_prim_paths()
        self._markup_path = new_markup_path or omni.usd.get_stage_next_free_path(
            self._stage, f"{MARKUP_ROOT_PRIM_PATH}/Markup_00", False
        )
        self._new_markup_name = cast(str, Sdf.Path(self._markup_path).name)
        self._create_markup(self._new_markup_name)
        self._add_markup_edit_hotkeys()
        self._prim_icon.add_prim_icon(self._markup_path, icon_url)
        self._prim_icon.set_icon_click_fn(self._markup_path, icon_click or self._recall_markup_from_prim_path)
        self._set_markup_icon_visibility()

    def begin_edit_markup(self, markup: ViewportMarkup, set_editing_markup=True) -> bool:

        self._same_layer = False
        for spec in markup.usd_prim.GetPrimStack():
            if self._stage.GetEditTarget().GetLayer() == spec.layer:
                self._same_layer = True
                break

        if self.__sidecar_data and self.__sidecar_data.read_only:  # pragma: no cover
            self.__sidecar_data.notify_read_only("Edit Markup")
            return False

        if self.editing_markup and self.editing_markup == markup:
            return False

        def serialize_editing_markup_prim():
            stage: Usd.Stage = self._stage
            prim: Usd.Prim = cast(Usd.Prim, stage.GetPrimAtPath(self.editing_markup.path))
            temp_stage: Usd.Stage = cast(Usd.Stage, Usd.Stage.CreateInMemory())
            for prim_spec in cast("list[Sdf.PrimSpec]", prim.GetPrimStack()):
                tmp_layer: Sdf.Layer = cast(Sdf.Layer, Sdf.Layer.CreateAnonymous())
                Sdf.CreatePrimInLayer(tmp_layer, prim_spec.path)
                Sdf.CopySpec(prim_spec.layer, prim_spec.path, tmp_layer, prim_spec.path)
                temp_stage.GetRootLayer().subLayerPaths.append(tmp_layer.identifier)
            return get_prim_as_text(temp_stage, [Sdf.Path(self.editing_markup.path)])

        self._selected_prim_paths = self._usd_selection.get_selected_prim_paths()
        self._usd_selection.clear_selected_prim_paths()

        if set_editing_markup:
            self.current_markup = markup
            self.editing_markup = markup
            self._old_edit_data = serialize_editing_markup_prim()
            if self._edit_state_change_fn:
                self._edit_state_change_fn(True)
            if markup.usd_prim:
                # Using an Attribute as a semaphore for live.
                at = markup.usd_prim.GetAttribute(LOCK_EDIT_ATTR)
                if not at:
                    at = cast(Usd.Attribute, markup.usd_prim.CreateAttribute(LOCK_EDIT_ATTR, Sdf.ValueTypeNames.Bool))
                at.Set(True)

        self._add_markup_edit_hotkeys()

        return True

    def end_edit_markup(
        self,
        markup: ViewportMarkup,
        *,
        save: bool = True,
        callback: Optional[Callable[[], None]] = None,
        update_thumbnail: bool = True,
    ) -> None:
        if not self.editing_markup:
            return
        if markup != self.editing_markup:  # pragma: no cover
            carb.log_error(f"Cannot end edit markup {markup.name} since it is not in edit!")
            return
        with self.edit_context:
            if markup.usd_prim and markup.usd_prim.HasAttribute(LOCK_EDIT_ATTR):
                markup.usd_prim.RemoveProperty(LOCK_EDIT_ATTR)
        if save:
            # Probably need to figure out how to unify all this callback nonsense. -Bob
            # Especially for undo/redo support.
            if update_thumbnail:
                if not callback:
                    markup.refresh_thumbnail(lambda w=markup: self._on_markup_changed(w))
                else:

                    def _cb(mark=markup, cb=callback):
                        self._on_markup_changed(mark)
                        cb()

                    markup.refresh_thumbnail(_cb)
        else:
            if self.__sidecar_data:  # pragma: no cover
                if not self.__sidecar_data.read_only:
                    with self.edit_context:
                        omni.kit.commands.execute("DeletePrims", paths=[markup.path])
                        if self._old_edit_data:
                            text_to_stage(self._stage, self._old_edit_data, Sdf.Path(MARKUP_ROOT_PRIM_PATH))
                    self._refresh_markups()
                else:
                    self.__sidecar_data.notify_read_only("End Edit->Delete")
            else:
                with self.edit_context:
                    if self._same_layer == True:
                        omni.kit.commands.execute("DeletePrims", paths=[markup.path])
                        if self._old_edit_data:
                            text_to_stage(self._stage, self._old_edit_data, Sdf.Path(MARKUP_ROOT_PRIM_PATH))
                    else:
                        ly = self._stage.GetEditTarget().GetLayer()
                        omni.kit.commands.execute(
                            "RemovePrimSpec", layer_identifier=ly.identifier, prim_spec_path=[markup.path]
                        )
                self._clear_markups()
                self._refresh_markups()
        self._same_layer = None

        # OM-51837 - Restoring selected prims now that the thumbnail is created.
        self._usd_selection.set_selected_prim_paths(self._selected_prim_paths, True)

        self.editing_markup = None
        self._old_edit_data = ""

        self._remove_markup_edit_hotkeys()
        window = ui.Workspace.get_window("Markups")
        if window is not None and window.visible:  # pragma: no cover
            window.focus()

    def delete_markup(self, markup: Optional[ViewportMarkup]) -> None:
        if self.__sidecar_data and self.__sidecar_data.read_only:  # pragma: no cover
            self.__sidecar_data.notify_read_only("Delete Markup")
            return
        if markup and self.can_edit_markup(markup):
            if self.current_markup == markup:
                self.current_markup = None

            with self.edit_context:
                self._remove_markup_icon_with_path(markup.path)
                self._markups.pop(markup.name)
                markup.delete()
                if self.__sidecar_data:  # pragma: no cover
                    self.__sidecar_data.save()
                for n in self._notifications:
                    if n.on_markup_deleted is not None:
                        n.on_markup_deleted(markup)

                if not self._markups and self._edit_end_fn:
                    self._edit_end_fn()

    def export_markups(self):
        if self._export_fn:
            self._export_fn()

    def recall_markup(
        self,
        markup: Optional[ViewportMarkup],
        without_camera=False,
        enable_settings: Optional[List[str]] = None,
        disable_settings: Optional[List[str]] = None,
        force: bool = False,
    ) -> None:
        if not markup:
            self.current_markup = None
            return

        if self.current_markup is not None:
            if markup == self.current_markup and not force:
                carb.log_info("On the same viewport markup. No need to switch the markup.")
                return

        markup.recall(without_camera=without_camera, enable_settings=enable_settings, disable_settings=disable_settings)
        self._timeline.set_current_time(markup.frame if markup.frame is not None else 0.0)
        self.current_markup = markup
        if self._open_callback:
            self._open_callback()

    def rename_markup(self, markup: ViewportMarkup, new_name: str) -> bool:
        if markup.name == new_name:
            return True
        if new_name in self._markups:
            carb.log_error(
                f"Can not rename viewport markup from '{markup.name}' to '{new_name}', the destination already exists"
            )
            return False

        if not Sdf.Path.IsValidPathString(new_name):  # pragma: no cover
            carb.log_warn(
                f"Can not rename viewport markup from '{markup.name}' to '{new_name}' as it's not a valid USD path"
            )
            return False

        self._markups.pop(markup.name)
        old_path = markup.path
        if markup.rename(new_name):
            self._markups[new_name] = markup

            # update the prim icon
            self._prim_icon.remove_prim_icon(old_path)
            self._prim_icon.add_prim_icon(markup.path, MARKUP_ICON_URL)

            self._on_markup_changed(markup)
            self._set_markup_icon_visibility()
            return True
        else:  # pragma: no cover
            carb.log_warn(f"Can not rename viewport markup from '{markup.name}' to '{new_name}'")
            return False

    def get_markups(self):
        return self._markups.values()

    def get_markup(self, name) -> Optional[ViewportMarkup]:
        if name in self._markups:
            return self._markups[name]
        return None

    def get_markup_from_prim_path(self, path: str) -> Optional[ViewportMarkup]:
        if self.is_markup_prim(path):
            sub_path = path[len(MARKUP_ROOT_PRIM_PATH + "/") :]
            name = sub_path.split("/")[0]
            return self.get_markup(name)
        return None

    def take_screenshot(self):
        if self.current_markup:
            return omni.kit.commands.execute("TakeMarkupScreenshot")

    def can_edit_markup(self, markup: ViewportMarkup, *, show_messages=True) -> bool:
        import omni.kit.notification_manager as nm

        if self.editing_markup:
            return self.editing_markup == markup

        if not markup.usd_prim:  # pragma: no cover
            return False
        if self._stage is None or not bool(self._stage):  # pragma: no cover
            return False
        at = markup.usd_prim.GetAttribute(LOCK_EDIT_ATTR)
        if at and at.Get():
            if show_messages:
                nm.post_notification("Markup locked by another user.")
            return False
        with self.edit_context:
            stage: Usd.Stage = self._stage
            root_layer: Sdf.Layer = cast(Sdf.Layer, stage.GetRootLayer())
            target_layer: Sdf.Layer = cast(Sdf.Layer, cast(Usd.EditTarget, stage.GetEditTarget()).GetLayer())

            if any(Sdf.Layer.IsAnonymousLayerIdentifier(layer.identifier) for layer in {root_layer, target_layer}):
                return True

            session_layer = stage.GetSessionLayer()
            strong_layers = [root_layer, session_layer]
            for sublayer_asset_path in session_layer.subLayerPaths:
                sublayer_absolute_path = session_layer.ComputeAbsolutePath(sublayer_asset_path)
                sublayer = Sdf.Find(sublayer_absolute_path)
                strong_layers.append(sublayer)
            if target_layer in strong_layers:
                return True

            if root_layer.GetPrimAtPath(markup.path) is not None:  # pragma: no cover
                if show_messages:
                    nm.post_notification(
                        "Cannot unlock markup, as it is overridden in a stronger layer.",
                        duration=3,
                        status=nm.NotificationStatus.WARNING,
                    )
                return False
            for layer_path in cast("list[str]", root_layer.subLayerPaths):
                layer: Sdf.Layer = cast(Sdf.Layer, Sdf.Layer.FindRelativeToLayer(root_layer, layer_path))
                if layer is None:
                    continue
                if layer == target_layer:
                    break
                if layer.GetPrimAtPath(markup.path):  # pragma: no cover
                    if show_messages:
                        nm.post_notification(
                            "Cannot unlock markup, as it is overridden in a stronger layer.",
                            duration=3,
                            status=nm.NotificationStatus.WARNING,
                        )
                    return False
            return True

    def _refresh_markups(self):
        self._markups.clear()
        self.editing_markup = None
        current_markup_name = self.current_markup.name if self.current_markup else None

        markup_root_path = MARKUP_ROOT_PRIM_PATH
        if self._stage is not None and bool(self._stage):  # pragma: no cover
            markup_root_node = self._stage.GetPrimAtPath(markup_root_path)
        else:
            markup_root_node = None
        if markup_root_node:
            for markup_prim in markup_root_node.GetChildren():
                markup = ViewportMarkup("", sidecar_data=self.__sidecar_data)
                if markup.create_from_prim(markup_prim):
                    self._markups[markup.name] = markup
                    self._prim_icon.add_prim_icon(markup.get_usd_prim_path(), MARKUP_ICON_URL)
                    self._prim_icon.set_icon_click_fn(markup.get_usd_prim_path(), self._recall_markup_from_prim_path)
                    # OMFP-2778 a markup icon can be added here due to a markup created by another user in a
                    # live session, even if markup icons are currently hidden here -- so set the visibility
                    # for the new icon explicitly:
                    self._set_markup_icon_visibility()
                else:  # pragma: no cover
                    carb.log_warn(f"Failed to create any viewport markup from {markup_prim.GetPath()}. Ignoring it.")

        if current_markup_name:
            if current_markup_name not in self._markups:  # pragma: no cover
                self.current_markup = None

        for n in self._notifications:
            n.on_reset()

    def _clear_markups(self):
        self._markups.clear()
        # OM-84954
        # Clearing the prim_icon interface is bad news for all other consumers of the extension, as it is a shared model
        # Much better to only remove the icons we directly care about.
        icon_model = self._prim_icon.get_model()
        if icon_model:
            to_remove = {
                prim_path for prim_path in icon_model.get_prim_paths() if prim_path.startswith(MARKUP_ROOT_PRIM_PATH)
            }
            for pth in to_remove:
                self._prim_icon.remove_prim_icon(pth)

        self.current_markup = None
        for n in self._notifications:
            n.on_reset()
        if self._edit_end_fn:
            self._edit_end_fn()

    def _create_markup(self, markup_name: str, *, trigger_edit_mode: bool = True):
        with self.edit_context:
            _, markup = omni.kit.commands.execute(
                "CreateMarkupEntry",
                entry_name=markup_name,
                on_create_fn=self._on_markup_created,
                on_undo_fn=self.delete_markup,
                sidecar_data=self.__sidecar_data,
            )
            markup.frame = self._timeline.get_current_time()

            self._markups[markup_name] = markup
            if trigger_edit_mode:
                # Using an Attribute as a semaphore for live.
                at = markup.usd_prim.GetAttribute(LOCK_EDIT_ATTR)
                if not at:
                    at = markup.usd_prim.CreateAttribute(LOCK_EDIT_ATTR, Sdf.ValueTypeNames.Bool)
                at.Set(True)
                self.current_markup = markup
                self.editing_markup = markup
                if self._edit_state_change_fn:
                    self._edit_state_change_fn(True)
                if self._open_callback:
                    self._open_callback()

    def _on_markup_created(self, markup: ViewportMarkup):
        if markup:
            if self.__sidecar_data:  # pragma: no cover
                self.__sidecar_data.save()
            for n in self._notifications:
                n.on_markup_created(markup)

    def _on_stage_opened(self):
        self._stage = self._usd_context.get_stage()
        self._markup_usd = None
        self.__register_stage_update()
        self.current_markup = None
        self._refresh_markups()
        self._set_markup_icon_visibility()

    def _on_stage_closing(self):
        # OM-53317: exit current markup to avoid crash when new stage
        if self._current_markup:
            self.editing_markup = None
            self.current_markup = None
        self.__deregister_stage_update()

    def _on_stage_closed(self):
        self._stage = cast(Usd.Stage, None)
        self._clear_markups()

    def _recall_markup_from_prim_path(self, prim_path: str):
        markup = self.get_markup_from_prim_path(prim_path)
        if markup:
            self.recall_markup(markup)

    def _show_markup_icons(self):
        markup_root_path = MARKUP_ROOT_PRIM_PATH
        if self._stage is not None and bool(self._stage):
            markup_root_node = self._stage.GetPrimAtPath(markup_root_path)
            if markup_root_node:
                for child in markup_root_node.GetChildren():
                    self._prim_icon.show_prim_icon(child.GetPrimPath().pathString)

    def _hide_markup_icons(self):
        markup_root_path = MARKUP_ROOT_PRIM_PATH
        if self._stage is not None and bool(self._stage):
            markup_root_node = self._stage.GetPrimAtPath(markup_root_path)
            if markup_root_node:
                for child in markup_root_node.GetChildren():
                    self._prim_icon.hide_prim_icon(child.GetPrimPath().pathString)

    def _remove_markup_icon_with_path(self, markup_path):
        markup_root_path = MARKUP_ROOT_PRIM_PATH
        if self._stage is not None and bool(self._stage):
            markup_root_node = self._stage.GetPrimAtPath(markup_root_path)
            if markup_root_node:
                for child in markup_root_node.GetChildren():
                    if markup_path == child.GetPrimPath().pathString:
                        self._prim_icon.remove_prim_icon(markup_path)
                        break

    def _on_visibility_setting_changed(self):
        self._set_markup_icon_visibility()

    def _set_markup_icon_visibility(self):
        if self._is_markup_icon_visible():
            self._show_markup_icons()
        else:
            self._hide_markup_icons()

    def _is_markup_icon_visible(self) -> int:
        return self._settings.get_as_int(SETTINGS_MARKUP_SHOW_ICONS) or 0

    def _on_markup_changed(self, markup):
        for n in self._notifications:
            if n.on_markup_changed is not None:
                n.on_markup_changed(markup)
        if self.__sidecar_data:  # pragma: no cover
            self.__sidecar_data.save()

    def _get_element_data_dict(
        self,
        element_style,
        text,
        points,
        element_type,
        shape_type,
        color,
        pixel_size=None,
    ):
        data = {}
        if element_style is not None:
            data["style"] = (Sdf.ValueTypeNames.String, str(element_style))
        if text is not None:
            data["text"] = (Sdf.ValueTypeNames.String, str(text))
        if points is not None:
            data["points"] = (Sdf.ValueTypeNames.Float2Array, deepcopy(points))
        if element_type is not None:
            data["type"] = (Sdf.ValueTypeNames.String, element_type)
        if shape_type is not None:
            data["shape_type"] = (Sdf.ValueTypeNames.String, shape_type)
        if color is not None:
            data["hex_color"] = (Sdf.ValueTypeNames.Int, color)
        if pixel_size is not None:
            data["pixel_size"] = (Sdf.ValueTypeNames.Float2, pixel_size)
        return data

    def set_open_callback(self, cb):
        self._open_callback = cb

    def get_markup_prim_path(self, name):
        return MARKUP_ROOT_PRIM_PATH + "/" + name

    def refresh_stage(self):
        self._markup_usd = MarkupUsd(sidecar_data=self.__sidecar_data)

    def get_all_markup_names(self):
        markups = []
        markup_root = self._getMarkupUSD().get_prim(MARKUP_ROOT_PRIM_PATH, False)

        if markup_root:
            for child in markup_root.GetChildren():
                markups.append(child.GetName())

        return markups

    def get_markup_name(self, prim_path: str):
        markup = self.get_markup_from_prim_path(prim_path)
        return markup.name if markup else prim_path.split("/")[1]

    def open_markup(self, name):
        if name != "":
            markup_prim_path = self.get_markup_prim_path(name)
            markup = self._getMarkupUSD().get_prim(markup_prim_path, False)

            if markup:
                carb.log_info(f"[MarkupToolElementDrawer] open markup {name}")
                self._recall_markup_from_prim_path(markup_prim_path)
            else:  # pragma: no cover
                carb.log_warn(f"[MarkupToolElementDrawer] can't find markup {name}")
                return False
        else:  # pragma: no cover
            return False

        return True

    def add_element(
        self,
        start_x,
        start_y,
        end_x,
        end_y,
        element_type,
        element_style,
        text=None,
        points=None,
        shape_type=None,
        color=None,
        pixel_size=None,
    ):
        # NOTE: omitting element_type in the data dict here; the creation command sets it directly.
        data = self._get_element_data_dict(element_style, text, points, None, shape_type, color, pixel_size=pixel_size)
        with self.edit_context:
            rect = (start_x, start_y, end_x, end_y)
            _, name = omni.kit.commands.execute(
                "CreateMarkupElement",
                markup=self.current_markup.path,
                element_type=element_type,
                rect=(Sdf.ValueTypeNames.Float4, rect),
                **data,
            )
            return name

    def remove_element(self, name: str):
        with self.edit_context:
            if self.current_markup is None:  # pragma: no cover
                return
            omni.kit.commands.execute("DeleteMarkupElement", element_name=name)

    def update_element_pos(self, element_name, start_x, start_y, end_x, end_y):
        with self.edit_context:
            if self.current_markup is None:  # pragma: no cover
                return
            data = {
                "rect": (Sdf.ValueTypeNames.Float4, (start_x, start_y, end_x, end_y)),
            }
            viewport_rect = self._settings.get("/persistent/exts/omni.kit.tool.markup/viewport_rect")
            if viewport_rect is not None:  # pragma: no cover
                dx = (end_x - start_x) / 100.0
                dy = (end_y - start_y) / 100.0
                viewport_size = (viewport_rect[2] - viewport_rect[0], viewport_rect[3] - viewport_rect[1])
                data["pixel_size"] = (Sdf.ValueTypeNames.Float2, (viewport_size[0] * dx, viewport_size[1] * dy))
            element_path = f"{self.current_markup.path}/{element_name}"
            omni.kit.commands.execute("UpdateMarkupElement", element=element_path, **data)

    def update_element_attrs(
        self, element_name, element_style=None, text=None, points=None, ele_type=None, shape_type=None, color=None
    ):
        with self.edit_context:
            if self.current_markup is None:
                return
            element_path = f"{self.current_markup.path}/{element_name}"
            data = self._get_element_data_dict(element_style, text, points, ele_type, shape_type, color)
            omni.kit.commands.execute("UpdateMarkupElement", element=element_path, **data)

    def get_element_attr(self, element_name, attr, default_value):
        if self.current_markup is None:
            return None
        element_path = f"{self.current_markup.path}/{element_name}"
        element_prim = self._getMarkupUSD().get_prim(element_path)
        return self._getMarkupUSD().get_prim_attribute(element_prim, attr, default_value)

    def _getMarkupUSD(self):
        if self._markup_usd is None:
            self._markup_usd = MarkupUsd(sidecar_data=self.__sidecar_data)
        return self._markup_usd

    def get_markup_elements(self):
        elements = []
        if self.current_markup is not None:
            markup = self.current_markup.usd_prim
            if markup:
                for child in markup.GetChildren():  # type: ignore
                    if child.IsA(UsdGeom.Camera) or child.HasAttribute("projection"):
                        continue
                    elements.append(child)
        return elements

    def lock_camera(self, camera_path: str) -> None:
        self._locked_camera_path = camera_path
        if not self._locked_camera_path:
            return
        if self._stage is None or not bool(self._stage):  # pragma: no cover
            return
        prim: Usd.Prim = self._stage.GetPrimAtPath(self._locked_camera_path)  # type: ignore
        prev = False
        if prim.HasAttribute(LOCK_CAMERA_ATTR):
            prev = prim.GetAttribute(LOCK_CAMERA_ATTR).Get()

        # skip if already locked
        if prev:
            return

        with omni.kit.undo.group():

            omni.kit.commands.execute(
                "ChangePropertyCommand",
                prop_path=prim.GetPath().AppendProperty(LOCK_CAMERA_ATTR),
                value=True,
                prev=prev,
                timecode=Usd.TimeCode.Default(),
                type_to_create_if_not_exist=Sdf.ValueTypeNames.Bool,
            )

            vp = get_active_viewport()
            if hasattr(vp, "legacy_window"):  # pragma: no cover
                context = omni.usd.get_context()
                omni.kit.commands.execute("LockSpecsCommand", usd_context=context, spec_paths=self._locked_camera_path)

    def unlock_camera(self):
        if not self._locked_camera_path:
            return
        if self._stage is None or not bool(self._stage):  # pragma: no cover
            return
        prim: Usd.Prim = self._stage.GetPrimAtPath(self._locked_camera_path)  # type: ignore
        with omni.kit.undo.group():

            omni.kit.commands.execute(
                "RemovePropertyCommand", prop_path=prim.GetPath().AppendProperty(LOCK_CAMERA_ATTR)
            )

            context = omni.usd.get_context()
            if context.get_stage_state() == omni.usd.StageState.OPENED:
                # OM-53317: when closing stage, donot need to unlock
                omni.kit.commands.execute(
                    "UnlockSpecsCommand", usd_context=context, spec_paths=self._locked_camera_path
                )

        self._locked_camera_path = ""

    def __register_display_setting(self):
        try:
            from omni.kit.viewport.menubar.core import CategoryStateItem
            from omni.kit.viewport.menubar.display import get_instance as get_display_instance

            inst = get_display_instance()
            self._markup_viewport_item = CategoryStateItem("Markup", setting_path=SETTINGS_MARKUP_SHOW_ICONS)  # type: ignore
            inst.register_custom_category_item("Show By Type", self._markup_viewport_item)
        except ImportError:  # pragma: no cover
            self._markup_viewport_item = None
        pass

    def __deregister_display_setting(self):  # pragma: no cover
        try:
            from omni.kit.viewport.menubar.display import get_instance as get_display_instance

            inst = get_display_instance()
            if self._markup_viewport_item:
                inst.deregister_custom_category_item("Show By Type", self._markup_viewport_item)  # type: ignore
        except ImportError:
            pass
        pass

    def show_preference(self, x: float, y: float):  # pragma: no cover
        # This will show prefences once those exist for markup.
        # In the meantime it keeps the APIs in sync with waypoing -Bob
        pass

    def set_selection_command(self, fn):
        """Set a command to make a selection on the MarkupListWindow."""
        self._selection_command = fn

    def select_markup_in_list_window(self, markup):
        if self._selection_command:
            self._selection_command(markup)

    def _register_hotkeys(self):
        enabled = self._settings.get_as_bool(SETTINGS_MARKUP_ENABLE_HOTKEYS) or False
        if self._hotkey_reg is None or self._action_reg is None:
            try:
                import omni.kit.actions.core
                import omni.kit.hotkeys.core

                self._hotkey_reg = omni.kit.hotkeys.core.get_hotkey_registry()
                self._action_reg = omni.kit.actions.core.get_action_registry()
                self._hotkey_context = omni.kit.hotkeys.core.get_hotkey_context()
            except:  # pragma: no cover
                carb.log_warn("Failed to import hotkeys extensions, markup hotkeys are disabled.")
                return
        if enabled:
            try:
                from omni.kit.hotkeys.core import HotkeyFilter
            except:  # pragma: no cover
                carb.log_warn("Failed to import hotkeys extensions, markup hotkeys are disabled.")
                return
            key = self._get_hotkey(SETTINGS_MARKUP_CREATE_HOTKEY, "M")
            self._register_hotkey("create", key, _create_markup)

            filter = HotkeyFilter(context=MARKUP_WINDOW_FOCUS_CONTEXT)
            key = self._get_hotkey(SETTINGS_MARKUP_NEXT_HOTKEY, "RIGHT")
            self._register_hotkey("next", key, _next_markup, filter=filter)
            key = self._get_hotkey(SETTINGS_MARKUP_PREVIOUS_HOTKEY, "LEFT")
            self._register_hotkey("previous", key, _previous_markup, filter=filter)
            key = self._get_hotkey(SETTINGS_MARKUP_CANCEL_HOTKEY, "ESCAPE")
            self._register_hotkey("deselect", key, _deselect_markup, filter=filter)
            key = self._get_hotkey(SETTINGS_MARKUP_DELETE_HOTKEY, "DEL")
            self._register_hotkey("delete-selected", key, _delete_markup, filter=filter)

            filter = HotkeyFilter(context=MARKUP_EDIT_CONTEXT)
            key = self._get_hotkey(SETTINGS_MARKUP_APPLY_HOTKEY, "ENTER")
            self._register_hotkey("apply", key, _apply_markup, filter=filter)
            key = self._get_hotkey(SETTINGS_MARKUP_CANCEL_HOTKEY, "ESCAPE")
            self._register_hotkey("cancel", key, _cancel_markup_edit, filter=filter)

            key = self._get_hotkey(SETTINGS_MARKUP_DELETE_HOTKEY, "DEL")
            self._register_hotkey("delete", key, _delete_markup, filter=filter)

            key = self._get_hotkey(SETTINGS_MARKUP_NEXT_TOOL_HOTKEY, "PAGE_UP")
            self._register_hotkey("next-tool", key, _next_tool, filter=filter)
            key = self._get_hotkey(SETTINGS_MARKUP_PREVIOUS_TOOL_HOTKEY, "PAGE_DOWN")
            self._register_hotkey("previous-tool", key, _previous_tool, filter=filter)
        else:
            self._deregister_all_hotkeys()

    def _register_hotkey(self, name: str, key: str, callback, filter=None) -> bool:
        enabled = self._settings.get_as_bool(SETTINGS_MARKUP_ENABLE_HOTKEYS) or False
        if not enabled or self._hotkey_reg is None or self._action_reg is None:  # pragma: no cover
            return False

        if name in self._actions.keys() and name in self._hotkeys.keys():  # pragma: no cover
            return False

        action_name = self._ext_name + "-" + name
        if name in self._actions.keys():  # pragma: no cover
            action = self._actions[name]
        else:
            display_name = "markup::" + name
            action = self._action_reg.register_action(self._ext_name, action_name, callback, display_name)
            self._actions[name] = action
        if name not in self._hotkeys.keys():
            hotkey = self._hotkey_reg.register_hotkey(self._ext_name, key, self._ext_name, action_name, filter=filter)
            self._hotkeys[name] = hotkey

        return True

    def _deregister_all_hotkeys(self):  # pragma: no cover
        if self._action_reg and self._hotkey_reg and self._ext_name is not None:
            self._hotkey_reg.deregister_all_hotkeys_for_extension(self._ext_name)
            self._action_reg.deregister_all_actions_for_extension(self._ext_name)
            self._actions = {}
            self._hotkeys = {}

    def _get_hotkey(self, setting_path: str, default: str) -> str:
        hotkey = self._settings.get_as_string(setting_path)
        if hotkey is None or hotkey == "":
            self._settings.set_string(setting_path, default)
            return default
        return hotkey

    def _on_hotkeys_enabled_changed(self, item, event):
        self._register_hotkeys()

    def _add_markup_edit_hotkeys(self):
        enabled = self._settings.get_as_bool(SETTINGS_MARKUP_ENABLE_HOTKEYS) or False
        if enabled and self._hotkey_context:
            self._hotkey_context.push(MARKUP_EDIT_CONTEXT)

    def _remove_markup_edit_hotkeys(self):
        if self._hotkey_context is not None:
            all_contexts = []
            while (top_context := self._hotkey_context.get()) is not None:
                all_contexts.append(top_context)
                self._hotkey_context.pop()
            for c in reversed(all_contexts):
                if c != MARKUP_EDIT_CONTEXT:
                    self._hotkey_context.push(c)


def _next_markup():
    try:
        from .widgets.playbar import MARKUP_PLAY_NEXT_EVENT
    except:  # pragma: no cover
        return

    get_eventdispatcher().dispatch_event(MARKUP_PLAY_NEXT_EVENT, {})


def _previous_markup():
    try:
        from .widgets.playbar import MARKUP_PLAY_PREVIOUS_EVENT
    except:  # pragma: no cover
        return

    get_eventdispatcher().dispatch_event(MARKUP_PLAY_PREVIOUS_EVENT, {})


def _create_markup():
    try:
        from .widgets.list_window import MarkupListWindow
    except:  # pragma: no cover
        return
    markups = get_instance()
    if markups and markups.editing_markup is None:
        markups.create_markup()


def _apply_markup():
    markups = get_instance()
    if markups and markups.current_markup:
        markups.end_edit_markup(markups.current_markup, save=True)


def _deselect_markup():
    settings = carb.settings.get_settings()
    edited_markup = settings.get_as_string(SETTINGS_MARKUP_EDITING)
    if edited_markup is None or edited_markup == "":
        markups = get_instance()
        if markups:
            markups.current_markup = None


def _cancel_markup_edit():
    markups = get_instance()
    if markups and markups.current_markup:
        markups.end_edit_markup(markups.current_markup, save=False)


def _delete_markup():
    settings = carb.settings.get_settings()
    current_markup = settings.get_as_string(SETTINGS_MARKUP_ACTIVE)
    markups = get_instance()

    if current_markup and current_markup != "" and markups:

        async def __delete(name: str):
            await omni.kit.app.get_app().next_update_async()  # type: ignore
            markup = get_instance().get_markup(name)
            markups.delete_markup(markup)

        run_coroutine(__delete(current_markup))


def _next_tool():
    settings = carb.settings.get_settings()
    current_tool = settings.get(SETTINGS_MARKUP_CURRENT_TOOL)
    try:
        index = MARKUP_TOOL_ORDER.index(current_tool)
    except ValueError:  # pragma: no cover
        return
    index = (index + 1) % len(MARKUP_TOOL_ORDER)
    settings.set_string(SETTINGS_MARKUP_CURRENT_TOOL, MARKUP_TOOL_ORDER[index])


def _previous_tool():
    settings = carb.settings.get_settings()
    current_tool = settings.get(SETTINGS_MARKUP_CURRENT_TOOL)
    try:
        index = MARKUP_TOOL_ORDER.index(current_tool)
    except ValueError:  # pragma: no cover
        return
    index = index - 1
    settings.set_string(SETTINGS_MARKUP_CURRENT_TOOL, MARKUP_TOOL_ORDER[index])
