from ._meshraycast import *


# Cached interface instance pointer
def get_mesh_raycast_interface() -> IMeshRaycast:
    """Returns cached :class:`omni.kit.mesh.raycast IMeshRaycast` interface"""

    if not hasattr(get_mesh_raycast_interface, "meshraycast"):
        get_mesh_raycast_interface.meshraycast = acquire_mesh_raycast_interface()
    return get_mesh_raycast_interface.meshraycast
