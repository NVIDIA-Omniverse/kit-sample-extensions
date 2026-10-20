# Copyright (c) 2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.
#

# __all__ = ["triangulate_face"]

# from enum import Enum
# from itertools import permutations
# from typing import Dict, List, Optional, Tuple

# from pxr import Gf


# TOLERANCE = 1e-7

# class AngleKind(Enum):
#     ANG = 1
#     ANG_CONVEX = 2
#     ANG_REFLEX = 3
#     ANG_TANGENT = 4
#     ANG_360 = 5


# def __triangles_to_dict(triangles: List[Tuple[int, int, int]]) -> Dict:
#     """
#         List of triangles (a, b, c) CCW-oriented indices

#         Returns:
#             Dictionary mapping all edges in triangles to the containing triangle list.
#     """
#     tri_dict = dict()
#     for i in range(len(triangles)):
#         (a, b, c) = t = triangles[i]
#         tri_dict[(a, b)] = t
#         tri_dict[(b, c)] = t
#         tri_dict[(c, a)] = t
#     return tri_dict


# def __other_vert(triangle: Tuple[int, int, int], a: int, b: int) -> Optional[int]:
#     """
#         triangle is a tuple of 3 vertex indices, two of which are a and b.

# 	    Return the third index, or None if all vertices are a or b
#     """
#     for vert in triangle:
#         if vert not in [a, b]:
#             return vert
#     return None


# def __in_circle(a: int, b: int, c: int, d: int, points: List[Gf.Vec3d]):
#     """
#     Return true if circle through points with indices a, b, c
#     contains point with index d (indices into points).
#     Except: if ABC forms a counterclockwise oriented triangle
#     then the test is reversed: return true if d is outside the circle.
#     Will get false, no matter what orientation, if d is cocircular, with TOL^2.
#         | xa ya xa^2+ya^2 1 |
#         | xb yb xb^2+yb^2 1 | > 0
#         | xc yc xc^2+yc^2 1 |
#         | xd yd xd^2+yd^2 1 |
# 	"""
#     def _icc(point: Gf.Vec3d):
#         (x, y) = (point[0], point[1])
#         return (x, y, x * x + y * y)

#     (xa, ya, za) = _icc(points[a])
#     (xb, yb, zb) = _icc(points[b])
#     (xc, yc, zc) = _icc(points[c])
#     (xd, yd, zd) = _icc(points[d])
#     det = xa * (yb * zc - yc * zb - yb * zd + yd * zb + yc * zd - yd * zc) \
#           - xb * (ya * zc - yc * za - ya * zd + yd * za + yc * zd - yd * zc) \
#           + xc * (ya * zb - yb * za - ya * zd + yd * za + yb * zd - yd * zb) \
#           - xd * (ya * zb - yb * za - ya * zc + yc * za + yb * zc - yc * zb)
#     return det > 0.0


# def __is_reversed(edge: Tuple[int, int], triangle_dict: Dict, points: List[Gf.Vec3d]) -> bool:
#     """
#         If e=(a,b) is a non-border edge, with left-face triangle `tl` and
# 	    right-face triangle `tr`, then it is 'reversed' if the circle through
# 	    a, b, and the other vertex of tl contains the other vertex of tr.
#     """
#     if not (tl := triangle_dict.get(edge)):
#         return False

#     (a, b) = edge
#     if not (tr := triangle_dict.get((b, a))):
#         return False

#     c = __other_vert(tl, a, b)
#     d = __other_vert(tr, a, b)

#     if c is None or d is None:
#         return False

#     return __in_circle(a, b, c, d, points)


# def __reverse_edges(
#         triangles: List[Tuple[int, int, int]],
#         triangle_dict: Dict, border: set[Tuple[int, int]],
#         points: List[Gf.Vec3d]
#     ) -> List[Tuple[int, int]]:
#     """
#         Return list of reversed edges in triangles.

#         Only want to capture edges not in border, and only a single instance of
#         (u, v)/(v, u).
#     """
#     edges = []
#     for i in range(len(triangles)):
#         (a, b, c) = triangles[i]
#         for e in [(a,b), (b,c), (c,a)]:
#             if e in border:
#                 continue
#             (u, v) = e
#             if u < v:
#                 if __is_reversed(e, triangle_dict, points):
#                     edges.append(e)
#     return edges


