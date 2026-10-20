class PortModel:
    """Port model stub with an inputs list."""

    def __init__(self, inputs: list | None = None) -> None:
        self.inputs = inputs or []


class MappingModel:
    """Model stub mapping arbitrary keys to model instances."""

    def __init__(self, mapping: dict) -> None:
        self._mapping = mapping

    def __getitem__(self, key: object):
        return self._mapping[key]
