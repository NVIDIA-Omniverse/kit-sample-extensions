# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from __future__ import annotations

import pathlib

import omni.kit.test
from omni.asset_validator.core import normalize_url
from omni.asset_validator.tests import (
    AsyncioValidationTestCaseMixin,
    Failure,
    IsAFailure,
    IsAnError,
    IsAWarning,
    ValidationTestCaseMixin,
)

__all__ = ["Failure", "IsAFailure", "IsAWarning", "IsAnError", "ValidationRuleTestCase", "get_url"]


def get_url(relative_path: str | pathlib.Path | None = "") -> str:
    return normalize_url(str(pathlib.Path(__file__).parent.joinpath("data").joinpath(relative_path)))


class ValidationRuleTestCase(omni.kit.test.AsyncTestCase, ValidationTestCaseMixin):
    """
    Specific implementation of ValidationTestCaseMixin for simready tests.
    """


class AsyncValidationRuleTestCase(omni.kit.test.AsyncTestCase, AsyncioValidationTestCaseMixin):
    """
    Specific implementation of AsyncioValidationTestCaseMixin for simready tests.
    """
