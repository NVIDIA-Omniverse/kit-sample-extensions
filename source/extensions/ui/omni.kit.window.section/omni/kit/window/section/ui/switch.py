import omni.ui as ui


class Switch:
    def __init__(self, model: ui.SimpleBoolModel, **kwargs):
        self._model = model

        self._image = ui.ImageWithProvider(
            checked=model.as_bool,
            width=24,
            height=24,
            # image_width=24,
            # image_height=24,
            style_type_name_override="Switch",
            mouse_pressed_fn=lambda x, y, key, a: self._on_clicked(key),
            identifier="switch",
            **kwargs,
        )

        self.__sub = model.subscribe_value_changed_fn(self.__on_changed)

    def destroy(self) -> None:
        self.__sub = None

    @property
    def model(self) -> ui.SimpleBoolModel:
        return self._model

    @property
    def checked(self) -> bool:
        return self._image.checked

    @checked.setter
    def checked(self, value: bool):
        self._image.checked = value

    def _on_clicked(self, button, *_):
        if button != 0:  # pragma: no cover
            return

        # The switch is changed.
        self.checked = not self.checked
        self._model.set_value(self.checked)

    def __on_changed(self, model: ui.SimpleBoolModel) -> None:
        self._image.checked = model.as_bool
