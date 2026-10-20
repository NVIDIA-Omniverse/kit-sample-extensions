-- Temporary compatibility probe, not an acceptance or packaging profile.
-- Every entry must have evidence and re-enable criteria in docs/kit111-issues.md.
newoption {
    trigger = "kit111-triage",
    description = "Windows Kit 111 probe: omit catalogued blocked extension builds",
}

local excluded = {
    ["omni.kit.window.material_graph"] = "K111-UI-001",
    ["omni.scene.optimizer.core"] = "K111-USD-001",
    ["omni.usd.schema.metrics.assembler"] = "K111-USD-002",
}

-- Not supported on Kit 111 EA1 (Damien, 2 Oct 2026). Always applied, on every platform: these extensions are not built,
-- so they get no staging and no tests-<ext> wrapper, and repo test does not run them. Their sources stay in the tree.
-- Re-enable an extension by deleting its line here (and from [repo_publish_exts] exts.exclude in repo.toml).
-- Reasons and re-enable criteria: docs/kit111-issues.md, "Kit 111 EA1 scope".
local not_supported_ea1 = {
    ["omni.metropolis.agent_registry"] = "K111-EA1-003: needs the Isaac Sim stack (omni.isaac.ml_archive), not on Kit 111",
}

local enabled = _OPTIONS["kit111-triage"] ~= nil
if enabled and os.target() ~= "windows" then
    error("--kit111-triage is scoped to Windows; other platforms have not been triaged")
end

return function(premake_file)
    local name = path.getname(path.getdirectory(premake_file))
    local ea1 = not_supported_ea1[name]
    if ea1 then
        print("KIT111 EA1: not supported / build omitted: "..name.." ("..ea1..")")
        return false
    end
    local issue = enabled and excluded[name]
    if issue then
        print("KIT111 TRIAGE: BLOCKED / build omitted: "..name.." ("..issue..")")
        return false
    end
    return true
end
