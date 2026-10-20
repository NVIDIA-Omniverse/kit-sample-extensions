# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: LicenseRef-NvidiaProprietary
#
# NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
# property and proprietary rights in and to this material, related
# documentation and any modifications thereto. Any use, reproduction,
# disclosure or distribution of this material and related documentation
# without an express license agreement from NVIDIA CORPORATION or
# its affiliates is strictly prohibited.
import carb
from omni.kit.window.preferences import get_instance as preferences_get_instance
from omni.kit.window.preferences import get_page_list as preferences_get_page_list
from omni.kit.window.preferences import register_page as preferences_add_page
from omni.kit.window.preferences import unregister_page as preferences_remove_page


def get_page_titles():
    pages = preferences_get_page_list()
    titles = [page.get_title() for page in pages]
    return titles


class PreferencesHelper:
    @staticmethod
    def add_page(page):
        preferences_add_page(page)

    @staticmethod
    def remove_page(page):
        preferences_remove_page(page)

    @staticmethod
    def find_page(title):
        pages = preferences_get_page_list()
        for page in pages:
            if page.get_title() == title:
                return page
        return None

    @staticmethod
    def get_page(index):
        return preferences_get_page_list()[index]

    @staticmethod
    def show_page(title):
        inst = preferences_get_instance()
        if not inst:
            carb.log_error("Preferences extension is not loaded yet")
            return False

        page = PreferencesHelper.find_page(title)
        if page:
            inst.select_page(page)
            if not inst._window_is_visible:
                inst._toggle_preferences_window()
        else:
            carb.log_error(f"Preferences page {title} not found!")
