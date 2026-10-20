-- Generate resource-only USD plugins using the USD shipped with Kit.
local schema = {}

function schema.project(ext, name, source_dir)
    local schema_file = source_dir.."/"..name.."/schema.usda"
    local generator = root.."/tools/schema/build_schema.py"
    local resources = ext.target_dir.."/"..name.."/resources"
    local repo_command
    if os.target() == "windows" then
        repo_command = '"'..root..'/repo.bat"'
    else
        repo_command = 'bash "'..root..'/repo.sh"'
    end

    project(name)
    kind "Utility"
    language "C++"
    targetdir(resources)
    files { schema_file }

    filter "files:**.usda"
        buildmessage "Generating codeless USD schema %{file.name}"
        buildcommands {
            repo_command..' build_schema -c %{cfg.buildcfg} -i "%{file.abspath}" -o "'..resources..'"'
        }
        buildinputs { generator }
        -- One output: with two, gmake2 writes a rule with two independent targets, and a parallel make
        -- ran the generator twice at once (one run read the other's half-written plugInfo.json).
        buildoutputs { resources.."/plugInfo.json" }
    filter {}
end

return schema
