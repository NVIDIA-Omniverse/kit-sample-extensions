:: Copyright (c) 2019-2023, NVIDIA CORPORATION.  All rights reserved.
::
:: NVIDIA CORPORATION and its licensors retain all intellectual property
:: and proprietary rights in and to this software, related documentation
:: and any modifications thereto.  Any use, reproduction, disclosure or
:: distribution of this software and related documentation without an express
:: license agreement from NVIDIA CORPORATION is strictly prohibited.

@echo off
setlocal

pushd "%~dp0"

if exist "%~dp0..\..\..\kit.bat" (
    set "EXT_ARGS="
    set "LOG_LEVEL="
    set "KIT_PATH=%~dp0..\..\..\kit.bat"
)
if exist "%~dp0..\..\..\..\_build\windows-x86_64" (
    set "EXT_ARGS=--ext-folder %~dp0..\..\..\..\_build\windows-x86_64\release\exts"
    set "LOG_LEVEL=--/log/outputStreamLevel=Info --/log/channels/carb.*=error --/log/channels/omni.*=error --/log/channels/omni_asset_validator=verbose"
    set "KIT_PATH=%~dp0..\..\..\..\_build\windows-x86_64\release\kit.bat"
)
if not defined KIT_PATH (
    echo "KIT_PATH could not be found"
    exit /b 1
)

call "%KIT_PATH%" %LOG_LEVEL% --enable omni.asset_validator.core --enable omni.usd_resolver %EXT_ARGS% --exec "%~dp0omni_asset_validator.py %*"
