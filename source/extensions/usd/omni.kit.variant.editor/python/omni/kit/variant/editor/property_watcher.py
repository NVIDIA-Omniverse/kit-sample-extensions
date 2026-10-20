# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#
import asyncio

import omni
import omni.ui as ui
from pxr import Sdf, Usd

from . import ui_const as ui_c
from .core import VariantEditorCore


class PropertyWatchButton(ui.Button):
    def __init__(
        self,
        property_path,
        is_variant_path: bool = False,
        is_payloads: bool = False,
        is_references: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.set_clicked_fn(self._on_clicked)
        self._core = VariantEditorCore.get_instance()
        self._stage = self._core._stage
        self._property_path = property_path
        self._prop = None
        self._is_variant = is_variant_path
        self._is_payloads = is_payloads
        self._is_references = is_references
        if self._is_variant:
            self._property_path = Sdf.Path(property_path)
        else:
            self._property_path = Sdf.Path(property_path).StripAllVariantSelections()
        self._local_opinion = False
        self.update()

    def destroy(self):
        self.model.destroy()

    def update(self):
        local_layer = self._stage.GetEditTarget().GetLayer()
        if not self._is_variant and not self._is_payloads and not self._is_references:
            self._prop = self._stage.GetPropertyAtPath(self._property_path)
            if self._prop:
                pstack = self._prop.GetPropertyStack(Usd.TimeCode.Default())

                if len(pstack) > 0:
                    lspecs = [spec for spec in pstack if spec.layer in self._stage.GetLayerStack()]
                    for spec in lspecs:
                        if (
                            spec.layer == local_layer
                            and not Sdf.Path(spec.path).ContainsPrimVariantSelection()
                            and (spec.default != None or type(spec) == Sdf.RelationshipSpec)
                        ):
                            self._local_spec = spec
                            self.set_style(ui_c.STYLE_PROP_LOCAL_OPINION)
                            self.set_tooltip_fn(
                                lambda: self._create_tooltip(
                                    "A local opinion is overriding your variant opinion\nClick Here to remove the local opinion."
                                )
                            )
                            self._local_opinion = True
                            break
                        elif spec.layer != local_layer and spec.default != None:
                            self.set_style(ui_c.STYLE_PROP_LAYER_OPINION)
                            self.set_tooltip_fn(
                                lambda: self._create_tooltip(
                                    f"Opinion overriden by a stronger layer:\n{str(spec.layer.realPath)}"
                                )
                            )
                            self._local_opinion = False
                            break
                        elif spec.layer == local_layer and Sdf.Path(spec.path).ContainsPrimVariantSelection():
                            self.set_style(ui_c.STYLE_PROP_VARIANT_OPINION)
                            self.set_tooltip_fn(
                                lambda: self._create_tooltip("Your variant opinion is currently the strongest opinion")
                            )
                            self._local_opinion = False
                            break
                        else:
                            self.set_style(ui_c.STYLE_PROP_VARIANT_OPINION)
                            self._local_opinion = False
                            break

                    else:
                        self.set_style(ui_c.STYLE_PROP_VARIANT_OPINION)
                        self.set_tooltip_fn(
                            lambda: self._create_tooltip("Your variant opinion is currently the strongest opinion")
                        )
                        self._local_opinion = False

                else:
                    self.set_style(ui_c.STYLE_PROP_VARIANT_OPINION)
                    self.set_tooltip_fn(
                        lambda: self._create_tooltip("Your variant opinion is currently the strongest opinion")
                    )
                    self._local_opinion = False

            else:
                self.set_style(ui_c.STYLE_PROP_VARIANT_OPINION)
                self.set_tooltip("Variant opinion inspection of Payloads and References not yet supported")
        elif self._is_payloads:
            # todo. Perhaps going to learn from omni.usd.get_composed_payloads_from_prim
            self.set_style(ui_c.STYLE_PROP_VARIANT_OPINION)
            self.set_tooltip_fn(
                lambda: self._create_tooltip("Payload variant opinion works in parallel with local opinion")
            )
            self._local_opinion = False
        elif self._is_references:
            # todo. Perhaps going to learn from omni.usd.get_composed_payloads_from_prim
            self.set_style(ui_c.STYLE_PROP_VARIANT_OPINION)
            self.set_tooltip_fn(
                lambda: self._create_tooltip("Reference variant opinion works in parallel with local opinion")
            )
            self._local_opinion = False
        else:
            # TODO Need to get specs where there are variant selections in different layers and check if any are local or inherited
            my_spec = self._core.find_spec_in_variant(self._property_path)
            if not my_spec:
                # No spec found in current layer stack; default to variant opinion styling
                self.set_style(ui_c.STYLE_PROP_VARIANT_OPINION)
                self._local_opinion = False
                return
            if isinstance(my_spec, Sdf.VariantSpec):
                vset_name = next(iter(my_spec.primSpec.variantSelections))
            else:
                vset_name = next(iter(my_spec.variantSelections))
            prim_path = self._property_path.StripAllVariantSelections()
            prim = self._stage.GetPrimAtPath(prim_path)
            pstack = prim.GetPrimStack()
            lspecs = [spec for spec in pstack if spec.layer in self._stage.GetLayerStack()]
            for spec in lspecs:
                vselection = spec.variantSelections.get(vset_name)
                if spec.layer == local_layer and vselection and spec != my_spec:
                    self._local_spec = spec
                    self.set_style(ui_c.STYLE_PROP_LOCAL_OPINION)
                    self.set_tooltip_fn(
                        lambda: self._create_tooltip(
                            "A local opinion is overriding your variant opinion\nClick Here to remove the local opinion."
                        )
                    )
                    self._local_opinion = True
                    break
                elif spec.layer != local_layer and vselection and spec != my_spec:
                    self.set_style(ui_c.STYLE_PROP_LAYER_OPINION)
                    self.set_tooltip_fn(
                        lambda: self._create_tooltip(
                            f"Opinion overriden by a stronger layer:\n{str(spec.layer.realPath)}"
                        )
                    )
                    self._local_opinion = False
                    break
                elif spec.layer == local_layer and spec == my_spec:
                    self.set_style(ui_c.STYLE_PROP_VARIANT_OPINION)
                    self.set_tooltip_fn(
                        lambda: self._create_tooltip("Your variant opinion is currently the strongest opinion")
                    )
                    self._local_opinion = False
                    break

    def _create_tooltip(self, text: str):
        with ui.ZStack(style=ui_c.STYLE_TOOLTIP):
            ui.Rectangle()
            ui.Label(text, style=ui_c.STYLE_TOOLTIP_TEXT)

    def _on_clicked(self):
        if not self._core.validate_variant_edit():
            return

        with omni.kit.undo.group(), self._core.AuthorVariant():
            if self._local_opinion and not self._is_variant:
                if isinstance(self._prop, Usd.Attribute):
                    self._prop.ClearDefault()
                elif isinstance(self._prop, Usd.Relationship):
                    self._prop.ClearTargets(True)
                elif isinstance(self._prop, Usd.VariantSet):
                    self._prop.ClearVariantSelection()
                else:
                    pass
            if self._local_opinion and self._is_variant:
                my_spec = (
                    omni.usd.get_context().get_stage().GetEditTarget().GetLayer().GetObjectAtPath(self._property_path)
                )
                if isinstance(my_spec, Sdf.VariantSpec):
                    vset_name = next(iter(my_spec.primSpec.variantSelections))
                else:
                    vset_name = next(iter(my_spec.variantSelections))

                vset = self._stage.GetPrimAtPath(self._property_path.StripAllVariantSelections()).GetVariantSet(
                    vset_name
                )
                omni.kit.commands.execute(
                    "SelectVariantPrim",
                    prim_path=vset.GetPrim().GetPath(),
                    vset_name=vset.GetName(),
                    var_name=None,
                )

            async def refresh_ui():
                await omni.kit.app.get_app().next_update_async()
                omni.kit.commands.execute("RefreshVariantUi")

            asyncio.ensure_future(refresh_ui())

        self.update()
