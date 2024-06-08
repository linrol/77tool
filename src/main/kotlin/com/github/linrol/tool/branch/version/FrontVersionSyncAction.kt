package com.github.linrol.tool.branch.version

import com.github.linrol.tool.base.AbstractDumbAction
import com.github.linrol.tool.model.GitCmd
import com.github.linrol.tool.utils.GitLabUtil
import com.intellij.openapi.actionSystem.AnActionEvent

class FrontVersionSyncAction: AbstractDumbAction() {

    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val repo = GitLabUtil.getRepository(project, "front-goserver")
        if (repo == null) {
            GitCmd.log(project, "请在本地打开front-goserver工程再进行操作")
            return
        }
        FrontVersionSyncDialog(project, e).showAndGet()
    }

    override fun update(e: AnActionEvent) {
        val project = e.project ?: return
        val repo = GitLabUtil.getRepository(project, "front-goserver")
        e.presentation.isEnabledAndVisible = repo != null
    }
}