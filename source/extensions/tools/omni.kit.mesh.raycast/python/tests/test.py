from pathlib import Path

import carb
import omni.kit.commands
import omni.kit.mesh.raycast
import omni.kit.test
import omni.timeline
import omni.usd
from pxr import Gf, UsdGeom


class RaycastTests(omni.kit.test.AsyncTestCase):
    async def setUp(self):
        extension_root_folder = Path(
            omni.kit.app.get_app().get_extension_manager().get_extension_path_by_module(__name__)
        )
        self._test_files = extension_root_folder.joinpath("data/usd")

        # Load the USD
        usd_context = omni.usd.get_context()
        test_file_path = self._test_files.joinpath("cube.usda").absolute()
        await usd_context.open_stage_async(str(test_file_path))

        await omni.kit.app.get_app().next_update_async()

        self._raycast = omni.kit.mesh.raycast.get_mesh_raycast_interface()
        self._raycast.set_bvh_refresh_rate(omni.kit.mesh.raycast.BvhRefreshRate.FAST, True)
        self._raycast.set_allowed_mesh_paths([])

    async def tearDown(self):
        omni.usd.get_context().close_stage()
        self._raycast.set_bvh_refresh_rate(omni.kit.mesh.raycast.BvhRefreshRate.SLOW, False)
        self._raycast = None

    def assertAlmostEqual_Float3(self, a: carb.Float3, b: carb.Float3):
        self.assertAlmostEqual(a[0], b[0], places=5)
        self.assertAlmostEqual(a[1], b[1], places=5)
        self.assertAlmostEqual(a[2], b[2], places=5)

    def _flush_bvh(self):
        """Fold pending stage edits into the BVH now, instead of on some later Kit update.

        The BVH is normally refreshed from an update handler, so a query issued right after a
        stage edit can still see the pre-edit scene. Passing ``wait_for_update=True`` runs that
        handler inline and returns once the edit is in the BVH, which keeps the queries below
        deterministic. The rate is already FAST from ``setUp``; re-passing it is only how the
        interface exposes the forced refresh.
        """
        self._raycast.set_bvh_refresh_rate(omni.kit.mesh.raycast.BvhRefreshRate.FAST, True)

    def _mesh_paths(self, mesh_indices):
        """Mesh paths behind a spherecast result, sorted so an assertion reads as a set."""
        return sorted(self._raycast.get_mesh_path_from_index(index) for index in mesh_indices)

    async def test_raycast(self):
        from_pos = Gf.Vec3d(100, 100, 100)
        dir = Gf.Vec3d(-1, -1, -1).GetNormalized()
        dist = 1000

        # closestRaycast
        hit_result = self._raycast.closestRaycast(from_pos, dir, dist)
        self.assertGreaterEqual(hit_result.meshIndex, 0, msg="the ray must hit the cube")
        self.assertAlmostEqual_Float3(hit_result.position, carb.Float3(50, 50, 50))
        self.assertAlmostEqual_Float3(hit_result.normal, carb.Float3(1, 0, 0))

        # invisible
        stage = omni.usd.get_context().get_stage()
        cube_prim = stage.GetPrimAtPath("/World/Cube")

        imageable = UsdGeom.Imageable(cube_prim)
        imageable.GetVisibilityAttr().Set(UsdGeom.Tokens.invisible)
        await omni.kit.app.get_app().next_update_async()

        self._flush_bvh()
        hit_result = self._raycast.closestRaycast(from_pos, dir, dist)
        self.assertLess(hit_result.meshIndex, 0, msg="an invisible cube must not be hit")

        imageable.GetVisibilityAttr().Set(UsdGeom.Tokens.inherited)
        await omni.kit.app.get_app().next_update_async()

        # sphere raycast: the swept sphere passes through the cube and through the sphere
        # nested under it, so both must be reported once visibility is restored.
        sphere_radius = 1
        self._flush_bvh()
        overlap_result = self._raycast.spherecast(from_pos, dir, sphere_radius, dist)
        self.assertEqual(
            self._mesh_paths(overlap_result),
            ["/World/Cube", "/World/Cube/Sphere"],
            msg="spherecast must report the cube and the sphere nested under it",
        )

        # overlap vertices
        center_pos = carb.Float3(50, 50, 50)
        vertices_result = self._raycast.overlap_vertices(center_pos, 10)
        self.assertEqual(
            [self._raycast.get_mesh_path_from_index(entry.meshIndex) for entry in vertices_result],
            ["/World/Cube"],
            msg="only the cube has vertices within 10 units of its (50, 50, 50) corner",
        )
        prim_path = self._raycast.get_mesh_path_from_index(vertices_result[0].meshIndex)

        # change prim on the fly
        omni.kit.commands.execute("DeletePrims", paths=[prim_path])
        omni.kit.commands.execute("CreatePrimCommand", prim_type="Sphere")
        await omni.kit.app.get_app().next_update_async()

        from_pos_2 = Gf.Vec3d(10, 0, 0)
        dir = Gf.Vec3d(-1, 0, 0)
        dist = 20
        self._flush_bvh()
        hit_result_2 = self._raycast.closestRaycast(from_pos_2, dir, dist)
        self.assertGreaterEqual(hit_result_2.meshIndex, 0, msg="the ray must hit the newly created sphere")
        self.assertAlmostEqual_Float3(hit_result_2.position, carb.Float3(1, 0, 0))
        self.assertAlmostEqual_Float3(hit_result_2.normal, carb.Float3(1, 0, 0))

        # flood
        density = 10
        prim_path = self._raycast.get_mesh_path_from_index(hit_result_2.meshIndex)
        result = self._raycast.getFloodPoints(prim_path, density, False)
        self.assertEqual(len(result["positions"]), 125)  # 125 = density * 4 * 3.14 * 1 * 1

    async def test_ancestor_becomes_geometry(self):
        await omni.usd.get_context().new_stage_async()
        stage = omni.usd.get_context().get_stage()
        UsdGeom.Xform.Define(stage, "/World/Parent")
        UsdGeom.Sphere.Define(stage, "/World/Parent/Child")
        await omni.kit.app.get_app().next_update_async()
        self._flush_bvh()

        def hit_paths():
            return self._mesh_paths(self._raycast.spherecast(Gf.Vec3d(10, 0, 0), Gf.Vec3d(-1, 0, 0), 0.1, 20))

        self.assertEqual(hit_paths(), ["/World/Parent/Child"])

        # The parent already has a BVH path entry for its descendant, but does not
        # own a bound. Adding geometry must allocate a separate bound for it.
        parent = UsdGeom.Cube.Define(stage, "/World/Parent")
        await omni.kit.app.get_app().next_update_async()
        self._flush_bvh()
        expected = ["/World/Parent", "/World/Parent/Child"]
        self.assertEqual(hit_paths(), expected)

        for _ in range(3):
            parent.MakeInvisible()
            await omni.kit.app.get_app().next_update_async()
            self._flush_bvh()
            self.assertEqual(hit_paths(), [])
            parent.MakeVisible()
            await omni.kit.app.get_app().next_update_async()
            self._flush_bvh()
            self.assertEqual(hit_paths(), expected)

    async def test_66407(self):
        # set invisible and remove a prim at the same frame
        timeline = omni.timeline.get_timeline_interface()
        stage = omni.usd.get_context().get_stage()
        timeline.play()
        await omni.kit.app.get_app().next_update_async()
        prim_path = "/test_crasher"
        cubeGeom = UsdGeom.Cube.Define(stage, prim_path)

        # This is somehow necessary to cause the bug
        imageable = UsdGeom.Imageable(cubeGeom)
        imageable.MakeInvisible()

        await omni.kit.app.get_app().next_update_async()
        from omni.usd.commands import DeletePrimsCommand

        DeletePrimsCommand([cubeGeom.GetPath()]).do()

    async def test_doubleside(self):
        await omni.usd.get_context().new_stage_async()
        stage = omni.usd.get_context().get_stage()
        result, path = omni.kit.commands.execute("CreateMeshPrim", prim_type="Disk")
        self.assertTrue(result)

        await omni.kit.app.get_app().next_update_async()

        from_pos = Gf.Vec3d(0, -100, 0)
        dir = Gf.Vec3d(0, 1, 0).GetNormalized()
        dist = 1000

        self._flush_bvh()
        hit_result = self._raycast.closestRaycast(from_pos, dir, dist)
        self.assertLess(hit_result.meshIndex, 0, msg="a single-sided disk must not be hit from behind")

        prim_disk = stage.GetPrimAtPath(path)
        prim_disk.GetAttribute("doubleSided").Set(True)
        await omni.kit.app.get_app().next_update_async()

        self._flush_bvh()
        hit_result = self._raycast.closestRaycast(from_pos, dir, dist)
        self.assertGreaterEqual(hit_result.meshIndex, 0, msg="a doubleSided disk must be hit from behind")
