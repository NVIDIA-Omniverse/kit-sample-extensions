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
from .test_util import PRIM_PATHS, TestMeasureBase, prim_path_world_pos, select_test_objects

CURRENT_PATH = Path(__file__).parent
TEST_DATA_PATH = CURRENT_PATH

# Matches TestMeasureBase.create_test_cubes; tests move cube B to MOVED_CUBE_B_POSITION to change the distance.
CUBE_A_POSITION = Gf.Vec3d(250, 0, 0)
CUBE_B_POSITION = Gf.Vec3d(0, 0, 250)
MOVED_CUBE_B_POSITION = Gf.Vec3d(0, 0, 500)
MOVED_DISTANCE_RATIO = (CUBE_A_POSITION - MOVED_CUBE_B_POSITION).GetLength() / (
    CUBE_A_POSITION - CUBE_B_POSITION
).GetLength()


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

    async def _measure_point_to_point(self, prim_paths) -> "MeasurePrim":
        """Create a point-to-point measurement between prims and return the new MeasurePrim."""
        from ..manager import MeasurementManager

        existing = {m.uuid for m in MeasurementManager()._model.get_items()}
        commands.execute(
            "CreateMeasurementPointToPointCommand",
            prim_paths=list(prim_paths),
            points=[prim_path_world_pos(path) for path in prim_paths],
        )
        await ui_test.human_delay(5)

        created = [m for m in MeasurementManager()._model.get_items() if m.uuid not in existing]
        self.assertEqual(len(created), 1)
        return created[0]

    async def test_measure_undo_keeps_previous_user_undo_entry(self):
        """
        OMPE-117923: undoing a measurement must only revert the measurement, leaving the user's previous
        command applied and still undoable.
        """
        from omni.kit import undo

        from ..manager import MeasurementManager

        user_prim_path = "/user_prim"
        commands.execute("CreatePrimCommand", prim_type="Xform", prim_path=user_prim_path)
        await ui_test.human_delay(5)
        stack_size_before_measure = len(undo.get_undo_stack())

        await self._measure_point_to_point(PRIM_PATHS)

        commands.execute("Undo")
        await ui_test.human_delay(5)

        self.assertEqual(len(MeasurementManager()._model.get_items()), 0)
        self.assertEqual(len(undo.get_undo_stack()), stack_size_before_measure)
        self.assertTrue(self._ctx.get_stage().GetPrimAtPath(user_prim_path).IsValid())

        # The user's own command must still be undoable.
        commands.execute("Undo")
        await ui_test.human_delay(5)
        self.assertFalse(self._ctx.get_stage().GetPrimAtPath(user_prim_path).IsValid())

    async def test_measure_delete_measured_prim_ancestor(self):
        """
        OMPE-117908: deleting an ancestor of the measured prims removes the measurement, and undo restores it.
        Measurements outside the deleted subtree, including ones on prims sharing a name prefix, are kept.
        """
        from ..manager import MeasurementManager

        for group in ["/group", "/group_sibling"]:
            commands.execute("CreatePrimCommand", prim_type="Xform", prim_path=group)
        group_paths = ["/group/cubeA", "/group/cubeB"]
        self.create_test_cubes(prim_paths=group_paths)
        self.create_test_cubes(prim_paths=["/group_sibling/cubeA", "/group_sibling/cubeB"])
        await ui_test.human_delay(5)

        grouped = await self._measure_point_to_point(group_paths)
        grouped_path = grouped.path
        kept = await self._measure_point_to_point(["/group_sibling/cubeA", "/group_sibling/cubeB"])

        commands.execute("DeletePrims", paths=["/group"])
        await ui_test.human_delay(5)

        stage = self._ctx.get_stage()
        self.assertEqual([m.uuid for m in MeasurementManager()._model.get_items()], [kept.uuid])
        self.assertFalse(stage.GetPrimAtPath(grouped_path).IsValid())
        self.assertTrue(stage.GetPrimAtPath(kept.path).IsValid())

        commands.execute("Undo")
        await ui_test.human_delay(5)

        self.assertTrue(stage.GetPrimAtPath("/group").IsValid())
        self.assertEqual(len(MeasurementManager()._model.get_items()), 2)

    async def test_measure_updates_on_stage_meters_per_unit_change(self):
        """
        OMPE-119252: changing the stage's metersPerUnit recomputes existing measurements, both the displayed
        value and the stored measure:compute:primary that is written to disk.
        """
        stage = self._ctx.get_stage()
        UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.LinearUnits.centimeters)
        await ui_test.human_delay(5)

        measurement = await self._measure_point_to_point(PRIM_PATHS)
        value_in_centimeters = measurement.payload.primary_value

        UsdGeom.SetStageMetersPerUnit(stage, UsdGeom.LinearUnits.meters)
        await ui_test.human_delay(5)

        self.assertAlmostEqual(measurement.payload.primary_value, value_in_centimeters * 100, 3)
        self.assertAlmostEqual(measurement.get_attribute("measure:compute:primary"), value_in_centimeters * 100, 3)

    async def _create_payload_cube(self, payload_prim_path: str) -> Usd.Stage:
        """Add a payload holding a cube at CUBE_B_POSITION; keep the returned stage alive while the payload is used."""
        payload_stage = Usd.Stage.CreateInMemory()
        cube = UsdGeom.Cube.Define(payload_stage, "/Root/Cube")
        cube.AddTranslateOp().Set(CUBE_B_POSITION)
        payload_stage.SetDefaultPrim(cube.GetPrim().GetParent())

        payload_prim = self._ctx.get_stage().DefinePrim(payload_prim_path, "Xform")
        payload_prim.GetPayloads().AddPayload(payload_stage.GetRootLayer().identifier)
        await ui_test.human_delay(5)
        return payload_stage

    async def test_measure_updates_when_sublayer_is_muted(self):
        """
        OMPE-117792: muting a sublayer that moves a measured prim recomputes the measurement, both the displayed
        value and the stored measure:compute:primary.
        """
        stage = self._ctx.get_stage()
        override_layer = Sdf.Layer.CreateAnonymous()
        # The test cubes are authored in the root layer, so the override must sit in a stronger layer to win.
        stage.GetSessionLayer().subLayerPaths.append(override_layer.identifier)
        override_stage = Usd.Stage.Open(override_layer)
        translate_type = stage.GetPrimAtPath(PRIM_PATHS[1]).GetAttribute("xformOp:translate").GetTypeName()
        override_prim = override_stage.OverridePrim(PRIM_PATHS[1])
        override_prim.CreateAttribute("xformOp:translate", translate_type).Set(MOVED_CUBE_B_POSITION)
        await ui_test.human_delay(5)

        measurement = await self._measure_point_to_point(PRIM_PATHS)
        overridden_value = measurement.payload.primary_value

        stage.MuteLayer(override_layer.identifier)
        await ui_test.human_delay(5)

        expected_value = overridden_value / MOVED_DISTANCE_RATIO
        self.assertAlmostEqual(measurement.payload.primary_value, expected_value, 3)
        self.assertAlmostEqual(measurement.get_attribute("measure:compute:primary"), expected_value, 3)

    async def test_measure_flagged_while_measured_payload_is_unloaded(self):
        """
        OMPE-117792: unloading a payload that holds a measured prim flags the measurement as unresolved and hides it
        in the viewport, keeping the last computed value instead of computing against missing geometry.
        """
        payload_stage = await self._create_payload_cube("/payload")
        measurement = await self._measure_point_to_point([PRIM_PATHS[0], "/payload/Cube"])
        measured_value = measurement.payload.primary_value

        self._ctx.get_stage().Unload("/payload")
        await ui_test.human_delay(5)

        self.assertEqual(measurement.payload.unresolved_prim_paths, [Sdf.Path("/payload/Cube")])
        self.assertFalse(self.reference_manager.measure_scene.read(measurement.uuid).visible)
        self.assertAlmostEqual(measurement.get_attribute("measure:compute:primary"), measured_value, 3)

    async def test_measure_recomputes_when_measured_payload_is_reloaded(self):
        """
        OMPE-117792: reloading a payload clears the unresolved flag and recomputes the measurement against the
        reloaded geometry, which here was moved while the payload was unloaded.
        """
        payload_stage = await self._create_payload_cube("/payload")
        measurement = await self._measure_point_to_point([PRIM_PATHS[0], "/payload/Cube"])
        measured_value = measurement.payload.primary_value

        stage = self._ctx.get_stage()
        stage.Unload("/payload")
        await ui_test.human_delay(5)
        payload_stage.GetPrimAtPath("/Root/Cube").GetAttribute("xformOp:translate").Set(MOVED_CUBE_B_POSITION)
        stage.Load("/payload")
        await ui_test.human_delay(5)

        self.assertTrue(measurement.payload.resolved)
        self.assertTrue(self.reference_manager.measure_scene.read(measurement.uuid).visible)
        self.assertAlmostEqual(measurement.payload.primary_value, measured_value * MOVED_DISTANCE_RATIO, 3)
