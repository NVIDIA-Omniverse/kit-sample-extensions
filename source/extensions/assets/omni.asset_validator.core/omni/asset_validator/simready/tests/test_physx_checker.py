# SPDX-FileCopyrightText: Copyright (c) 2025-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#

from omni.asset_validator.core.tests import AsyncValidationRuleTestCase, IsAFailure
from pxr import Sdf, Usd, UsdGeom, UsdPhysics

from .._physx_checker import PhysxArticulationChecker, PhysxRigidBodyChecker


class TestPhysxRigidBodyChecker(AsyncValidationRuleTestCase):
    async def test_rigid_body_nesting(self):
        stage = Usd.Stage.CreateInMemory()

        rigidbody0 = UsdGeom.Xform.Define(stage, "/rigidBody0")
        UsdPhysics.RigidBodyAPI.Apply(rigidbody0.GetPrim())
        await self.assertRuleAsync(asset=stage, rule=PhysxRigidBodyChecker, asserts=[])

        rigidbody1 = UsdGeom.Xform.Define(stage, "/rigidBody0/rigidBody1")
        UsdPhysics.RigidBodyAPI.Apply(rigidbody1.GetPrim())
        expected_failure = IsAFailure(
            message=PhysxRigidBodyChecker._NESTED_RIGID_BODY_MESSAGE.format("/rigidBody0"),
            at=Sdf.Path("/rigidBody0/rigidBody1"),
            requirement=PhysxRigidBodyChecker._NESTED_RIGID_BODY_REQUIREMENT,
        )
        await self.assertRuleAsync(asset=stage, rule=PhysxRigidBodyChecker, asserts=[expected_failure])

        rigidbody1.SetResetXformStack(True)
        await self.assertRuleAsync(asset=stage, rule=PhysxRigidBodyChecker, asserts=[])

        rigidbody2 = UsdGeom.Xform.Define(stage, "/rigidBody0/rigidBody1/rigidBody2")
        UsdPhysics.RigidBodyAPI.Apply(rigidbody2.GetPrim())
        expected_failure = IsAFailure(
            message=PhysxRigidBodyChecker._NESTED_RIGID_BODY_MESSAGE.format("/rigidBody0/rigidBody1"),
            at=Sdf.Path("/rigidBody0/rigidBody1/rigidBody2"),
            requirement=PhysxRigidBodyChecker._NESTED_RIGID_BODY_REQUIREMENT,
        )
        await self.assertRuleAsync(asset=stage, rule=PhysxRigidBodyChecker, asserts=[expected_failure])

        rigidbody3 = UsdGeom.Xform.Define(stage, "/rigidBody0/rigidBody1/interior/rigidBody3")
        UsdPhysics.RigidBodyAPI.Apply(rigidbody3.GetPrim())
        expected_failures = [
            expected_failure,
            IsAFailure(
                message=PhysxRigidBodyChecker._NESTED_RIGID_BODY_MESSAGE.format("/rigidBody0/rigidBody1"),
                at=Sdf.Path("/rigidBody0/rigidBody1/interior/rigidBody3"),
                requirement=PhysxRigidBodyChecker._NESTED_RIGID_BODY_REQUIREMENT,
            ),
        ]
        await self.assertRuleAsync(asset=stage, rule=PhysxRigidBodyChecker, asserts=expected_failures)

    async def test_rigid_body_nesting_cache(self):
        stage = Usd.Stage.CreateInMemory()
        checker = PhysxRigidBodyChecker(verbose=True, consumerLevelChecks=True, assetLevelChecks=True)

        rigidbody0 = UsdGeom.Xform.Define(stage, "/rigidBody0")
        rigidbody1 = UsdGeom.Xform.Define(stage, "/rigidBody0/rigidBody1")
        rigidbody2 = UsdGeom.Xform.Define(stage, "/rigidBody0/rigidBody1/rigidBody2")
        rigidbody3 = UsdGeom.Xform.Define(stage, "/rigidBody0/rigidBody1/rigidBody3")
        nonbody0 = UsdGeom.Xform.Define(stage, "/rigidBody0/rigidBody1/rigidBody3/nonBody0")
        rigidbody4 = UsdGeom.Xform.Define(stage, "/rigidBody0/rigidBody1/rigidBody3/nonBody0/rigidBody4")

        UsdPhysics.RigidBodyAPI.Apply(rigidbody0.GetPrim())
        rb1_api = UsdPhysics.RigidBodyAPI.Apply(rigidbody1.GetPrim())
        rb2_api = UsdPhysics.RigidBodyAPI.Apply(rigidbody2.GetPrim())
        UsdPhysics.RigidBodyAPI.Apply(rigidbody3.GetPrim())
        rb4_api = UsdPhysics.RigidBodyAPI.Apply(rigidbody4.GetPrim())

        rb1_api.GetRigidBodyEnabledAttr().Set(False)

        # test xform reset on node
        rigidbody1.SetResetXformStack(True)
        ret = checker._has_dynamic_body_parent(rigidbody1.GetPrim(), rb1_api)
        self.assertFalse(ret[0])
        self.assertEqual(checker._is_a_or_under_a_dynamic_body_cache, {})

        # test xform reset above node and rb disabled
        ret = checker._has_dynamic_body_parent(rigidbody2.GetPrim(), rb2_api)
        self.assertFalse(ret[0])
        expected_cache = {
            rigidbody1.GetPath(): (False, None),
        }
        self.assertEqual(checker._is_a_or_under_a_dynamic_body_cache, expected_cache)

        # xform reset change and reset caches
        rigidbody1.SetResetXformStack(False)
        checker.ResetCaches()

        # test cache content in two steps
        ret = checker._has_dynamic_body_parent(rigidbody2.GetPrim(), rb2_api)
        self.assertTrue(ret[0])
        self.assertEqual(ret[1], rigidbody0.GetPrim())
        expected_cache = {
            rigidbody1.GetPath(): (True, rigidbody0.GetPrim()),
            rigidbody0.GetPath(): (True, rigidbody0.GetPrim()),
            rigidbody2.GetPath(): (True, rigidbody2.GetPrim()),
        }
        self.assertEqual(checker._is_a_or_under_a_dynamic_body_cache, expected_cache)

        ret = checker._has_dynamic_body_parent(rigidbody4.GetPrim(), rb4_api)
        self.assertTrue(ret[0])
        self.assertEqual(ret[1], rigidbody3.GetPrim())
        expected_cache = {
            rigidbody1.GetPath(): (True, rigidbody0.GetPrim()),
            rigidbody0.GetPath(): (True, rigidbody0.GetPrim()),
            rigidbody2.GetPath(): (True, rigidbody2.GetPrim()),
            nonbody0.GetPath(): (True, rigidbody3.GetPrim()),
            rigidbody3.GetPath(): (True, rigidbody3.GetPrim()),
            rigidbody4.GetPath(): (True, rigidbody4.GetPrim()),
        }
        self.assertEqual(checker._is_a_or_under_a_dynamic_body_cache, expected_cache)

        # reset cache and repeat
        checker.ResetCaches()
        ret = checker._has_dynamic_body_parent(rigidbody4.GetPrim(), rb4_api)
        self.assertTrue(ret[0])
        self.assertEqual(ret[1], rigidbody3.GetPrim())
        expected_cache = {
            nonbody0.GetPath(): (True, rigidbody3.GetPrim()),
            rigidbody3.GetPath(): (True, rigidbody3.GetPrim()),
            rigidbody4.GetPath(): (True, rigidbody4.GetPrim()),
        }
        self.assertEqual(checker._is_a_or_under_a_dynamic_body_cache, expected_cache)


