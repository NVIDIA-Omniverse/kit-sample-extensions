# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import asyncio
import weakref
from typing import Any, Callable, Union

import carb
import omni.client.utils as clientutils
import omni.kit.usd.layers as layers
import omni.ui as ui
import omni.usd
from carb.eventdispatcher import get_eventdispatcher
from omni.kit.property.usd.prim_selection_payload import PrimSelectionPayload
from omni.kit.property.usd.references_widget import (
    PayloadReferenceWidget,
    _get_plus_glyph,
)
from omni.kit.window.file_importer import get_file_importer
from pxr import Sdf, Usd

from . import ui_const as ui_c
from .asset_filepicker import replace_query, show_asset_file_picker
from .core import VariantEditorCore
from .variant_property_widget_builder import UsdVariantPropertiesWidgetBuilder
from .variant_tree import VariantTreeModel

DEFAULT_PRIM_TAG = "<Default Prim>"
REF_LABEL_WIDTH = 80
DEFAULT_FILE_EXTS = ("*.*", "All Files")

try:
    from omni.kit.usd.layers import layer_event_name

    _is_legacy_layer_event = False
except ImportError:
    _is_legacy_layer_event = True


# Pick asset for new References or Payloads
async def pick_ref_asset(model: VariantTreeModel):
    def replace_query(url, new_query):
        client_url = omni.client.break_url(url)
        return omni.client.make_url(
            scheme=client_url.scheme,
            user=client_url.user,
            host=client_url.host,
            port=client_url.port,
            path=client_url.path,
            query=new_query,
            fragment=client_url.fragment,
        )

    fallback = model._editor_core._stage.GetRootLayer().identifier
    nav_layer = model._editor_core._stage.GetRootLayer()
    navigate_to = None
    layer_weak = None

    multi_selection = False
    stage = model._editor_core._stage
    if navigate_to is None:
        if stage and not stage.GetRootLayer().anonymous:
            fallback = stage.GetRootLayer().identifier
    if layer_weak:
        layer = layer_weak()
        if layer:
            navigate_to = nav_layer.ComputeAbsolutePath(navigate_to)
    if navigate_to:
        navigate_to = replace_query(navigate_to, None)

    file_importer = get_file_importer()
    if file_importer:
        file_exts = (DEFAULT_FILE_EXTS,)

        f = asyncio.Future()

        async def on_import(filename, dirname, selections=[]):
            paths = selections.copy()
            if not paths:
                paths.append(omni.client.combine_urls(dirname, filename))
            paths.sort()
            if not multi_selection:
                paths = paths[-1:]

            async def check_paths(paths):
                for path in paths:
                    result, entry = await omni.client.stat_async(path)
                    if result == omni.client.Result.OK:
                        if (
                            file_exts
                            and file_exts != (DEFAULT_FILE_EXTS,)
                            and entry.flags & omni.client.ItemFlags.CAN_HAVE_CHILDREN
                        ):
                            carb.log_warn("Please select a file, not a folder!")
                    else:
                        carb.log_warn(f"Selected file {path} does not exist!")
                        return

            await check_paths(paths)

            result = paths
            f.set_result(result)

    file_importer.show_window(
        title="Select Reference",
        import_button_label="Select",
        import_handler=lambda *args, **kwargs: asyncio.ensure_future(on_import(*args, **kwargs)),
        file_extension_types=file_exts,
        filename_url=navigate_to,
    )

    if fallback and not file_importer._dialog.get_current_directory():
        file_importer._dialog.show(fallback)

    return await f


