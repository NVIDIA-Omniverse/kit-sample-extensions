"""Internal isolation-model command used to remove and restore IO helper nodes."""

import omni.kit.commands

# pylint: disable=isinstance-second-argument-not-valid-type


class MaterialGraph_IsolationModelRemoveCommand(omni.kit.commands.Command):
    """Undoable removal of isolation input/output nodes."""

    def __init__(self, isolation_model: object, node: object, graph_model: object) -> None:
        """Initialize removal with isolation model and node."""
        from ...models.graph.isolation import MaterialGraphIsolationModel

        self._isolation_model = isolation_model
        self._node = node
        input_cls = getattr(MaterialGraphIsolationModel, "InputNode", None)
        self._is_input = False
        if input_cls:
            try:
                self._is_input = isinstance(node, input_cls)
            except TypeError:
                # input_cls may be a non-type proxy in some runtime builds.
                self._is_input = False
        if not self._is_input:
            self._is_input = hasattr(node, "remove_input") and not hasattr(node, "remove_output")
        self._position = node.position
        self._graph_model = graph_model
        self._failed = False

    def do(self) -> bool:
        """Execute isolation removal while preserving enough state to support a consistent undo operation."""
        if self._failed:
            return False
        if self._is_input:
            node_result = self._node.remove_input()
            if node_result is False or getattr(node_result, "success", True) is False:
                self._failed = True
                return False
            model_result = self._isolation_model.remove_input()
        else:
            node_result = self._node.remove_output()
            if node_result is False or getattr(node_result, "success", True) is False:
                self._failed = True
                return False
            model_result = self._isolation_model.remove_output()
        if model_result is False or getattr(model_result, "success", True) is False:
            self._isolation_model.add_input_or_output(self._position, self._is_input)
            self._failed = True
            return False
        return True

    def undo(self) -> None:
        """Restore the removed node."""
        if self._failed:
            return
        self._isolation_model.add_input_or_output(self._position, self._is_input)
        if hasattr(self._isolation_model, "refresh"):
            self._isolation_model.refresh()
