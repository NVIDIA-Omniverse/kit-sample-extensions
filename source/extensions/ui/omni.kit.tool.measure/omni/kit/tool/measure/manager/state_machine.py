# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

__all__ = ["StateMachine"]

from typing import Callable, Dict, Type, Union, cast

import carb.eventdispatcher
import omni.kit.usd as oku
from carb import log_error
from carb.events import IEvent
from carb.input import (
    DeviceType,
    GamepadEvent,
    InputEvent,
    KeyboardEvent,
    KeyboardEventType,
    KeyboardInput,
    MouseEvent,
    MouseEventType,
    acquire_input_interface,
)
from omni import ui
from omni.kit.usd.layers import (
    LayerEventPayload,
    LayerEventType,
    Layers,
    get_layer_event_payload,
    get_layers,
)
from omni.usd import StageEventType, get_context
from pxr import Tf, Usd

from ..common import MeasureCreationState, MeasureEditState, MeasureMode, MeasureState, UserSettings

KEYBOARD_INPUTS = [KeyboardInput.ESCAPE, KeyboardInput.DEL, KeyboardInput.ENTER]

LastMeasureMode: MeasureMode = MeasureMode.AREA


class StateMachineEvent:
    """
    Handler for events within the state machine
    """

    def __init__(self, event_type: Type[Callable[..., None]]):
        self._event_type = event_type
        self._subscriber_id: int = 1
        self._event_subscribers: Dict[int, event_type] = {}

    def subscribe(self, callback: Type[Callable[..., None]]) -> int:
        id = self._subscriber_id
        self._subscriber_id += 1
        self._event_subscribers[id] = callback
        return id

    def unsubscribe(self, id: int) -> None:
        self._event_subscribers.pop(id, None)

    def _run(self, *args, **kwargs):
        for fn in self._event_subscribers.values():
            fn(*args, **kwargs)

    __call__ = _run


class StateMachineStageListenerManager:
    def __init__(self):
        self.__subscriber_id: int = 1
        self.__events: Dict[int, Callable] = {}

    def reset(self):
        self.__events = {}

    def subscribe(self, callback: Callable):
        id = self.__subscriber_id
        self.__subscriber_id += 1
        self.__events[id] = callback
        return id

    def unsubscribe(self, id: int) -> None:
        self.__events.pop(id, None)

    def exec_event(self, notice):
        for fn in self.__events.values():
            fn(notice)


class StateMachineKeyPressedManager:
    def __init__(self):
        self.__subscriber_id: int = 1
        self.__events: Dict[int, Callable[[KeyboardInput], None]] = {}

    def reset(self):
        self.__events = {}

    def subscribe(self, callback: Callable[[KeyboardInput], None]):
        id = self.__subscriber_id
        self.__subscriber_id += 1
        self.__events[id] = callback
        return id

    def unsubscribe(self, id: int) -> None:
        self.__events.pop(id, None)

    def exec_event(self, key: KeyboardInput):
        for fn in self.__events.values():
            fn(key)


class StateMachineStageEventManager:
    def __init__(self):
        self.__events: Dict[StageEventType, StateMachineEvent] = {
            StageEventType.OPENING: StateMachineEvent(Callable),
            StageEventType.OPENED: StateMachineEvent(Callable),
            StageEventType.CLOSING: StateMachineEvent(Callable),
            StageEventType.CLOSED: StateMachineEvent(Callable),
            StageEventType.SAVED: StateMachineEvent(Callable),
            StageEventType.SELECTION_CHANGED: StateMachineEvent(Callable),
        }

    def subscribe(self, callback: Callable, event_type: StageEventType) -> int:
        return self.__events[event_type].subscribe(callback)

    def unsubscribe(self, id: int, event_type: StageEventType) -> None:
        self.__events[event_type].unsubscribe(id)

    def exec_event(self, event: carb.eventdispatcher.Event) -> None:
        event_type = get_context().stage_event_type(event.event_name)
        stage_event = self.__events.get(event_type, lambda *args, **kwargs: None)
        stage_event()


