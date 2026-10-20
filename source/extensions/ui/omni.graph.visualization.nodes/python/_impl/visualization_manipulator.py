# Copyright (c) 2022-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

__all__ = ["VisualizationManipulator"]

import omni.ui
from omni.ui import scene as sc


class VisualizationManipulator(sc.Manipulator):
    """Manipulator that displays lines generated in the OG node OgnDrawLine."""

    def on_build(self):
        """Called when the model is changed and rebuilds the whole manipulator"""
        for path, line in self.model.lines.items():
            sc.Line(line.start.tolist(), line.end.tolist(), color=line.color.tolist(), thickness=line.thickness)

        for path, label in self.model.labels.items():
            with sc.Transform(sc.Matrix44(*label.transform.tolist())):
                sc.Label(label.text, color=label.color.tolist(), size=label.size, alignment=omni.ui.Alignment.CENTER)

    def on_model_updated(self, item):
        # Regenerate the manipulator
        self.invalidate()

    def __del__(self):
        self.destroy()

    def destroy(self):
        if self.model:
            self.model.destroy()
            self.model = None
