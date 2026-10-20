import omni.ext

_EXT = None


class PublicExtension(omni.ext.IExt):
    def on_startup(self, ext_id):
        global extension_path
        manager = omni.kit.app.get_app().get_extension_manager()
        self.extension_path = manager.get_extension_path(ext_id)
        global _EXT
        _EXT = self

    def on_shutdown(self):
        global _EXT
        _EXT = None

    def get_ext_path(self):
        return self.extension_path


def get_ext() -> PublicExtension:
    global _EXT
    return _EXT
