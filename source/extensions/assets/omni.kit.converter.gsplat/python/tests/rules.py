# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: CC-BY-4.0 AND Apache-2.0
#
"""
Custom BaseRuleChecker for ParticleField3DGaussianSplat schema conformance.

Validates that converted USD output meets the 3D Gaussian Splatting schema
requirements: required attributes, consistent array sizes, correct value
ranges, and proper spherical harmonics configuration.

Reference: UsdVol.ParticleField3DGaussianSplat (OpenUSD 26.03+)

Usage in tests::

    from .rules import GaussianSplatSchemaChecker

    engine = omni.asset_validator.core.ValidationEngine()
    engine.enable_rule(GaussianSplatSchemaChecker)
    result = engine.validate(usd_path)
"""

import math

import omni.asset_validator.core
from pxr import Usd, UsdGeom

_PRIM_TYPE = "ParticleField3DGaussianSplat"

# Each of these is declared twice by the schema: a float form and a half form
# suffixed ``h``. Exactly one of a pair should be authored, so these rules resolve
# whichever is present rather than insisting on the float name.
_PAIRED_ATTRS = (
    "positions",
    "scales",
    "orientations",
    "opacities",
    "radiance:sphericalHarmonicsCoefficients",
)

# No half counterpart: the degree is an int, not a bulk array.
_REQUIRED_SCALARS = ("radiance:sphericalHarmonicsDegree",)


def _resolve(prim: Usd.Prim, base: str):
    """
    Return the authored attribute of a float/half pair, preferring the float form.

    Preferring float mirrors what RTX does when it finds both, which is also why
    authoring both is reported as an error: the half arrays would be ignored, so a
    producer that wrote them believing they were used would be misled.
    """
    float_attr = prim.GetAttribute(base)
    half_attr = prim.GetAttribute(f"{base}h")
    has_float = bool(float_attr) and float_attr.HasValue()
    has_half = bool(half_attr) and half_attr.HasValue()
    if has_float:
        return float_attr, has_half
    if has_half:
        return half_attr, False
    return None, False


_SH_DEGREE_TO_ELEMENT_SIZE = {0: 1, 1: 4, 2: 9, 3: 16}

_QUAT_NORM_TOL = 1e-3