# def __ccw(a: int, b: int, c: int, points: List[Gf.Vec3d]) -> bool:
#     """
#         Return true if ABC is a counterclockwise-oriented triangle,
#         where a, b, and c are indices into points.

#         Returns false if not, or if colinear within tolerance.
#     """
#     tri = [points[a], points[b], points[c]]

#     totals = sum([(tri[(i+1) % 3][0] - tri[i][0]) * (tri[i][1] + tri[(i+1) % 3][1]) for i in range(2)])
#     return totals > TOLERANCE


# def __is_ccw(points: List[Gf.Vec3d]) -> bool:
#     totals = sum([(points[(i+1) % 3][0] - points[i][0]) * (points[i][1] + points[(i+1) % 3][1]) for i in range(len(points) - 1)])
#     return totals > TOLERANCE


# def __segment_intersect(ixa: int, ixb: int, ixc: int, ixd: int, points: List[Gf.Vec3d]) -> bool:
#     """
#         Return true if segment AB intersects CD, false if they just touch.
#         ixa, ixb, ixc, ixd are indices into points.
#     """
#     a, b, c, d = points[ixa], points[ixb], points[ixc], points[ixd]
#     u = b - a
#     v = d - c
#     w = a - c
#     pp = u[0] * v[1] - u[1] * b[0]  # 2d cross product?
#     if abs(pp) > TOLERANCE:
#         si = (v[0] * w[0] - v[1] * w[1]) / pp
#         ti = (u[0] * w[0] - u[1] * w[1]) / pp
#         return 0.0 < si < 1.0 and 0.0 < ti < 1.0
#     else:
#         # parallel or overlapping
#         if Gf.Dot(u, u) == 0.0 or Gf.Dot(v, v) == 0.0:
#             return False
#         else:
#             pp2 = w[0] * v[1] - w[1] * v[0]
#             if abs(pp2) > TOLERANCE:
#                 return False
#             z = b - c

#             (vx, vy) = v[:2]
#             (wx, wy) = w[:2]
#             (zx, zy) = z[:2]
#             (t0, t1) = (wy / vy, zy / vy) if vx == 0.0 else (wx / vx, zx / vx)
#             return 0.0 < t0 < 1.0 and 0.0 < t1 < 1.0


# def __angle_kind(a: int, b: int, c: int, points: List[Gf.Vec3d]) -> int:
#     """
#         Return one of the Ang... constants to classify Angle formed by ABC,
#         in a counterclockwise traversal of a face, where a, b, c are indices into points.
#     """
#     if __ccw(a, b, c, points):
#         return AngleKind.ANG_CONVEX.value
#     elif __ccw(a, c, b, points):
#         return AngleKind.ANG_REFLEX.value
#     else:
#         vb = points[b]
#         return AngleKind.ANG_TANGENT.value if Gf.Dot(vb - points[a], points[c] - vb) > 0.0 else AngleKind.ANG.value


# def __ear_check(face: List[int], n: int, ang_k: List[int], vm1: int, v0: int, v1:int, points: List[Gf.Vec3d]) -> bool:
#     """
#         Return True if the successive vertices vm1, v0, v1
#         forms an ear.

#         What remains to check is that the edge vm1-v1 doesn't
#         intersect any other edge of the face (besides vm1-v0
#         and v0-v1).

#         Equivalently, there can't be a reflex Angle
#         inside the triangle vm1-v0-v1.
#     """
#     for j in range(n):
#         fv = face[j]
#         k = ang_k[j]
#         b = (k in [AngleKind.ANG_REFLEX.value, AngleKind.ANG_360.value]) and not (fv in [vm1, v0, v1])
#         if b:
#             c = not __ccw(v0, vm1, fv, points) or __ccw(vm1, v1, fv, points) or __ccw(v1, v0, fv, points)
#             fvm1 = face[(j-1) % n]
#             fv1 = face[(j+1) % n]

#             d = __segment_intersect(fvm1, fv, vm1, v0, points) or \
#                 __segment_intersect(fvm1, fv, v0, v1, points) or \
#                 __segment_intersect(fv, fv1, vm1, v0, points) or \
#                 __segment_intersect(fv, fv1, v0, v1, points)
#             if c or d:
#                 return False
#     return True


# def __is_ear(face: List[int], i: int, n: int, ang_k: List[int], points: List[Gf.Vec3d], mode: int) -> bool:
#     """
#         Return true, false depending on ear status of vertices
# 	    with indices i-1, i, i+1.