# implement widget for Payloads and References in variant editor, using PayloadReferenceWidget code as much as possible
class UsdVariantPayloadReferenceWidget(PayloadReferenceWidget):
    class DummyPayRefs:
        def __init__(self, widget):
            self._widget = widget

        def GetPrim(self):
            return self._widget._get_prim(None)

    def __init__(
        self,
        model: VariantTreeModel,
        item,
        variant_owner_prim_path: Sdf.Path,
        use_payloads=False,
    ):
        # just do PayloadReferenceWidget.__init__(), but remove its' side effect of PrimPathWidget.add_button_menu_entry()
        # It is not a blackbox reuse, it is not graceful, but I have to do it.
        super().__init__(use_payloads)
        from omni.kit.property.usd import PrimPathWidget

        menu_entries = PrimPathWidget.get_button_menu_entries()
        if menu_entries:  # in case PrimPathWidget does not exist
            just_added = menu_entries[-1]
            PrimPathWidget.remove_button_menu_entry(just_added)

        self._editor_core = VariantEditorCore.get_instance()
        self._variant_owner_prim_path = variant_owner_prim_path  # todo vset.GetPrim().GetPath()
        self._model = model
        self._item = item
        self._layers_event_subs = []

    def clean(self):
        super().clean()
        if self._layers_event_subs:
            self._layers_event_subs.clear()
            self._layers_event_subs = None

    def get_active_variant_set(self):
        vset_name = self._editor_core._get_active_variant_set()
        vset = self._editor_core._get_variant_set_by_name(vset_name)
        return vset_name, vset

    # override PayloadReferenceWidget.on_new_payload
    def on_new_payload(self, payload: PrimSelectionPayload) -> bool:
        """
        See PropertyWidget.on_new_payload
        """
        # skip {PayloadReferenceWidget}.on_new_payload(), {PayloadReferenceWidget}.super().on_new_payload()
        if not super(PayloadReferenceWidget, self).on_new_payload(payload):
            return False

        if len(payload.get_paths()) == 0:
            return False

        for pr in payload.get_paths():
            if self._use_payloads:
                if type(pr) != Sdf.Payload:
                    return False
            else:
                if type(pr) != Sdf.Reference:
                    return False

        return True

    # like PayloadReferenceWidget.build_items()
    def build_items(self):
        self.reset()

        self._payrefs = self.DummyPayRefs(self)
        self._ref_and_layers = []
        for pr in self._payload.get_paths():
            if self._use_payloads:
                if type(pr) != Sdf.Payload:
                    carb.log_error("Unexpected code path in UsdVariantPayloadReferenceWidget.build_items()")
            else:
                if type(pr) != Sdf.Reference:
                    carb.log_error("Unexpected code path in UsdVariantPayloadReferenceWidget.build_items()")
            self._ref_and_layers.append((pr, self._editor_core._get_edit_target_layer()))

        # no vertical spacing for this VStack to make live sessions flush with reference/payload.
        with ui.VStack(height=0, spacing=0, name="frame_v_stack"):
            if len(self._ref_and_layers):
                if self._payload_loaded_cb:
                    self._payload_loaded_cb.enabled = True

                usd_context = omni.usd.get_context_from_stage(self._payload.get_stage())
                self._layers_interface = layers.get_layers(usd_context) if usd_context else None
                if self._layers_interface is not None:
                    self._live_syncing = self._layers_interface.get_live_syncing()
                    self._layers_state = self._layers_interface.get_layers_state()
                    if _is_legacy_layer_event:
                        self._layers_event_sub = self._layers_interface.get_event_stream().create_subscription_to_pop(
                            self._on_layer_event, name="Variant Editor"
                        )
                    else:
                        self._layers_event_subs = [
                            get_eventdispatcher().observe_event(
                                observer_name="omni.kit.variant.editor:UsdVariantPayloadReferenceWidget",
                                event_name=layers.layer_event_name(event),
                                on_event=func,
                                filter=self._layers_interface.get_event_key(),
                            )
                            for event, func in (
                                (
                                    layers.LayerEventType.LIVE_SESSION_LIST_CHANGED,
                                    lambda _: self._update_session_widget_states(),
                                ),
                                (
                                    layers.LayerEventType.OUTDATE_STATE_CHANGED,
                                    lambda _: self._on_outdate_state_changed(),
                                ),
                            )
                        ]

                    auto_reload_ids = self._layers_state.get_auto_reload_layers()
                    outdated_layer_ids = self._layers_state.get_outdated_non_sublayer_identifiers()
                else:
                    # No Layers interface resolved: skip the subscriptions rather than
                    # dereferencing None. _live_syncing / _layers_state must still be set,
                    # they are read unconditionally further down this method.
                    carb.log_info(
                        "Variant Editor could not resolve a Layers interface for the "
                        "reference/payload widget; live-session state is not tracked."
                    )
                    self._live_syncing = None
                    self._layers_state = None
                    auto_reload_ids = []
                    outdated_layer_ids = []

                for ref, layer in self._ref_and_layers:
                    self._abs_path = (
                        omni.client.combine_urls(layer.identifier, ref.assetPath)
                        if len(ref.assetPath)
                        else ref.assetPath
                    )
                    if not self._editor_core.validate_variant_edit(False):
                        self._in_sess = True
                    else:
                        self._in_sess = (
                            self._live_syncing.is_prim_in_live_session(self._variant_owner_prim_path, self._abs_path)
                            if self._live_syncing
                            else False
                        )
                    self._is_live = (
                        self._live_syncing.is_live_session_layer(self._abs_path) if self._live_syncing else False
                    )
                    self._outdated = self._abs_path in outdated_layer_ids
                    self._auto_reload = self._abs_path in auto_reload_ids
                    self._build_payload_reference(ref, layer)
                    if self._in_sess and self._payload_loaded_cb:
                        self._payload_loaded_cb.enabled = False

            async def on_add_payload_reference():
                if not self._editor_core.validate_variant_edit():
                    return

                asset_path = await pick_ref_asset(self._model)
                if asset_path:
                    parent_prim_item = self._model.get_parent_item(self._item)
                    self._model.add_ref_or_payload_variant_to_prim(
                        parent_prim_item,
                        self._variant_owner_prim_path,
                        asset_path,
                        "Payload" if self._use_payloads else "Reference",
                    )
                else:
                    carb.log_warn("No valid asset path provided.")

            ui.Button(
                (f"{_get_plus_glyph()} Add Payload" if self._use_payloads else f"{_get_plus_glyph()} Add Reference"),
                identifier=("Variant Add Payload" if self._use_payloads else "Variant Add Reference"),  # for unit test
                clicked_fn=lambda: asyncio.ensure_future(on_add_payload_reference()),
            )

        self._update_session_widget_states()

    # just override super()._on_payload_reference_edited in a very similar way
    def _on_payload_reference_edited(
        self,
        model_or_item,
        stage: Usd.Stage,
        prim_path: Sdf.Path,
        payref: Union[Sdf.Reference, Sdf.Payload],
        intro_layer: Sdf.Layer,
    ):
        ref_prim_path = self._ref_dict[payref].prim_path_field.model.get_value_as_string()
        # any references with invalid paths get deleted
        if ref_prim_path and ref_prim_path[0] != "/":
            ref_prim_path = "/" + ref_prim_path
        ref_prim_path = Sdf.Path(ref_prim_path) if ref_prim_path and ref_prim_path != DEFAULT_PRIM_TAG else Sdf.Path()
        new_asset_path = self._ref_dict[payref].asset_path_field.model.get_value_as_string()

        try:
            from omni.kit.widget.versioning.checkpoints_model import CheckpointItem

            if isinstance(model_or_item, CheckpointItem):
                new_asset_path = replace_query(new_asset_path, model_or_item.get_relative_path())
            elif model_or_item is None:
                new_asset_path = replace_query(new_asset_path, None)
        except:
            pass

        # When replacing a reference/payload on a different layer, the replaced assetPath should be relative to edit target layer, not introducing layer
        edit_target_layer = stage.GetEditTarget().GetLayer()
        if intro_layer != edit_target_layer:
            if self._use_payloads:
                payref = self._editor_core.anchor_payload_asset_path_to_layer(payref, intro_layer, edit_target_layer)
            else:
                payref = self._editor_core.anchor_reference_asset_path_to_layer(payref, intro_layer, edit_target_layer)

        if clientutils.equal_urls(payref.assetPath, new_asset_path) and payref.primPath == ref_prim_path:
            return False

        elif self._use_payloads:
            vset_name, vset = self.get_active_variant_set()

            # to avoid recursive update in variant editor, do not execute the command immediately but asynchronously
            async def async_execute():
                omni.kit.commands.execute(
                    "EditVariant",
                    prim_path=vset.GetPrim().GetPath().pathString,
                    variant_set_name=vset_name,
                    cmd_name="ReplacePayload",
                    cmd_args={
                        "stage": stage,
                        "prim_path": prim_path,
                        "old_payload": payref,
                        "new_payload": Sdf.Payload(assetPath=new_asset_path, primPath=ref_prim_path),
                    },
                )

            asyncio.ensure_future(async_execute())
        else:
            vset_name, vset = self.get_active_variant_set()

            # to avoid recursive update in variant editor, do not execute the command immediately but asynchronously
            async def async_execute():
                omni.kit.commands.execute(
                    "EditVariant",
                    prim_path=vset.GetPrim().GetPath().pathString,
                    variant_set_name=vset_name,
                    cmd_name="ReplaceReference",
                    cmd_args={
                        "stage": stage,
                        "prim_path": prim_path,
                        "old_reference": payref,
                        "new_reference": Sdf.Reference(assetPath=new_asset_path, primPath=ref_prim_path),
                    },
                )

            asyncio.ensure_future(async_execute())

        return True

    # override super()._get_prim
    def _get_prim(self, prim_path):
        prim_path = self._variant_owner_prim_path
        return super()._get_prim(prim_path)

    # override super's _build_remove_payload_reference_button.
    def _build_remove_payload_reference_button(self, payref, intro_layer):
        def on_remove_payload_reference(ref, layer_weak, payrefs):
            if not ref or not payrefs:
                return

            stage = payrefs.GetPrim().GetStage()
            edit_target_layer = stage.GetEditTarget().GetLayer()
            intro_layer = layer_weak() if layer_weak else None

            if self._use_payloads:
                # When removing a payload on a different layer, the deleted assetPath should be relative to edit target layer, not introducing layer
                if intro_layer and intro_layer != edit_target_layer:
                    ref = self._editor_core.anchor_payload_asset_path_to_layer(ref, intro_layer, edit_target_layer)

            else:
                # When removing a reference on a different layer, the deleted assetPath should be relative to edit target layer, not introducing layer
                if intro_layer and intro_layer != edit_target_layer:
                    ref = self._editor_core.anchor_reference_asset_path_to_layer(ref, intro_layer, edit_target_layer)

            self._model.remove_item(self._item, ref)

        # I have to copy super()._build_remove_payload_reference_button()'s ui code because inner func on_remove_payload_reference can not be redirected
        with ui.ZStack(width=16, style=ui_c.STYLE_REMOVE_BUTTON):
            ui.Rectangle(visible=self._is_live)
            ui.Button(
                identifier="Variant Remove PayRef",  # for unit test
                style=ui_c.STYLE_REMOVE_BUTTON,
                image_url=f"{ui_c.PATH_EXTENSION}{ui_c.PATH_ICON_REMOVE_DARK}",
                clicked_fn=lambda ref=payref, layer_weak=(
                    weakref.ref(intro_layer) if intro_layer else None
                ), refs=self._payrefs: on_remove_payload_reference(ref, layer_weak, refs),
                width=16,
                visible=not self._is_live and not self._in_sess,
                enabled=not self._in_sess,
            )
