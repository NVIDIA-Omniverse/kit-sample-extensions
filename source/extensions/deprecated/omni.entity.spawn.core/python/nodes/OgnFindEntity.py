import omni.graph.core as og
from omni.entity.spawn.core.scripts.commands import *


class OgnFindEntity:
    def compute(db):
        db.outputs.entityNames = FindEntityCommand(db.inputs.sourcePath).do()
        db.outputs.execOut = og.ExecutionAttributeState.ENABLED
        return True
