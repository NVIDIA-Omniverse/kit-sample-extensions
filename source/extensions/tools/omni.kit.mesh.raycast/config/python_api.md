# Public API for module omni.kit.mesh.raycast:

## Classes

- class BoundResult
  - [property] def distance(self) -> float
  - [property] def meshIndex(self) -> int

- class BvhRefreshRate
  - def __init__(self, value: int)
  - [property] def name(self) -> str
  - [property] def value(self) -> int
  - FAST: omni.kit.mesh.raycast._meshraycast.BvhRefreshRate
  - SLOW: omni.kit.mesh.raycast._meshraycast.BvhRefreshRate

- class CurveTessellateResult
  - [property] def positions(self) -> typing.Any
  - [property] def tangents(self) -> typing.Any

- class HitResult
  - [property] def face_index(self) -> int
  - [property] def meshIndex(self) -> int
  - [property] def mesh_index(self) -> int
  - [property] def normal(self) -> carb._carb.Float3
  - [property] def position(self) -> carb._carb.Float3

- class IMeshRaycast
  - def closestRaycast(self, origin: carb._carb.Float3, dir: carb._carb.Float3, dist: float, context: RaycastContext = None) -> HitResult
  - def closestRaycastBound(self, origin: carb._carb.Float3, dir: carb._carb.Float3, dist: float, context: RaycastContext = None) -> BoundResult
  - def closestRaycastMesh(self, arg0: str, arg1: carb._carb.Float3, arg2: carb._carb.Float3, arg3: float, arg4: bool) -> HitResult
  - def create_context(self) -> RaycastContext
  - def destroy_context(self, arg0: RaycastContext)
  - def getFloodPoints(self, arg0: str, arg1: float, arg2: bool) -> dict
  - def get_bvh_refresh_rate(self) -> BvhRefreshRate
  - def get_mesh_path_from_index(self, arg0: int) -> str
  - def get_mesh_paths(self) -> typing.List[str]
  - def get_mesh_raycast_event_stream(self) -> carb.events._events.IEventStream
  - def get_vertex_local_positions(self, arg0: str, arg1: typing.List[int]) -> typing.List[carb._carb.Float3]
  - def overlap_vertices(self, origin: carb._carb.Float3, radius: float, context: RaycastContext = None) -> typing.List[OverlapVerticesEntry]
  - static def sample_curve_segment_at_t(*args, **kwargs) -> typing.Any
  - def set_allowed_mesh_paths(self, paths: typing.List[str], context: RaycastContext = None)
  - def set_bvh_refresh_rate(self, arg0: BvhRefreshRate, arg1: bool)
  - def set_disallowed_mesh_paths(self, paths: typing.List[str], include_descendents: bool, context: RaycastContext = None)
  - def set_hit_filter_fn(self, fn: typing.Callable[[str], bool], context: RaycastContext = None)
  - def spherecast(self, origin: carb._carb.Float3, dir: carb._carb.Float3, radius: float, dist: float, context: RaycastContext = None) -> typing.List[int]
  - def tessellate_curve(self, arg0: str, arg1: int, arg2: bool) -> typing.List[CurveTessellateResult]

- class OverlapVerticesEntry
  - [property] def faceIndices(self) -> typing.List[int]
  - [property] def meshIndex(self) -> int
  - [property] def vertexIndices(self) -> typing.List[int]

- class RaycastContext

- class RaycastEventType
  - def __init__(self, value: int)
  - [property] def name(self) -> str
  - [property] def value(self) -> int
  - BVH_REBUILT: omni.kit.mesh.raycast._meshraycast.RaycastEventType

## Functions

- def acquire_mesh_raycast_interface(plugin_name: str = None, library_path: str = None) -> IMeshRaycast
- def release_mesh_raycast_interface(arg0: IMeshRaycast)
- def get_mesh_raycast_interface() -> IMeshRaycast
