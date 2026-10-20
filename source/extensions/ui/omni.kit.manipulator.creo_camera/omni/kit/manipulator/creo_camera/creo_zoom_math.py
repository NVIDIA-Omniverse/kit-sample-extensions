## Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
##
## NVIDIA CORPORATION and its licensors retain all intellectual property
## and proprietary rights in and to this software, related documentation
## and any modifications thereto.  Any use, reproduction, disclosure or
## distribution of this software and related documentation without an express
## license agreement from NVIDIA CORPORATION is strictly prohibited.
##

"""
Shared zoom math for Creo camera manipulator.

Provides common zoom calculation with pan compensation and COI adjustment.
"""

__all__ = [
    "apply_zoom_with_pan_compensation",
    "adjust_coi_for_zoom",
    "calculate_percentage_zoom_distance",
    "get_coi_distance_from_model",
]

from pxr import Gf


def apply_zoom_with_pan_compensation(current_transform, projection, zoom_distance, mouse_ndc, target_world_pos):
    """
    Apply zoom forward/backward with pan compensation to keep target at mouse position.

    Args:
        current_transform: Current camera transform (Gf.Matrix4d)
        projection: Projection matrix (Gf.Matrix4d)
        zoom_distance: Distance to move forward (positive) or backward (negative)
        mouse_ndc: Mouse position in NDC coordinates [x, y]
        target_world_pos: World position to keep at mouse cursor (Gf.Vec3d)

    Returns:
        New camera transform (Gf.Matrix4d)
    """
    inv_projection = projection.GetInverse()

    # Step 1: Move camera forward/backward along its Z axis
    camera_rotation = current_transform.ExtractRotationMatrix()
    camera_forward = -camera_rotation.GetRow(2)  # Camera looks along -Z

    new_camera_pos = current_transform.ExtractTranslation() + (camera_forward * zoom_distance)

    # Build transform after zoom
    new_transform = Gf.Matrix4d(1.0)
    new_transform.SetRotateOnly(camera_rotation)
    new_transform.SetTranslateOnly(new_camera_pos)

    # Step 2: Pan compensation to keep target at mouse position
    camera_inverse = new_transform.GetInverse()
    target_cam_space = camera_inverse.Transform(target_world_pos)

    # Only apply pan if target is in front of camera
    if target_cam_space[2] < -0.01:
        target_depth = abs(target_cam_space[2])

        # Where mouse ray hits at target depth in camera space
        mouse_ray_ndc = Gf.Vec3d(mouse_ndc[0], mouse_ndc[1], -1)
        mouse_ray = inv_projection.Transform(mouse_ray_ndc).GetNormalized()

        if abs(mouse_ray[2]) > 0.0001:
            # Scale ray to target depth
            scale_factor = -target_depth / mouse_ray[2]
            desired_cam_position = mouse_ray * scale_factor

            # Calculate pan to align target with mouse position
            pan = target_cam_space - desired_cam_position
            pan_xy_only = Gf.Vec3d(pan[0], pan[1], 0.0)  # Only X,Y, no Z

            # Apply pan in camera space
            pan_matrix = Gf.Matrix4d().SetTranslate(pan_xy_only)
            new_transform = pan_matrix * new_transform

    return new_transform


def adjust_coi_for_zoom(model, target_world_pos):
    """
    Adjust center of interest using Kit's object-centric mechanism.

    This uses Kit's built-in COI adjustment that:
    1. Stores the world anchor point (target_world_pos)
    2. Automatically recalculates COI distance from camera to that point
    3. Writes the adjusted COI to USD

    Must be called BEFORE triggering interaction_ended write.

    Args:
        model: Camera manipulator model
        target_world_pos: World position to use as COI anchor (Gf.Vec3d or list/tuple)

    Usage:
        # After updating transform, before writing:
        adjust_coi_for_zoom(self.model, target_world_pos)

        # Then trigger undoable write:
        self.model.set_ints("interaction_ended", [1])
        self.model._item_changed("transform")
        self.model.set_ints("interaction_ended", [0])
    """
    # Convert to list if needed
    if hasattr(target_world_pos, "__getitem__"):
        world_pos = [target_world_pos[0], target_world_pos[1], target_world_pos[2]]
    else:
        world_pos = [target_world_pos.x, target_world_pos.y, target_world_pos.z]

    # 1. Store the world anchor point that COI should track
    model.set_floats("center_of_interest_picked", world_pos)

    # 2. Save current COI as start value for comparison
    coi = model.get_as_floats("center_of_interest")
    if coi:
        model.set_floats("center_of_interest_start", coi.copy())

    # 3. Enable object-centric mode
    # This tells adjust_center_of_interest() to use center_of_interest_picked
    model.set_ints("object_centric_movement", [1])


def get_coi_distance_from_model(model):
    """
    Extract COI distance from camera manipulator model.

    Args:
        model: Camera manipulator model

    Returns:
        float: COI distance (positive), defaults to 100.0 if not available
    """
    coi = model.get_as_floats("center_of_interest")
    return abs(coi[2]) if coi and len(coi) >= 3 else 100.0


def calculate_percentage_zoom_distance(
    zoom_amount, camera_transform, target_world_pos, coi_distance, zoom_percent=0.15
):
    """
    Calculate zoom distance based on percentage of reference distance.

    Uses asymmetric formula to ensure forward/backward operations return to same position:
    - Forward (zoom in): distance * percent
    - Backward (zoom out): distance * (1.0/(1.0 - percent) - 1.0)

    Reference distance is min(COI distance, distance to target).

    Args:
        zoom_amount: Zoom input (positive = zoom in, negative = zoom out)
        camera_transform: Current camera transform (Gf.Matrix4d)
        target_world_pos: World position of zoom target (Gf.Vec3d)
        coi_distance: Current center of interest distance (positive float)
        zoom_percent: Zoom percentage per unit (default 0.15 = 15%)

    Returns:
        float: Zoom distance (positive = forward/zoom in, negative = backward/zoom out)

    Example:
        Distance = 100, percent = 15%
        Forward (1.0): 100 * 0.15 = 15 units forward
        Backward (-1.0): 100 * (1.0/(1.0-0.15) - 1.0) = 17.65 units backward
        Result: 100 - 15 = 85, then 85 * 1.176... = 100 (returns to start)
    """
    # Calculate distance from camera to target
    camera_pos = camera_transform.ExtractTranslation()
    distance_to_target = (target_world_pos - camera_pos).GetLength()

    # Reference distance is minimum of COI and target distance
    reference_distance = min(coi_distance, distance_to_target)

    # Ensure minimum reference distance to avoid extreme speeds
    reference_distance = max(reference_distance, 1.0)

    # Calculate zoom distance based on direction using asymmetric formula
    if zoom_amount > 0:
        # Zoom in (forward): simple percentage
        zoom_distance = reference_distance * zoom_percent * zoom_amount
    else:
        # Zoom out (backward): inverse formula for symmetry
        # distance * (1.0/(1.0 - percent) - 1.0)
        zoom_distance = reference_distance * (1.0 / (1.0 - zoom_percent) - 1.0) * zoom_amount

    return zoom_distance
