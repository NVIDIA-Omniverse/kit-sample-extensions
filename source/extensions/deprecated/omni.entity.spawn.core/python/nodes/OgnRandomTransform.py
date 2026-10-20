import array
import random

import omni.graph.core as og
from pxr import Gf


class OgnRandomTransform:
    def compute(db):
        def rand_vec(vec, vec_rand):
            rand = array.array("f", [random.random() * 2 - 1, random.random() * 2 - 1, random.random() * 2 - 1])
            return vec + rand * vec_rand

        translate = rand_vec(db.inputs.position, db.inputs.positionRandom)
        rotate = rand_vec(db.inputs.rotateXYZ, db.inputs.rotateXYZRandom)
        scale = rand_vec(db.inputs.scale, db.inputs.scaleRandom)

        scale_transform = Gf.Matrix4d()
        scale_transform.SetScale(Gf.Vec3d(abs(scale[0]), abs(scale[1]), abs(scale[2])))

        transform = Gf.Matrix4d()
        transform.SetIdentity()
        rot_x = Gf.Rotation(Gf.Vec3d.XAxis(), rotate[0])
        rot_y = Gf.Rotation(Gf.Vec3d.YAxis(), rotate[1])
        rot_z = Gf.Rotation(Gf.Vec3d.ZAxis(), rotate[2])
        transform.SetRotateOnly(rot_x * rot_y * rot_z)
        transform.SetTranslateOnly(Gf.Vec3d(translate[0], translate[1], translate[2]))

        db.outputs.transform = scale_transform * transform

        return True
