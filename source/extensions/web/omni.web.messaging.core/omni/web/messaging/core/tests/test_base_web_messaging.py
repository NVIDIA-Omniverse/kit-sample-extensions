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

from ..base_web_messaging import BaseWebMessaging


class TestBaseWebMessaging(omni.kit.test.AsyncTestCase):
    """Test suite for BaseWebMessaging class."""

    async def setUp(self):
        """Set up test fixtures before each test."""
        self.messaging = None
        self.app = omni.kit.app.get_app()
        self.dispatcher = carb.eventdispatcher.get_eventdispatcher()

    async def tearDown(self):
        """Clean up after each test."""
        if self.messaging:
            self.messaging.destroy()
            self.messaging = None
        await omni.kit.app.get_app().next_update_async()

    async def test_incoming_decorator_with_custom_name(self):
        """Test incoming handler with custom event name."""

        class TestMessaging(BaseWebMessaging):
            def __init__(self):
                self.received_data = None
                super().__init__()

            @BaseWebMessaging.incoming("custom_request")
            def on_request(self, data: str):
                self.received_data = data

        self.messaging = TestMessaging()

        # Send event
        self.dispatcher.dispatch_event("custom_request", payload={"data": "test_value"})

        await omni.kit.app.get_app().next_update_async()

        self.assertEqual(self.messaging.received_data, "test_value")

    async def test_incoming_decorator_without_name(self):
        """Test incoming handler using method name as event name."""

        class TestMessaging(BaseWebMessaging):
            def __init__(self):
                self.called = False
                super().__init__()

            @BaseWebMessaging.incoming
            def my_handler(self):
                self.called = True

        self.messaging = TestMessaging()

        # Event name should be "my_handler"
        self.dispatcher.dispatch_event("my_handler", payload={})

        await omni.kit.app.get_app().next_update_async()

        self.assertTrue(self.messaging.called)

    async def test_incoming_decorator_with_parentheses(self):
        """Test incoming handler with empty parentheses."""

        class TestMessaging(BaseWebMessaging):
            def __init__(self):
                self.value = None
                super().__init__()

            @BaseWebMessaging.incoming()
            def process_data(self, value: int):
                self.value = value

        self.messaging = TestMessaging()

        self.dispatcher.dispatch_event("process_data", payload={"value": 123})

        await omni.kit.app.get_app().next_update_async()

        self.assertEqual(self.messaging.value, 123)

    async def test_outgoing_decorator_with_custom_name(self):
        """Test outgoing event with custom name."""

        class TestMessaging(BaseWebMessaging):
            @BaseWebMessaging.outgoing("status_update")
            def send_status(self, status: str):
                # Method body can do additional work
                pass

        self.messaging = TestMessaging()

        received = []

        def on_event(e: carb.eventdispatcher.Event):
            payload = {}
            if e.payload:
                for key in e.payload.keys():
                    payload[str(key)] = e.payload[key]
            received.append(payload)

        sub = self.dispatcher.observe_event(
            observer_name="test_outgoing_custom_name", event_name="status_update", on_event=on_event
        )

        try:
            self.messaging.send_status(status="ready")

            await omni.kit.app.get_app().next_update_async()

            self.assertEqual(len(received), 1)
            self.assertEqual(received[0].get("status"), "ready")

        finally:
            # Events 2.0: ObserverGuard cleans up automatically when set to None
            sub = None

    async def test_outgoing_decorator_without_name(self):
        """Test outgoing event using method name."""

        class TestMessaging(BaseWebMessaging):
            @BaseWebMessaging.outgoing
            def send_notification(self, message: str):
                pass

        self.messaging = TestMessaging()

        received = []

        def on_event(e: carb.eventdispatcher.Event):
            payload = {}
            if e.payload:
                for key in e.payload.keys():
                    payload[str(key)] = e.payload[key]
            received.append(payload)

        sub = self.dispatcher.observe_event(
            observer_name="test_outgoing_no_name", event_name="send_notification", on_event=on_event
        )

        try:
            self.messaging.send_notification(message="hello")

            await omni.kit.app.get_app().next_update_async()

            self.assertEqual(len(received), 1)
            self.assertEqual(received[0].get("message"), "hello")

        finally:
            # Events 2.0: ObserverGuard cleans up automatically when set to None
            sub = None

    async def test_outgoing_decorator_with_parentheses(self):
        """Test outgoing event with empty parentheses."""

        class TestMessaging(BaseWebMessaging):
            @BaseWebMessaging.outgoing()
            def emit_event(self, data: dict):
                pass

        self.messaging = TestMessaging()

        received = []

        def on_event(e: carb.eventdispatcher.Event):
            payload = {}
            if e.payload:
                for key in e.payload.keys():
                    payload[str(key)] = e.payload[key]
            received.append(payload)

        sub = self.dispatcher.observe_event(
            observer_name="test_outgoing_with_parens", event_name="emit_event", on_event=on_event
        )

        try:
            self.messaging.emit_event(data={"key": "value"})

            await omni.kit.app.get_app().next_update_async()

            self.assertEqual(len(received), 1)
            self.assertIn("data", received[0])

        finally:
            # Events 2.0: ObserverGuard cleans up automatically when set to None
            sub = None

    async def test_multiple_handlers(self):
        """Test class with multiple incoming and outgoing handlers."""

        class TestMessaging(BaseWebMessaging):
            def __init__(self):
                self.request_count = 0
                self.command_data = None
                super().__init__()

            @BaseWebMessaging.incoming("request1")
            def on_request1(self):
                self.request_count += 1

            @BaseWebMessaging.incoming("request2")
            def on_request2(self):
                self.request_count += 1

            @BaseWebMessaging.incoming("command")
            def on_command(self, data: str):
                self.command_data = data

            @BaseWebMessaging.outgoing("response")
            def send_response(self, result: str):
                pass

            @BaseWebMessaging.outgoing("notification")
            def send_notification(self, msg: str):
                pass

        self.messaging = TestMessaging()

        # Test incoming handlers
        self.dispatcher.dispatch_event("request1", payload={})
        self.dispatcher.dispatch_event("request2", payload={})
        self.dispatcher.dispatch_event("command", payload={"data": "execute"})

        await omni.kit.app.get_app().next_update_async()

        self.assertEqual(self.messaging.request_count, 2)
        self.assertEqual(self.messaging.command_data, "execute")

        # Test outgoing handlers
        received_response = []
        received_notification = []

        def on_response(e):
            payload = {}
            if e.payload:
                for key in e.payload.keys():
                    payload[str(key)] = e.payload[key]
            received_response.append(payload)

        def on_notification(e):
            payload = {}
            if e.payload:
                for key in e.payload.keys():
                    payload[str(key)] = e.payload[key]
            received_notification.append(payload)

        sub1 = self.dispatcher.observe_event(
            observer_name="test_multiple_handlers_response", event_name="response", on_event=on_response
        )
        sub2 = self.dispatcher.observe_event(
            observer_name="test_multiple_handlers_notification", event_name="notification", on_event=on_notification
        )

        try:
            self.messaging.send_response(result="success")
            self.messaging.send_notification(msg="done")

            await omni.kit.app.get_app().next_update_async()

            self.assertEqual(len(received_response), 1)
            self.assertEqual(received_response[0].get("result"), "success")
            self.assertEqual(len(received_notification), 1)
            self.assertEqual(received_notification[0].get("msg"), "done")

        finally:
            # Events 2.0: ObserverGuard cleans up automatically when set to None
            sub1 = None
            sub2 = None

    async def test_destroy(self):
        """Test that destroy properly cleans up resources."""

        class TestMessaging(BaseWebMessaging):
            def __init__(self):
                self.call_count = 0
                super().__init__()

            @BaseWebMessaging.incoming("test_destroy")
            def handler(self):
                self.call_count += 1

        self.messaging = TestMessaging()

        # Send event before destroy
        self.dispatcher.dispatch_event("test_destroy", payload={})
        await omni.kit.app.get_app().next_update_async()

        self.assertEqual(self.messaging.call_count, 1)

        # Destroy
        self.messaging.destroy()

        # Send event after destroy - should not be received
        self.dispatcher.dispatch_event("test_destroy", payload={})
        await omni.kit.app.get_app().next_update_async()

        # Count should still be 1
        self.assertEqual(self.messaging.call_count, 1)

        # Calling destroy again should be safe
        self.messaging.destroy()

    async def test_inheritance(self):
        """Test that BaseWebMessaging can be properly inherited."""

        class ParentMessaging(BaseWebMessaging):
            def __init__(self):
                self.parent_called = False
                super().__init__()

            @BaseWebMessaging.incoming("parent_event")
            def on_parent(self):
                self.parent_called = True

        class ChildMessaging(ParentMessaging):
            def __init__(self):
                self.child_called = False
                super().__init__()

            @BaseWebMessaging.incoming("child_event")
            def on_child(self):
                self.child_called = True

        self.messaging = ChildMessaging()

        # Test parent handler
        self.dispatcher.dispatch_event("parent_event", payload={})
        await omni.kit.app.get_app().next_update_async()
        self.assertTrue(self.messaging.parent_called)

        # Test child handler
        self.dispatcher.dispatch_event("child_event", payload={})
        await omni.kit.app.get_app().next_update_async()
        self.assertTrue(self.messaging.child_called)

    async def test_method_execution_with_outgoing(self):
        """Test that outgoing decorator executes both event sending and method body."""

        class TestMessaging(BaseWebMessaging):
            def __init__(self):
                self.method_executed = False
                super().__init__()

            @BaseWebMessaging.outgoing("test_method")
            def my_method(self, value: str):
                # This method body should be executed
                self.method_executed = True
                return value.upper()

        self.messaging = TestMessaging()

        received = []

        def on_event(e):
            payload = {}
            if e.payload:
                for key in e.payload.keys():
                    payload[str(key)] = e.payload[key]
            received.append(payload)

        sub = self.dispatcher.observe_event(
            observer_name="test_method_execution", event_name="test_method", on_event=on_event
        )

        try:
            result = self.messaging.my_method(value="test")

            await omni.kit.app.get_app().next_update_async()

            # Method should be executed
            self.assertTrue(self.messaging.method_executed)
            # Return value should be preserved
            self.assertEqual(result, "TEST")
            # Event should be sent
            self.assertEqual(len(received), 1)
            self.assertEqual(received[0].get("value"), "test")

        finally:
            # Events 2.0: ObserverGuard cleans up automatically when set to None
            sub = None

    async def test_empty_class(self):
        """Test that BaseWebMessaging can be instantiated without handlers."""

        class EmptyMessaging(BaseWebMessaging):
            pass

        # Should not raise any errors
        self.messaging = EmptyMessaging()
        self.assertIsNotNone(self.messaging)

        # Cleanup should work
        self.messaging.destroy()
