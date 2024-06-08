package com.github.linrol.tool.branch.protect

import com.github.linrol.tool.base.AbstractDumbAction
import com.intellij.openapi.actionSystem.AnActionEvent

class ProtectBranchAction: AbstractDumbAction()  {
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        ProtectBranchDialog(project, e).showAndGet()
    }
}