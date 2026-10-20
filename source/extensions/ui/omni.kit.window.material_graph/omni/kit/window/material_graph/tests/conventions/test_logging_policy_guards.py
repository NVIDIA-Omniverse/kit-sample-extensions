import ast
import re
from pathlib import Path
from unittest.mock import MagicMock

from ...scripts.config.logging import log_exception
from ..base import MaterialGraphTestBase


class TestLoggingPolicyGuards(MaterialGraphTestBase):
    """Extension logging conventions: we disallow f-strings in logger calls (use % or .format so
    lazy evaluation is possible) and disallow bare except without an explicit allow comment. These
    tests scan the scripts tree for violations so the style stays consistent."""

    _EXEMPT_FILES = {
        "scripts/config/logging.py",
    }

    def _scripts_root(self) -> Path:
        return Path(__file__).resolve().parents[2] / "scripts"

    async def test_no_fstring_logging_calls(self) -> None:
        """No logger calls with f-strings."""
        scripts_root = self._scripts_root()
        pattern = re.compile(r"logger\.(debug|info|warning|error|exception|critical)\(\s*f['\"]")
        violations: list[str] = []
        for path in scripts_root.rglob("*.py"):
            rel = path.relative_to(scripts_root.parent).as_posix()
            if rel in self._EXEMPT_FILES:
                continue
            text = path.read_text(encoding="utf-8")
            if pattern.search(text):
                violations.append(rel)
        self.assertFalse(violations, f"f-string logging violations: {violations}")

    async def test_no_bare_except_without_comment(self) -> None:
        """No bare except without # allow-bare-except."""
        scripts_root = self._scripts_root()
        pattern = re.compile(r"^\s*except\s*:\s*$", re.MULTILINE)
        violations: list[str] = []
        for path in scripts_root.rglob("*.py"):
            rel = path.relative_to(scripts_root.parent).as_posix()
            text = path.read_text(encoding="utf-8")
            for match in pattern.finditer(text):
                line_start = text.rfind("\n", 0, match.start()) + 1
                line_end = text.find("\n", match.start())
                if line_end == -1:
                    line_end = len(text)
                line = text[line_start:line_end]
                if "# allow-bare-except" not in line:
                    violations.append(rel)
                    break
        self.assertFalse(violations, f"bare except violations: {violations}")

    async def test_no_tracebacks_bypass_extension_logger(self) -> None:
        """Production exceptions must use the structured extension logger."""
        violations = []
        for path in self._scripts_root().rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if any(
                token in text
                for token in (
                    "traceback.print_exc(",
                    "traceback.format_exc(",
                    "carb.log_error(",
                    "carb.log_warn(",
                    "carb.log_warning(",
                )
            ):
                violations.append(path.relative_to(self._scripts_root().parent).as_posix())
        self.assertFalse(violations, f"exception logging bypasses: {violations}")

    async def test_warning_and_error_calls_are_not_context_free_variables(self) -> None:
        """Dynamic diagnostics need a stable operation label instead of an unexplained message variable."""
        pattern = re.compile(r"logger\.(warning|error|critical)\(\s*(message|reason)\s*\)")
        violations = []
        for path in self._scripts_root().rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if pattern.search(text):
                violations.append(path.relative_to(self._scripts_root().parent).as_posix())
        self.assertFalse(violations, f"context-free dynamic diagnostics: {violations}")

    async def test_log_exception_calls_include_operation_context(self) -> None:
        """Exception boundaries must identify the affected operation or object."""
        context_keys = {
            "action",
            "command_name",
            "context",
            "context_name",
            "ext_id",
            "file_path",
            "plugin_name",
            "prim_path",
            "stage_id",
        }
        violations = []
        for path in self._scripts_root().rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not (
                    isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "log_exception"
                ):
                    continue
                keyword_names = {keyword.arg for keyword in node.keywords if keyword.arg}
                if not keyword_names.intersection(context_keys):
                    rel = path.relative_to(self._scripts_root().parent).as_posix()
                    violations.append(f"{rel}:{node.lineno}")
        self.assertFalse(violations, f"context-free log_exception calls: {violations}")

    async def test_event_owned_menus_are_replaced_instead_of_cleared(self) -> None:
        """Menu callbacks must not clear OmniUI containers during event dispatch."""
        pattern = re.compile(r"self\._[A-Za-z0-9_]*menu\.clear\(")
        violations = []
        for path in self._scripts_root().rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if pattern.search(text):
                violations.append(path.relative_to(self._scripts_root().parent).as_posix())
        self.assertFalse(violations, f"event-owned menu clear violations: {violations}")

    async def test_background_tasks_use_an_observing_scheduler(self) -> None:
        """Direct ensure_future use is limited to schedulers that observe task results."""
        violations = []
        allowed = {
            "scripts/utils/async_utils.py",
            "scripts/utils/lifecycle_registry.py",
        }
        for path in self._scripts_root().rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            rel = path.relative_to(self._scripts_root().parent).as_posix()
            if "asyncio.ensure_future(" in text and rel not in allowed:
                violations.append(rel)
        self.assertFalse(violations, f"unobserved ensure_future calls: {violations}")

    async def test_log_exception_preserves_explicit_exception_traceback(self) -> None:
        """Deferred boundary logging should retain the original exception traceback."""
        logger = MagicMock()
        try:
            raise KeyError("boom")
        except KeyError as exc:
            captured = exc

        log_exception(logger, "operation failed", action="test", exc=captured)

        exc_info = logger.log.call_args.kwargs["exc_info"]
        self.assertIs(exc_info[1], captured)
        self.assertIsNotNone(exc_info[2])
