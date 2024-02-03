package com.github.linrol.tool.branch.commit.extension

import com.intellij.openapi.diagnostic.logger
import com.intellij.openapi.project.Project
import com.intellij.openapi.util.NlsSafe
import com.intellij.openapi.vcs.changes.Change
import com.intellij.openapi.vcs.changes.CommitSession
import git4idea.GitUtil
import git4idea.GitVcs
import org.apache.commons.lang3.exception.ExceptionUtils
import com.github.linrol.tool.branch.command.GitCommand.push
import com.github.linrol.tool.model.GitCmd
import com.github.linrol.tool.utils.GitLabUtil

class CommitMergeRequestSession(private val project: Project) : CommitSession {
    companion object {
        private val logger = logger<CommitMergeRequestSession>()
    }

    override fun canExecute(changes: Collection<Change>, commitMessage: String): Boolean {
        return changes.isNotEmpty()
    }

    override fun execute(changes: Collection<Change>, commitMessage: @NlsSafe String?) {
        try {
            GitCmd.clear()
            val changeList = changes.toList()
            val checkinEnvironment = GitVcs.getInstance(project).checkinEnvironment ?: throw RuntimeException("getCheckinEnvironment null")
            if (commitMessage.isNullOrBlank()) {
                throw RuntimeException("请输入提交消息")
            }
            checkinEnvironment.commit(changeList, commitMessage)
            val repoRoots = GitLabUtil.getRepositories(project, changeList).map {
                push(GitCmd(project, it))
                it.root
            }
            GitUtil.refreshVfsInRoots(repoRoots)
        } catch (e: RuntimeException) {
            e.printStackTrace()
            GitCmd.log(project, ExceptionUtils.getRootCauseMessage(e))
        } catch (e: Throwable) {
            e.printStackTrace()
            GitCmd.log(project, ExceptionUtils.getRootCauseMessage(e))
            logger.error("GitCommitMrSession execute failed", e)
        }
    }

}
