import carb

from .utils import TangentData, TangentSideData, get_curve_plugin


class KeyData:
    def __init__(self, time: float = 0, value=None, idx: int = 0, tangent: TangentData = None):
        self.time = time
        self.value = value
        self.idx = idx
        self.tangent = tangent

    def __str__(self):
        return str("time: {}, value: {}, idx: {}").format(self.time, self.value, self.idx)


class SimplificationAlgorithm:
    """
    Algorithm to be used for curve simplification.

    CatmullRemove:
        Iterative removal of keys based on Catmull-Rom spline fitting. No new keys are created.
    """

    CatmullRemove = 0
    Default = CatmullRemove


class CurveSimplifier:
    VALUE_RANGE_EPS = 0.00001

    def __init__(self, maxErrorPercent: float = 1, continuous_algorithm: SimplificationAlgorithm = None) -> None:
        self.maxErrorRatio = maxErrorPercent * 0.01
        self.continuous_algorithm = continuous_algorithm
        if self.continuous_algorithm is None:
            self.continuous_algorithm = SimplificationAlgorithm.Default

    def is_discrete(self, attribute_name: str) -> bool:
        if "visibility" in attribute_name:
            return True
        return False

    # keeps keys which change the value compared to the previous key
    def simplify_keys_discrete(self, keys: list):
        assert len(keys) >= 2
        keys_out = [keys[0]]
        for i in range(1, len(keys) - 1):
            if keys[i].value != keys[i - 1].value:
                keys_out.append(keys[i])
        keys_out.append(keys[-1])
        return keys_out

    # Iteratively removes points which are closest to a fitted Catmull-Rom
    def simplify_keys_catmullromfit(self, keys: list, optimized: bool = True):
        new_keys = get_curve_plugin().simplify_catmull(
            [key.time for key in keys], [key.value for key in keys], self.VALUE_RANGE_EPS, self.maxErrorRatio
        )
        out_keys = []
        for k in new_keys:
            out_keys.append(KeyData(k[0], k[1]))
        return out_keys

    def simplify_keys_continuous(self, keys: list):
        if self.continuous_algorithm != SimplificationAlgorithm.CatmullRemove:
            carb.log_warn("Only support Catmull Rom Fitting Algorithm!")
        return self.simplify_keys_catmullromfit(keys)

    def compute_tangents(self, orig_keys: list, keys: list):
        for i, key in enumerate(keys):
            idx = key.idx  # index in the original key list
            set_inTangent = idx > 0
            set_outTangent = idx < len(orig_keys) - 1

            # Heuristic: if the keys were originally close, we want to keep the smooth transition
            if i > 0 and abs(keys[i - 1].idx - key.idx) <= 2:
                set_inTangent = False
            if i < len(keys) - 1 and abs(keys[i + 1].idx - key.idx) <= 2:
                set_outTangent = False

            key.tangent = TangentData()
            key.tangent.inTangent = TangentSideData()
            key.tangent.outTangent = TangentSideData()
            key.tangent.tangentBroken = False
            if set_inTangent:
                key.tangent.tangentBroken = True
                key.tangent.inTangent.type = "fixed"
                t = orig_keys[idx - 1].time - key.time
                v = orig_keys[idx - 1].value - key.value
                key.tangent.inTangent.time = t
                key.tangent.inTangent.value = v
            else:
                key.tangent.inTangent.type = "auto"
            if set_outTangent:
                key.tangent.tangentBroken = True
                key.tangent.outTangent.type = "fixed"
                t = orig_keys[idx + 1].time - key.time
                v = orig_keys[idx + 1].value - key.value
                key.tangent.outTangent.time = t
                key.tangent.outTangent.value = v
            else:
                key.tangent.outTangent.type = "auto"

    def simplify_keys(self, keys: list, attribute_name: str, compute_tangents: bool = False):
        if len(keys) <= 2:
            return keys

        if self.is_discrete(attribute_name):
            return self.simplify_keys_discrete(keys)
        else:
            if compute_tangents:
                orig_keys = keys.copy()
            keys = self.simplify_keys_continuous(keys)
            if compute_tangents:
                self.compute_tangents(orig_keys, keys)
            return keys
