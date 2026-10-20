import omni.scene.visualization.core
import omni.ui as ui
from omni.kit.window.preferences import PreferenceBuilder, SettingType


class VisualizationPreferences(PreferenceBuilder):
    def __init__(self):
        super().__init__("Visualization")

    def build(self):
        with ui.VStack(height=0):
            with self.add_frame("Visualization"):
                with ui.VStack():
                    self.create_setting_widget(
                        "Point Diameter",
                        omni.scene.visualization.core.pointWidthSettingName,
                        SettingType.FLOAT,
                        range_from=1.0,
                        range_to=100.0,
                        speed=0.5,
                    )

                    self.create_setting_widget(
                        "Line Width",
                        omni.scene.visualization.core.lineWidthSettingName,
                        SettingType.FLOAT,
                        range_from=1.0,
                        range_to=100.0,
                        speed=0.5,
                    )

                    self.create_setting_widget(
                        "Use Widths Primvar (Curves Only)",
                        omni.scene.visualization.core.useWidthsPrimvar,
                        SettingType.BOOL,
                        tooltip="If enabled, for BasisCurves prim visualization only, the widths primvar will be used as a multiplier "
                        "on Point Diameter and Line Width for vertex and wireframe visualization, respectively."
                        "Otherwise Point Diameter / Line Width alone will be used for their respective visualizations.",
                    )

                    self.create_setting_widget(
                        "Propagate Options to Selection Descendants",
                        omni.scene.visualization.core.applyToDescendantsSettingName,
                        SettingType.BOOL,
                        tooltip="If enabled, setting a visualization option on "
                        "a prim will also set that option on all the "
                        "prim's descendants.",
                    )

                    self.create_setting_widget(
                        "Use SceneVis Prim to Track Visualized Prims",
                        omni.scene.visualization.core.useSceneVisPrim,
                        SettingType.BOOL,
                        tooltip="If enabled, a hidden prim will be created on the stage to track "
                        "which prims have visualization attributes enabled. Use this "
                        "option to accelerate load times for large stages where persistent "
                        "visualization settings are desired.",
                    )
