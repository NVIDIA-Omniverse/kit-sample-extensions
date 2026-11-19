# SPDX-FileCopyrightText: Copyright (c) 2021-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.


# The usd_optimize package is deployed at this extension's root (a PEP-420 namespace package).
# Kit's custom importer resolves declared modules by path rather than putting the extension root on
# sys.path, so ensure the root is importable before pulling in usd_optimize.
import os as _os
import sys as _sys

_ext_root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", "..", ".."))
if _ext_root not in _sys.path:
    _sys.path.insert(0, _ext_root)

# Re-expose the operation base module under this extension's product path so that python-implemented
# operations can do `from omni.scene.optimizer.core.operation import Operation`. The implementation
# lives in the external usd_optimize package.
from usd_optimize.core import operation as _operation

# import the core library (now the external usd_optimize package) and expose it as the API
from usd_optimize.impl.core import *

from .scripts.extension import *

_sys.modules[__name__ + ".operation"] = _operation
