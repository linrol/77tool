package com.github.linrol.tool.branch.delete

import com.github.linrol.tool.base.AbstractDumbAction
import com.intellij.openapi.actionSystem.AnActionEvent

class DeleteBranchAction : AbstractDumbAction()  {
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        DeleteBranchDialog(project, e).showAndGet()
    }
}