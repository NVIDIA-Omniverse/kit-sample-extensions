# SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.

from omni.kit.test import AsyncTestCase
from omni.services.core import _encoding, main


class EncoderTestCase(AsyncTestCase):
    """Test case for Omniverse Service encoders."""

    async def test_registering_a_valid_encoder_succeeds(self) -> None:
        """Validate that a valid Omnivers Service encoder does not raise any Exceptions."""

        class CustomEncoder:
            def compress(self, data: str):
                pass  # pragma: no cover

            def decompress(self, data: str):
                pass  # pragma: no cover

        main.register_encoder("custom", CustomEncoder)
        self.assertEqual(_encoding.get_encoder("custom"), CustomEncoder)

    async def test_registering_invalid_encoders_raises_exceptions(self) -> None:
        """Validate that registering encoders not implementing the exected interface raises an Exception."""

        class InvalidEncoderWithMissingCompressAndDecompress:
            """Invalid encoder without both `compress()` and `decompress()` methods."""

            pass  # pragma: no cover

        class InvalidEncoderWithMissingDecompress:
            """Invalid encoder without a `decompress()` method."""

            def compress(self, data: str):
                pass  # pragma: no cover

        class InvalidEncoderWithMissingCompress:
            """Invalid encoder without a `compress()` method."""

            def decompress(self, data: str):
                pass  # pragma: no cover

        for EncoderClass in [
            InvalidEncoderWithMissingCompressAndDecompress,
            InvalidEncoderWithMissingDecompress,
            InvalidEncoderWithMissingCompress,
        ]:
            with self.subTest(EncoderClass=EncoderClass):
                with self.assertRaises(
                    expected_exception=AttributeError,
                    msg="custom is missing the 'compress' or 'decompress' (or both) function. Cannot register encoder.",
                ):
                    main.register_encoder("custom", EncoderClass)

    async def test_retrieving_a_missing_encoder_raises_exception(self) -> None:
        """Validate that retrieving a missing encoder raises an Exception."""
        with self.assertRaises(KeyError):
            _encoding.get_encoder("invalid")
