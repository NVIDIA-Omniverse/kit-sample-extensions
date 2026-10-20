# pylint: disable=relative-beyond-top-level
from unittest.mock import patch

import omni.kit.commands

from ...scripts.commands.execution import execute_command
from ...scripts.commands.result import CommandResult
from ...scripts.config.paths import Paths
from .base import CommandsTestBase


class TestCommandUtils(CommandsTestBase):
    """execute_command wraps omni.kit.commands.execute and normalizes return values into CommandResult;
    it handles exceptions, tuple/bool/None returns, and optional failure logging. Callers depend on
    consistent success/payload/error_code. We test missing name, exception path, tuple normalization,
    payload normalization, bool result, None->failure, failure logging context, and CommandResult
    passthrough."""

    async def test_execute_command_missing_name(self) -> None:
        """Missing command name returns failure result."""
        result = execute_command("")
        self.assertFalse(result.success)
        self.assertEqual(result.error_code, "invalid_command")

    async def test_execute_command_exception(self) -> None:
        """Exception returns failure result."""
        # Patch omni.kit.commands.execute to raise so we test exception handling without a real failing command.
        with patch.object(omni.kit.commands, "execute", autospec=True, side_effect=RuntimeError("boom")):
            result = execute_command("FailCommand", log_errors=False)
            self.assertFalse(result.success)
            self.assertEqual(result.error_code, "exception")

    async def test_execute_command_tuple_normalization(self) -> None:
        """Tuple return normalized into CommandResult."""
        # Patch execute to return (False, "payload") to test tuple->CommandResult conversion.
        with patch.object(omni.kit.commands, "execute", autospec=True, return_value=(False, "payload")):
            result = execute_command("TupleCommand")
            self.assertFalse(result.success)
            self.assertEqual(result.payload, "payload")

    async def test_execute_command_payload_normalization(self) -> None:
        """Non-tuple return treated as success."""
        # Patch execute to return a plain value to test success + payload.
        with patch.object(omni.kit.commands, "execute", autospec=True, return_value="value"):
            result = execute_command("SimpleCommand")
            self.assertTrue(result.success)
            self.assertEqual(result.payload, "value")

    async def test_execute_command_bool_result(self) -> None:
        """Bool return treated as success/failure."""
        # Patch execute to return False then True to test bool handling.
        with patch.object(omni.kit.commands, "execute", autospec=True, return_value=False):
            result = execute_command("BoolCommand")
            self.assertFalse(result.success)
        with patch.object(omni.kit.commands, "execute", autospec=True, return_value=True):
            result = execute_command("BoolCommand")
            self.assertTrue(result.success)

    async def test_execute_command_none_result_fails(self) -> None:
        """None return fails by default."""
        # Patch execute to return None to test no_result error code.
        with patch.object(omni.kit.commands, "execute", autospec=True, return_value=None):
            result = execute_command("NoneCommand")
            self.assertFalse(result.success)
            self.assertEqual(result.error_code, "no_result")

    async def test_execute_command_failure_logs_context(self) -> None:
        """Failure log includes key context args."""
        # Patch execute to return False and logger.warning to assert log content includes command name and prim_path.
        with (
            patch.object(omni.kit.commands, "execute", autospec=True, return_value=False),
            patch(
                f"{Paths.MODULE_ID}.scripts.commands.execution.logger.warning",
                autospec=True,
            ) as log_warn,
        ):
            execute_command("FailCommand", prim_path="/World/Looks/Material", node_type="Shader")
            log_warn.assert_called()
            log_text = str(log_warn.call_args)
            self.assertIn("command failed", log_text)
            self.assertIn("FailCommand", log_text)
            self.assertIn("prim_path", log_text)

    async def test_execute_command_command_result_passthrough(self) -> None:
        """CommandResult return passed through unchanged."""
        # Patch execute to return a CommandResult to test passthrough.
        expected = CommandResult(True, payload="ok")
        with patch.object(omni.kit.commands, "execute", autospec=True, return_value=expected):
            result = execute_command("ResultCommand")
            self.assertIs(result, expected)
