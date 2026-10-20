# Copyright (c) 2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from collections import OrderedDict
from typing import List

from omni.kit.core.collection import usd  # TODO: are we happy with this dependency?
from omni.kit.property.usd.usd_property_widget import UsdPropertiesWidget, UsdPropertyUiEntry
from omni.kit.window.property.templates import build_frame_header
from pxr import Sdf, Tf, Usd


class CollectionPropertiesWidget(UsdPropertiesWidget):
    def on_new_payload(self, payload):
        """
        This gets called whenever we click on a tree item in the Collection Widget
        We only want to handle Collection Properties and skip everything else
        """

        # Basic checks
        if not super().on_new_payload(payload):
            return False

        if len(self._payload.get_collection_paths()) == 0:
            return False

        if self._multi_edit:
            paths = self._payload.get_collection_paths()
        else:
            paths = self._payload.get_collection_paths()[-1:]

        for path in paths:
            if not usd.CollectionHelper.is_valid_collection_path(path):
                return False

        return True

    def build_group_frames(self, stage, ungrouped_props: List):
        """
        Args:
            ungrouped_props: the list of collection properties (include, expansionRule etc)

        """
        if self._multi_edit:
            paths = self._payload.get_collection_paths()
        else:
            paths = self._payload.get_collection_paths()[-1:]

        prim_paths = []
        for path in paths:
            prim_paths.append(path.GetPrimPath())

        for prop in ungrouped_props:
            self.build_property_item(stage, prop, prim_paths)

    def build_items(self):
        """
        See SimplePropertyWidget.build_items
        """
        self.reset()

        if len(self._payload.get_collection_paths()) == 0:
            return

        last_prim_or_prop = self._payload.get_collection_paths()[-1]
        coll_helper = usd.CollectionHelper(last_prim_or_prop)
        if not coll_helper.is_valid():
            return

        stage = coll_helper.collection_prim.GetStage()
        if not stage:
            return

        self._listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_usd_changed, stage)
        shared_props = []
        collection_props = usd.CollectionHelper.collection_properties
        for c in collection_props:
            usd_prop = stage.GetPropertyAtPath(Sdf.Path(last_prim_or_prop.pathString + ":" + c))
            if usd_prop.IsValid():
                metadata = usd_prop.GetAllMetadata()
                metadata[Sdf.PropertySpec.DisplayNameKey] = c
                ui_prop = UsdPropertyUiEntry(usd_prop.GetName(), usd_prop.GetDisplayGroup(), metadata, type(usd_prop))
                shared_props.append(ui_prop)

        if not shared_props:
            return

        shared_props = self._customize_props_layout(shared_props)

        grouped_props = OrderedDict()
        ungrouped_props = []

        for prop in shared_props:
            if prop[1] != "":
                grouped_props.setdefault(prop[1], []).append(prop)
            else:
                ungrouped_props.append(prop)

        self.build_group_frames(stage, ungrouped_props)
