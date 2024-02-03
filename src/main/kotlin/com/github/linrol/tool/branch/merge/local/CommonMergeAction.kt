package com.github.linrol.tool.branch.merge.local

import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.project.DumbAwareAction

class CommonMergeAction : DumbAwareAction() {
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        CommonMergeDialog(project, e).showAndGet()
    }
}
