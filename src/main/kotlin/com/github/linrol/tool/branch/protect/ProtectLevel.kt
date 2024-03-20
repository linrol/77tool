package com.github.linrol.tool.branch.protect

enum class ProtectLevel(val level: String, val desc: String)  {
    Noone("No one", "不允许任何人合并和推送"),
    Hotfix("MaintainerMerge", "管理员可以合并代码"),
    Release("MaintainerMergeAndPush", "管理员可以合并或推送"),
    Dev("DeveloperMergeAndPush", "开发人与可以合并或推送"),
    Delete("DeleteProtect", "删除分支保护")
}