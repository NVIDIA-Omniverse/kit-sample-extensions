# Copyright (c) 2018-2021, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
from math import *

import omni.ui as ui


class CalculatorModel(ui.AbstractItemModel):
    """
    The model that evals the search request. If the execution is successful,
    it creates a child with the result of the execution.
    """

    class _CalculatorItem(ui.AbstractItem):
        """Simplest item of the model, it only has a name"""

        def __init__(self, text: str):
            super().__init__()
            self.name_model = ui.SimpleStringModel(text)

        def __repr__(self):
            return f'"{self.name_model.as_string}"'

    def __init__(self, *args, **kwargs):
        super().__init__()
        self._children = []
        # We need to keep the filter text to know if we need to update the only
        # child
        self._search_request = None

    def get_item_children(self, item):
        """Returns all the children when the widget asks it"""
        if item is not None:
            return []

        return self._children

    def get_item_value_model_count(self, item):
        """The number of columns"""
        return 1

    def get_item_value_model(self, item, column_id):
        if column_id == 0:
            return item.name_model

    def filter_by_text(self, search_request: str):
        """Called when the user entered something in the search field"""
        # Check if the search request is changed
        if self._search_request == search_request:
            return

        self._search_request = search_request

        if search_request:
            # Execute the search request
            try:
                result = eval(self._search_request)
            except:
                # If something goes wrong, just return empty child
                result = None

            if result is not None:
                self._children = [self._CalculatorItem(str(result))]
            else:
                self._children = []
        else:
            self._children = []

        self._item_changed(None)
