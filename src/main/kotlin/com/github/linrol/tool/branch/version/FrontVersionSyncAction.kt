package com.github.linrol.tool.branch.version

import com.github.linrol.tool.utils.GitLabUtil
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.project.DumbAwareAction

class FrontVersionSyncAction: DumbAwareAction()  {

    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        FrontVersionSyncDialog(project, e).showAndGet()
    }

    override fun update(e: AnActionEvent) {
        val project = e.project ?: return
        val repo = GitLabUtil.getRepository(project, "front-goserver")
        e.presentation.isEnabledAndVisible = repo != null
    }
}