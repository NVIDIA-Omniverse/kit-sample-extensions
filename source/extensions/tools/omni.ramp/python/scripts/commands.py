import omni.kit as ok
import omni.usd as ou


class SetRampValuesCommand(ok.commands.Command):
    def __init__(
        self,
        prim_path=None,
        pos_attr_name=None,
        val_attr_name=None,
        int_attr_name=None,
        old_positions=None,
        old_values=None,
        old_interps=None,
        new_positions=None,
        new_values=None,
        new_interps=None,
        **kwargs,
    ):
        self.prim_path = prim_path
        self.pos_attr_name = pos_attr_name
        self.val_attr_name = val_attr_name
        self.int_attr_name = int_attr_name
        self.old_pos = old_positions
        self.old_val = old_values
        self.old_int = old_interps
        self.new_pos = new_positions
        self.new_val = new_values
        self.new_int = new_interps

    def do(self):
        stage = ou.get_context().get_stage()
        if not stage:
            return

        prim = stage.GetPrimAtPath(self.prim_path)
        if not prim:
            return

        if self.new_pos and self.new_val and self.new_int:
            pos_attr = prim.GetAttribute(self.pos_attr_name)
            val_attr = prim.GetAttribute(self.val_attr_name)
            int_attr = prim.GetAttribute(self.int_attr_name)

            if pos_attr and val_attr and int_attr:
                pos_attr.Set(self.new_pos)
                val_attr.Set(self.new_val)
                int_attr.Set(self.new_int)

    def undo(self):
        stage = ou.get_context().get_stage()
        if not stage:
            return

        prim = stage.GetPrimAtPath(self.prim_path)
        if not prim:
            return

        if self.old_pos and self.old_val and self.old_int:
            pos_attr = prim.GetAttribute(self.pos_attr_name)
            val_attr = prim.GetAttribute(self.val_attr_name)
            int_attr = prim.GetAttribute(self.int_attr_name)

            if pos_attr and val_attr and int_attr:
                pos_attr.Set(self.old_pos)
                val_attr.Set(self.old_val)
                int_attr.Set(self.old_int)


ok.commands.register(SetRampValuesCommand)