# 	    mode is amount of desperation: 0 is Normal mode,
# 	    mode 1 allows degenerate triangles (with repeated vertices)
# 	    mode 2 allows local self crossing (folded) ears
# 	    mode 3 allows any convex vertex (should always be one)
# 	    mode 4 allows anything (just to be sure loop terminates!)
#     """
#     k = ang_k[i]
#     vm2 = face[(i-2) % n]
#     vm1 = face[(i-1) % n]
#     v0 = face[i]
#     v1 = face[(i+1) % n]
#     v2 = face[(i+2) % n]

#     if vm1 == v0 or v0 == v1:
#         return mode > 0
#     b = k in [AngleKind.ANG_CONVEX.value, AngleKind.ANG_TANGENT.value, AngleKind.ANG.value]
#     c = __in_cone(vm1, v0, v1, v2, ang_k[(i+1) % n], points) and \
#         __in_cone(v1, vm2, vm1, v0, ang_k[(i-1) % n], points)
#     if b and c:
#         return __ear_check(face, n, ang_k, vm1, v0, v1, points)
#     if mode < 2:
#         return False
#     if mode == 3:
#         return __segment_intersect(vm2, vm1, v0, v1, points)
#     if mode == 4:
#         return b
#     return True


# def __find_ear(face: List[int], n: int, start: int, incr: int, points: List[Gf.Vec3d]) -> Optional[int]:
#     """
#         An ear of a polygon consists of three consecutive vertices
#         v(-1), v0, v1 such that v(-1) can connect to v1 without intersecting
#         the polygon.

#         Finds an ear, starting at index 'start' and moving
#         in direction incr. (We attempt to alternate directions, to find
#         'nice' triangulations for simple convex polygons.)

#         Returns index into faces of v0 (will always find one, because
#         uses a desperation mode if fails to find one with above rule).
#     """
#     def classify_angles(face: List[int], n: int, points: Gf.Vec3d) -> List[int]:
#         """
#             Return vector of anglekinds of the Angle around each point in face.
#         """
#         return [__angle_kind(face[(i-1) % n], face[i], face[(i+1) % n], points) for i in range(n)]

#     ang_k = classify_angles(face, n, points)
#     for mode in range(5):
#         i = start
#         while True:
#             if __is_ear(face, i, n, ang_k, points, mode):
#                 return i
#             i = (i + incr) % n
#             if i == start:
#                 break


# def __in_cone(vtest: int, a: int, b: int, c: int, b_kind: int, points: List[Gf.Vec3d]) -> bool:
#     """
#         Return true if point with index vtest is in Cone of points with
# 	    indices a, b, c, where Angle ABC has AngleKind Bkind.

# 	    The Cone is the set of points inside the left face defined by
# 	    segments ab and bc, disregarding all other segments of polygon for
# 	    purposes of inside test.
#     """
#     if b_kind in [AngleKind.ANG_REFLEX.value, AngleKind.ANG_360]:
#         if __in_cone(vtest, c, b, a, AngleKind.ANG_CONVEX.value, points):
#             return False
#         return not ((not __ccw(b, a, vtest, points) and not __ccw(b, vtest, a, points) and __ccw(b, a, vtest, points))
#                     or (not __ccw(b, c, vtest, points) and not __ccw(b, vtest, c, points) and __ccw(b, a, vtest, points)))

#     return __ccw(a, b, vtest, points) and __ccw(b, c, vtest, points)


# def __ear_chop_triangle_face(face: List[int], points: List[Gf.Vec3d]) -> List[Tuple[int, int, int]]:
#     """
#         Triangulate given face, with coords given by indexing into points.
# 	    Return list of faces, each of which will be a triangle.
# 	    Use the ear-chopping method.
#     """
#     def get_least_idx(face: List[int], points: List[Gf.Vec3d]):
#         """
#             Return index of coordinate that is leftmost, lowest in face.
#         """
#         idx: int = 0
#         best_pos = points[face[0]]
#         for i in range(1, len(face)):
#             pos = points[face[i]]
#             if pos[0] < best_pos[0] or (pos[0] == best_pos[0] and pos[1] < best_pos[1]):
#                 idx = i
#                 best_pos = pos
#         return idx

#     def chop_ear(face: List[int], i: int):
#         """
#             Return a copy of face (of length n), omitting element i.
#         """
#         return face[0:i] + face[i+1:]

#     triangles = []

