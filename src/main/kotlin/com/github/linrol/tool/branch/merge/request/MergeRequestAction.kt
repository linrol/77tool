package com.github.linrol.tool.branch.merge.request

import com.intellij.dvcs.push.PushInfo
import com.intellij.dvcs.push.ui.VcsPushDialog
import com.intellij.dvcs.push.ui.VcsPushUi
import com.intellij.openapi.diagnostic.logger
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.DialogWrapper
import git4idea.GitUtil
import git4idea.repo.GitRepository
import org.apache.commons.lang3.exception.ExceptionUtils
import com.github.linrol.tool.branch.command.GitCommand
import com.github.linrol.tool.model.GitCmd
import com.intellij.dvcs.push.ui.PushActionBase
import org.jetbrains.annotations.Nls

class MergeRequestAction : PushActionBase("Merge Request") {
    override fun isEnabled(dialog: VcsPushUi): Boolean {
        return true
    }

    override fun getDescription(dialog: VcsPushUi, enabled: Boolean): @Nls String {
        return "Create Merge Request"
    }

    override fun actionPerformed(project: Project, dialog: VcsPushUi) {
        try {
            GitCmd.clear()
            val repoRoots = dialog.selectedPushSpecs.values.flatMap { it.map { obj: PushInfo -> obj.repository } }.map {
                // 实现逻辑
                val cmd = GitCmd(project, it as GitRepository)
                GitCommand.push(cmd)
                it.root
            }
            GitUtil.refreshVfsInRoots(repoRoots)
            close(dialog, DialogWrapper.OK_EXIT_CODE)
        } catch (e: RuntimeException) {
            e.printStackTrace()
            GitCmd.log(project, ExceptionUtils.getRootCauseMessage(e))
        } catch (e: Throwable) {
            close(dialog, DialogWrapper.OK_EXIT_CODE)
            e.printStackTrace()
            GitCmd.log(project, ExceptionUtils.getRootCauseMessage(e))
            logger.error("GitMergeRequestAction execute failed", e)
        }
    }

    private fun close(dialog: VcsPushUi, exitCode: Int) {
        if (dialog is VcsPushDialog) {
            // 关闭push窗口
            dialog.close(exitCode)
        }
    }

    companion object {
        private val logger = logger<MergeRequestAction>()
    }
}
