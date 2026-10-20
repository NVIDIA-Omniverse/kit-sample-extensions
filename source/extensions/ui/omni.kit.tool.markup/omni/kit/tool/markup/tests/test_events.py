# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import asyncio

import carb
import omni.kit.test


class TestMarkupEvent(omni.kit.test.AsyncTestCase):

    async def test_create_event(self):
        """Create an instance and initialize data."""
        from omni.kit.tool.markup.ui.events import MarkupEvent

        event = MarkupEvent(field_int=1, field_text="text")

        self.assertEqual(getattr(event, "_data"), {"field_int": 1, "field_text": "text"})
        self.assertIsInstance(getattr(event, "_handlers"), set)

    async def test_add_handler_function(self):
        """Add a function event handler"""
        from weakref import ref

        from omni.kit.tool.markup.ui.events import MarkupEvent

        def dummy(x):
            return x

        event = MarkupEvent()
        event.add_handler(dummy)

        self.assertTrue(event._handlers)
        self.assertIsInstance(event._handlers.pop(), ref)

    async def test_add_handler_magic(self):
        """Add a event handler through magic method"""
        from weakref import ref

        from omni.kit.tool.markup.ui.events import MarkupEvent

        def dummy(x):
            return x

        event = MarkupEvent()

        event += dummy

        self.assertTrue(event._handlers)
        self.assertIsInstance(event._handlers.pop(), ref)

    async def test_add_handler_method(self):
        """Add a method event handler"""
        from weakref import WeakMethod

        from omni.kit.tool.markup.ui.events import MarkupEvent

        class Dummy:
            def callable(self, x):
                return x

        dummy = Dummy()

        event = MarkupEvent()

        event.add_handler(dummy.callable)

        self.assertTrue(event._handlers)
        self.assertIsInstance(event._handlers.pop(), WeakMethod)

    async def test_add_handler_raise_valueerror(self):
        """Add a non-callable event handler and raises ValueError"""
        from omni.kit.tool.markup.ui.events import MarkupEvent

        event = MarkupEvent()

        self.assertRaises(ValueError, lambda: event.add_handler("x"))

    async def test_remove_handler_function(self):
        """Remove a function event handler"""
        from weakref import ref

        from omni.kit.tool.markup.ui.events import MarkupEvent

        def dummy(x):
            return x

        event = MarkupEvent()
        event.add_handler(dummy)

        self.assertTrue(event._handlers)
        event.remove_handler(dummy)
        self.assertFalse(event._handlers)

    async def test_remove_handler_magic(self):
        """Remove an event handler through magic method"""
        from weakref import ref

        from omni.kit.tool.markup.ui.events import MarkupEvent

        def dummy(x):
            return x

        event = MarkupEvent()
        event.add_handler(dummy)

        self.assertTrue(event._handlers)
        event -= dummy
        self.assertFalse(event._handlers)

    async def test_remove_handler_method(self):
        """Remove a method event handler"""
        from weakref import WeakMethod

        from omni.kit.tool.markup.ui.events import MarkupEvent

        class Dummy:
            def callable(self, x):
                return x

        dummy = Dummy()

        event = MarkupEvent()
        event.add_handler(dummy.callable)

        self.assertTrue(event._handlers)
        event.remove_handler(dummy.callable)
        self.assertFalse(event._handlers)

    async def test_remove_handler_raise_valueerror(self):
        """Remove a non-callable event handler and raises ValueError"""
        from omni.kit.tool.markup.ui.events import MarkupEvent

        event = MarkupEvent()

        self.assertRaises(ValueError, lambda: event.remove_handler("x"))

    async def test_run_event(self):
        """Run event handlers"""
        from omni.kit.tool.markup.ui.events import MarkupEvent

        class Dummy:
            def __init__(self):
                self.args = []
                self.keys = {}

            def store(self, *x, **y):
                self.args.extend(x)
                self.keys.update(y)

        dummy = Dummy()

        event = MarkupEvent()
        event.add_handler(dummy.store)

        event.run(1, arg1=2)
        self.assertTrue(dummy.args, [1])
        self.assertTrue(dummy.keys, {"arg1": 2})

    async def test_call_event(self):
        """Run event handlers through a call"""
        from omni.kit.tool.markup.ui.events import MarkupEvent

        class Dummy:
            def __init__(self):
                self.args = []
                self.keys = {}

            def store(self, *x, **y):
                self.args.extend(x)
                self.keys.update(y)

        dummy = Dummy()

        event = MarkupEvent()
        event.add_handler(dummy.store)

        event(3, arg2=4)
        self.assertTrue(dummy.args, [3])
        self.assertTrue(dummy.keys, {"arg2": 4})
