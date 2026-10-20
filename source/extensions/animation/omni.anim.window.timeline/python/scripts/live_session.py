## Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

import omni.kit.usd.layers as layers
import omni.timeline.live_session
import omni.ui as ui
import omni.usd


class TimelineLiveSession:
    def __init__(self, usd_context_name: str = ""):
        self._timeline_session = None
        self._on_listen_fns = set()
        self._presenter_user = None
        self._usd_context = omni.usd.get_context(usd_context_name)
        self._layers_event_subscription = (
            layers.get_layers(self._usd_context)
            .get_event_stream()
            .create_subscription_to_pop(self._on_layers_event, name="timeline_window_layer_sub")
        )

    def __del__(self):
        self._on_listen_fn.clear()
        self._layers_event_subscription = None
        if self._timeline_session:
            self._timeline_session.remove_presenter_changed_fn(self._on_presenter_changed)
            self._timeline_session.remove_enable_sync_changed_fn(self._on_enable_sync_changed)
            self._timeline_session = None

    # When a live session is joined, register callback for presenter changed events
    def _on_layers_event(self, event):
        payload = layers.get_layer_event_payload(event)
        if not payload:
            return

        # Only events from root layer session are handled.
        if not payload.is_layer_influenced(self._usd_context.get_stage_url()):
            return

        if payload.event_type == layers.LayerEventType.LIVE_SESSION_STATE_CHANGED:
            # Get the timeline session and register our own callback for presenter changed
            self._timeline_session = omni.timeline.live_session.get_timeline_session()
            if self._timeline_session is not None:
                if self._timeline_session.is_running():
                    # join session
                    self._timeline_session.add_presenter_changed_fn(self._on_presenter_changed)
                    self._timeline_session.add_enable_sync_changed_fn(self._on_enable_sync_changed)
                    self._toggle_listen()
                else:
                    # leave session
                    self._timeline_session.remove_presenter_changed_fn(self._on_presenter_changed)
                    self._timeline_session.remove_enable_sync_changed_fn(self._on_enable_sync_changed)
                    self._timeline_session = None
                    for listen_fn in self._on_listen_fns:
                        listen_fn(False, False)

    # Our callback that is called by the timeline sync extension when the presenter is changed.
    def _on_presenter_changed(self, user: layers.LiveSessionUser):
        self._presenter_user = user
        self._toggle_listen()

    def _on_enable_sync_changed(self, enabled: bool):
        self._toggle_listen()

    def register_status_changed_fn(self, listen_fn: callable):
        self._on_listen_fns.add(listen_fn)

    def deregister_status_changed_fn(self, listen_fn: callable):
        self._on_listen_fns.discard(listen_fn)

    def _toggle_listen(self):
        if self._timeline_session is not None:
            syncing = self._timeline_session.is_sync_enabled()
            presenter = self._timeline_session.am_i_presenter()
            for listen_fn in self._on_listen_fns:
                listen_fn(presenter, syncing)

    def am_i_presenter(self) -> bool:
        if self._timeline_session is not None:
            return self._timeline_session.am_i_presenter()
        return False

    def is_sync_enabled(self) -> bool:
        if self._timeline_session is not None:
            return self._timeline_session.is_sync_enabled()
        return False

    def get_presenter_user_name(self) -> str:
        if self._presenter_user:
            return self._presenter_user.user_name
        return ""

    def get_presenter_user_short_name(self) -> str:
        if self._presenter_user:
            return layers.get_short_user_name(self._presenter_user.user_name)
        return ""

    def get_presenter_user_color(self) -> ui.color:
        if self._presenter_user:
            return ui.color(*self._presenter_user.user_color)
        return ui.color("#000000")
