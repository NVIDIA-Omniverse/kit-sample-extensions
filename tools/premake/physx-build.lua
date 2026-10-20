-- SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
-- SPDX-License-Identifier: LicenseRef-NvidiaProprietary

-- Physics 110.4 no longer distributes extension_physxsdk_deps. Retain the
-- existing consumers' static-library and checked-release policy locally.
local physx = {}

function physx.add_dependencies(sdk_dir, release_flavor)
    local release_flavor = release_flavor or "checked"
    local libraries = {
        "PhysXVehicle_static_64", "PhysXExtensions_static_64",
        "PhysXCharacterKinematic_static_64", "PhysX_static_64",
        "PhysXPvdSDK_static_64", "PhysXCooking_static_64",
        "PhysXCommon_static_64", "PhysXFoundation_static_64",
    }
    includedirs { sdk_dir.."/include" }
    defines { "PX_PHYSX_STATIC_LIB" }

    filter { "configurations:debug" }
        defines { "_DEBUG" }
    filter { "configurations:release" }
        defines { "NDEBUG" }

    filter { "system:windows" }
        links(libraries)
    filter { "system:windows", "platforms:x86_64", "configurations:debug" }
        libdirs { sdk_dir.."/bin/win.x86_64.vc142.md/debug" }
    filter { "system:windows", "platforms:x86_64", "configurations:release" }
        libdirs { sdk_dir.."/bin/win.x86_64.vc142.md/"..release_flavor }

    filter { "system:linux" }
        buildoptions { "-Wno-invalid-offsetof" }
        linkoptions { "-lpthread -Wl,--start-group -l"..table.concat(libraries, " -l").." -Wl,--end-group -ldl" }
    filter { "system:linux", "platforms:x86_64", "configurations:debug" }
        libdirs { sdk_dir.."/bin/linux.x86_64/debug" }
    filter { "system:linux", "platforms:x86_64", "configurations:release" }
        libdirs { sdk_dir.."/bin/linux.x86_64/"..release_flavor }
    filter { "system:linux", "platforms:aarch64", "configurations:debug" }
        libdirs { sdk_dir.."/bin/linux.aarch64/debug" }
    filter { "system:linux", "platforms:aarch64", "configurations:release" }
        libdirs { sdk_dir.."/bin/linux.aarch64/"..release_flavor }
    filter {}
end

return physx
