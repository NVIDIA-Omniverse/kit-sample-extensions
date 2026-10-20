# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

"""Tests to validate that template USD files have correct attribute types.

These tests prevent regressions of OMPE-76857 where the ``enable_emission``
parameter was incorrectly typed as ``float`` in the thumbnail template USD
files. MDL expects ``bool`` for this parameter. A type mismatch causes
``[UsdToMdl] Reached invalid assignment`` error spam during thumbnail
generation.

The tests also validate the configurable timeout setting to ensure the
default is high enough for material compilation scenarios.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import carb.settings
import omni.kit.test
from pxr import Sdf, Usd

from ..constants import DEFAULT_TIMEOUT, SETTING_TIMEOUT

CURRENT_PATH = Path(__file__).parent
DATA_PATH = CURRENT_PATH.parent.parent.parent.parent.parent.joinpath("data")

# The production template assets live under data/template/ since
# OMPE-83737 (the former data/tests/template/SubUSDs/ copies were removed on
# main). We keep the test template directory entries below in case a future
# change restores a test-only template; they simply skip if the directory
# is missing.
PRODUCTION_TEMPLATE_DIR = DATA_PATH / "template"
PRODUCTION_TEMPLATE_USD = PRODUCTION_TEMPLATE_DIR / "Material_Default.thumbnail.usd"
TEST_TEMPLATE_DIR = DATA_PATH / "tests" / "template"
TEST_TEMPLATE_USD = TEST_TEMPLATE_DIR / "Material_Default.thumbnail.usd"


class TestTemplateValidation(omni.kit.test.AsyncTestCase):
    """Validate that thumbnail template USD files have correct attribute types."""

    # Map of attribute names to their expected USD types.
    # MDL bool parameters must be authored as bool in USD, not float.
    EXPECTED_TYPES = {
        "inputs:enable_emission": Sdf.ValueTypeNames.Bool,
    }

    def _collect_usd_files(self, root_dir: str):
        """Collect all USD files under a directory."""
        usd_files = []
        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                if filename.endswith((".usd", ".usda", ".usdc")):
                    usd_files.append(os.path.join(dirpath, filename))
        return usd_files

    def _validate_attribute_types_in_layer(self, layer_path: str):
        """Validate attribute types in a single USD layer.

        Uses the Sdf layer API (not composed Usd.Stage) so we check the
        actual authored opinions, including those in referenced sub-layers.
        This catches type mismatches at the source rather than relying on
        composition to propagate fixes.

        Returns:
            list: A list of error strings for any type mismatches found.
        """
        errors = []
        layer = Sdf.Layer.FindOrOpen(layer_path)
        if not layer:
            return errors

        def _traverse(prim_path):
            prim_spec = layer.GetPrimAtPath(prim_path)
            if prim_spec is None:
                return

            for attr_name, expected_type in self.EXPECTED_TYPES.items():
                attr_spec = prim_spec.attributes.get(attr_name)
                if attr_spec is not None and attr_spec.typeName != expected_type:
                    errors.append(
                        f"{layer_path}: {prim_path}.{attr_name} has type "
                        f"'{attr_spec.typeName}' but expected '{expected_type}'. "
                        f"MDL requires the correct type to avoid UsdToMdl assignment errors."
                    )

            for child_name in prim_spec.nameChildren.keys():
                _traverse(prim_path.AppendChild(child_name))

        for prim_name in layer.rootPrims.keys():
            _traverse(Sdf.Path(f"/{prim_name}"))

        return errors

    def _validate_attribute_types_in_composed_stage(self, stage_path: str):
        """Validate attribute types via a composed Usd.Stage.

        This catches cases where composition (references/payloads) might
        accidentally bring in a wrongly-typed attribute from a sub-layer
        that was not covered by the per-layer validation.

        Returns:
            list: A list of error strings for any type mismatches found.
        """
        errors = []
        stage = Usd.Stage.Open(stage_path)
        if not stage:
            errors.append(f"{stage_path}: failed to open stage")
            return errors

        for prim in stage.Traverse():
            for attr_name, expected_type in self.EXPECTED_TYPES.items():
                attr = prim.GetAttribute(attr_name)
                if attr and attr.IsValid():
                    actual_type = attr.GetTypeName()
                    if actual_type != expected_type:
                        errors.append(
                            f"{stage_path}: {prim.GetPath()}.{attr_name} "
                            f"type={actual_type}, expected={expected_type}"
                        )
        return errors

    async def test_production_template_attribute_types(self):
        """Verify production template USD files have correct attribute types.

        OMPE-76857: The enable_emission parameter must be bool (not float) to
        match MDL expectations. A float type causes [UsdToMdl] error spam.
        This inspects each .usd file under data/template/ via the Sdf API so
        wrongly-typed opinions are caught at the source layer, regardless of
        composition.
        """
        if not PRODUCTION_TEMPLATE_DIR.is_dir():
            self.fail(f"Production template directory is missing: {PRODUCTION_TEMPLATE_DIR}")

        usd_files = self._collect_usd_files(str(PRODUCTION_TEMPLATE_DIR))
        self.assertGreater(len(usd_files), 0, "No USD files found in production template directory")

        all_errors = []
        for usd_file in usd_files:
            all_errors.extend(self._validate_attribute_types_in_layer(usd_file))

        self.assertEqual(
            all_errors,
            [],
            f"Found {len(all_errors)} type mismatch(es) in production templates:\n" + "\n".join(all_errors),
        )

    async def test_production_composed_template_attribute_types(self):
        """Verify the composed production template has no wrongly-typed attrs.

        This complements ``test_production_template_attribute_types`` (which
        inspects each layer in isolation) by opening the top-level
        ``Material_Default.thumbnail.usd`` as a composed ``Usd.Stage``. If a
        reference or payload brings in an ``inputs:enable_emission`` of the
        wrong type, it is caught here even if the per-layer check misses it.

        Addresses review comment 2 (OMPE-76857 MR !275): explicitly validate
        the PRODUCTION ``Material_Default.thumbnail.usd`` (not just the test
        copy) so that a future regression of any referenced SubUSD is caught.
        """
        if not PRODUCTION_TEMPLATE_USD.exists():
            self.fail(f"Production template is missing: {PRODUCTION_TEMPLATE_USD}")

        errors = self._validate_attribute_types_in_composed_stage(str(PRODUCTION_TEMPLATE_USD))
        self.assertEqual(
            errors,
            [],
            f"Found {len(errors)} type mismatch(es) in composed production template:\n" + "\n".join(errors),
        )

    async def test_test_template_attribute_types(self):
        """Verify test template USD files have correct attribute types.

        Test templates should also have correct types so that tests exercise
        the same code paths as production without masking errors. If the
        test template directory does not exist on the current branch (it was
        consolidated into ``data/template`` on main by OMPE-83737), this
        test is skipped rather than failed.
        """
        if not TEST_TEMPLATE_DIR.is_dir():
            self.skipTest(f"Test template directory not present (consolidated into {PRODUCTION_TEMPLATE_DIR})")

        usd_files = self._collect_usd_files(str(TEST_TEMPLATE_DIR))
        self.assertGreater(len(usd_files), 0, "No USD files found in test template directory")

        all_errors = []
        for usd_file in usd_files:
            all_errors.extend(self._validate_attribute_types_in_layer(usd_file))

        self.assertEqual(
            all_errors,
            [],
            f"Found {len(all_errors)} type mismatch(es) in test templates:\n" + "\n".join(all_errors),
        )

    async def test_composed_template_attribute_types(self):
        """Verify that composed (referenced) prims also have correct types.

        The main Material_Default.thumbnail.usd references sub-USDs. After
        composition, all enable_emission attributes must resolve to bool.
        Checks the test template if it exists, otherwise skips (the
        production-level composed check is covered by
        ``test_production_composed_template_attribute_types``).
        """
        if not TEST_TEMPLATE_USD.exists():
            self.skipTest(
                "Test template not found (consolidated into data/template/ on main); "
                "production-level composition is covered by "
                "test_production_composed_template_attribute_types"
            )

        errors = self._validate_attribute_types_in_composed_stage(str(TEST_TEMPLATE_USD))
        self.assertEqual(
            errors,
            [],
            f"Found {len(errors)} type mismatch(es) in composed test template:\n" + "\n".join(errors),
        )


class TestTimeoutSetting(omni.kit.test.AsyncTestCase):
    """Validate the configurable timeout setting for thumbnail generation."""

    async def test_default_timeout_is_sufficient(self):
        """Verify the default timeout is at least 60 seconds.

        OMPE-76857: The previous default of 20s was too short for MDL material
        compilation, causing frequent timeouts and flaky thumbnail generation.
        The default should be generous enough for first-time compilation.
        """
        self.assertGreaterEqual(
            DEFAULT_TIMEOUT,
            60,
            f"Default timeout ({DEFAULT_TIMEOUT}s) is too low. MDL material "
            f"compilation can take significantly longer than 20 seconds.",
        )

    async def test_timeout_setting_is_registered(self):
        """Verify the timeout setting exists and has a reasonable default."""
        settings = carb.settings.get_settings()
        timeout = settings.get(SETTING_TIMEOUT)
        # The setting should exist and be a positive number
        self.assertIsNotNone(timeout, f"Setting {SETTING_TIMEOUT} not found")
        self.assertGreater(timeout, 0, f"Timeout setting must be positive, got {timeout}")
        self.assertGreaterEqual(
            timeout,
            60,
            f"Timeout setting ({timeout}s) should be at least 60s for material compilation",
        )

    async def test_thumbnail_manager_uses_setting(self):
        """Verify ThumbnailManager reads the timeout from the extension setting.

        Addresses review comments 3 (note_46871699, Roman Zulak) and 6
        (note_46847923, CodeRabbit):

        * Pick ``test_timeout`` dynamically so it is guaranteed to differ
          from both the current setting value and ``DEFAULT_TIMEOUT``. This
          prevents the test from trivially passing if the setting happened
          to already equal the hard-coded test value.
        * Do not inspect ``_work_queue`` with ``get_nowait`` - that races
          with the ``_run`` task started in ``__init__`` which is already
          awaiting ``_work_queue.get()`` at the time we call ``put``.
          Instead, spy on ``_work_queue.put_nowait`` and read the resolved
          timeout from the call arguments, which is deterministic and
          uncoupled from the worker loop.
        """
        from ..thumbnail_manager import ThumbnailManager

        settings = carb.settings.get_settings()
        original_timeout = settings.get(SETTING_TIMEOUT)

        # Pick a value that is guaranteed to be distinct from both the
        # current setting and the default, so ''equal to test_timeout''
        # actually proves the manager used our value.
        base = original_timeout if isinstance(original_timeout, (int, float)) else 0
        test_timeout = int(max(base, DEFAULT_TIMEOUT)) + 47
        self.assertNotEqual(test_timeout, original_timeout)
        self.assertNotEqual(test_timeout, DEFAULT_TIMEOUT)

        try:
            settings.set(SETTING_TIMEOUT, test_timeout)

            manager = ThumbnailManager()
            try:
                # Cancel the _run task immediately so it cannot race with us
                # and consume the item off _work_queue before we inspect it.
                manager._run_task.cancel()

                # Spy on _work_queue.put_nowait so we can read exactly what
                # the manager enqueued.
                recorded = []
                real_put_nowait = manager._work_queue.put_nowait

                def spy_put_nowait(item):
                    recorded.append(item)
                    return real_put_nowait(item)

                with patch.object(manager._work_queue, "put_nowait", side_effect=spy_put_nowait):
                    mock_generator = MagicMock()
                    manager.put(mock_generator)  # no explicit timeout

                self.assertEqual(len(recorded), 1, f"Expected one enqueue, got {len(recorded)}")
                generator, actual_timeout, retry = recorded[0]
                self.assertIs(generator, mock_generator)
                self.assertEqual(
                    actual_timeout,
                    test_timeout,
                    f"Expected timeout {test_timeout} from settings, got {actual_timeout}",
                )
                self.assertEqual(retry, 0)
            finally:
                manager.destroy()
        finally:
            settings.set(SETTING_TIMEOUT, original_timeout)

    async def test_thumbnail_manager_preserves_explicit_zero(self):
        """Review comment 1: timeout=0 from the setting must NOT fall back to the default.

        A user who sets ``/exts/omni.kit.thumbnails.mdl/timeout = 0`` to
        disable the timeout should see the resolved timeout be exactly 0,
        not ``DEFAULT_TIMEOUT``.
        """
        from ..thumbnail_manager import ThumbnailManager

        settings = carb.settings.get_settings()
        original_timeout = settings.get(SETTING_TIMEOUT)
        try:
            settings.set(SETTING_TIMEOUT, 0)

            manager = ThumbnailManager()
            try:
                # Prevent the _run task from consuming the item before we look.
                manager._run_task.cancel()

                recorded = []
                real_put_nowait = manager._work_queue.put_nowait

                def spy_put_nowait(item):
                    recorded.append(item)
                    return real_put_nowait(item)

                with patch.object(manager._work_queue, "put_nowait", side_effect=spy_put_nowait):
                    manager.put(MagicMock())

                self.assertEqual(len(recorded), 1)
                _, actual_timeout, _ = recorded[0]
                self.assertEqual(
                    actual_timeout,
                    0,
                    "Explicit timeout=0 setting must be preserved (means 'disable timeout'), "
                    "not replaced by DEFAULT_TIMEOUT.",
                )
            finally:
                manager.destroy()
        finally:
            settings.set(SETTING_TIMEOUT, original_timeout)
