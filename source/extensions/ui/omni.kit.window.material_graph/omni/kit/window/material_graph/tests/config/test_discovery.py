"""Contracts that prevent test modules or classes from silently disappearing from Kit discovery."""

import inspect
import sys
from pathlib import Path

import omni.kit.test


class TestDiscoveryContract(omni.kit.test.AsyncTestCase):
    """Verify that every test source module and class reaches the root test package."""

    _PACKAGE = "omni.kit.window.material_graph.tests"

    @classmethod
    def _test_module_names(cls):
        tests_root = Path(__file__).resolve().parent.parent
        for source_path in sorted(tests_root.rglob("test_*.py")):
            relative = source_path.relative_to(tests_root).with_suffix("")
            yield cls._PACKAGE + "." + ".".join(relative.parts)

    async def test_every_test_module_is_imported(self) -> None:
        """A test file omitted from a package initializer must fail the registered suite."""
        missing = [module_name for module_name in self._test_module_names() if module_name not in sys.modules]
        self.assertEqual(missing, [], f"Test modules missing from Kit discovery: {missing}")

    async def test_every_test_class_is_exported_once(self) -> None:
        """Root exports must contain every test class without name collisions."""
        root_module = sys.modules[self._PACKAGE]
        root_classes = {
            name: value
            for name, value in vars(root_module).items()
            if inspect.isclass(value) and name.startswith("Test")
        }
        missing = []
        collisions = []
        seen_names = {}
        for module_name in self._test_module_names():
            module = sys.modules[module_name]
            for class_name, test_class in inspect.getmembers(module, inspect.isclass):
                if not class_name.startswith("Test") or test_class.__module__ != module_name:
                    continue
                previous = seen_names.setdefault(class_name, module_name)
                if previous != module_name:
                    collisions.append(f"{class_name}: {previous}, {module_name}")
                if root_classes.get(class_name) is not test_class:
                    missing.append(f"{module_name}.{class_name}")
        self.assertEqual(collisions, [], f"Duplicate root test class names: {collisions}")
        self.assertEqual(missing, [], f"Test classes missing from root exports: {missing}")
