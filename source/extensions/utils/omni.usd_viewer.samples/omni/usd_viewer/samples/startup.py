"""
Module to affect copying the /samples folder contents to
_build/<platform>/release/samples on startup.
"""

import os
import shutil
import sys

import omni.ext
from carb.tokens import get_tokens_interface


class SamplesStartup(omni.ext.IExt):
    """A class to hold the startup commands for the Samples extension"""

    def on_startup(self, ext_id):
        """Gather the 2 required paths and affect the copy."""

    def on_shutdown(self):
        """Clean up any resources on extension shutdown"""
