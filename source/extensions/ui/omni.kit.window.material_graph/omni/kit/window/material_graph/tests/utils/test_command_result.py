from dataclasses import FrozenInstanceError

import omni.kit.test

from ...scripts.commands.result import CommandResult


class TestCommandResult(omni.kit.test.AsyncTestCase):
    """CommandResult is the standard return type for command helpers: success, payload, optional
    message/error_code. We test that ok/success reflect the flag, that the dataclass is frozen,
    and that payload is accessible."""

    async def test_ok_property(self) -> None:
        """ok reflects success."""
        result = CommandResult(True, payload="value")
        self.assertTrue(result.ok)
        self.assertTrue(result.success)

    async def test_frozen(self) -> None:
        """CommandResult is immutable."""
        result = CommandResult(False, message="nope")
        with self.assertRaises(FrozenInstanceError):
            result.success = True

    async def test_payload_access(self) -> None:
        """Payload accessible."""
        result = CommandResult(True, payload={"x": 1})
        self.assertEqual(result.payload, {"x": 1})
