// SPDX-FileCopyrightText: Copyright (c) 2020-2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: LicenseRef-NvidiaProprietary
//
// NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
// property and proprietary rights in and to this material, related
// documentation and any modifications thereto. Any use, reproduction,
// disclosure or distribution of this material and related documentation
// without an express license agreement from NVIDIA CORPORATION or
// its affiliates is strictly prohibited.

#pragma once

inline pxr::GfQuaternion getQuaternion(const pxr::GfVec3d& angles, const pxr::UsdGeomXformOp::Type& opType, bool& valid)
{
    using namespace pxr;

    GfMatrix3d xRot(GfRotation(GfVec3f::XAxis(), angles[0]));
    GfMatrix3d yRot(GfRotation(GfVec3f::YAxis(), angles[1]));
    GfMatrix3d zRot(GfRotation(GfVec3f::ZAxis(), angles[2]));
    GfMatrix3d rotMat;

    switch (opType)
    {
    case PXR_NS::UsdGeomXformOp::TypeRotateXYZ:
    case PXR_NS::UsdGeomXformOp::TypeTransform:
        rotMat = xRot * yRot * zRot;
        break;
    case PXR_NS::UsdGeomXformOp::TypeRotateXZY:
        rotMat = xRot * zRot * yRot;
        break;
    case PXR_NS::UsdGeomXformOp::TypeRotateYXZ:
        rotMat = yRot * xRot * zRot;
        break;
    case PXR_NS::UsdGeomXformOp::TypeRotateYZX:
        rotMat = yRot * zRot * xRot;
        break;
    case PXR_NS::UsdGeomXformOp::TypeRotateZXY:
        rotMat = zRot * xRot * yRot;
        break;
    case PXR_NS::UsdGeomXformOp::TypeRotateZYX:
        rotMat = zRot * yRot * xRot;
        break;
    default:
        valid = false;
        return pxr::GfQuaternion();
    }

    pxr::GfQuaternion q = rotMat.ExtractRotationQuaternion();
    return q;
}

inline pxr::GfQuaternion slerp(double alpha, const pxr::GfQuaternion& q0, const pxr::GfQuaternion& q1)
{
    double cosTheta = q0.GetImaginary() * q1.GetImaginary() + q0.GetReal() * q1.GetReal();
    bool flip1 = false;

    if (cosTheta < 0.0)
    {
        cosTheta = -cosTheta;
        flip1 = true;
    }

    double scale0, scale1;

    if (1.0 - cosTheta > 0.00001)
    {
        // standard case
        double theta = acos(cosTheta), sinTheta = sin(theta);

        scale0 = sin((1.0 - alpha) * theta) / sinTheta;
        scale1 = sin(alpha * theta) / sinTheta;
    }
    else
    {
        // rot0 and rot1 very close - just do linear interp and renormalize.
        scale0 = 1.0 - alpha;
        scale1 = alpha;
    }

    if (flip1)
        scale1 = -scale1;

    return scale0 * q0 + scale1 * q1;
}

inline pxr::GfVec3d decomposeQuatToEuler(const pxr::GfQuaternion& q, const pxr::UsdGeomXformOp::Type& rotateOpType)
{
    pxr::GfVec3d axis0, axis1, axis2;

    // note that axis decomposition order is reverse of composition order
    switch (rotateOpType)
    {
    case PXR_NS::UsdGeomXformOp::TypeRotateXYZ:
    case PXR_NS::UsdGeomXformOp::TypeTransform:
        axis0 = pxr::GfVec3d::ZAxis();
        axis1 = pxr::GfVec3d::YAxis();
        axis2 = pxr::GfVec3d::XAxis();
        break;
    case PXR_NS::UsdGeomXformOp::TypeRotateXZY:
        axis0 = pxr::GfVec3d::YAxis();
        axis1 = pxr::GfVec3d::ZAxis();
        axis2 = pxr::GfVec3d::XAxis();
        break;
    case PXR_NS::UsdGeomXformOp::TypeRotateYXZ:
        axis0 = pxr::GfVec3d::ZAxis();
        axis1 = pxr::GfVec3d::XAxis();
        axis2 = pxr::GfVec3d::YAxis();
        break;
    case PXR_NS::UsdGeomXformOp::TypeRotateYZX:
        axis0 = pxr::GfVec3d::XAxis();
        axis1 = pxr::GfVec3d::ZAxis();
        axis2 = pxr::GfVec3d::YAxis();
        break;
    case PXR_NS::UsdGeomXformOp::TypeRotateZXY:
        axis0 = pxr::GfVec3d::YAxis();
        axis1 = pxr::GfVec3d::XAxis();
        axis2 = pxr::GfVec3d::ZAxis();
        break;
    case PXR_NS::UsdGeomXformOp::TypeRotateZYX:
        axis0 = pxr::GfVec3d::XAxis();
        axis1 = pxr::GfVec3d::YAxis();
        axis2 = pxr::GfVec3d::ZAxis();
        break;
    }

    pxr::GfRotation rot(q);
    pxr::GfVec3d angles = rot.Decompose(axis0, axis1, axis2);

    // need to reverse the order to map this back to composition order
    return pxr::GfVec3d(angles[2], angles[1], angles[0]);
}

static pxr::GfMatrix3f rotationMatrixFromEulerZYX(double z, double y, double x)
{
    pxr::GfMatrix3f xRot(pxr::GfRotation(pxr::GfVec3f::XAxis(), x));
    pxr::GfMatrix3f yRot(pxr::GfRotation(pxr::GfVec3f::YAxis(), y));
    pxr::GfMatrix3f zRot(pxr::GfRotation(pxr::GfVec3f::ZAxis(), z));

    pxr::GfMatrix3f result;
    result = zRot * yRot * xRot;

    return result;
}
