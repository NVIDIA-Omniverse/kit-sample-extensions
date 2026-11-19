-- Shared build scripts from repo_build package
repo_build = require("omni/repo/build")

-- Repo root
root = repo_build.get_abs_path(".")

-- Insert kit template premake configuration, it creates solution, finds extensions.. Look inside for more details.
kit = require("_repo/deps/repo_kit_tools/kit-template/premake5-kit")
kit.setup_all()

-- Use this consumer's Packman bootstrap for generators. Kernel49's copied
-- bootstrap requires the SDK publisher's KIT_PACKMAN_CAPTURE_WRAPPER variable.
if os.host() == "windows" then
    pythonScriptPath = 'call "'..root..'/tools/packman/python.bat"'
else
    pythonScriptPath = '"'..root..'/tools/packman/python.sh"'
end

-- The extension manager gives the last folder precedence for identical versions.
-- Test the local outputs even when precache also contains a published copy.
local test_script_dir = os.target() == "windows" and "%~dp0" or "$SCRIPT_DIR"
EXT_TEST_GLOBAL_EXTRA_ARGS = EXT_TEST_GLOBAL_EXTRA_ARGS or {}
table.insert(EXT_TEST_GLOBAL_EXTRA_ARGS, '--ext-folder "'..test_script_dir..'/exts" ')

-- Preserve the standalone OG build policy only while including its group.
local omnigraph = os.isfile("tools/premake/omnigraph.lua") and dofile("tools/premake/omnigraph.lua")
newoption { trigger = "omnigraph-only", description = "Build only the imported OmniGraph group for focused validation" }

-- Consolidated native helpers; retain KSE discovery below.
so_build = require("tools/premake/scene-optimizer-build")
dofile("tools/premake/particle-ogn.lua")
includedirs { "%{root}/include", "%{root}/source/pch" }
-- Source SDKs may omit dev/gsl; use the exact GSL fetched from all-deps.
includedirs { "%{root}/_build/target-deps/gsl/include" }
-- Kit main declares TBB separately from OpenUSD; retain the SDK's linkage policy
-- while resolving headers and import libraries from that exact package.
externalincludedirs { "%{root}/_build/target-deps/tbb/%{cfg.buildcfg}/include" }
libdirs { "%{root}/_build/target-deps/tbb/%{cfg.buildcfg}/lib" }

-- Extensions and apps not to build, from repo.toml [exclusions] extensions.
newoption { trigger = "excluded-extensions", value = "LIST", description = "Extensions and apps not to build" }
local excluded_extensions = {}
for name in (_OPTIONS["excluded-extensions"] or ""):gmatch("[%w_.]+") do excluded_extensions[name] = true end

-- Auto-include extensions with groups
local include_for_probe = dofile("tools/premake/kit111_triage.lua")
for _, group in ipairs(os.matchdirs(root.."/source/extensions/*")) do
    -- Each extension's premake5.lua is directly in its folder. Not "**": on Windows premake cannot
    -- encode the deep test-data paths ("unable to encode mask").
    for _, ext in ipairs(os.matchfiles(group.."/*/premake5.lua")) do
        if (not _OPTIONS["omnigraph-only"] or path.getname(group) == "omnigraph")
            and os.isfile(ext) and include_for_probe(ext) and not excluded_extensions[ext:sub(#group + 2):match("^[^/]+")] then
            if path.getname(group) == "omnigraph" then
                assert(omnigraph, "OmniGraph sources require their private build integration")
                omnigraph.include_extension(ext)
            else
                include (ext)
            end
        end
    end
end

-- Auto-add apps:
for _, app in ipairs(os.matchfiles(root.."/source/apps/*.kit")) do
    if os.isfile(app) then
        local app_name = path.getbasename(app)
        if app_name ~= "exts.deps.generated" and not excluded_extensions[app_name] then
            define_app (app_name)
        end
    end
end
