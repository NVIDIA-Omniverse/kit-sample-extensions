# Copyright (c) 2022-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

import omni.graph.core as og
from omni.graph.visualization.nodes import VisualizationModel

from ..OgnDrawLineDatabase import OgnDrawLineDatabase


class OgnDrawLine:
    @staticmethod
    def compute(db: OgnDrawLineDatabase) -> bool:

        try:
            inputs = db.inputs

            VisualizationModel().add_line(
                db.node.get_prim_path(), inputs.start, inputs.end, inputs.color, inputs.thickness
            )

        except Exception:
            import traceback

            raise RuntimeError(traceback.format_exc())

        db.outputs.execOut = og.ExecutionAttributeState.ENABLED
        return True