class StateMachineLegacyLayerEventManager:
    def __init__(self):
        self.__events: Dict[int, StateMachineEvent] = {
            int(LayerEventType.EDIT_TARGET_CHANGED): StateMachineEvent(Callable[[LayerEventPayload, bool], None]),
            int(LayerEventType.LIVE_SESSION_STATE_CHANGED): StateMachineEvent(
                Callable[[LayerEventPayload, bool], None]
            ),
            # int(LayerEventType.LIVE_SESSION_JOINING): StateMachineEvent(Callable[[LayerEventPayload, bool], None]),  # Kit 105.1
            int(LayerEventType.LIVE_SESSION_USER_JOINED): StateMachineEvent(Callable[[LayerEventPayload, bool], None]),
            int(LayerEventType.LIVE_SESSION_USER_LEFT): StateMachineEvent(Callable[[LayerEventPayload, bool], None]),
            int(LayerEventType.PRIM_SPECS_CHANGED): StateMachineEvent(Callable[[LayerEventPayload, bool], None]),
        }

    def subscribe(self, callback: Callable[["LayerEventPayload", bool], None], event_type: LayerEventType) -> int:
        if self.__events.get(int(event_type), None) == None:
            log_error(f"{event_type} is not a supported event for StateMachineLayerEventManager.")
            return -1

        return self.__events[int(event_type)].subscribe(callback)

    def unsubscribe(self, id: int, event_type: LayerEventType) -> None:
        self.__events[int(event_type)].unsubscribe(id)

    def exec_event(self, event: IEvent, live_session: bool) -> None:
        payload = get_layer_event_payload(event)
        if not payload or payload.event_type is None:
            return

        stage_event = self.__events.get(int(payload.event_type), lambda *args, **kwargs: None)
        stage_event(payload, live_session)


class StateMachineLayerEventManager:
    def __init__(self):
        self.__events: Dict[LayerEventType, StateMachineEvent] = {
            LayerEventType.EDIT_TARGET_CHANGED: StateMachineEvent(Callable[[LayerEventPayload, bool], None]),
            LayerEventType.LIVE_SESSION_STATE_CHANGED: StateMachineEvent(Callable[[LayerEventPayload, bool], None]),
            # int(LayerEventType.LIVE_SESSION_JOINING): StateMachineEvent(Callable[[LayerEventPayload, bool], None]),  # Kit 105.1
            LayerEventType.LIVE_SESSION_USER_JOINED: StateMachineEvent(Callable[[LayerEventPayload, bool], None]),
            LayerEventType.LIVE_SESSION_USER_LEFT: StateMachineEvent(Callable[[LayerEventPayload, bool], None]),
            LayerEventType.PRIM_SPECS_CHANGED: StateMachineEvent(Callable[[LayerEventPayload, bool], None]),
        }

    def subscribe(self, callback: Callable[["LayerEventPayload", bool], None], event_type: LayerEventType) -> int:
        if self.__events.get(event_type, None) == None:
            log_error(f"{event_type} is not a supported event for StateMachineLayerEventManager.")
            return -1

        return self.__events[event_type].subscribe(callback)

    def unsubscribe(self, id: int, event_type: LayerEventType) -> None:
        self.__events[event_type].unsubscribe(id)

    def exec_event(self, event: carb.eventdispatcher.Event, live_session: bool) -> None:
        payload = get_layer_event_payload(event)
        if not payload or payload.event_type is None:
            return

        stage_event = self.__events.get(payload.event_type, lambda *args, **kwargs: None)
        stage_event(payload, live_session)


