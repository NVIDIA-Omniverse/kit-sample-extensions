import weakref
from functools import lru_cache
from typing import List

import carb
import omni.kit
import omni.ui as ui
from omni.kit.property.usd.usd_object_model import MetadataObjectModel
from omni.kit.property.usd.usd_property_widget_builder import (
    UsdPropertiesWidgetBuilder,
    get_ui_style,
)
from omni.kit.property.usd.widgets import ICON_PATH
from omni.kit.window.property.templates import (
    HORIZONTAL_SPACING,
    LABEL_HEIGHT,
    LABEL_WIDTH,
    LABEL_WIDTH_LIGHT,
)
from pxr import Sdf, Usd

from . import ui_const as ui_c
from .core import get_shader_display_name
from .variant_property_label import VariantLabel
from .variant_property_models import (
    GfVecAttributeModelVariant,
    GfVecAttributeSingleChannelModelVariant,
    MdlEnumAttributeModelVariant,
    MetadataObjectModelVariant,
    RelationshipArrayModelVariant,
    SdfAssetPathArrayAttributeItemModelVariant,
    SdfAssetPathAttributeModelVariant,
    SdfRelationshipArrayItemModelVariant,
    SdfTimeCodeModelVariant,
    TfTokenAttributeModelVariant,
    UsdAttributeModelVariant,
)


@lru_cache()
def _get_plus_glyph():
    return omni.kit.ui.get_custom_glyph_code("${glyphs}/menu_context.svg")


