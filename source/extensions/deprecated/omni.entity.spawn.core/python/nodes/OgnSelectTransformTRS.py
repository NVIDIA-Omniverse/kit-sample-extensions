from pxr import Gf


class OgnSelectTransformTRS:
    def compute(db):
        matrix = Gf.Matrix4d(*db.inputs.transform)
        result, r, s, u, t, p = matrix.Factor()

        matrix.SetIdentity()

        if db.inputs.useScale:
            matrix.SetScale(s)

        if db.inputs.useRotation:
            matrix = matrix * r

        if db.inputs.useTranslation:
            matrix.SetTranslateOnly(t)

        db.outputs.transform = matrix
        return True
