local function first_to_upper(value)
    return value:gsub("^%l", string.upper)
end

local function library_suffix()
    if os.target() == "windows" then
        return ".lib"
    end
    return ""
end

function project_metrics_assembler_schema(schema_name, source, target_dir)
    targetname(schema_name)

    repo_build.prebuild_copy {
        { source.."/generatedSchema.usda", target_dir.."/resources" },
        { source.."/schema.usda", target_dir.."/resources/"..schema_name },
        { source.."/plugInfo_%{platform}.json", target_dir.."/resources/plugInfo.json" },
    }

    files { source.."/**.h", source.."/**.cpp" }
    removefiles { source.."/wrap*.cpp", source.."/module.cpp" }
    add_usd { "usdGeom" }
    defines { schema_name:upper().."_EXPORTS" }

    filter { "system:windows", "configurations:release" }
        defines { "WIN32", "_WINDOWS", "NDEBUG", "TBB_USE_THREADING_TOOLS" }
        buildoptions { "/Zc:rvalueCast", "/Zc:inline-", "/W3", "/WX-", "/Zi", "/GR" }
    filter { "system:windows", "configurations:debug" }
        defines { "WIN32", "_WINDOWS", "_DEBUG", "TBB_USE_DEBUG", "TBB_USE_ASSERT", "TBB_USE_THREADING_TOOLS" }
        buildoptions { "/Zc:rvalueCast", "/Zc:inline-", "/W3", "/WX-", "/Zi", "/GR" }
    filter { "system:linux", "configurations:release" }
        defines { "LINUX", "NDEBUG", "TBB_USE_THREADING_TOOLS" }
        buildoptions { "-Wno-deprecated", "-Wno-deprecated-declarations", "-Wno-inconsistent-missing-override" }
    filter { "system:linux", "configurations:debug" }
        defines { "LINUX", "TBB_USE_DEBUG", "TBB_USE_ASSERT", "TBB_USE_THREADING_TOOLS" }
        buildoptions { "-Wno-deprecated", "-Wno-deprecated-declarations", "-Wno-inconsistent-missing-override" }
    filter {}
end

function project_metrics_assembler_schema_python(schema_name, source)
    targetname("_"..schema_name)
    targetprefix("")

    add_usd { "usdGeom" }
    usd_module.use_usd_python_modules(schema_name, first_to_upper(schema_name))

    filter { "system:windows", "configurations:release" }
        defines { "WIN32", "_WINDOWS", "NDEBUG", "TBB_USE_THREADING_TOOLS" }
        buildoptions { "/WX-" }
    filter { "system:windows", "configurations:debug" }
        defines { "WIN32", "_WINDOWS", "_DEBUG", "TBB_USE_DEBUG", "TBB_USE_ASSERT", "TBB_USE_THREADING_TOOLS" }
        buildoptions { "/WX-" }
    filter { "system:linux", "configurations:release" }
        defines { "LINUX", "NDEBUG", "TBB_USE_THREADING_TOOLS" }
        buildoptions { "-Wno-deprecated", "-Wno-deprecated-declarations", "-Wno-inconsistent-missing-override" }
    filter { "system:linux", "configurations:debug" }
        defines { "LINUX", "TBB_USE_DEBUG", "TBB_USE_ASSERT", "TBB_USE_THREADING_TOOLS" }
        buildoptions { "-Wno-deprecated", "-Wno-deprecated-declarations", "-Wno-inconsistent-missing-override" }
    filter {}

    links { "usd_usd", "usd_sdf", "usd_tf", "usd_arch", "usd_vt", "usd_usdGeom" }
    links { schema_name..library_suffix() }

    filter { "system:windows" }
        targetextension(".pyd")
    filter { "system:linux" }
        targetextension(".so")
    filter {}

    files { source.."/wrap*.cpp", source.."/module.cpp" }
end
