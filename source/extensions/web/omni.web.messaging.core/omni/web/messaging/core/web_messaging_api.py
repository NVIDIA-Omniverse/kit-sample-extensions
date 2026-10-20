## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

"""Web messaging API framework for Omniverse Kit extensions.

This module provides the WebMessagingAPI class, a framework for creating
incoming and outgoing message handlers that bridge Kit Python code with
web clients via WebRTC data channels. It manages message bus subscriptions
and event handling to enable bidirectional communication.

The framework supports:
    - Incoming handlers: Functions that process client messages
    - Outgoing handlers: Functions that send events to subscribed clients
    - Automatic cleanup: Proper resource management for all handlers
    - No web-side library dependency: Works with any WebRTC client

Example:
    from omni.web.messaging.core import WebMessagingAPI

    api = WebMessagingAPI()

    @api.incoming
    def my_handler(param: str):
        print(f"Received {param}")

    @api.outgoing
    def my_event(data: str):
        print(f"Sending {data}")
"""

from typing import Callable

import carb
import carb.eventdispatcher
import omni.kit.livestream.messaging as messaging


class WebMessagingAPI:
    """A class that facilitates WebRTC message handling in Kit applications.

    This class provides decorators to easily create incoming message handlers
    and outgoing message senders. It manages the lifecycle of message bus
    subscriptions and event handling.

    Methods:
        incoming: Decorator to register a function as an incoming message handler.
        outgoing: Decorator to register a function as an outgoing message sender.
        cleanup: Removes all subscriptions and event handlers.

    Example:
        from omni.web.messaging.core import WebMessagingAPI

        api = WebMessagingAPI()

        @api.incoming
        def handle_request(param: str):
            print(f"Received: {param}")

        @api.outgoing
        def send_event(data: str):
            print(f"Sending: {data}")

        # Call to send event
        api.send_event(data="hello")

        # Cleanup when done
        api.cleanup()
    """

    # Class-level reference counting for outgoing events (shared across all instances)
    _outgoing_event_refcount: dict[str, int] = {}

    def __init__(self) -> None:
        """Initialize the WebMessagingAPI instance."""
        self._subscriptions: dict[str, carb.eventdispatcher.ISubscription] = {}
        self._registered_outgoing_events: list[str] = []
        self._dispatcher = carb.eventdispatcher.get_eventdispatcher()

    def __del__(self) -> None:
        """Clean up resources when this instance is deleted."""
        self.cleanup()

    def cleanup(self) -> None:
        """Remove all subscriptions and event handlers.

        This method ensures proper cleanup of resources by clearing all
        event subscriptions (Events 2.0 subscriptions clean up automatically)
        and unregistering the outgoing events that were registered by this
        specific instance.

        Uses reference counting to ensure events are only unregistered when
        no other WebMessagingAPI instances are using them.
        """
        # Events 2.0 subscriptions clean up automatically when they go out of scope
        self._subscriptions = {}

        # Unregister outgoing events with reference counting
        for event_name in self._registered_outgoing_events:
            # Decrement reference count
            if event_name in WebMessagingAPI._outgoing_event_refcount:
                WebMessagingAPI._outgoing_event_refcount[event_name] -= 1

                # Only unregister if no other instances are using this event
                if WebMessagingAPI._outgoing_event_refcount[event_name] <= 0:
                    messaging.unregister_event_type_to_send(event_name)
                    del WebMessagingAPI._outgoing_event_refcount[event_name]

        self._registered_outgoing_events.clear()

    def incoming(self, name_or_func=None) -> Callable:
        """Decorator to register a function as an incoming message handler.

        Args:
            name_or_func: Optional event name string, or the function itself when used without parentheses.

        Returns:
            The original function unchanged.

        Example:
            @api.incoming
            def handle_undo():
                print("Undo requested")

            @api.incoming()
            def handle_request():
                # Event name will be "handle_request"
                print("Request received")

            @api.incoming("customEvent")
            def handle_custom(param: str):
                print(f"Custom: {param}")
        """

        def decorator(f: Callable) -> Callable:
            # Determine event name
            if isinstance(name_or_func, str):
                event_name = name_or_func
            else:
                event_name = f.__name__

            def on_event(e: carb.eventdispatcher.Event):
                # Get the payload as a Python dict
                # Events 2.0 payload is accessed via dictionary-style interface
                args = {}
                if e.payload:
                    # Convert variant payload to dict
                    for key in e.payload.keys():
                        args[str(key)] = e.payload[key]

                try:
                    # Call the function with unpacked args
                    f(**args)
                except (TypeError, ValueError) as exc:
                    carb.log_error(f"WebMessagingAPI: Error in incoming handler '{event_name}': {exc}")

            # Subscribe to the event using Events 2.0
            sub = self._dispatcher.observe_event(
                observer_name=f"WebMessagingAPI.{event_name}", event_name=event_name, on_event=on_event
            )
            self._subscriptions[event_name] = sub
            carb.log_info(f"WebMessagingAPI: Registered incoming handler for '{event_name}'")

            return f

        # If called without parentheses (@api.incoming)
        if callable(name_or_func):
            return decorator(name_or_func)

        # If called with parentheses (@api.incoming() or @api.incoming("name"))
        return decorator

    def outgoing(self, name_or_func=None) -> Callable:
        """Decorator to register a function as an outgoing message sender.

        Args:
            name_or_func: Optional event name string, or the function itself when used without parentheses.

        Returns:
            A wrapper function that sends the event and executes the original function.

        Example:
            @api.outgoing
            def send_update(data: str):
                print(f"Sending: {data}")

            @api.outgoing()
            def send_event(data: str):
                # Event name will be "send_event"
                print(f"Sending: {data}")

            @api.outgoing("customEvent")
            def send_custom(param: str):
                print(f"Custom: {param}")
        """

        def decorator(f: Callable) -> Callable:
            # Determine event name
            if isinstance(name_or_func, str):
                event_name = name_or_func
            else:
                event_name = f.__name__

            # Register event type for sending with reference counting
            if event_name not in WebMessagingAPI._outgoing_event_refcount:
                # First instance registering this event
                messaging.register_event_type_to_send(event_name)
                WebMessagingAPI._outgoing_event_refcount[event_name] = 0

            # Increment reference count
            WebMessagingAPI._outgoing_event_refcount[event_name] += 1
            self._registered_outgoing_events.append(event_name)
            carb.log_info(
                f"WebMessagingAPI: Registered outgoing event '{event_name}' (refcount: {WebMessagingAPI._outgoing_event_refcount[event_name]})"
            )

            def wrapper(**kwargs):
                # Dispatch event using Events 2.0
                try:
                    self._dispatcher.dispatch_event(event_name, payload=kwargs)
                except Exception as exc:
                    carb.log_error(f"WebMessagingAPI: Error sending outgoing event '{event_name}': {exc}")

                # Execute original function
                return f(**kwargs)

            return wrapper

        # If called without parentheses (@api.outgoing)
        if callable(name_or_func):
            return decorator(name_or_func)

        # If called with parentheses (@api.outgoing() or @api.outgoing("name"))
        return decorator
