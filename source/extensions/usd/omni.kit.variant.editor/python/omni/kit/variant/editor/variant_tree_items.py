# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from enum import IntEnum

import carb
import omni.ui as ui
from pxr import Sdf, Usd

from .list import ListItem


class Column(IntEnum):
    NAME = 1
    TYPE = 2
    ID = 0
    COUNT = 3


class VariantSetCard:
    VARIANTSET = "variantset"

    @staticmethod
    def create(type, **kwargs):
        if type == VariantSetCard.VARIANTSET:
            return VariantSetCard(**kwargs)
        else:
            carb.log_error(f"[variant editor] Unknown variant set card type: {type}")
            return None

    def __init__(self, name: str, path: str):
        self.type = self.VARIANTSET
        self.name = name
        self.path = path


class VariantSetCardItem(ListItem):
    """Single item of VariantSet card"""

    def __init__(self, card: VariantSetCard, index):
        super().__init__([f"{index+1}##int", card.name, card.type])
        self._sub_id = None
        self._sub_name = None
        self._name_model = None  # Cache the name model to prevent creating new instances

        self.data = card

    @property
    def name_model(self):
        # Cache the model to ensure the same instance is used throughout the item's lifecycle
        if self._name_model is None:
            self._name_model = ui.SimpleStringModel(self.data.name)
        else:
            # Sync the cached model with the current data
            if self._name_model.as_string != self.data.name:
                self._name_model.set_value(self.data.name)
        return self._name_model

    @property
    def type_model(self):
        return self.get_value_model(Column.TYPE)

    @property
    def index_model(self):
        return self.get_value_model(Column.ID)

    @property
    def path_model(self):
        return ui.SimpleStringModel(str(self.data.path))

    def _get_values(self, card: VariantSetCard, index):
        return [f"{index}##int", card.name, card.type, card.path]

    def change_index(self, differ):
        self.index_model.set_value(self.index_model.as_int + differ)

    def set_index(self, index):
        self.index_model.set_value(index + 1)

    def subscribe_index_changed_fn(self, fn):
        self._sub_id = self.index_model.subscribe_value_changed_fn(fn)

    def get_value_model(self, index=0):
        if index == Column.NAME:
            return self.name_model
        else:
            return super().get_value_model(index)

    def __repr__(self):
        return f'"{self.index_model.as_string}: {self.name_model.as_string} {self.type_model.as_string} {self.path_model.as_string}"'


class VariantCard:
    VARIANT = "variant"

    @staticmethod
    def create(type, **kwargs):
        if type == VariantCard.VARIANT:
            return VariantCard(**kwargs)
        else:
            carb.log_error(f"[variant editor] Unknown variant card type: {type}")
            return None

    def __init__(self, name: str, path: str, activated=False):
        self.type = self.VARIANT
        self.name = name
        self.path = path
        self.activated = activated


class VariantCardItem(ListItem):
    """Single item of Variant card"""

    def __init__(self, card: VariantCard, index):
        super().__init__([f"{index+1}##int", card.name, card.type])
        self._sub_id = None
        self._name_model = None  # Cache the name model to prevent creating new instances

        self.data = card

    @property
    def name_model(self):
        # Cache the model to ensure the same instance is used throughout the item's lifecycle
        if self._name_model is None:
            self._name_model = ui.SimpleStringModel(self.data.name)
        else:
            # Sync the cached model with the current data
            if self._name_model.as_string != self.data.name:
                self._name_model.set_value(self.data.name)
        return self._name_model

    @property
    def type_model(self):
        return self.get_value_model(Column.TYPE)

    @property
    def index_model(self):
        return self.get_value_model(Column.ID)

    @property
    def path_model(self):
        return ui.SimpleStringModel(str(self.data.path))

    def add_child_item(self, child_item):
        self._children.append(child_item)
        if isinstance(child_item, PrimCardItem):
            self._children.sort(key=self._get_name)

    def _get_name(self, element):
        return element.data.name

    def _get_values(self, card: VariantCard, index):
        return [f"{index}##int", card.name, card.type, card.path]

    def change_index(self, differ):
        self.index_model.set_value(self.index_model.as_int + differ)

    def set_index(self, index):
        self.index_model.set_value(index + 1)

    def subscribe_index_changed_fn(self, fn):
        self._sub_id = self.index_model.subscribe_value_changed_fn(fn)

    def get_value_model(self, index=0):
        if index == Column.NAME:
            return self.name_model
        else:
            return super().get_value_model(index)

    def __repr__(self):
        return f'"{self.index_model.as_string}: {self.name_model.as_string} {self.type_model.as_string} {self.path_model.as_string}"'


class VariantTreeHelperItem(ui.AbstractItem):
    """Helper Item for delegates to draw additional display widgets"""

    def __init__(self):
        super().__init__()

        self._children = []

    def destroy(self): ...

    @property
    def children(self):
        return self._children


# Prim Card Data Structure
class PrimCard:
    PRIM = "prim"

    @staticmethod
    def create(type, **kwargs):
        if type == PrimCard.PRIM:
            return PrimCard(**kwargs)
        else:
            carb.log_error(f"[variant editor] Unknown prim card type: {type}")
            return None

    def __init__(self, name: str, path: str, highlight: bool = False):
        self.type = self.PRIM
        self.name = name
        self.path = path
        self.highlight = highlight


