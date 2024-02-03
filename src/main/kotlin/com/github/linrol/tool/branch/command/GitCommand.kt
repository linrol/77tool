package com.github.linrol.tool.branch.command

import com.intellij.openapi.project.Project
import git4idea.commands.GitCommandResult
import org.apache.commons.collections.CollectionUtils
import com.github.linrol.tool.model.GitCmd
import com.github.linrol.tool.model.RepositoryChange
import com.github.linrol.tool.utils.TimeUtils

object GitCommand {
    private fun createMergeRequest(project: Project, changes: RepositoryChange): GitCommandResult? {
        val repository = changes.repository

        val cmd = GitCmd(project, repository)
        val remotes = repository.remotes
        if (CollectionUtils.isEmpty(remotes)) {
            throw RuntimeException("远程仓库未找到不存在，请检查你的git remote配置")
        }

        val url = cmd.remoteUrl
        if (url.isBlank()) {
            throw RuntimeException("远程仓库未找到不存在，请检查你的git remote配置")
        }
        repository.currentBranch ?: throw RuntimeException("本地仓库当前分支获取失败")

        commit(changes)
        return push(cmd)
    }

    private fun commit(changes: RepositoryChange) {
        val title = changes.commitMessage
        if (title.isNullOrBlank()) {
            return
        }
        val checkinEnvironment = changes.repository.vcs.checkinEnvironment ?: throw RuntimeException("getCheckinEnvironment null")
        checkinEnvironment.commit(changes.changeFileList, title)
    }

    fun push(cmd: GitCmd): GitCommandResult? {
        val branch = cmd.currentBranchName
        val url = cmd.remoteUrl
        if (!needPush(cmd, branch)) {
            return null
        }
        val tmpBranch = "77tool_mr_${TimeUtils.getCurrentTime("yyyyMMddHHmmss")}"
        val ret = cmd.build(git4idea.commands.GitCommand.PUSH).config(false, false, url)
                .addParameters("origin")
                .addParameters("head:${tmpBranch}")
                .addParameters("-o", "merge_request.create")
                .addParameters("-o", "merge_request.target=${branch}")
                .addParameters("-o", "merge_request.remove_source_branch")
                .addParameters("-f").run()
        cmd.log(ret.errorOutputAsJoinedString)
        return ret
    }

    private fun needPush(cmd: GitCmd, branch: String): Boolean {
        val logRet = cmd.build(git4idea.commands.GitCommand.LOG, branch, "^origin/${branch}").run().outputAsJoinedString
        val noNeed = logRet.isBlank()
        if (noNeed) {
            val rootName = cmd.root.name
            cmd.log(String.format("工程【%s】分支【%s】没有需要push的代码!!!", rootName, branch))
        }
        return !noNeed
    }
}