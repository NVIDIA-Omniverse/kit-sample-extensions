## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

from functools import wraps

import carb

from .web_messaging_api import WebMessagingAPI


class BaseWebMessaging:
    """Base class for WebRTC messaging with decorator-based event registration.

    This class provides a convenient way to define incoming and outgoing message
    handlers using decorators. It automatically discovers and registers all
    decorated methods on initialization.

    Uses WebMessagingAPI internally for all messaging operations.

    Usage:
        class MyMessaging(BaseWebMessaging):
            @BaseWebMessaging.incoming("some_request")
            def on_some_request(self, **kwargs):
                print("Received request:", kwargs)

            @BaseWebMessaging.outgoing("some_event")
            def send_some_event(self, **kwargs):
                print("Sending event:", kwargs)

        messaging = MyMessaging()

        # Calling this will push event to message bus and execute the method
        messaging.send_some_event(data="hello")

        # Explicit cleanup (optional, __del__ will also call destroy)
        messaging.destroy()
    """

    def __init__(self):
        self._api = WebMessagingAPI()

        # Automatically discover and register all decorated methods
        self._register_handlers()

    @classmethod
    def incoming(cls, name_or_func=None):
        """Decorator for marking a method as an incoming message handler.

        Args:
            name_or_func: Optional event name string, or the function itself when used without parentheses.

        Usage:
            @BaseWebMessaging.incoming("undoRequest")
            def on_undo_request(self, **kwargs):
                print("Undo requested")

            @BaseWebMessaging.incoming()
            def my_handler(self, **kwargs):
                # Event name will be "my_handler"
                pass

            @BaseWebMessaging.incoming
            def another_handler(self, **kwargs):
                # Event name will be "another_handler"
                pass
        """

        def decorator(func):
            # Determine event name
            if isinstance(name_or_func, str):
                event_name = name_or_func
            else:
                event_name = func.__name__

            # Store the event name on the function itself
            func._incoming_event_name = event_name
            func._is_incoming_handler = True
            return func

        # If called without parentheses (@BaseWebMessaging.incoming)
        if callable(name_or_func):
            return decorator(name_or_func)

        # If called with parentheses (@BaseWebMessaging.incoming() or @BaseWebMessaging.incoming("name"))
        return decorator

    @classmethod
    def outgoing(cls, name_or_func=None):
        """Decorator for marking a method as an outgoing message sender.

        Args:
            name_or_func: Optional event name string, or the function itself when used without parentheses.

        Usage:
            @BaseWebMessaging.outgoing("modelTreeUpdated")
            def send_model_tree_updated(self, **kwargs):
                print("Sending model tree")

            @BaseWebMessaging.outgoing()
            def send_update(self, **kwargs):
                # Event name will be "send_update"
                pass

            @BaseWebMessaging.outgoing
            def send_another(self, **kwargs):
                # Event name will be "send_another"
                pass
        """

        def decorator(func):
            # Determine event name
            if isinstance(name_or_func, str):
                event_name = name_or_func
            else:
                event_name = func.__name__

            # Store the event name on the function itself
            func._outgoing_event_name = event_name
            func._is_outgoing_handler = True

            @wraps(func)
            def wrapper(self, **kwargs):
                # Get the wrapped outgoing method from the API
                outgoing_method = getattr(self, f"_api_outgoing_{event_name}", None)
                if outgoing_method:
                    # Call it to send the event
                    outgoing_method(**kwargs)

                # Execute original method
                return func(self, **kwargs)

            # Keep the metadata on the wrapper
            wrapper._outgoing_event_name = event_name
            wrapper._is_outgoing_handler = True
            return wrapper

        # If called without parentheses (@BaseWebMessaging.outgoing)
        if callable(name_or_func):
            return decorator(name_or_func)

        # If called with parentheses (@BaseWebMessaging.outgoing() or @BaseWebMessaging.outgoing("name"))
        return decorator

    def _register_handlers(self):
        """Discover and register all decorated methods."""
        incoming_count = 0
        outgoing_count = 0

        # Discover and register incoming handlers
        for attr_name in dir(self):
            attr = getattr(self, attr_name)

            # Check for incoming message handlers
            if hasattr(attr, "_is_incoming_handler") and attr._is_incoming_handler:
                event_name = attr._incoming_event_name

                # Create a wrapper function that will be registered with the API
                # We need to bind the method to self
                def make_handler(method):
                    def handler(**kwargs):
                        method(**kwargs)

                    return handler

                # Register with the API using its incoming decorator
                handler = make_handler(attr)
                # Call decorator pattern: incoming(event_name) returns decorator, apply it to handler
                self._api.incoming(event_name)(handler)
                incoming_count += 1
                carb.log_info(f"{self.__class__.__name__}: Registered incoming handler for '{event_name}'")

            # Check for outgoing message handlers
            if hasattr(attr, "_is_outgoing_handler") and attr._is_outgoing_handler:
                event_name = attr._outgoing_event_name

                # Create an outgoing method wrapper and store it on the instance
                def make_outgoing_sender(name):
                    def sender(**kwargs):
                        pass

                    return sender

                outgoing_sender = make_outgoing_sender(event_name)
                # Register with the API - call decorator pattern: outgoing(event_name) returns decorator
                wrapped_sender = self._api.outgoing(event_name)(outgoing_sender)
                # Store it so the outgoing decorator can find it
                setattr(self, f"_api_outgoing_{event_name}", wrapped_sender)
                outgoing_count += 1
                carb.log_info(f"{self.__class__.__name__}: Registered outgoing event '{event_name}'")

        carb.log_info(
            f"{self.__class__.__name__}: Initialized - {incoming_count} incoming handlers, {outgoing_count} outgoing events"
        )

    def destroy(self):
        """Clean up subscriptions and registered events. Safe to call multiple times."""
        if hasattr(self, "_api") and self._api:
            self._api.cleanup()
            self._api = None
            carb.log_info(f"{self.__class__.__name__}: Cleaned up")

    def __del__(self):
        """Automatic cleanup on deletion."""
        self.destroy()
