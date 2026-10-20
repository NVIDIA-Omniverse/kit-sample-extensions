import os.path

import carb
import omni.graph.core as og
import omni.usd
from omni.entity.spawn.core.scripts.commands import *
from pxr import Gf, Tf, Usd


class OgnSpawnEntity:
    def __init__(self) -> None:
        self._usd_listener = None
        self._db = None

    def __del__(self):
        if self._usd_listener is not None:
            self._usd_listener.Revoke()

    def _on_usd_changed(self, notice, stage):
        parent_prim = get_parent_prim(stage, False)
        if not parent_prim:
            return

        if not self._db.outputs.allSpawnedEntityNames:
            return

        paths = []

        for path in notice.GetResyncedPaths():
            if not path.IsAbsoluteRootOrPrimPath():
                continue

            if parent_prim.GetPath().HasPrefix(path):
                paths.append(path)
            elif path.GetParentPath() == parent_prim.GetPath():
                paths.append(path)

        if not paths:
            return

        removed_names = []

        for name in self._db.outputs.allSpawnedEntityNames:
            spawned_path = parent_prim.GetPath().AppendChild(name)
            for path in paths:
                if not spawned_path.HasPrefix(path):
                    continue

                if not stage.GetPrimAtPath(spawned_path):
                    removed_names.append(name)
                    break

        if not removed_names:
            return

        self._db.outputs.allSpawnedEntityNames = [
            name for name in self._db.outputs.allSpawnedEntityNames if name not in removed_names
        ]

    def internal_state():
        return __class__()

    def compute(db):

        self = db.internal_state
        self._db = db

        if self._usd_listener is not None:
            self._usd_listener.Revoke()
            self._usd_listener = None

        world_transform = Gf.Matrix4d()
        world_transform.Set(*db.inputs.transform)

        cmd = SpawnEntityCommand(db.inputs.sourcePaths, world_transform)
        spawned_names = cmd.do()

        db.outputs.entityNames = spawned_names
        spawned_names.extend(db.outputs.allSpawnedEntityNames)
        db.outputs.allSpawnedEntityNames = spawned_names

        db.outputs.execOut = og.ExecutionAttributeState.ENABLED

        stage = omni.usd.get_context().get_stage()
        self._usd_listener = Tf.Notice.Register(Usd.Notice.ObjectsChanged, self._on_usd_changed, stage)

        return True
