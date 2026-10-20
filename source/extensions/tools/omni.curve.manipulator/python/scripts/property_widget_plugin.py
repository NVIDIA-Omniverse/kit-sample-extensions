# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#


class BasisCurvesCvWidgetPlugin:
    __section_build_fns = {}

    @staticmethod
    def get_build_fns():
        return BasisCurvesCvWidgetPlugin.__section_build_fns

    @staticmethod
    def register_property_build_fn(section_name, build_fn):
        if build_fn:
            BasisCurvesCvWidgetPlugin.__section_build_fns[section_name] = build_fn
        else:
            BasisCurvesCvWidgetPlugin.unregister_property_build_fn(section_name)

    @staticmethod
    def unregister_property_build_fn(section_name):
        if section_name in BasisCurvesCvWidgetPlugin.__section_build_fns:
            del BasisCurvesCvWidgetPlugin.__section_build_fns[section_name]
