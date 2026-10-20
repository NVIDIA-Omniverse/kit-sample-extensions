#!/bin/bash -e

# Copyright (c) 2019-2023, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

set -e

SCRIPT_DIR=$( dirname -- "$( readlink -f -- "$0"; )"; )

cd $SCRIPT_DIR

if [[ -d "../../../kit.bat" ]]; then
    export EXT_ARGS=""
    export LOG_LEVEL=""
    export KIT_PATH="${SCRIPT_DIR}/../../../kit.bat"
fi
if [[ -d "../../../../_build/linux-$(arch)" ]]; then
    export EXT_ARGS="--ext-folder ${SCRIPT_DIR}/../../../../_build/linux-$(arch)/release/exts"
    export LOG_LEVEL="--/log/outputStreamLevel=Info --/log/channels/carb.*=error --/log/channels/omni.*=error --/log/channels/omni_asset_validator=verbose"
    export KIT_PATH="${SCRIPT_DIR}/../../../../_build/linux-$(arch)/release/kit.sh"
fi
if [[ -z "${KIT_PATH}" ]]; then
    echo "KIT_PATH could not be found"
    exit 1
fi

${KIT_PATH} ${LOG_LEVEL} --enable omni.asset_validator.core  --enable omni.usd_resolver ${EXT_ARGS} --exec "${SCRIPT_DIR}/omni_asset_validator.py $*"
