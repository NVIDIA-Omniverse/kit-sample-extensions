import os
import sys
from pathlib import Path

import carb
import omni.kit.app
import omni.kit.test
import omni.usd
import usdex.core
import usdex.rtx
from pxr import Gf, Sdf, Usd


def get_ext_root_path() -> Path:
    return Path(carb.tokens.get_tokens_interface().resolve("${omni.usdex.libs}"))


class TestUsdex(omni.kit.test.AsyncTestCase):

    async def test_usdex_core(self):
        """Test that usdex.core loaded correctly and the version is what we expect"""

        # read Version.h from include and parse the version string from the bottom of the file
        ext_root_path = get_ext_root_path()
        version_file_path = os.path.join(ext_root_path, "include", "usdex", "core", "Version.h")

        version_string = ""
        with open(version_file_path, "r") as file_handle:
            last_line = file_handle.readlines()[-1]
            version_string = last_line.split(" ")[-1].strip()

        # ensure the versions match
        self.assertTrue(usdex.core.version(), version_string)
        self.assertTrue("usdex.core" in sys.modules)

    async def test_major_minor_version_match(self):
        # Ensure that the major minor version of the extension matches that of the OpenUSD Exchange library

        # Get the major minor versions of this extension
        ext_manager = omni.kit.app.get_app().get_extension_manager()
        ext_id = ext_manager.get_extension_id_by_module("omni.usdex.libs")
        self.assertIsNotNone(ext_id, msg="Unable to get extension id for omni.usdex.libs")
        ext_dict = ext_manager.get_extension_dict(ext_id)
        ext_version = ext_dict.get("package", {}).get("version")
        self.assertIsNotNone(ext_version, msg="Unable to get extension version for omni.usdex.libs")
        ext_version_parts = ext_version.split(".")
        self.assertTrue(
            (len(ext_version_parts) >= 2), msg=f"Unable to get Extension major minor versions from {ext_version}"
        )
        ext_major_version = ext_version_parts[0]
        ext_minor_version = ext_version_parts[1]

        # Get the major minor versions of OpenUSD Exchange
        usdex_version = usdex.core.version()
        usdex_version_parts = usdex_version.split(".")
        self.assertTrue(
            (len(ext_version_parts) >= 2), msg=f"Unable to get usdex major minor versions from {usdex_version}"
        )
        usdex_major_version = usdex_version_parts[0]
        usdex_minor_version = usdex_version_parts[1]

        # Assert that the versions match
        self.assertEqual(ext_major_version, usdex_major_version)
        self.assertEqual(ext_minor_version, usdex_minor_version)

    async def test_usdex_rtx(self):
        """Test that usdex.rtx loaded correctly"""
        self.assertTrue("usdex.rtx" in sys.modules)

    async def test_passing_pxr_types(self):
        """Test that pxr types can be passed back and forth correctly"""
        name_cache = usdex.core.NameCache()

        # An SdfPath can be passed as the parent and a valid an unique name will be returned
        parent: Sdf.Path = Sdf.Path("/path")
        self.assertEqual(name_cache.getPrimName(parent, "foo"), "foo")
        self.assertEqual(name_cache.getPrimName(parent, "foo"), "foo_1")

        # An empty string will return the minimal valid name
        self.assertEqual(usdex.core.getValidPrimName(""), "tn__")

        # Illegal characters are correctly encoded
        self.assertEqual(usdex.core.getValidPrimName("/"), "tn__l0")
        self.assertEqual(usdex.core.getValidPrimName("#"), "tn__Z0")
        self.assertEqual(usdex.core.getValidPrimName(" "), "tn__W0")

        # Leading numerics are correctly encoded
        self.assertEqual(usdex.core.getValidPrimName("1"), "tn__1_")
        self.assertEqual(usdex.core.getValidPrimName("1_mesh"), "tn__1_mesh_")

        # A combination of illegal characters and leading numerics
        self.assertEqual(usdex.core.getValidPrimName("1 mesh"), "tn__1mesh_c5")

        # A valid name will return that same value
        self.assertEqual(usdex.core.getValidPrimName("_"), "_")
        self.assertEqual(usdex.core.getValidPrimName("_1"), "_1")
        self.assertEqual(usdex.core.getValidPrimName("mesh"), "mesh")

        # UTF-8 characters are correctly encoded and decoded.
        self.assertEqual(usdex.core.getValidPrimName("カーテンウォール"), "tn__sxB76l2Y5o0X16")

        # ISO-8859-1 encoding will cause encoding to fail resulting in the fallback character substitution being used.
        # The fallback character substitution slightly differs from pxr::TfMakeValidIdentifier in how it handles leading numerics
        self.assertEqual(usdex.core.getValidPrimName("mesh_Ä".encode("latin-1")), "mesh__")
        self.assertEqual(usdex.core.getValidPrimName("1_Ä".encode("latin-1")), "_1__")

    async def test_define_xform(self):
        """Test pxr/boost bound types can interop with usdex/pybind11 bound types"""
        omni.usd.get_context().new_stage()
        stage = omni.usd.get_context().get_stage()

        path = Sdf.Path("/Root")
        translation = Gf.Vec3d(10.0, 20.0, 30.0)
        rotate = Gf.Vec3f(45.0, 0.0, 0.0)
        rotation = Gf.Rotation(Gf.Vec3d.XAxis(), 45.0)
        scale = Gf.Vec3d(2.0, 2.0, 2.0)
        transform = Gf.Transform()
        transform.SetTranslation(translation)
        transform.SetPivotPosition(translation)
        transform.SetRotation(rotation)
        transform.SetScale(scale)
        xform = usdex.core.defineXform(stage, path, transform=transform)

        returned = usdex.core.getLocalTransformComponents(xform.GetPrim())
        self.assertEqual(returned[0], translation)
        self.assertEqual(returned[1], translation)
        self.assertEqual(returned[2], rotate)
        self.assertEqual(returned[3], usdex.core.RotationOrder.eXyz)
        self.assertEqual(returned[4], scale)

        # modify components by passing in t/r/s to usdex.core.setLocalTransform
        translation = Gf.Vec3d(15.0, 25.0, 35.0)
        rotate = Gf.Vec3f(50.0, 0.0, 0.0)
        rotation = Gf.Rotation(Gf.Vec3d.XAxis(), 50.0)
        scale = Gf.Vec3f(3.0, 3.0, 3.0)
        usdex.core.setLocalTransform(
            xform.GetPrim(),
            translation,
            translation,
            rotate,
            usdex.core.RotationOrder.eXyz,
            scale,
            Usd.TimeCode.Default(),
        )
        returned = usdex.core.getLocalTransformComponents(xform.GetPrim())
        self.assertEqual(returned[0], translation)
        self.assertEqual(returned[1], translation)
        self.assertEqual(returned[2], rotate)
        self.assertEqual(returned[3], usdex.core.RotationOrder.eXyz)
        self.assertEqual(returned[4], scale)

        # verify the values match bewteen USDEX function and traditional omni.usd approach
        # returned would be a tuple of (scale, rotate_euler, rotate_order, translation)
        returned = omni.usd.get_local_transform_SRT(xform.GetPrim())
        self.assertEqual(scale, returned[0])
        self.assertEqual(rotate, returned[1])
        self.assertEqual(Gf.Vec3i(0, 1, 2), returned[2])
        self.assertEqual(translation, returned[3])
