## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

import carb
import carb.eventdispatcher
import omni.kit.app
import omni.kit.test

from ..web_messaging_api import WebMessagingAPI


class TestWebMessagingAPI(omni.kit.test.AsyncTestCase):
    """Test suite for WebMessagingAPI class."""

    async def setUp(self):
        """Set up test fixtures before each test."""
        self.api = None
        self.received_events = []
        self.app = omni.kit.app.get_app()
        self.dispatcher = carb.eventdispatcher.get_eventdispatcher()

    async def tearDown(self):
        """Clean up after each test."""
        if self.api:
            self.api.cleanup()
            self.api = None
        self.received_events.clear()
        await omni.kit.app.get_app().next_update_async()

    async def test_incoming_decorator_without_parentheses(self):
        """Test incoming decorator used without parentheses."""
        self.api = WebMessagingAPI()

        received_params = {}

        @self.api.incoming
        def test_handler(param1: str, param2: int):
            received_params["param1"] = param1
            received_params["param2"] = param2

        # Send event via event dispatcher
        self.dispatcher.dispatch_event("test_handler", payload={"param1": "hello", "param2": 42})

        # Wait for event processing
        await omni.kit.app.get_app().next_update_async()

        # Verify handler was called with correct parameters
        self.assertEqual(received_params.get("param1"), "hello")
        self.assertEqual(received_params.get("param2"), 42)

    async def test_incoming_decorator_with_parentheses(self):
        """Test incoming decorator used with empty parentheses."""
        self.api = WebMessagingAPI()

        received_params = {}

        @self.api.incoming()
        def another_handler(data: str):
            received_params["data"] = data

        # Send event
        self.dispatcher.dispatch_event("another_handler", payload={"data": "test"})

        await omni.kit.app.get_app().next_update_async()

        self.assertEqual(received_params.get("data"), "test")

    async def test_incoming_decorator_with_custom_name(self):
        """Test incoming decorator with custom event name."""
        self.api = WebMessagingAPI()

        received_value = []

        @self.api.incoming("customEventName")
        def my_handler(value: str):
            received_value.append(value)

        # Send event with custom name
        self.dispatcher.dispatch_event("customEventName", payload={"value": "custom"})

        await omni.kit.app.get_app().next_update_async()

        self.assertEqual(len(received_value), 1)
        self.assertEqual(received_value[0], "custom")

    async def test_outgoing_decorator_without_parentheses(self):
        """Test outgoing decorator used without parentheses."""
        self.api = WebMessagingAPI()

        received_events = []

        @self.api.outgoing
        def send_event(message: str):
            """Outgoing event sender."""
            pass

        # Subscribe to the event
        def on_event(e: carb.eventdispatcher.Event):
            payload = {}
            if e.payload:
                for key in e.payload.keys():
                    payload[str(key)] = e.payload[key]
            received_events.append(payload)

        sub = self.dispatcher.observe_event(
            observer_name="test_outgoing_no_parens", event_name="send_event", on_event=on_event
        )

        try:
            # Call the outgoing handler
            send_event(message="test message")

            await omni.kit.app.get_app().next_update_async()

            # Verify event was sent
            self.assertEqual(len(received_events), 1)
            self.assertEqual(received_events[0].get("message"), "test message")

        finally:
            # Events 2.0: ObserverGuard cleans up automatically when set to None
            sub = None

    async def test_outgoing_decorator_with_parentheses(self):
        """Test outgoing decorator used with empty parentheses."""
        self.api = WebMessagingAPI()

        received_events = []

        @self.api.outgoing()
        def send_update(data: dict):
            """Outgoing update sender."""
            pass

        def on_event(e: carb.eventdispatcher.Event):
            payload = {}
            if e.payload:
                for key in e.payload.keys():
                    payload[str(key)] = e.payload[key]
            received_events.append(payload)

        sub = self.dispatcher.observe_event(
            observer_name="test_outgoing_with_parens", event_name="send_update", on_event=on_event
        )

        try:
            send_update(data={"key": "value"})
            await omni.kit.app.get_app().next_update_async()

            self.assertEqual(len(received_events), 1)
            self.assertIn("data", received_events[0])

        finally:
            # Events 2.0: ObserverGuard cleans up automatically when set to None
            sub = None

    async def test_outgoing_decorator_with_custom_name(self):
        """Test outgoing decorator with custom event name."""
        self.api = WebMessagingAPI()

        received_events = []

        @self.api.outgoing("myCustomEvent")
        def send_custom(value: int):
            """Custom event sender."""
            pass

        def on_event(e: carb.eventdispatcher.Event):
            payload = {}
            if e.payload:
                for key in e.payload.keys():
                    payload[str(key)] = e.payload[key]
            received_events.append(payload)

        sub = self.dispatcher.observe_event(
            observer_name="test_outgoing_custom_name", event_name="myCustomEvent", on_event=on_event
        )

        try:
            send_custom(value=123)
            await omni.kit.app.get_app().next_update_async()

            self.assertEqual(len(received_events), 1)
            self.assertEqual(received_events[0].get("value"), 123)

        finally:
            # Events 2.0: ObserverGuard cleans up automatically when set to None
            sub = None

    async def test_cleanup(self):
        """Test that cleanup properly removes subscriptions."""
        self.api = WebMessagingAPI()

        call_count = []

        @self.api.incoming("test_cleanup")
        def handler():
            call_count.append(1)

        # Send event before cleanup
        self.dispatcher.dispatch_event("test_cleanup", payload={})
        await omni.kit.app.get_app().next_update_async()

        self.assertEqual(len(call_count), 1)

        # Cleanup
        self.api.cleanup()

        # Send event after cleanup - should not be received
        self.dispatcher.dispatch_event("test_cleanup", payload={})
        await omni.kit.app.get_app().next_update_async()

        # Count should still be 1 (handler not called after cleanup)
        self.assertEqual(len(call_count), 1)

    async def test_reference_counting_single_instance(self):
        """Test reference counting with single API instance."""
        api1 = WebMessagingAPI()

        @api1.outgoing("refcount_test")
        def send_event():
            pass

        # Check that refcount is 1
        self.assertEqual(WebMessagingAPI._outgoing_event_refcount.get("refcount_test"), 1)

        # Cleanup
        api1.cleanup()

        # Event should be unregistered
        self.assertNotIn("refcount_test", WebMessagingAPI._outgoing_event_refcount)

    async def test_reference_counting_multiple_instances(self):
        """Test reference counting with multiple API instances sharing same event."""
        api1 = WebMessagingAPI()
        api2 = WebMessagingAPI()

        @api1.outgoing("shared_event")
        def send_from_api1():
            pass

        @api2.outgoing("shared_event")
        def send_from_api2():
            pass

        # Refcount should be 2
        self.assertEqual(WebMessagingAPI._outgoing_event_refcount.get("shared_event"), 2)

        # Cleanup first instance
        api1.cleanup()

        # Refcount should be 1
        self.assertEqual(WebMessagingAPI._outgoing_event_refcount.get("shared_event"), 1)

        # Cleanup second instance
        api2.cleanup()

        # Event should be fully unregistered
        self.assertNotIn("shared_event", WebMessagingAPI._outgoing_event_refcount)

    async def test_multiple_incoming_handlers(self):
        """Test multiple incoming handlers on same API instance."""
        self.api = WebMessagingAPI()

        results = {}

        @self.api.incoming("event1")
        def handler1(data: str):
            results["event1"] = data

        @self.api.incoming("event2")
        def handler2(data: str):
            results["event2"] = data

        # Send both events
        self.dispatcher.dispatch_event("event1", payload={"data": "first"})
        self.dispatcher.dispatch_event("event2", payload={"data": "second"})

        await omni.kit.app.get_app().next_update_async()

        self.assertEqual(results.get("event1"), "first")
        self.assertEqual(results.get("event2"), "second")

    async def test_multiple_outgoing_handlers(self):
        """Test multiple outgoing handlers on same API instance."""
        self.api = WebMessagingAPI()

        received = {}

        @self.api.outgoing("out1")
        def send1(value: int):
            pass

        @self.api.outgoing("out2")
        def send2(value: str):
            pass

        # Subscribe to both
        def make_handler(key):
            def handler(e):
                payload = {}
                if e.payload:
                    for payload_key in e.payload.keys():
                        payload[str(payload_key)] = e.payload[payload_key]
                received[key] = payload

            return handler

        sub1 = self.dispatcher.observe_event(
            observer_name="test_multiple_outgoing_1", event_name="out1", on_event=make_handler("out1")
        )
        sub2 = self.dispatcher.observe_event(
            observer_name="test_multiple_outgoing_2", event_name="out2", on_event=make_handler("out2")
        )

        try:
            send1(value=100)
            send2(value="test")

            await omni.kit.app.get_app().next_update_async()

            self.assertEqual(received.get("out1", {}).get("value"), 100)
            self.assertEqual(received.get("out2", {}).get("value"), "test")

        finally:
            # Events 2.0: ObserverGuard cleans up automatically when set to None
            sub1 = None
            sub2 = None