class PrimCardItem(ListItem):
    """Single item of Prim card"""

    def __init__(self, card: PrimCard, index):
        super().__init__([f"{index+1}##int", card.name, card.type, card.path])
        self._sub_id = None

        self.data = card

        # A default VariantTreeHelperItem is inserted as first child item, this is for delegate to draw "add property buttons"
        self._children.append(VariantTreeHelperItem())

    @property
    def name_model(self):
        return ui.SimpleStringModel(self.data.name)

    @property
    def type_model(self):
        return self.get_value_model(Column.TYPE)

    @property
    def index_model(self):
        return self.get_value_model(Column.ID)

    @property
    def path_model(self):
        return ui.SimpleStringModel(self.data.path)

    @property
    def highlight_model(self):
        return ui.SimpleBoolModel(self.data.highlight)

    def add_child_item(self, child_item):
        self._children.append(child_item)
        if isinstance(child_item, PropertyCardItem):
            self._children.sort(key=self._get_name)

    def _get_name(self, element):
        if isinstance(element, VariantTreeHelperItem):
            return "///"
        else:
            return element.data.name

    def _get_values(self, card: PrimCard, index, path, highlight):
        return [f"{index}##int", card.name, card.type, card.path, card.highlight]

    def change_index(self, differ):
        self.index_model.set_value(self.index_model.as_int + differ)

    def set_index(self, index):
        self.index_model.set_value(index + 1)

    def subscribe_index_changed_fn(self, fn):
        self._sub_id = self.index_model.subscribe_value_changed_fn(fn)

    def get_value_model(self, index=0):
        if index == Column.NAME:
            return self.name_model
        else:
            return super().get_value_model(index)

    def __repr__(self):
        return f'"{self.index_model.as_string}: {self.name_model.as_string} {self.type_model.as_string}"'


class PropertyCard:
    PROPERTY = "property"
    REFERENCES = "references"
    PAYLOADS = "payloads"

    @staticmethod
    def create(type, **kwargs):
        if type in [
            PropertyCard.PROPERTY,
            PropertyCard.REFERENCES,
            PropertyCard.PAYLOADS,
        ]:
            return PropertyCard(**kwargs)
        else:
            carb.log_error(f"[variant editor] Unknown property card type: {type}")
            return None

    def __init__(
        self,
        name: str,
        path: str,
        prop: Usd.Property,
        metadata: dict,
        layer: Sdf.Layer,
        prim_path: str,
        references=[],
        payloads=[],
    ):
        self.name = name
        self.metadata = metadata
        self.layer = layer
        self.prim_path = prim_path
        if len(references):
            self.type = self.REFERENCES
            self.prop = ""
            self.path = ""
            self.properties = references
            self.asset_paths = [ref.assetPath for ref in references]
        elif len(payloads):
            self.type = self.PAYLOADS
            self.prop = ""
            self.path = ""
            self.properties = payloads
            self.asset_paths = [pl.assetPath for pl in payloads]
        else:
            self.type = self.PROPERTY
            self.prop = prop
            self.path = path
            self.properties = []
            self.asset_paths = []


class PropertyCardItem(ListItem):
    """Single item of Property card"""

    def __init__(self, card: PropertyCard, index):
        super().__init__(
            [
                f"{index+1}##int",
                card.name,
                card.type,
                card.prop,
                card.path,
                card.layer,
                card.prim_path,
            ]
        )
        self._sub_id = None

        self.data = card
        # Delegate will store attribute models here
        self.attr_model: tuple = None

    def destroy(self):
        if self.attr_model is not None:
            if isinstance(self.attr_model, tuple) or isinstance(self.attr_model, list):
                models = self.attr_model[0]
                if isinstance(models, list):
                    for sub_model in models:
                        if hasattr(sub_model, "destroy"):
                            sub_model.destroy()
                        sub_model = None

                    models.clear()

                else:
                    if hasattr(models, "destroy"):
                        models.destroy()
            else:
                try:
                    self.attr_model.destroy()
                except:
                    pass

            self.attr_model = None

        super().destroy()

    @property
    def name_model(self):
        return ui.SimpleStringModel(self.data.name)

    @property
    def type_model(self):
        return self.get_value_model(Column.TYPE)

    @property
    def index_model(self):
        return self.get_value_model(Column.ID)

    @property
    def path_model(self):
        return ui.SimpleStringModel(str(self.data.path))

    @property
    def prop_model(self):
        return ui.SimpleStringModel(str(self.data.prop))

    @property
    def metadata_model(self):
        return ui.SimpleStringModel(str(self.data.metadata))

    @property
    def layer_model(self):
        return ui.SimpleStringModel(str(self.data.layer))

    @property
    def prim_path_model(self):
        return ui.SimpleStringModel(str(self.data.prim_path))

    def _get_values(self, card: PropertyCard, index):
        return [
            f"{index}##int",
            card.name,
            card.type,
            card.path,
            card.prop,
            card.metadata,
            card.layer,
            card.prim_path,
        ]

    def change_index(self, differ):
        self.index_model.set_value(self.index_model.as_int + differ)

    def set_index(self, index):
        self.index_model.set_value(index + 1)

    def subscribe_index_changed_fn(self, fn):
        self._sub_id = self.index_model.subscribe_value_changed_fn(fn)

    def get_value_model(self, index=0):
        if index == Column.NAME:
            return self.name_model
        else:
            return super().get_value_model(index)

    def __repr__(self):
        return f'"{self.index_model.as_string}: {self.name_model.as_string} {self.type_model.as_string} {self.path_model.as_string} {self.prop_model.as_string} {self.metadata_model.as_string} {self.layer_model.as_string} {self.prim_path_model.as_string}"'
