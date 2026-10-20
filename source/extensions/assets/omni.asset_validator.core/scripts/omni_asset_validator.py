# SPDX-FileCopyrightText: Copyright (c) 2022-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
import argparse
import logging
import os
import sys
import traceback

# Should have been imported by main
from omni.asset_validator.core import ValidationArgsExec, ValidationEngine, create_validation_parser


class _OmniLogHandler(logging.StreamHandler):
    def emit(self, record: logging.LogRecord):
        import omni.log

        if record.levelno == logging.DEBUG:
            omni.log.verbose(record.msg, channel="omni_asset_validator")
        elif record.levelno == logging.INFO:
            omni.log.info(record.msg, channel="omni_asset_validator")
        elif record.levelno == logging.WARNING:
            omni.log.warn(record.msg, channel="omni_asset_validator")
        elif record.levelno == logging.ERROR:
            omni.log.error(record.msg, channel="omni_asset_validator")


class _ValidationArgsExec(ValidationArgsExec):

    def _create_engine(self) -> ValidationEngine:
        return ValidationEngine(
            init_rules=self.init_rules,
            variants=self.variants,
            instance_prototypes=self.instance_prototypes,
        )


def main():
    try:
        # Python 3.8 - PATH no longer works, use this to add DLL search paths
        if hasattr(os, "add_dll_directory"):
            if "CARB_APP_PATH" in os.environ:
                os.add_dll_directory(os.environ["CARB_APP_PATH"])
        import carb
    except ModuleNotFoundError:
        print(
            "Unable to import carb module. Did you configure your PYTHONPATH correctly? "
            f"See traceback for details:\n{traceback.format_exc()}"
        )
        return 1

    import omni.log

    log = omni.log.get_log()
    log.set_channel_level("carb.settings.plugin", omni.log.Level.FATAL, omni.log.SettingBehavior.OVERRIDE)
    log.set_channel_level("omni.core.ITypeFactory", omni.log.Level.ERROR, omni.log.SettingBehavior.OVERRIDE)
    carb.get_framework().startup([])

    log.set_channel_enabled("omni_asset_validator", True, omni.log.SettingBehavior.OVERRIDE)
    log.set_channel_level("omni_asset_validator", omni.log.Level.VERBOSE, omni.log.SettingBehavior.OVERRIDE)
    omni.log.info(f"Running in {os.getcwd()}", channel="omni_asset_validator")

    # Redirect python logging to omni.log
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    logger.addHandler(_OmniLogHandler())

    parser: argparse.ArgumentParser = create_validation_parser()
    args = _ValidationArgsExec(parser.parse_args())
    args.run_validation()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit as error:
        if error.code != 0:
            raise error
