"""
Module to affect copying the /data folder light rig contents to a destination
folder as specified in the exts."omni.light_rigs".setup_extension_name setting.
"""

import omni.ext


class LightRigsStartup(omni.ext.IExt):
    """A class to hold the startup commands for the Light Rig extension"""

    def on_startup(self, ext_id):
        pass

    def on_shutdown(self):
        """Clean up any resources on extension shutdown"""
        pass
