-- Shared build scripts from repo_build package
repo_build = require("omni/repo/build")

-- Repo root
root = repo_build.get_abs_path(".")

-- Insert kit template premake configuration, it creates solution, finds extensions.. Look inside for more details.
kit = require("_repo/deps/repo_kit_tools/kit-template/premake5-kit")
kit.setup_all()

-- Consolidated native helpers; retain KSE discovery below.
so_build = require("tools/premake/scene-optimizer-build")
dofile("tools/premake/particle-ogn.lua")
includedirs { "%{root}/include", "%{root}/source/pch" }
-- Source SDKs may omit dev/gsl; use the exact GSL fetched from all-deps.
includedirs { "%{root}/_build/target-deps/gsl/include" }

-- Extensions not to build, from repo.toml [exclusions] extensions.
newoption { trigger = "excluded-extensions", value = "LIST", description = "Extensions not to build" }
local excluded_extensions = {}
for name in (_OPTIONS["excluded-extensions"] or ""):gmatch("[%w_.]+") do excluded_extensions[name] = true end

-- Auto-include extensions with groups
local include_for_probe = dofile("tools/premake/kit111_triage.lua")
for _, group in ipairs(os.matchdirs(root.."/source/extensions/*")) do
    -- Each extension's premake5.lua is directly in its folder. Not "**": on Windows premake cannot
    -- encode the deep test-data paths ("unable to encode mask").
    for _, ext in ipairs(os.matchfiles(group.."/*/premake5.lua")) do
        if os.isfile(ext) and include_for_probe(ext) and not excluded_extensions[ext:sub(#group + 2):match("^[^/]+")] then
            include (ext)
        end
    end
end
