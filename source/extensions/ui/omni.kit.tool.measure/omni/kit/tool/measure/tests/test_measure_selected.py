# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

from pathlib import Path

import omni.kit.app
import omni.kit.ui_test as ui_test
import omni.usd
from omni.kit import commands
from omni.kit.test import get_test_output_path
from pxr import Gf, Sdf, Usd, UsdGeom, Vt

from ..common import (
    MeasureMode,
    UnitType,
)
from .test_util import PRIM_PATHS, TestMeasureBase, select_test_objects

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH


class TestMeasureSelected(TestMeasureBase):
    async def setUp(self):
        await super().setUp()

        self._extension._show_window(None, True)
        await ui_test.human_delay(8)

    async def tearDown(self):
        self._extension._show_window(None, False)
        await super().tearDown()
        await ui_test.human_delay(8)

    async def test_measure_selected_center(self):
        """
        Testing created a measurement from selection - Center
        """
        # Select objects and test to be sure both objects are selected
        select_test_objects(PRIM_PATHS)
        await ui_test.wait_n_updates(10)

        selection = self._ctx.get_selection()
        self.assertEqual(len(selection.get_selected_prim_paths()), 2)

        ### Run the measure tool, simulating the button press in the UI [CENTER]
        await ui_test.human_delay(5)
        self._extension._measure_panel._pn_global._on_measure_selected()
        await ui_test.human_delay(5)

        # Ensure the measurement was created by checking the Measurement Manager
        from ..manager import MeasurementManager

        measurements = MeasurementManager()._model.get_items()
        self.assertEqual(len(measurements), 1)
        self.assertEqual(
            measurements[0].payload.tool_mode,
            MeasureMode.SELECTED,
            "Failed to find Measurement with mode SELECTED after creation!",
        )

        # Frame Selection, Hide Selection, Hide All
        uuid = measurements[0].payload.uuid
        MeasurementManager().frame_measurement(uuid)
        await ui_test.human_delay(5)
        MeasurementManager().set_visibility(uuid, False)
        await ui_test.human_delay(5)
        MeasurementManager().set_visibility_all(True)
        await ui_test.human_delay(5)
        MeasurementManager().delete_all()
        await ui_test.human_delay(10)
        measurements = MeasurementManager()._model.get_items()
        self.assertEqual(len(measurements), 0)

    async def test_measure_selected_payloads_min_max(self):
        """
        Testing created a measurement from selected payloads (OMFP-1103)
        """
        # Create 2 payloads
        new_stage = Usd.Stage.CreateInMemory("payload1.usd")
        mesh_path = "/Root/Cube"
        mesh = UsdGeom.Mesh.Define(new_stage, mesh_path)
        parent = mesh.GetPrim().GetParent()
        new_stage.SetDefaultPrim(parent)

        # Draw a triangle
        points = [Gf.Vec3f(0, 100, 0), Gf.Vec3f(50, 0, 0), Gf.Vec3f(-50, 0, 0)]
        mesh.GetPointsAttr().Set(Vt.Vec3fArray(points))
        mesh.GetFaceVertexIndicesAttr().Set([0, 1, 2])
        mesh.GetFaceVertexCountsAttr().Set([3])

        self._ctx.new_stage()

        def create_payload(payload_prim_path: str):
            # Create a cube in another stage and reference to current stage as payload
            stage = self._ctx.get_stage()
            commands.execute("CreatePrim", prim_type="Xform", prim_path=payload_prim_path, stage=stage)
            payload_prim = stage.GetPrimAtPath(payload_prim_path)
            # payload_prim.GetPayloads().AddPayload(temp_path)
            payload_prim.GetPayloads().AddPayload(Sdf.Payload(new_stage.GetRootLayer().identifier, "/Root"))

            return payload_prim

        payload_a_path = "/payload_a"
        payload_prim_a = create_payload(payload_a_path)
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()

        payload_b_path = "/payload_b"
        payload_prim_b = create_payload(payload_b_path)
        await omni.kit.app.get_app().next_update_async()
        await omni.kit.app.get_app().next_update_async()

        # Move one payload
        payload_a_translation = Gf.Vec3d(200, 0, 0)
        commands.execute(
            "TransformPrimCommand",
            path=payload_a_path,
            new_transform_matrix=Gf.Matrix4d().SetTranslate(payload_a_translation),
        )

        self.assertTrue(
            Gf.IsClose(
                omni.usd.get_world_transform_matrix(payload_prim_a).ExtractTranslation(), payload_a_translation, 1e-6
            )
        )

        # Select these 2 payloads and measure
        select_test_objects([payload_a_path, payload_b_path])
        await ui_test.wait_n_updates(10)

        selection = self._ctx.get_selection()
        self.assertEqual(len(selection.get_selected_prim_paths()), 2)

        # Run the measure tool, simulating the button press in the UI
        await ui_test.human_delay(5)
        # Set measure selected mode to MIN
        self._extension._measure_panel._pn_global._cb_distance.model.get_item_value_model().set_value(0)
        self._extension._measure_panel._pn_global._on_measure_selected()
        await ui_test.human_delay(5)

        # Ensure the measurement was created by checking the Measurement Manager
        from ..manager import MeasurementManager

        measurements = MeasurementManager()._model.get_items()
        self.assertEqual(len(measurements), 1)
        self.assertEqual(
            measurements[0].payload.tool_mode,
            MeasureMode.SELECTED,
            "Failed to find Measurement with mode SELECTED after creation!",
        )

        # Check measured distance
        # Ensure the unit type is meters, so the computed value can match
        measurements[0].set_attribute("measure:prop:unit", UnitType.METERS, Sdf.ValueTypeNames.Token)
        await omni.kit.app.get_app().next_update_async()  # This await is to hold for the unit change to propagate
        await omni.kit.app.get_app().next_update_async()  # This await is to hold for the fabric sync
        measured_length = measurements[0].get_attribute("measure:compute:primary")

        self.assertEqual(measured_length, 1.0)

    async def test_measure_selected_implicit_shapes_min_max(self):
        """
        KSE-QA-BUG-004: Min and Max between implicit shapes (UsdGeom.Cube, no points) measure their surfaces, not
        their pivots. Two 100-unit cubes 400 units apart: Min is the gap between the facing faces (3 m), Max the
        furthest corners (sqrt(5^2 + 1^2 + 1^2) m).
        """
        from ..manager import MeasurementManager

        self.create_test_cubes(positions=[(0, 0, 0), (400, 0, 0)])
        await ui_test.wait_n_updates(2)
        for path in PRIM_PATHS:
            self.assertTrue(self._ctx.get_stage().GetPrimAtPath(path).IsA(UsdGeom.Cube))

        for sub_mode, expected in ((0, 3.0), (1, 27.0**0.5)):
            select_test_objects(PRIM_PATHS)
            await ui_test.wait_n_updates(10)
            self.assertEqual(len(self._ctx.get_selection().get_selected_prim_paths()), 2)

            self._extension._measure_panel._pn_global._cb_distance.model.get_item_value_model().set_value(sub_mode)
            self._extension._measure_panel._pn_global._on_measure_selected()
            await ui_test.human_delay(5)

            measurements = MeasurementManager()._model.get_items()
            self.assertEqual(len(measurements), 1)
            measurements[0].set_attribute("measure:prop:unit", UnitType.METERS, Sdf.ValueTypeNames.Token)
            await omni.kit.app.get_app().next_update_async()
            await omni.kit.app.get_app().next_update_async()
            measured = measurements[0].get_attribute("measure:compute:primary")
            self.assertAlmostEqual(
                measured, expected, places=4, msg=f"{'Min' if sub_mode == 0 else 'Max'} between two implicit cubes"
            )

            MeasurementManager().delete_all()
            await ui_test.human_delay(5)

    async def test_measure_selected_undo(self):
        """
        Tests creating a measurement from selection, undo the creation
        """

        # Select objects and test to be sure both objects are selected
        select_test_objects(PRIM_PATHS)
        await ui_test.human_delay(5)

        selection = omni.usd.get_context().get_selection()
        self.assertEqual(len(selection.get_selected_prim_paths()), 2)

        # Run the measure tool, simulating the button press in the UI
        self._extension._measure_panel._pn_global._on_measure_selected()
        await ui_test.human_delay(5)

        # Move a prim
        prim = self._ctx.get_stage().GetPrimAtPath("/test_cubeA")
        self.assertTrue(prim.IsValid())
        prim.GetAttribute("xformOp:translate").Set(Gf.Vec3d(500, 0, 0))
        await ui_test.human_delay(5)

        # Run Undo/
        commands.execute("Undo")
        await ui_test.human_delay(5)

        from ..manager import MeasurementManager

        measurements = MeasurementManager()._model.get_item_children(None)
        self.assertEqual(len(measurements), 0)

    async def test_measure_selected_delete(self):
        """
        Tests creating a measurement from selection, deleting, and undoing the delete.
        """
        # Select objects and test to be sure both objects are selected
        select_test_objects(PRIM_PATHS)
        await ui_test.human_delay(5)

        selection = omni.usd.get_context().get_selection()
        self.assertEqual(len(selection.get_selected_prim_paths()), 2)

        # Run the measure tool, simulating the button press in the UI
        self._extension._measure_panel._pn_global._on_measure_selected()
        await ui_test.human_delay(5)

        # Get the Item UUID to delete
        from ..manager import MeasurementManager

        measurements = MeasurementManager()._model.get_item_children(None)

        self.assertEqual(len(measurements), 1)

        uuid = measurements[0].uuid

        # Call the delete function in the measurement manager
        MeasurementManager().delete(uuid)
        await ui_test.human_delay(5)

        # Regrab measurements
        measurements = MeasurementManager()._model.get_item_children(None)
        self.assertEqual(len(measurements), 0)

        # Undo the delete
        commands.execute("Undo")
        await ui_test.human_delay(5)

        # Regrab Measurements
        measurements = MeasurementManager()._model.get_item_children(None)
        self.assertEqual(len(measurements), 1)

    async def test_measure_delete_measured_prim(self):
        """
        Tests removing a mesurement when a measured prim is removed and undoing the delete.
        """
        # Select objects and test to be sure both objects are selected
        select_test_objects(PRIM_PATHS)
        await ui_test.human_delay(5)

        selection = omni.usd.get_context().get_selection()
        self.assertEqual(len(selection.get_selected_prim_paths()), 2)

        # Run the measure tool, simulating the button press in the UI
        self._extension._measure_panel._pn_global._on_measure_selected()
        await ui_test.human_delay(5)

        # Get the Item UUID to delete
        from ..manager import MeasurementManager

        measurements = MeasurementManager()._model.get_item_children(None)

        self.assertEqual(len(measurements), 1)

        # Delete the measured prims
        commands.execute("DeletePrims", paths=[PRIM_PATHS[0]])
        await ui_test.human_delay(5)

        # Regrab measurements
        measurements = MeasurementManager()._model.get_item_children(None)
        self.assertEqual(len(measurements), 0)

        # Undo the delete
        commands.execute("Undo")
        await ui_test.human_delay(5)

        # Regrab Measurements
        measurements = MeasurementManager()._model.get_item_children(None)
        self.assertEqual(len(measurements), 1)

    async def test_measure_save_export_and_open(self):
        """
        Tests creating a measurement, saving the file, exporting the data, clearing the scene, opening the file
        and validating the measurement exists
        """
        import tempfile

        from omni.kit.tool.measure.system.export import ExportPanel, _export_csv

        from ..manager import MeasurementManager

        usd_context = omni.usd.get_context()

        # Select objects and test to be sure both objects are selected
        select_test_objects(PRIM_PATHS)
        await ui_test.human_delay(5)

        selection = omni.usd.get_context().get_selection()
        self.assertEqual(len(selection.get_selected_prim_paths()), 2)

        # Run the measure tool, simulating the button press in the UI
        self._extension._measure_panel._on_measure_selected()
        await ui_test.wait_n_updates(5)

        temp_dir = tempfile.TemporaryDirectory().name
        temp_path = f"{temp_dir}/tmp.usda"

        # Save the stage
        result = usd_context.save_as_stage(temp_path)
        self.assertTrue(result)

        # # collect the data to export the CSV to build folder path
        folder_path = f"{get_test_output_path()}"
        export_panel = ExportPanel()
        export_panel.visible = True
        await ui_test.human_delay(5)
        export_panel._on_export_dir_picked(folder_path)
        await ui_test.human_delay(5)
        export_panel._on_export_clicked()
        await ui_test.human_delay(5)
        export_panel.destroy()

        # Close the stage
        await usd_context.close_stage_async()
        await ui_test.human_delay(5)

        # open stage
        result = usd_context.open_stage(temp_path)
        self.assertTrue(result)
        await ui_test.human_delay(5)

        # Ensure the measurement was created by checking length of the created measurements
        measurements = MeasurementManager()._model.get_item_children(None)
        self.assertEqual(len(measurements), 1, "Failed to find Measurement after stage load!")

        await self.wait_for_notifications(timeout_seconds=15.0)

    async def test_measure_settings(self):
        """
        Testing updating a value after serialization and reading the value
        """
        from ..common import UserSettings

        # Set the user settings to default and check that a specific value is its default value
        user_settings = UserSettings()

        # Hard Reset for code coverage testing
        user_settings._persistent_settings = None
        user_settings._session_settings = None
        user_settings.persistent
        user_settings.session

        user_settings.reset_to_default()
        user_settings.serialize()
        self.assertEqual(user_settings.get_property("distance", user_settings.session.distance), 2)

        # change the value of an input via interface, serialize, and check against the new value
        user_settings.serialize()

    async def test_measure_selected_rename(self):
        """
        Tests creating a measurement from selection, renaming, and undoing the rename.
        """
        # Select objects and test to be sure both objects are selected
        select_test_objects(PRIM_PATHS)
        await ui_test.human_delay(5)

        selection = omni.usd.get_context().get_selection()
        self.assertEqual(len(selection.get_selected_prim_paths()), 2)

        # Run the measure tool, simulating the button press in the UI
        self._extension._measure_panel._pn_global._on_measure_selected()
        await ui_test.human_delay(5)

        # Get the Item UUID to rename
        from ..manager import MeasurementManager

        measurements = MeasurementManager()._model.get_item_children(None)

        self.assertEqual(len(measurements), 1)

        uuid = measurements[0].uuid
        original_name = measurements[0].name
        original_path = measurements[0]._prim.GetPath()

        # Call the rename function in the measurement manager
        MeasurementManager().rename(uuid, "rename_test")
        await ui_test.human_delay(5)

        # Regrab measurements
        measurements = MeasurementManager()._model.get_item_children(None)
        self.assertEqual(len(measurements), 1)

        # Check measurement name
        self.assertEqual(measurements[0].name, "rename_test")

        # Check measurement path
        self.assertEqual(measurements[0]._prim.GetPath(), Sdf.Path("/Viewport_Measure/rename_test"))

        # Undo the rename
        commands.execute("Undo")
        await ui_test.human_delay(5)

        # Regrab Measurements
        measurements = MeasurementManager()._model.get_item_children(None)
        self.assertEqual(len(measurements), 1)

        # Check measurement name
        self.assertEqual(measurements[0].name, original_name)

        # Check measurement path
        self.assertEqual(measurements[0]._prim.GetPath(), original_path)