#     start: int = get_least_idx(face, points)
#     incr = 1
#     n = len(face)

#     while n > 3:
#         i = __find_ear(face, n, start, incr, points)
#         if i is None:
#             return []
#         vm1 = face[(i - 1) % n]
#         v0, v1 = face[i], face[(i + 1) % n]
#         face = chop_ear(face, i)
#         n = len(face)
#         incr = -incr
#         start = i % n if incr == 1 else (i - 1) % n
#         triangles.append((vm1, v0, v1))
#     triangles.append(tuple(face))
#     return triangles


# def __constrained_delaunay(triangles: List[Tuple[int, int, int]], border: set[Tuple[int, int]], points: List[Gf.Vec3d]):
#     """
#         Args:
#             triangles: List of triangles (a, b, c) CCW-oriented indices into points
#             border: set of border edges (u, v) oriented so that triangles is a triangulation of the left face of the border(s)
#             points: points

#         Returns:
#             list of triangles in new triangulation
#     """

#     tri_dict: Dict = __triangles_to_dict(triangles)
#     rev_edges = __reverse_edges(triangles, tri_dict, border, points)
#     tri_set = set(triangles)

#     while len(rev_edges) > 0:
#         (a, b) = e = rev_edges.pop()
#         if e in border or not __is_reversed(e, tri_dict, points):
#             continue

#         # rotate e in quat adbc to get other diagonal
#         e_rev = (b, a)
#         if not (tl := tri_dict.get(e)) or not (tr := tri_dict.get(e_rev)):
#             continue  # should not happen
#         if (c := __other_vert(tl, a, b)) is None or (d := __other_vert(tr, a, b)) is None:
#             continue  # should not happen

#         new_tri_a, new_tri_b = (c, d, b) , (c, a, d)

#         del tri_dict[e]
#         del tri_dict[e_rev]

#         # Add new triangles
#         tri_dict[(c, d)] = new_tri_a
#         tri_dict[(d, b)] = new_tri_a
#         tri_dict[(b, c)] = new_tri_a

#         tri_dict[(d, c)] = new_tri_b
#         tri_dict[(c, a)] = new_tri_b
#         tri_dict[(a, d)] = new_tri_b

#         if tl in tri_set:
#             tri_set.remove(tl)
#         if tr in tri_set:
#             tri_set.remove(tr)

#         tri_set.add(new_tri_a)
#         tri_set.add(new_tri_b)
#         rev_edges.extend([(d, b), (b, c), (c, a), (a, d)])

#     return list(tri_set)

# def __edge_intersection(edge_a: Tuple[int, int], edge_b: Tuple[int, int], points: List[Gf.Vec3d]) -> Optional[Gf.Vec3d]:
#     def get_contact_point(normal, plane_dot, a, b):
#         norm_ab = (b - a).GetNormalized()
#         return a + norm_ab * Gf.Dot(normal, plane_dot - a) / Gf.Dot(normal, norm_ab)

#     ab = (a := points[edge_a[0]]) - (b := points[edge_a[1]])
#     cd = (c := points[edge_b[0]]) - (d := points[edge_b[1]])

#     if a in [c, d] or b in [c, d]:
#         return

#     line = Gf.Cross(ab, cd)
#     cross_ab = Gf.Cross(line, ab)

#     return get_contact_point(cross_ab, a, c, d)


# def __border_edges(face_list: List[int]) -> set[Tuple[int, int]]:
#     """
#         Return a set of (u,v) where u and v are successive vertex indices
#         in some face in the list in facelist.
#     """
#     edges = set()
#     for i in range(1, len(face_list)):
#         edges.add((face_list[i-1], face_list[i]))
#     edges.add((face_list[-1], face_list[0]))

#     return edges

# def triangulate_face(points: List[Gf.Vec3d]) -> List[Tuple[int, int, int]]:
#     """
#         Triangulate the given face
#     """
#     face: List[int] = [i for i in range(len(points))]

#     if len(face) <= 3:
#         return [tuple(face)]

#     if not __is_ccw(points):
#         face = face[::-1]
#         points = points[::-1]

#     triangles: List[Tuple[int, int, int]] = __ear_chop_triangle_face(face, points)
#     border: set[Tuple[int, int]] = __border_edges(face)

#     inter_pts = set([__edge_intersection(p[0], p[1], points) for p in permutations(border, r=2)])

#     # return triangles
#     return __constrained_delaunay(triangles, border, points)
