import omni.graph.core as og
from omni.entity.spawn.core.scripts.commands import *


class OgnDestroyEntity:
    def compute(db):
        DestroyEntityCommand(db.inputs.entityNames).do()

        db.outputs.execOut = og.ExecutionAttributeState.ENABLED

        return True
