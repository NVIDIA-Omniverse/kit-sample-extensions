import AnimationSchemaTools
from pxr import Gf


def compute_tangent(time, value, hasPrev, prevTime, prevKey, hasNext, nextTime, nextKey, interpolation_method):
    key = AnimationSchemaTools.Key()
    prev = AnimationSchemaTools.Key()
    next = AnimationSchemaTools.Key()

    key.time = time
    key.value = value
    if hasPrev:
        prev.time = prevTime
        prev.value = prevKey
    if hasNext:
        next.time = nextTime
        next.value = nextKey

    AnimationSchemaTools.ComputeTangent(
        key,
        prev,
        next,
        True,
    )
    AnimationSchemaTools.ComputeTangent(key, prev, next, False)
    return Gf.Vec4d(key.inRawTangent[0], key.inRawTangent[1], key.outRawTangent[0], key.outRawTangent[1])
