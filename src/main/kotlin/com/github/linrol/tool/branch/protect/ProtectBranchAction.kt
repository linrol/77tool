package com.github.linrol.tool.branch.protect

import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.project.DumbAwareAction

class ProtectBranchAction: DumbAwareAction()  {
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        ProtectBranchDialog(project, e).showAndGet()
    }
}