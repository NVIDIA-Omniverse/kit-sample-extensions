# pylint: disable=relative-beyond-top-level
from unittest.mock import patch

import omni.kit.commands

from ...scripts.commands.impl import registry
from .base import CommandsTestBase


class TestCommandRegistry(CommandsTestBase):
    """registry registers and unregisters material graph commands with omni.kit.commands. We test
    that register_all_commands / unregister_all_commands call the kit API in the right order and
    count; we patch omni.kit.commands so we don't affect the real app."""

    async def test_register_unregister_commands(self) -> None:
        """Register then unregister calls kit API in reverse order."""
        # Patch omni.kit.commands.register and unregister to avoid affecting real app and assert counts/order.
        registry._commands_registered = False
        with (
            patch.object(omni.kit.commands, "register", autospec=True) as register_mock,
            patch.object(omni.kit.commands, "unregister", autospec=True) as unregister_mock,
        ):
            registry.register_all_commands()
            self.assertTrue(registry._commands_registered)
            self.assertEqual(register_mock.call_count, len(registry._REGISTERED_COMMANDS))

            registry.unregister_all_commands()
            self.assertFalse(registry._commands_registered)
            self.assertEqual(unregister_mock.call_count, len(registry._REGISTERED_COMMANDS))

            expected_unregister_order = list(reversed(registry._REGISTERED_COMMANDS))
            actual_unregister_order = [call.args[0] for call in unregister_mock.call_args_list]
            self.assertEqual(actual_unregister_order, expected_unregister_order)
