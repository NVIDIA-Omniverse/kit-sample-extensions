## Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

"""Logic and Data class module

Classes:

    Variant - Data class for variant items
    Prim - Data class for prim items
    Group - Data class for group items
"""

import typing

import omni.ui as ui


class Variant(ui.AbstractItem):
    """Variant data class"""

    def __init__(self, prim=None, vset=None, vset_name=None, variant_selection=None, group=None):
        """Constructor

        Args:
            label (str): Label to show in ui
            prim_path (str): prim path to the variant
        """
        super(Variant, self).__init__()
        self._name_model = ui.SimpleStringModel(vset_name)
        self._prim = prim
        self._prim_path = prim.GetPath().pathString
        self._vset = vset
        self._vset_name = vset_name
        self._variant_selection = variant_selection
        self._group_path = group

    @property
    def name_model(self) -> ui.SimpleStringModel:
        """Used for the label

        Returns:
            ui.SimpleStringModel: Model to get the value from and also listen to changes to.
        """
        return self._name_model

    @property
    def prim_path(self) -> str:
        """Prim path to the variant

        Returns:
            str: prim path that the variant is created from
        """
        return self._prim_path

    @property
    def group(self) -> str:
        """Path of parent group

        Returns:
            str: returns the collections path of the parent group
        """
        return self._group_path


class Group(ui.AbstractItem):
    """Group data class"""

    def __init__(self, group_name, group_path):
        """Constructor

        Args:
            label (str): Label to show in ui
            prim_path (str): prim path to the variant
        """
        super(Group, self).__init__()
        self._name_model = ui.SimpleStringModel(group_name)
        self._group_name = group_name
        self._group_path = group_path
        self._variants: typing.List[Variant] = []
        self._drop = None

    def add_variant(self, variant: Variant) -> None:
        """Method to add variant to Group

        Args:
            variant (Variant): Variant data to be added to the list
        """
        self._variants.append(variant)

    def remove_variant(self, variant: Variant) -> None:
        """Method to remove variant from Group

        Args:
            variant (Variant): Variant data to be removed from the list
        """
        self._variants.remove(variant)

    @property
    def name_model(self) -> ui.SimpleStringModel:
        """Used for the label

        Returns:
            ui.SimpleStringModel: Model to get the value from and also listen to changes to.
        """
        return self._name_model

    @property
    def group_name(self) -> str:
        """Variant Group name

        Returns:
            str: name of variant group
        """
        return self._group_name

    @property
    def group_path(self) -> str:
        """Variant Group path

        Returns:
            str: Collection path associated with group
        """
        return self._group_path

    @property
    def variants(self) -> typing.List[Variant]:
        """List of variant data for the prim

        Returns:
            typing.List[Variant]: Variant data instances
        """
        return self._variants[:]


class Prim(ui.AbstractItem):
    """Prim data class"""

    def __init__(self, prim_path):
        """Constructor

        Args:
            label (str): Label to show in ui
            prim_path (str): prim path to the prim
        """
        super(Prim, self).__init__()
        self._name_model = ui.SimpleStringModel(prim_path)
        self._selected_model = ui.SimpleBoolModel()
        self._prim_path = prim_path
        self._variants: typing.List[Variant] = []

    def add_variant(self, variant: Variant) -> None:
        """Method to add variant to Prim

        Args:
            variant (Variant): Variant data to be added to the list
        """
        self._variants.append(variant)

    def remove_variant(self, variant: Variant) -> None:
        """Method to remove variant from Prim

        Args:
            variant (Variant): Variant data to be removed from the list
        """
        self._variants.remove(variant)

    @property
    def name_model(self) -> ui.SimpleStringModel:
        """Used for the label

        Returns:
            ui.SimpleStringModel: Model to get the value from and also listen to changes to.
        """
        return self._name_model

    @property
    def selected_model(self) -> ui.SimpleBoolModel:
        """Selected prim data

        Returns:
            ui.SimpleBoolModel: Model to get the value from and also listen to changes to.
        """
        return self._selected_model

    @property
    def prim_path(self) -> str:
        """Prim path to the prim

        Returns:
            str: prim path that the prim is created from
        """
        return self._prim_path

    @property
    def variants(self) -> typing.List[Variant]:
        """List of variant data for the prim

        Returns:
            typing.List[Variant]: Variant data instances
        """
        return self._variants[:]
