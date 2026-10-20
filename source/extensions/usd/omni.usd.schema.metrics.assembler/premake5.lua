local ext = get_current_extension_info()
dofile(_SCRIPT_DIR.."/schema_helpers.lua")

project_ext (ext)

-- link directories
repo_build.prebuild_link
{
    { "config", ext.target_dir.."/config" },
    { "data", ext.target_dir.."/data" },
	{ "docs", ext.target_dir.."/docs"  },
    { "python/tests", ext.target_dir.."/usd/schema/metricsassembler/tests"  },
}

-- copy init file
repo_build.prebuild_copy
{
    { "python/__init__.py", ext.target_dir.."/usd/schema/metricsassembler" },
    { "source/__init__.py", ext.target_dir.."/omni/MetricsAssembler" },
}

project_ext_plugin(ext, "omni.usd.schema.metrics.assembler")

    cppdialect "C++17"

    project_metrics_assembler_schema("metricsAssembler", "source", ext.target_dir)

    filter { "system:linux" }
        removeflags { "UndefinedIdentifiers" }
        buildoptions { "-pthread" }
        links { "dl", "pthread" }
    filter {}

project_ext_plugin(ext, "omni.usd.schema.metrics.assembler.python")
    dependson { "omni.usd.schema.metrics.assembler" }

    cppdialect "C++17"

    project_metrics_assembler_schema_python("metricsAssembler", "source")

    filter { "system:linux" }
        removeflags { "UndefinedIdentifiers" }
        buildoptions { "-pthread" }
        links { "dl", "pthread" }
    filter {}

    targetdir (ext.target_dir.."/omni/MetricsAssembler")

    libdirs {
        ext.bin_dir
    }
