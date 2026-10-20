# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
from omni.kit.search_core import AbstractSearchItem


class SearchServiceItem(AbstractSearchItem):
    def __init__(self, dir_path, relative_path, date, size, is_folder):
        super().__init__()
        self._dir_path = dir_path
        self._relative_path = relative_path
        self._size = size
        self._date = date
        self._is_folder = is_folder

    @property
    def path(self):
        return self._dir_path + self._relative_path

    @property
    def name(self):
        return self._relative_path

    @property
    def date(self):
        return self._date

    @property
    def size(self):
        return self._size

    @property
    def is_folder(self):
        return self._is_folder
