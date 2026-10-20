# Copyright (c) 2018-2020, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import weakref
from typing import List, Optional

import omni.usd
from omni.kit.property.usd.prim_selection_payload import PrimSelectionPayload
from pxr import Sdf, Usd

_is_legacy_stage_event_system = False
try:
    from carb.eventdispatcher import get_eventdispatcher
except ImportError:
    _is_legacy_stage_event_system = True


class CollectionSelectionPayload(PrimSelectionPayload):
    """
    A custom payload object that works with USD Collections - not prims.
    It is only interpreted (or interpretable) by the Property Widget in omni.kit.property.collection
    """

    def __init__(self, stage: weakref.ReferenceType(Usd.Stage), collection_paths: List[Sdf.Path]):
        super().__init__(stage, [])
        self._collection_paths = collection_paths

    def get_collection_paths(self) -> List[Sdf.Path]:
        return self._collection_paths

    def __bool__(self):
        return self._stage is not None and self._stage() is not None and len(self._collection_paths) > 0


class SelectionWatch(object):
    """
    The object that update selection in TreeView when the scene selection is
    changed and updated scene selection when TreeView selection is changed.
    """

    def __init__(self, tree_view=None):
        super().__init__()
        self._usd_context = omni.usd.get_context()
        self._selection = None
        self._in_selection = False
        self._tree_view = None
        if self._usd_context is not None:
            self._selection = self._usd_context.get_selection()
            self._subscribe_stage_events()

        if tree_view:
            self.set_tree_view(tree_view)

        self.__filter_string: Optional[str] = None
        # When True, SelectionWatch should consider filtering
        self.__filter_checking: bool = False

    def _subscribe_stage_events(self):
        if self._usd_context:
            global _is_legacy_stage_event_system
            if not _is_legacy_stage_event_system:
                try:
                    # this is not working less than kit sdk 107.3, and we also want this extension to work with  106.5
                    self._stage_sub = get_eventdispatcher().observe_event(
                        observer_name="omni.kit.collection.window:selection_update",
                        event_name=self._usd_context.stage_event_name(omni.usd.StageEventType.SELECTION_CHANGED),
                        on_event=lambda _: self._on_kit_selection_changed(),
                    )
                except AttributeError:
                    _is_legacy_stage_event_system = True
            if _is_legacy_stage_event_system:
                self._stage_sub = self._usd_context.get_stage_event_stream().create_subscription_to_pop(
                    self._on_stage_event, name="omni.kit.collection.window:selection_update"
                )

    def destroy(self):
        if _is_legacy_stage_event_system:
            self._stage_sub.unsubscribe()
        else:
            self._stage_sub.reset()
        self._stage_sub = None
        self._tree_view = None

    def set_tree_view(self, tree_view):
        """Replace TreeView that should show the selection"""
        self._tree_view = tree_view
        self._tree_view.set_selection_changed_fn(self._on_widget_selection_changed)
        self._last_selected_prim_paths = None
        self._on_kit_selection_changed()

    def set_filtering(self, filter_string: Optional[str]):
        if filter_string:
            self.__filter_string = filter_string.lower()
        else:
            self.__filter_string = filter_string

    def enable_filtering_checking(self, enable: bool):
        """
        When `enable` is True, SelectionWatch should consider filtering when
        changing Kit's selection.
        """
        self.__filter_checking = enable

    def _on_stage_event(self, event):
        """Called by stage_event_stream"""
        if event.type == int(omni.usd.StageEventType.SELECTION_CHANGED):
            self._on_kit_selection_changed()

    def _on_kit_selection_changed(self):
        """Send the selection from Kit to TreeView"""
        if not self._tree_view or self._in_selection:
            return

        # Make sure it's a new selection. It happens that omni.usd sends the same selection twice. No sorting because
        # the order of selection is important.
        prim_paths = self._selection.get_selected_prim_paths()
        if prim_paths == self._last_selected_prim_paths:
            return

        self._last_selected_prim_paths = prim_paths

        # Pump the changes to the model because to select something, TreeView should be updated.
        self._tree_view.model.update_dirty()

        selection = []
        for path in prim_paths:
            # Get the selected item and its parents. Expand all the parents of the new selection.
            full_chain = self._tree_view.model.find_full_chain(path)
            # When the new object is created, omni.usd sends the selection is changed before the object appears in the
            # stage and it means we can't select it. In this way it's better to return because we don't have the item
            # in the model yet.
            # TODO: Use UsdNotice to track if the object is created.
            if not full_chain or full_chain[-1].path != path:
                return
            if full_chain:
                for item in full_chain[:-1]:
                    self._tree_view.set_expanded(item, True, False)
                # Save the last item in the chain. It's the selected item
                selection.append(full_chain[-1])

        # Send all of this to TreeView.
        self._in_selection = True
        self._tree_view.selection = selection
        self._in_selection = False

    def _notify_property_window(self, prim_paths: List[str]):
        import weakref

        import omni.kit.window.property as p

        # TODO _property_window_context_id
        w = p.get_window()
        if w:
            stage = weakref.ref(self._usd_context.get_stage())
            selected_prim_paths = [Sdf.Path(path).GetPrimPath() for path in prim_paths]
            selected_collections = [
                Sdf.Path(path) for path in prim_paths if Usd.CollectionAPI.IsCollectionAPIPath(path)
            ]
            if selected_collections:
                payload = CollectionSelectionPayload(stage, selected_collections)
                w.notify("collection", payload)
            else:
                payload = PrimSelectionPayload(stage, selected_prim_paths)
                w.notify("prim", payload)

    def _on_widget_selection_changed(self, selection):
        """Send the selection from TreeView to Kit"""

        if self._in_selection:
            return

        prim_paths = [item.path.pathString for item in selection if item]

        # Filter selection
        if self.__filter_string or self.__filter_checking:
            # Check if the selected prims are filtered and re-select filtered items only if necessary.
            filtered_paths = [item.path.pathString for item in selection if item and item.filtered]
            if filtered_paths != prim_paths:
                filtered_selection = [item for item in selection if item and item.path in filtered_paths]
                self._tree_view.selection = filtered_selection
                return

        # Deselect instance proxy items if they was selected
        items_without_proxy = [item for item in selection if item]
        prim_paths_without_proxy = [str(item.path) for item in items_without_proxy]
        if prim_paths != prim_paths_without_proxy:
            self._tree_view.selection = items_without_proxy
            prim_paths = prim_paths_without_proxy

        if prim_paths == self._last_selected_prim_paths:
            return

        self._last_selected_prim_paths = prim_paths

        self._notify_property_window(prim_paths)

        # Don't use Kit selection if we have a collection selected, as it stops us from
        # being able to single select collections and see the property view.
        non_prim_paths = [p for p in prim_paths if not Sdf.Path(p).IsPrimPath()]
        if len(non_prim_paths) == 0:
            # Send the selection to Kit
            self._in_selection = True
            self._selection.set_selected_prim_paths(prim_paths, False)
            self._in_selection = False