class GaussianSplatSchemaChecker(omni.asset_validator.core.BaseRuleChecker):
    """Validate that ParticleField3DGaussianSplat prims conform to the schema.

    Stage-level checks:
        - Default prim is set
        - metersPerUnit is set and positive
        - upAxis is set

    Prim-level checks (for ParticleField3DGaussianSplat prims):
        - All required attributes are present and authored
        - All per-vertex arrays have consistent, non-zero element count
        - Opacities are in [0, 1]
        - Scales are all positive
        - Orientations are unit quaternions
        - SH degree is in {0, 1, 2, 3}
        - SH elementSize matches declared degree
        - SH array length equals N * elementSize
        - SH coefficients primvar has vertex interpolation and elementSize set
    """

    def CheckStage(self, usdStage: Usd.Stage) -> None:
        default_prim = usdStage.GetDefaultPrim()
        if not default_prim or not default_prim.IsValid():
            self._AddError(message="Stage has no default prim set.")

        if UsdGeom.GetStageMetersPerUnit(usdStage) <= 0:
            self._AddError(message="Stage metersPerUnit is missing or non-positive.")

        if not UsdGeom.GetStageUpAxis(usdStage):
            self._AddError(message="Stage upAxis is not set.")

    def CheckPrim(self, prim: Usd.Prim) -> None:
        if prim.GetTypeName() != _PRIM_TYPE:
            return

        self._check_required_attrs(prim)
        vertex_count = self._check_vertex_count_consistency(prim)
        if vertex_count is None or vertex_count == 0:
            return
        self._check_opacity_range(prim)
        self._check_scales_positive(prim)
        self._check_orientations_unit(prim)
        self._check_sh_degree(prim)
        self._check_sh_coefficients(prim, vertex_count)

    # ------------------------------------------------------------------
    # Required attributes
    # ------------------------------------------------------------------

    def _check_required_attrs(self, prim: Usd.Prim) -> None:
        for base in _PAIRED_ATTRS:
            attr, both = _resolve(prim, base)
            if attr is None:
                self._AddError(
                    message=f"Required attribute '{base}' (or '{base}h') is missing or has no value.",
                    at=prim,
                )
            elif both:
                self._AddError(
                    message=(
                        f"Both '{base}' and '{base}h' are authored. Consumers prefer the "
                        f"float form, so the half data would be ignored; author one."
                    ),
                    at=prim,
                )

        for attr_name in _REQUIRED_SCALARS:
            attr = prim.GetAttribute(attr_name)
            if not attr or not attr.HasValue():
                self._AddError(
                    message=f"Required attribute '{attr_name}' is missing or has no value.",
                    at=prim,
                )

        extent_attr = UsdGeom.Boundable(prim).GetExtentAttr()
        if not extent_attr or not extent_attr.HasValue():
            self._AddError(
                message="Required attribute 'extent' is missing or has no value.",
                at=prim,
            )

    # ------------------------------------------------------------------
    # Consistent vertex count
    # ------------------------------------------------------------------

    def _check_vertex_count_consistency(self, prim: Usd.Prim):
        """Return the vertex count N, or None if positions are missing."""
        positions_attr, _ = _resolve(prim, "positions")
        if positions_attr is None:
            return None

        N = len(positions_attr.Get())
        if N == 0:
            self._AddError(message="positions array is empty.", at=prim)
            return 0

        for name in ("scales", "orientations", "opacities"):
            attr, _ = _resolve(prim, name)
            if attr is not None:
                count = len(attr.Get())
                if count != N:
                    self._AddError(
                        message=f"'{name}' has {count} elements, expected {N} (positions count).",
                        at=prim,
                    )
        return N

    # ------------------------------------------------------------------
    # Value-range checks (report first violation only to avoid flooding)
    # ------------------------------------------------------------------

    def _check_opacity_range(self, prim: Usd.Prim) -> None:
        attr, _ = _resolve(prim, "opacities")
        if attr is None:
            return
        for i, val in enumerate(attr.Get()):
            if val < 0.0 or val > 1.0:
                self._AddError(
                    message=f"Opacity at index {i} is {val}, expected range [0, 1].",
                    at=prim,
                )
                break

    def _check_scales_positive(self, prim: Usd.Prim) -> None:
        attr, _ = _resolve(prim, "scales")
        if attr is None:
            return
        for i, s in enumerate(attr.Get()):
            if s[0] <= 0 or s[1] <= 0 or s[2] <= 0:
                self._AddError(
                    message=f"Scale at index {i} has non-positive component: ({s[0]}, {s[1]}, {s[2]}).",
                    at=prim,
                )
                break

    def _check_orientations_unit(self, prim: Usd.Prim) -> None:
        attr, _ = _resolve(prim, "orientations")
        if attr is None:
            return
        for i, q in enumerate(attr.Get()):
            real = q.GetReal()
            imag = q.GetImaginary()
            norm = math.sqrt(real**2 + imag[0] ** 2 + imag[1] ** 2 + imag[2] ** 2)
            if abs(norm - 1.0) > _QUAT_NORM_TOL:
                self._AddError(
                    message=f"Orientation at index {i} is not a unit quaternion (norm={norm:.6f}).",
                    at=prim,
                )
                break

    # ------------------------------------------------------------------
    # Spherical harmonics
    # ------------------------------------------------------------------

    def _check_sh_degree(self, prim: Usd.Prim) -> None:
        attr = prim.GetAttribute("radiance:sphericalHarmonicsDegree")
        if not attr or not attr.HasValue():
            return
        degree = attr.Get()
        if degree not in _SH_DEGREE_TO_ELEMENT_SIZE:
            self._AddError(
                message=f"SH degree is {degree}, expected one of {{0, 1, 2, 3}}.",
                at=prim,
            )

    def _check_sh_coefficients(self, prim: Usd.Prim, N: int) -> None:
        attr, _ = _resolve(prim, "radiance:sphericalHarmonicsCoefficients")
        if attr is None:
            return

        sh_primvar = UsdGeom.Primvar(attr)

        interpolation = sh_primvar.GetInterpolation()
        if interpolation != UsdGeom.Tokens.vertex:
            self._AddError(
                message=(f"SH coefficients primvar interpolation is " f"'{interpolation}', expected 'vertex'."),
                at=prim,
            )

        element_size = sh_primvar.GetElementSize()
        if element_size <= 0:
            self._AddError(
                message="SH coefficients primvar elementSize is not set.",
                at=prim,
            )
            return

        sh_degree_attr = prim.GetAttribute("radiance:sphericalHarmonicsDegree")
        if sh_degree_attr and sh_degree_attr.HasValue():
            degree = sh_degree_attr.Get()
            if degree in _SH_DEGREE_TO_ELEMENT_SIZE:
                expected = _SH_DEGREE_TO_ELEMENT_SIZE[degree]
                if element_size != expected:
                    self._AddError(
                        message=(f"SH elementSize is {element_size} but degree " f"{degree} expects {expected}."),
                        at=prim,
                    )

        total = len(attr.Get())
        expected_total = N * element_size
        if total != expected_total:
            self._AddError(
                message=(
                    f"SH coefficients array has {total} elements, " f"expected {N} x {element_size} = {expected_total}."
                ),
                at=prim,
            )