class UsdVariantPropertiesWidgetBuilder(UsdPropertiesWidgetBuilder):
    @classmethod
    def startup(cls):
        super().startup()
        cls.init_arg_writer_table()

    @classmethod
    def init_arg_writer_table(cls):
        cls.arg_writer_table = {
            cls.tf_half: cls.floating_point_arg_writer,
            cls.tf_float: cls.floating_point_arg_writer,
            cls.tf_double: cls.floating_point_arg_writer,
            cls.tf_uchar: cls.integer_arg_writer,
            cls.tf_uint: cls.integer_arg_writer,
            cls.tf_int: cls.integer_arg_writer,
            cls.tf_int64: cls.integer_arg_writer,
            cls.tf_uint64: cls.integer_arg_writer,
            cls.tf_bool: cls.bool_arg_writer,
            cls.tf_string: cls.string_arg_writer,
            cls.tf_gf_vec2i: cls.vec_per_channel_arg_writer,
            cls.tf_gf_vec2h: cls.vec_per_channel_arg_writer,
            cls.tf_gf_vec2f: cls.vec_per_channel_arg_writer,
            cls.tf_gf_vec2d: cls.vec_per_channel_arg_writer,
            cls.tf_gf_vec3i: cls.vec_per_channel_arg_writer,
            cls.tf_gf_vec3h: cls.vec_per_channel_arg_writer,
            cls.tf_gf_vec3f: cls.vec_per_channel_arg_writer,
            cls.tf_gf_vec3d: cls.vec_per_channel_arg_writer,
            cls.tf_gf_vec4i: cls.vec_per_channel_arg_writer,
            cls.tf_gf_vec4h: cls.vec_per_channel_arg_writer,
            cls.tf_gf_vec4f: cls.vec_per_channel_arg_writer,
            cls.tf_gf_vec4d: cls.vec_per_channel_arg_writer,
            cls.tf_tf_token: cls.tftoken_arg_writer,
            cls.tf_sdf_asset_path: cls.sdf_asset_path_arg_writer,
            cls.tf_sdf_time_code: cls.time_code_arg_writer,
            cls.tf_sdf_asset_array_path: cls.sdf_asset_path_array_arg_writer,
        }

    @classmethod
    def floating_point_arg_writer(cls, metadata, additional_widget_kwargs):
        additional_widget_kwargs.update({"model_cls": UsdAttributeModelVariant})

    @classmethod
    def integer_arg_writer(cls, metadata, additional_widget_kwargs):
        is_mdl_enum = False
        if metadata.get("renderType", None):
            sdr_metadata = metadata.get("sdrMetadata", None)
            if sdr_metadata and sdr_metadata.get("options", None):
                is_mdl_enum = True
        if is_mdl_enum:
            additional_widget_kwargs.update({"model_cls": MdlEnumAttributeModelVariant})
        else:
            additional_widget_kwargs.update({"model_cls": UsdAttributeModelVariant})

    @classmethod
    def bool_arg_writer(cls, metadata, additional_widget_kwargs):
        additional_widget_kwargs.update({"model_cls": UsdAttributeModelVariant})

    @classmethod
    def string_arg_writer(cls, metadata, additional_widget_kwargs):
        additional_widget_kwargs.update({"model_cls": UsdAttributeModelVariant})

    @classmethod
    def vec_per_channel_arg_writer(cls, metadata, additional_widget_kwargs):
        additional_widget_kwargs.update(
            {
                "model_cls": GfVecAttributeModelVariant,
                "single_channel_model_cls": GfVecAttributeSingleChannelModelVariant,
            }
        )

    @classmethod
    def tftoken_arg_writer(cls, metadata, additional_widget_kwargs):
        tokens = metadata.get("allowedTokens")
        has_allowed_token = tokens is not None and len(tokens) > 0
        vcls = TfTokenAttributeModelVariant if has_allowed_token else UsdAttributeModelVariant
        additional_widget_kwargs.update({"model_cls": vcls})

    @classmethod
    def sdf_asset_path_arg_writer(cls, metadata, additional_widget_kwargs):
        additional_widget_kwargs.update({"model_cls": SdfAssetPathAttributeModelVariant})

    @classmethod
    def time_code_arg_writer(cls, metadata, additional_widget_kwargs):
        additional_widget_kwargs.update({"model_cls": SdfTimeCodeModelVariant})

    @classmethod
    def sdf_asset_path_array_arg_writer(cls, metadata, additional_widget_kwargs):
        additional_widget_kwargs.update({"model_cls": SdfAssetPathArrayAttributeItemModelVariant})

    @classmethod
    def write_args(
        cls,
        property_type: type[Usd.Attribute | Usd.Relationship],
        metadata,
        additional_widget_kwargs,
    ):
        if property_type == Usd.Relationship:
            additional_widget_kwargs.update({"model_cls": SdfRelationshipArrayItemModelVariant})
            return
        if not (metadata and additional_widget_kwargs):
            return
        type_name = cls.get_type_name(metadata)
        tf_type = type_name.type
        if tf_type not in cls.arg_writer_table:
            carb.log_warn(f"{tf_type} has no correspond arg writer, please make sure it's expected")
            return
        write_func = cls.arg_writer_table.get(tf_type)
        write_func(metadata, additional_widget_kwargs)

    @classmethod
    def _create_path_widget(
        cls,
        model,
        stage: Usd.Stage,
        attr_name,
        metadata,
        prim_paths,
        additional_label_kwargs,
        additional_widget_kwargs,
    ):
        prim_path = Sdf.Path(prim_paths[-1]).StripAllVariantSelections()
        usd_prim = stage.GetPrimAtPath(prim_path)
        prop_path = prim_path.AppendProperty(attr_name)
        usd_prop = stage.GetAttributeAtPath(prop_path)
        need_colorspace = usd_prop.HasColorSpace() or "Shader" == usd_prim.GetTypeName()
        need_colorspace &= attr_name not in [
            "info:mdl:sourceAsset",
            "info:mdl:sourceAsset:subIdentifier",
        ]
        if need_colorspace:
            colorspace_model = MetadataObjectModelVariant(
                stage,
                [path.AppendProperty(attr_name).StripAllVariantSelections() for path in prim_paths],
                False,
                metadata,
                key="colorSpace",
                default="auto",
                options=["auto", "raw", "sRGB"],
            )
        else:
            colorspace_model = None

        extra_widgets = []

        with ui.HStack(spacing=HORIZONTAL_SPACING):
            label = cls.create_label(attr_name, metadata, additional_label_kwargs)
            with ui.VStack(spacing=5):
                with ui.HStack():
                    widget_kwargs = {"name": "models", "model": model}
                    if additional_widget_kwargs:
                        widget_kwargs.update(additional_widget_kwargs)

                    value_widget, mixed_overlay = cls._build_path_field(
                        model, stage, attr_name, widget_kwargs, None, extra_widgets
                    )

                    cls.create_control_state(
                        value_widget=value_widget,
                        mixed_overlay=mixed_overlay,
                        extra_widgets=extra_widgets,
                        **widget_kwargs,
                        label=label,
                    )

                if colorspace_model:
                    with ui.HStack():
                        value_widget = ui.ComboBox(colorspace_model, name="choices")
                        value_widget.identifier = f"colorspace_{attr_name}"
                        mixed_overlay = cls.create_mixed_text_overlay()
                        widget_kwargs = {"no_default": True}
                        cls.create_control_state(
                            colorspace_model,
                            value_widget,
                            mixed_overlay,
                            **widget_kwargs,
                            label=label,
                        )
                ui.Spacer()

        if colorspace_model:
            # Returns colorspace model also so it could receive updates.
            return [model, colorspace_model]
        else:
            return [model]

    @classmethod
    def build(
        cls,
        stage,
        attr_name,
        metadata,
        property_type,
        prim_paths: List[Sdf.Path],
        additional_label_kwargs=None,
        additional_widget_kwargs=None,
    ):
        cls.write_args(property_type, metadata, additional_widget_kwargs)
        return (
            super().build(
                stage,
                attr_name,
                metadata,
                property_type,
                prim_paths,
                additional_label_kwargs,
                additional_widget_kwargs,
            ),
            additional_label_kwargs,
        )

    @classmethod
    def create_label(cls, attr_name, metadata=None, additional_label_kwargs=None):
        alignment = cls._get_alignment()
        label_kwargs = {
            "name": "label",
            "elided_text": True,
            "width": ui_c.PROPERTY_LABEL_WIDTH,
            "height": ui_c.PROPERTY_LABEL_HEIGHT,
            "alignment": alignment,
        }
        if get_ui_style() == "NvidiaLight":
            label_kwargs["width"] = ui_c.PROPERTY_LABEL_WIDTH_LIGHT
        if additional_label_kwargs:
            label_kwargs.update(additional_label_kwargs)
        if metadata and "tooltip" not in label_kwargs:
            label_kwargs["tooltip"] = cls._generate_tooltip_string(attr_name, metadata)

        display_name = ""
        # retrieve display name from shader display name cache
        if attr_name.startswith("inputs:"):
            display_name = get_shader_display_name(attr_name)

        if not display_name:
            display_name = cls._get_display_name(attr_name, metadata)

        label = VariantLabel(display_name, **label_kwargs)
        ui.Spacer(width=5)
        if additional_label_kwargs:
            additional_label_kwargs.update({"variant_label": label})
        return label

    @classmethod
    def create_attribute_context_menu(cls, widget, model, comp_index=-1):
        return
