local _ = dofileopt("premake5_helpers.lua")

-- Build file for the Omnigraph image composition extension.
local ext = get_current_extension_info()

-- Helper variable containing standard configuration information for the OGN files in this project
local ogn = get_ogn_project_information(ext, "omni/genproc/core", "TypeConfigurationLinAlg.json")

-- Put this project into the simulation IDE group
ext.group = "omnigraph"

project_ext( ext )

-- add_cuda_dependencies copied from kit/premake5.lua
function add_cuda_dependencies()
    -- First the build rules for CUDA files
    filter { "files:**.cu", "system:windows", "configurations:debug" }
        make_nvcc_command(nvccPath, nvccHostCompilerVS, "/MDd", "-g -G")
    filter { "files:**.cu", "system:windows", "configurations:release" }
        make_nvcc_command(nvccPath, nvccHostCompilerVS, "/MD", "")
    filter { "files:**.cu", "system:linux", "configurations:debug" }
        make_nvcc_command(nvccPath, nvccHostCompilerVS, "-fPIC -g", "-g")
    filter { "files:**.cu", "system:linux", "configurations:release" }
        make_nvcc_command(nvccPath, nvccHostCompilerVS, "-fPIC", "")
    filter {}

    -- Add in the library directories
    filter { "system:linux"}
        libdirs { target_deps.."/cuda/lib64" }
        links { "cudart_static", "cublas_static", "cublasLt_static", "cusparse_static", "culibos" }
    filter { "system:windows" }
        libdirs { target_deps.."/cuda/lib/x64" }
        links { "cudart_static", "cublas", "cublasLt", "cusparse" }
    filter {}

    -- CUDA-specific include directory
    filter { "system:linux" }
        includedirs { target_deps.."/cuda/include" }
    filter { "system:windows" }
        includedirs { target_deps.."/cuda/include" }
    filter {}

    -- Depends on the CUDA compute plugin
    dependson {"omni.gpucompute-*.plugin"}
end


-- ----------------------------------------------------------------------
-- The main plugin is what implements the compute graph functionality
project_ext_plugin( ext, ogn.plugin_project )
    -- Preserve particle-system root warning policy; cleanup is tracked separately.
    removeflags { "FatalCompileWarnings" }

    -- Sort out the files into rough correspondence with the file tree
    add_files("impl", ogn.plugin_path)
    -- add_files("impl/aabtree", ogn.plugin_path.."/aabtree")
    add_files("ogn", ogn.nodes_path)
    add_files("docs", ogn.docs_path)
    add_files("config", "config")

    -- Add the standard dependencies all OGN projects have
    extra_usd_libs = {
        "usdGeom",
        "usdUtils",
        "work"
    }
    add_ogn_dependencies_override(ogn, extra_usd_libs)

    filter { "system:windows" }
        disablewarnings {
            "4005", -- (warning C4005: NOMINMAX macro redefinition)
        }
    filter {}

    -- carbonfitePlugin { ifaces = "include/omni/kit", impl = ogn.plugin_path }

    -- Extension dependencies
    dependson { "prebuild", "reflection.gen", "carb", "omni.gpucompute-*.plugin" }

    -- omni.physx and physx deps
    physx_target_deps = root.."/_build/target-deps"
    local physx = dofile(root.."/tools/premake/physx-build.lua")
    physx.add_dependencies(physx_target_deps.."/physx", "checked")

    -- Extra include dependencies
    includedirs {
        target_deps.."/rtx_plugins/include",
        -- target_deps.."/newton/%{config}/include", -- XXX see note in target-deps.packman.xml
    }

    -- Linux-specific compile information
    filter { "system:linux" }
        exceptionhandling "On"
        removeflags { "FatalCompileWarnings", "UndefinedIdentifiers" }
        includedirs {
            target_deps.."/rtx_plugins/include",

        }
        buildoptions { "-pthread" }
        links { "dl", "pthread", "rt" }
        libdirs {
            target_deps.."/cuda/lib64",
            target_deps.."/slang/lib",
        }
    filter { "system:windows" }
        libdirs {
            target_deps.."/slang/lib"
        }
        repo_build.copy_to_targetdir(root.."/_build/target-deps/cuda/bin/cublas*")
        repo_build.copy_to_targetdir(root.."/_build/target-deps/cuda/bin/cusparse*")
        -- cusparse64_12.dll depends on nvJitLink_120_0.dll (not shipped in kit's cuda package on some branches),
        -- so we pull it from a dedicated packman dep (see deps/target-deps.packman.xml).
        repo_build.copy_to_targetdir(root.."/_build/target-deps/cuda_nvjitlink/bin/nvJitLink*")
    filter {}

    libdirs {
        "%{root}/_build/%{platform_target}/%{config}/kit/plugins",
        extsbuild_dir.."/omni.usd.core/bin",
        --target_deps.."/newton/%{config}/lib", -- XXX see note in target-deps.packman.xml
    }
    links {
        -- "newton", -- XXX see note in target-deps.packman.xml
    }

    -- Specifies the external libraries required by the nodes
    links {"carb", "slang", "omni.usd"}

    -- Link the data and docs directories for easy discovery
    repo_build.prebuild_link {
        { "data", ext.target_dir.."/data" },
        { "docs", ext.target_dir.."/docs" },
    }

    -- CUDA file processing
    add_cuda_dependencies()


-- ----------------------------------------------------------------------
-- Break this out as a separate project ensures the .ogn files are processed before their results are needed
project_ext_ogn( ext, ogn )


-- ----------------------------------------------------------------------
-- Python support and scripts for the Omnigraph image composition files
project_ext_bindings {
    ext = ext,
    project_name = ogn.python_project,
    module = ogn.bindings_module,
    src = ogn.bindings_path,
    target_subdir = ogn.bindings_target_path
}

    -- All Python script and documentation files are part of this project
    add_files("bindings", "bindings/*.*")
    add_files("python", "*.py")
    add_files("python", ogn.python_path.."**.py")
    add_files("python/tests", "python/tests")

    -- Add the standard dependencies all OGN projects have
    add_ogn_dependencies_override(ogn)

    -- Copy the init script directly into the build tree to avoid reload conflicts.
    repo_build.prebuild_copy {
        { "python/__init__.py", ogn.python_target_path },
    }
    -- Linking directories allows them to hot reload when files are modified in the source tree
    repo_build.prebuild_link {
        { "python/scripts", ogn.python_target_path.."/scripts" },
        { "python/tests", ogn.python_tests_target_path },
    }
