# Copyright (c) 2018-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#


from typing import Type


class Delegate:

    widget_types_by_item_type = {}

    @classmethod
    def register_type(cls, widget_type, item_type):
        """
        Registers a new widget type for a given item type.

        :param widget_type: The widget class to register.
        :param item_type: The item class to associate with the widget.
        :return: A TypeRegistry instance that handles adding/removing the mapping.
        """

        class TypeRegistry:
            def __init__(self):
                # Add the mapping to the widget_types_by_item_type dictionary.
                cls.widget_types_by_item_type[item_type] = widget_type

            def __del__(self):
                # Remove the mapping from the widget_types_by_item_type dictionary.
                del cls.widget_types_by_item_type[item_type]

        # Return an instance of the TypeRegistry class.
        return TypeRegistry()

    @classmethod
    def get_widget(cls, item) -> Type:
        """
        Finds the widget class for a given item class, taking inheritance into account.

        :param item_type: The item class to find the associated widget class for.
        :return: The widget class associated with the item class, or None if not found.
        """
        # Iterate over the base classes of the item_type.
        for base_type in type(item).mro():
            # If a widget type is found for the current base class, return it.
            if base_type in cls.widget_types_by_item_type:
                return cls.widget_types_by_item_type[base_type]

        # If no widget type is found for any of the base classes, return None.
        return None
