# Deprecated extensions retained for review

The workbook-listed source extensions have been removed except for the required
graph schema and the retained graph editor example with its Neo dependency. The following seven payloads remain in this review group.

| Extension | Reason retained |
| --- | --- |
| [omni.anim.graph.schema](omni.anim.graph.schema) | Required by omni.anim.asset; user explicitly retains the extension until consumer migration. |
| [omni.kit.graph.editor.example](omni.kit.graph.editor.example) | User retains as the Default/Modern delegate test dependency. |
| [omni.kit.graph.delegate.neo](omni.kit.graph.delegate.neo) | Required by the retained example. |
| [omni.anim.camera_tool](omni.anim.camera_tool) | Not listed in the workbook Tier 1/Tier 2 sheets; retained for review. |
| [omni.entity.spawn.bundle](omni.entity.spawn.bundle) | Not listed in the workbook Tier 1/Tier 2 sheets; retained for review. |
| [omni.entity.spawn.core](omni.entity.spawn.core) | Not listed in the workbook Tier 1/Tier 2 sheets; retained for review. |
| [omni.entity.spawn.ui](omni.entity.spawn.ui) | Not listed in the workbook Tier 1/Tier 2 sheets; retained for review. |

`omni.anim.timeline` is explicitly kept and has returned to
[the animation group](../animation/omni.anim.timeline). Its upstream deprecation
warning remains metadata; this change retains its payload and current build/test policy.

The removed scene UI documentation extension included its DIN Pro fonts.