class TestPhysxArticulationChecker(AsyncValidationRuleTestCase):
    async def test_articulation_on_kinematic_body(self):
        stage = Usd.Stage.CreateInMemory()

        # Create articulation with rigid body
        articulation = UsdGeom.Xform.Define(stage, "/articulation")
        UsdPhysics.ArticulationRootAPI.Apply(articulation.GetPrim())
        rigid_body = UsdPhysics.RigidBodyAPI.Apply(articulation.GetPrim())

        # Test passes when rigid body is dynamic (enabled=True, kinematic=False)
        rigid_body.GetRigidBodyEnabledAttr().Set(True)
        rigid_body.GetKinematicEnabledAttr().Set(False)
        await self.assertRuleAsync(asset=stage, rule=PhysxArticulationChecker, asserts=[])

        # Test fails when kinematic is enabled
        rigid_body.GetRigidBodyEnabledAttr().Set(True)
        rigid_body.GetKinematicEnabledAttr().Set(True)

        expected_failure = IsAFailure(
            message=PhysxArticulationChecker._ARTICULATION_ON_KINEMATIC_BODY_MESSAGE,
            at=Sdf.Path("/articulation"),
            requirement=PhysxArticulationChecker._ARTICULATION_ON_KINEMATIC_BODY_REQUIREMENT,
        )
        await self.assertRuleAsync(asset=stage, rule=PhysxArticulationChecker, asserts=[expected_failure])
