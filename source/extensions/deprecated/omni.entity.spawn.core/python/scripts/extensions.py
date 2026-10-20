import omni.ext

from . import commands


class SpawnEntityExtension(omni.ext.IExt):
    def on_startup(self):
        self._reg_cmds = omni.kit.commands.register_all_commands_in_module(commands)

    def on_shutdown(self):
        omni.kit.commands.unregister_module_commands(self._reg_cmds)
        self._reg_cmds = None