class StateMachine:
    # TODO: Tool state and Tool mode need to have a global state change as well for cases of
    # being in a create mode, but switching to another mode in create. Currently resetting to default before swap works.
    __state_type = Callable[[MeasureState, MeasureMode], None]
    __create_state_changed = Callable[[MeasureCreationState], None]
    __mode_type = Callable[[MeasureMode], None]

    """
        The Measure Tool State Machine.
    """

    def __singleton_init__(self):

        self.__latest_layer_event = hasattr(oku.layers, "layer_event_name")

        # Carb Input
        self._input = acquire_input_interface()
        self._input_sub_id = self._subscribe_input()

        self._subtool_live_session_notify: bool = True
        self._tool_state: ui.SimpleIntModel = ui.SimpleIntModel()  # MeasureState
        self._tool_mode: ui.SimpleIntModel = ui.SimpleIntModel()  # MeasureMode
        self._tool_creation_state: ui.SimpleIntModel = ui.SimpleIntModel()

        self._on_state_changed_evt: StateMachineEvent = StateMachineEvent(event_type=self.__state_type)
        self._on_create_state_changed_evt: StateMachineEvent = StateMachineEvent(event_type=self.__create_state_changed)
        self._on_create_evt: StateMachineEvent = StateMachineEvent(event_type=self.__mode_type)
        self._on_edit_evt: StateMachineEvent = StateMachineEvent(event_type=self.__mode_type)

        self._stage_listener_manager = StateMachineStageListenerManager()
        self._stage_event_manager = StateMachineStageEventManager()
        self._legacy_layer_event_manager = StateMachineLegacyLayerEventManager()
        self._layer_event_manager = StateMachineLayerEventManager()
        self._key_pressed_manager = StateMachineKeyPressedManager()
        self._reset_sub = self._stage_event_manager.subscribe(self.reset_state_to_default, StageEventType.OPENED)

        ed = carb.eventdispatcher.get_eventdispatcher()

        # Stage event registering
        self.__stage_event_sub = []
        fixed_event_types = [
            StageEventType.OPENING,
            StageEventType.OPENED,
            StageEventType.CLOSING,
            StageEventType.CLOSED,
            StageEventType.SAVING,
            StageEventType.SELECTION_CHANGED,
        ]

        for event_type in fixed_event_types:
            event_str = get_context().stage_event_name(event_type)
            sub = ed.observe_event(
                observer_name=f"omni.kit.tool.measure::StateMachine:StageEvent:{event_type.name.lower()}",
                event_name=event_str,
                on_event=self.__on_stage_event,
            )
            self.__stage_event_sub.append(sub)

        # Layers
        self.__layers = cast(Layers, get_layers(get_context()))
        self.__layer_event_sub = []
        self.__legacy_layer_event_sub = None

        if self.__latest_layer_event:
            # Layers 2.0
            fixed_layer_events = [
                LayerEventType.EDIT_TARGET_CHANGED,
                LayerEventType.LIVE_SESSION_STATE_CHANGED,
                # LayerEventType.LIVE_SESSION_JOINING,  # Kit 105.1
                LayerEventType.LIVE_SESSION_USER_JOINED,
                LayerEventType.LIVE_SESSION_USER_LEFT,
                LayerEventType.PRIM_SPECS_CHANGED,
            ]

            for event_type in fixed_layer_events:
                event_str = oku.layers.layer_event_name(event_type)
                sub = ed.observe_event(
                    observer_name=f"omni.kit.tool.measure::StateMachine:LayerEvent:{event_type.name.lower()}",
                    event_name=event_str,
                    on_event=self.__on_layer_event,
                )
                self.__layer_event_sub.append(sub)
        else:
            # Legacy Layer Subscription
            self.__legacy_layer_event_sub = self.__layers.get_event_stream().create_subscription_to_pop(
                self.__on_legacy_layer_event, name="omni.kit.tool.measure::StateMachine:LegacyLayerEvent"
            )
        self._tool_state.add_value_changed_fn(self._on_tool_state_changed)
        self._tool_mode.add_value_changed_fn(self._on_tool_mode_changed)
        self._tool_creation_state.add_value_changed_fn(self._on_tool_creation_state_changed)

        self.__stage_listener = Tf.Notice.Register(
            Usd.Notice.ObjectsChanged, self.__on_stage_objects_changed, get_context().get_stage()
        )

    def __new__(cls):
        if not hasattr(cls, "_instance"):
            cls._instance = super().__new__(cls)
            cls._instance.__singleton_init__()
        return cls._instance

    def __repr__(self) -> str:
        return f"StateMachine<{self.tool_state}, {self.tool_mode}>"

    @property
    def tool_state(self) -> MeasureState:
        return MeasureState(self._tool_state.as_int)

    @tool_state.setter
    def tool_state(self, state: MeasureState) -> None:
        self._tool_state.as_int = state.value

    @property
    def tool_mode(self) -> MeasureMode:
        return MeasureMode(self._tool_mode.as_int)

    @tool_mode.setter
    def tool_mode(self, mode: MeasureMode) -> None:
        self._tool_mode.as_int = mode.value

    @property
    def tool_creation_state(self) -> MeasureCreationState:
        return MeasureCreationState(self._tool_creation_state.as_int)

    @tool_creation_state.setter
    def tool_creation_state(self, state: MeasureCreationState) -> None:
        self._tool_creation_state.as_int = state.value

    def set_creation_state(self, mode: MeasureMode) -> None:
        """
        Sets the creation state of the input mode

        Args:
            mode (MeasureMode): The tool mode.
        """
        self.reset_state_to_default()
        self.tool_mode = mode
        self.tool_state = MeasureState.CREATE
        UserSettings().session.startup_tool = mode

    def set_next_creation_state(self) -> None:
        """
        Sets the creation state of the input mode to the next one
        """
        tool_int = self.tool_mode.value
        tool_int = (tool_int + 1) % (LastMeasureMode.value + 1)
        self.set_creation_state(MeasureMode(tool_int))

    def set_previous_creation_state(self) -> None:
        """
        Sets the creation state of the input mode to the previous one
        """
        tool_int = self.tool_mode.value
        tool_int = tool_int - 1
        if tool_int < 0:
            tool_int = LastMeasureMode.value
        self.set_creation_state(MeasureMode(tool_int))

    def set_edit_state(self, mode: MeasureMode) -> None:
        """
        Sets the edit state of the input mode

        Args:
            mode (MeasureMode): The tool mode.
        """
        self.reset_state_to_default()
        self.tool_mode = mode
        self.tool_state = MeasureState.EDIT

    def reset_state_to_default(self, is_current_tool: bool = True):
        """
        Resets the state machine.
        """
        # FIXME: Do not change order of reset - check _on_tool_state_changed
        self.tool_mode = MeasureMode.NONE
        self.tool_state = MeasureState.NONE

        if not is_current_tool:
            UserSettings().set_app_current_tool(measure_enabled=False)

    def add_tool_state_changed_fn(self, func: Callable[[MeasureState, MeasureMode], None]) -> int:
        """
        Adds the function to call for every time the tool state changes
        """
        id = self._on_state_changed_evt.subscribe(func)
        return id

    def add_tool_creation_state_changed_fn(self, func: Callable[[MeasureCreationState], None]) -> int:
        """
        Adds the function to call for every time the active tool creation state changes
        """
        id = self._on_create_state_changed_evt.subscribe(func)
        return id

    def add_on_create_mode_fn(self, func: Callable[[MeasureMode], None]) -> int:
        """
        Adds the function to call for ever time the tool state changes to MeasureMode.CREATE
        """
        return self._on_create_evt.subscribe(func)

    def add_on_edit_mode_fn(self, func: Callable[[MeasureMode], None]) -> int:
        """
        Adds the function to call for ever time the tool state changes to MeasureMode.EDIT
        """
        return self._on_edit_evt.subscribe(func)

    def _on_tool_state_changed(self, model: ui.AbstractValueModel):
        state = MeasureState(model.as_int)
        mode = self.tool_mode

        if state in [MeasureState.CREATE, MeasureState.EDIT]:
            # NOTE: This will occur when a subtool button is pressed.
            # When a tool is unchecked, measure_state will be NONE and this will not execute.
            from ..common import UserSettings

            UserSettings().set_app_current_tool()
            self._on_create_evt(mode) if state == MeasureState.CREATE else self._on_edit_evt(mode)

        # This will always be called, as its the global state change
        self._on_state_changed_evt(state, mode)

    def _on_tool_mode_changed(self, model: ui.AbstractValueModel):
        return

    def _on_tool_creation_state_changed(self, model: ui.AbstractValueModel):
        creation_state = MeasureCreationState(model.as_int)
        self._on_create_state_changed_evt(creation_state)

    # Stage Listener Logic
    def __on_stage_objects_changed(self, notice, stage):
        self._stage_listener_manager.exec_event(notice)

    def subscribe_to_stage_listener(self, callback: Callable) -> int:
        return self._stage_listener_manager.subscribe(callback)

    def unsubscribe_to_stage_listener(self, id: int) -> None:
        self._stage_listener_manager.unsubscribe(id)

    # Stage Event Logic
    def __on_stage_event(self, event: carb.eventdispatcher.Event) -> None:
        self._stage_event_manager.exec_event(event)

    def subscribe_to_stage_event(self, callback: Callable, event_type: StageEventType) -> int:
        """
        Adds a function to be called to the stage event stream by the event type.

        Args:
            callback (Callable): function to call
            event_type (StageEventType): The event type

        Returns:
            (int) Subscription ID
        """
        return self._stage_event_manager.subscribe(callback, event_type)

    def unsubscribe_to_stage_event(self, id: int, event_type: StageEventType) -> None:
        """
        Removes the subscription to the event stream.

        Args:
            id (int): Subscription ID
            event_type (StageEventType): The Event Type ID was subscribed to.
        """
        self._stage_event_manager.unsubscribe(id, event_type)

    # Layer Event Logic
    def __on_legacy_layer_event(self, event: IEvent) -> None:
        live_session: bool = self.__layers.get_live_syncing().is_in_live_session()
        self._legacy_layer_event_manager.exec_event(event, live_session)

    def __on_layer_event(self, event: carb.eventdispatcher.Event) -> None:
        live_session: bool = self.__layers.get_live_syncing().is_in_live_session()
        self._layer_event_manager.exec_event(event, live_session)

    def subscribe_to_layer_event(
        self, callback: Callable[["LayerEventPayload", bool], None], event_type: LayerEventType
    ) -> int:
        if self.__latest_layer_event:
            return self._layer_event_manager.subscribe(callback, event_type)
        return self._legacy_layer_event_manager.subscribe(callback, event_type)

    def unsubscribe_to_layer_event(self, id: int, event_type: LayerEventType) -> None:
        if self.__latest_layer_event:
            self._layer_event_manager.unsubscribe(id, event_type)
        else:
            self._legacy_layer_event_manager.unsubscribe(id, event_type)

    # Key Pressed Logic
    def _on_key_pressed(self, key: KeyboardInput) -> None:
        self._key_pressed_manager.exec_event(key)

    def subscribe_to_key_pressed_event(self, callback: Callable[[KeyboardInput], None]) -> int:
        return self._key_pressed_manager.subscribe(callback)

    def unsubscribe_to_key_pressed_event(self, id: int) -> None:
        self._key_pressed_manager.unsubscribe(id)

    # Carb Input Handling
    def _subscribe_input(self):
        return self._input.subscribe_to_input_events(self._on_input_event, order=0)

    def _unsubscribe_input(self):
        if self._input_sub_id:
            self._input.unsubscribe_to_input_events(self._input_sub_id)
            self._input_sub_id = None

    def _on_input_event(self, event: InputEvent, *_) -> bool:
        if event.deviceType == DeviceType.MOUSE:
            return self._on_mouse_event(event.event)
        elif event.deviceType == DeviceType.KEYBOARD:
            return self._on_keyboard_event(event.event)
        elif event.deviceType == DeviceType.GAMEPAD:
            return self._on_gamepad_event(event.event)
        return True

    def _on_mouse_event(self, event: Union[object, MouseEvent], *args, **kwargs) -> bool:
        if isinstance(event, MouseEvent):
            if event.type == MouseEventType.LEFT_BUTTON_DOWN:
                pass
        return True

    def _on_keyboard_event(self, event: Union[object, KeyboardEvent], *args, **kwargs) -> bool:
        if isinstance(event, KeyboardEvent) and event.input in KEYBOARD_INPUTS:
            if event.type == KeyboardEventType.KEY_RELEASE:
                self._on_key_pressed(event.input)
        return True

    def _on_gamepad_event(self, event: Union[object, GamepadEvent], *args, **kwargs) -> bool:
        if isinstance(event, GamepadEvent):
            pass
        return True

    def deinit(self) -> None:
        self.reset_state_to_default()

        self.__stage_event_sub.clear()
        self.__legacy_layer_event_sub = None
        self.__layer_event_sub.clear()

        self._unsubscribe_input()
