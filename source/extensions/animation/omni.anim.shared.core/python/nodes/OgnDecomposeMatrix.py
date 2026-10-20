import numpy as np
from pxr import Gf


class OgnDecomposeMatrix:
    @staticmethod
    def compute(db) -> bool:
        # Inputs
        # matrix
        matrix = Gf.Matrix4d(db.inputs.matrix.reshape(4, 4))

        # rotateOrder
        rotate_order = db.inputs.rotateOrder

        # outputs
        # translate
        db.outputs.translate = np.array(matrix.ExtractTranslation()).tolist()

        # rotate
        # 0=xyz, 1=yzx, 2=zxy, 3=xzy, 4=yxz, 5=zyx.
        if rotate_order == 1:
            rotate_coord = [Gf.Vec3d.YAxis(), Gf.Vec3d.ZAxis(), Gf.Vec3d.XAxis()]
            radY, radZ, radX = Gf.Rotation.DecomposeRotation3(matrix, *rotate_coord, 1.0)
        elif rotate_order == 2:
            rotate_coord = [Gf.Vec3d.ZAxis(), Gf.Vec3d.XAxis(), Gf.Vec3d.YAxis()]
            radZ, radX, radY = Gf.Rotation.DecomposeRotation3(matrix, *rotate_coord, 1.0)
        elif rotate_order == 3:
            rotate_coord = [Gf.Vec3d.XAxis(), Gf.Vec3d.ZAxis(), Gf.Vec3d.YAxis()]
            radX, radZ, radY = Gf.Rotation.DecomposeRotation3(matrix, *rotate_coord, 1.0)
        elif rotate_order == 4:
            rotate_coord = [Gf.Vec3d.YAxis(), Gf.Vec3d.XAxis(), Gf.Vec3d.ZAxis()]
            radY, radX, radZ = Gf.Rotation.DecomposeRotation3(matrix, *rotate_coord, 1.0)
        elif rotate_order == 5:
            rotate_coord = [Gf.Vec3d.ZAxis(), Gf.Vec3d.YAxis(), Gf.Vec3d.XAxis()]
            radZ, radY, radX = Gf.Rotation.DecomposeRotation3(matrix, *rotate_coord, 1.0)
        else:
            rotate_coord = [Gf.Vec3d.XAxis(), Gf.Vec3d.YAxis(), Gf.Vec3d.ZAxis()]
            radX, radY, radZ = Gf.Rotation.DecomposeRotation3(matrix, *rotate_coord, 1.0)
        db.outputs.rotate = [Gf.RadiansToDegrees(radX), Gf.RadiansToDegrees(radY), Gf.RadiansToDegrees(radZ)]

        # quaternion
        quat = matrix.ExtractRotationQuat()
        db.outputs.quaternion = [*quat.GetImaginary(), quat.GetReal()]

        # scale
        db.outputs.scale = np.linalg.norm(db.inputs.matrix.reshape(4, 4), axis=1)[:3]

        return True
