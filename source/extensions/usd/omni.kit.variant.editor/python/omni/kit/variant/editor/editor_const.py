# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from copy import deepcopy

import omni.kit.app

# Paths
PATH_EXTENSION = omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
PERSISTENT_SETTINGS_PREFIX = "/persistent"
SETTINGS_VEDITOR_ROOT = f"{PERSISTENT_SETTINGS_PREFIX}/exts/omni.kit.variant.editor/"
ADD_PROPS_TO_ALL_VARIANTS_SETTING = f"{SETTINGS_VEDITOR_ROOT}add_props_to_all_variants"
CREATE_VISIBILITY_BY_DEFAULT_SETTING = f"{SETTINGS_VEDITOR_ROOT}create_visibility_by_default"


# Defaults
DEFAULT_ROOT_PRIM_PATH = "/World"
DEFAULT_VARIANT_SET_NAME = "Variant_Set"
DEFAULT_VARIANT_NAME = "Variant"
DEFAULT_VARIANT_SET_LIST = []
DEFAULT_VARIANT_LIST = []
DEFAULT_PRIM_LIST = []
DEFAULT_PROPERTY_LIST = []

# Default Tool Value Names
NAME_ROOT_PRIM_PATH = "root_prim_path"
NAME_VARIANT_SET_LIST = "variant_set_list"
NAME_VARIANT_LIST = "variant_list"
NAME_PRIM_LIST = "prim_list"
NAME_PROPERTY_LIST = "property_list"


class EditorParams:
    def __init__(self):
        self.reset_to_defaults()

    def reset_to_defaults(self):
        self._values = {}
        self._values[NAME_VARIANT_SET_LIST] = DEFAULT_VARIANT_SET_LIST
        self._values[NAME_VARIANT_LIST] = DEFAULT_VARIANT_LIST
        self._values[NAME_PRIM_LIST] = DEFAULT_PRIM_LIST
        self._values[NAME_PROPERTY_LIST] = DEFAULT_PROPERTY_LIST

    def get_defaults(self):
        if not self._values:
            self.reset_to_defaults()
        return deepcopy(self._values)
