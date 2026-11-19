# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
from .test_default_delegate import TestDelegate
# The example-derived fixture suite is internal; public source exports retain TestDelegate.
from pathlib import Path

if Path(__file__).with_name("test_delegate.py").is_file():
    from .test_delegate import TestDefaultDelegate
