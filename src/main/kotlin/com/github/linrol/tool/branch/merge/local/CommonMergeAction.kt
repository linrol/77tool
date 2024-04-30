package com.github.linrol.tool.branch.merge.local

import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.project.DumbAwareAction

class CommonMergeAction : DumbAwareAction() {
    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        CommonMergeDialog(project, e).showAndGet()
    }

//    override fun update(e: AnActionEvent) {
//        val project = e.project ?: return
//        val repo = GitLabUtil.getRepository(project, "build")
//        e.presentation.isEnabledAndVisible = repo != null
//    }
}
