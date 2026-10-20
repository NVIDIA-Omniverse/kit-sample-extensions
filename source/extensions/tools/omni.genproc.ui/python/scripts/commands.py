from typing import Callable, List

import omni.kit as ok
from omni.usd.commands import DeletePrimsCommand


class CreateGenProcEntityCommand(ok.commands.Command):
    def __init__(self, callback: Callable[[], List[str]]):
        self._callback = callback
        self._created_paths = []

    def do(self):
        if self._callback:
            self._created_paths = self._callback()

    def undo(self):
        delete_cmd = DeletePrimsCommand(sorted(self._created_paths, key=len, reverse=True))
        delete_cmd.do()
        self._created_paths = []


ok.commands.register(CreateGenProcEntityCommand)
