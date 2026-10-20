# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from unittest.mock import Mock

import omni.kit.test
from omni.asset_validator.ui import ProgressModel


class ProgressModelTest(omni.kit.test.AsyncTestCase):
    def setUp(self):
        self.model = ProgressModel()

    def test_initial_value(self):
        self.assertEqual(self.model.get_value_as_float(), 0.0)
        self.assertEqual(self.model.get_value_as_string(), "Computing dependencies")

    def test_set_and_get_value(self):
        self.model.set_value(0.0)
        self.assertEqual(self.model.get_value_as_float(), 0.0)
        self.assertEqual(self.model.get_value_as_string(), "0 %")

        self.model.set_value(0.5)
        self.assertAlmostEqual(self.model.get_value_as_float(), 0.5)
        self.assertEqual(self.model.get_value_as_string(), "50 %")

        self.model.set_value(1.0)
        self.assertEqual(self.model.get_value_as_float(), 1.0)
        self.assertEqual(self.model.get_value_as_string(), "100 %")

    def test_set_value_precision(self):
        func = Mock()
        _subscription = self.model.subscribe_value_changed_fn(func)

        self.model.set_value(0.1234)
        self.model.set_value(0.1249)
        func.assert_called_once()
