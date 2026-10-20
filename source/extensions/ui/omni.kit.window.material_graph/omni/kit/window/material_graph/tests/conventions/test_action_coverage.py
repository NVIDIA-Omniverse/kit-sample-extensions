"""Enforce the action-to-test contract for the user-visible extension surface."""

import ast
import sys
from pathlib import Path

import omni.kit.test

from .action_coverage import ACTION_COVERAGE


class TestActionCoverageContract(omni.kit.test.AsyncTestCase):
    """Fail quickly when an action map source anchor or test reference goes stale."""

    _PACKAGE = "omni.kit.window.material_graph.tests"
    _MODULE_ROOT = Path(__file__).resolve().parents[2]
    _ALLOWED_LAYERS = {
        "controller",
        "failure",
        "model",
        "native_input",
        "semantic_ui",
        "undo_redo",
        "usd",
    }
    _BEHAVIOR_LAYERS = {"controller", "model", "native_input", "semantic_ui", "usd"}
    _SEMANTIC_CONTROL_SURFACES = {
        "asset_field",
        "background_menu",
        "badge",
        "button",
        "button_context_menu",
        "button_hotkey",
        "checkbox",
        "color_field",
        "context_menu",
        "dropdown",
        "folder_picker",
        "hotkey_context_menu",
        "menu",
        "menu_hotkey",
        "node_menu",
        "splitter_button",
        "tab",
        "text_input",
        "variant_menu",
        "window",
    }

    @classmethod
    def _resolve_test(cls, reference: str):
        module_name, class_name, method_name = reference.rsplit(".", 2)
        module = sys.modules.get(f"{cls._PACKAGE}.{module_name}")
        if module is None:
            return None
        test_class = getattr(module, class_name, None)
        return getattr(test_class, method_name, None) if test_class else None

    async def test_every_action_has_live_source_and_behavioral_test(self) -> None:
        """Every mapped action must still exist and resolve to registered tests."""
        action_ids = [entry.action_id for entry in ACTION_COVERAGE]
        self.assertEqual(len(action_ids), len(set(action_ids)), "action IDs must be unique")

        failures = []
        for entry in ACTION_COVERAGE:
            source_path = self._MODULE_ROOT / entry.source
            if not source_path.is_file():
                failures.append(f"{entry.action_id}: missing source {entry.source}")
                continue
            if entry.anchor not in source_path.read_text(encoding="utf-8"):
                failures.append(f"{entry.action_id}: missing source anchor {entry.anchor!r}")
            if not entry.tests:
                failures.append(f"{entry.action_id}: no tests")
            for reference in entry.tests:
                if self._resolve_test(reference) is None:
                    failures.append(f"{entry.action_id}: unresolved test {reference}")
            unknown_layers = entry.layers - self._ALLOWED_LAYERS
            if unknown_layers:
                failures.append(f"{entry.action_id}: unknown layers {sorted(unknown_layers)}")
            if not (entry.layers & self._BEHAVIOR_LAYERS):
                failures.append(f"{entry.action_id}: no behavioral test layer")
            if entry.surface in self._SEMANTIC_CONTROL_SURFACES and "semantic_ui" not in entry.layers:
                failures.append(f"{entry.action_id}: extension-owned control lacks semantic UI coverage")
            if "undo_redo" in entry.layers and "usd" not in entry.layers:
                failures.append(f"{entry.action_id}: undo/redo coverage must exercise USD")

        self.assertEqual(failures, [], "\n".join(failures))

    async def test_every_toolbar_registry_action_is_in_the_action_map(self) -> None:
        """Adding a hotkey/action requires adding its behavioral evidence to the map."""
        source_path = self._MODULE_ROOT / "scripts/ui/sections/toolbar/actions.py"
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        registered_ids = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            if not any(isinstance(target, ast.Name) and target.id == "actions" for target in node.targets):
                continue
            if not isinstance(node.value, (ast.List, ast.Tuple)):
                continue
            for element in node.value.elts:
                if not isinstance(element, ast.Tuple) or not element.elts:
                    continue
                action_id = element.elts[0]
                if isinstance(action_id, ast.Constant) and isinstance(action_id.value, str):
                    registered_ids.add(action_id.value)

        mapped_ids = {entry.registry_action for entry in ACTION_COVERAGE if entry.registry_action}
        self.assertTrue(registered_ids, "toolbar action registry could not be parsed")
        self.assertEqual(mapped_ids, registered_ids)
