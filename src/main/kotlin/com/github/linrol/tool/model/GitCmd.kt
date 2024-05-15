package com.github.linrol.tool.model

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.diagnostic.logger
import com.intellij.openapi.progress.ProcessCanceledException
import com.intellij.openapi.progress.ProgressIndicator
import com.intellij.openapi.progress.ProgressManager
import com.intellij.openapi.progress.Task
import com.intellij.openapi.project.Project
import com.intellij.openapi.vcs.VcsException
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.openapi.wm.ToolWindowManager
import git4idea.commands.Git
import git4idea.commands.GitCommand
import git4idea.commands.GitCommandResult
import git4idea.commands.GitLineHandler
import git4idea.repo.GitRepository
import org.apache.commons.lang3.exception.ExceptionUtils
import com.github.linrol.tool.tollwindow.ToolWindowConsole
import com.intellij.openapi.project.ProjectManager


class GitCmd(private var project: Project, private var repository: GitRepository) {
    var root: VirtualFile = repository.root

    private lateinit var handler: GitLineHandler

    private lateinit var command: GitCommand

    fun addParameters(vararg parameters: String): GitCmd {
        parameters.forEach { handler.addParameters(it) }
        return this
    }

    fun build(command: GitCommand, vararg parameters: String): GitCmd {
        this.command = command
        return build(command, parameters.toList())
    }

    private fun build(command: GitCommand, parameters: List<String>): GitCmd {
        this.command = command
        val handler = GitLineHandler(project, this.root, command)
        parameters.forEach { handler.addParameters(it) }
        this.handler = handler
        return this
    }

    fun config(silent: Boolean, stdoutSuppressed: Boolean, vararg urls: String): GitCmd {
        handler.urls = urls.toList()
        handler.setSilent(silent)
        handler.setStdoutSuppressed(stdoutSuppressed)
        return this
    }

    fun run(): GitCommandResult {
        try {
            val runString = handler.printableCommandLine()
            logger.debug(runString)
            val title = "Git ${this.command} running"
            val ret = ProgressManager.getInstance().run(object : Task.WithResult<GitCommandResult, VcsException>(project, title, true) {
                override fun compute(indicator: ProgressIndicator): GitCommandResult {
                    return Git.getInstance().runCommand(handler)
                }
            })
            // GitCommandResult ret = Git.getInstance().runCommand(this.handler);
            if (!ret.success()) {
                val errorString = ret.errorOutputAsJoinedString
                logger.info("Git run command:${runString} failed case by:${errorString}")
                throw RuntimeException(errorString)
            }
            return ret
        } catch (e: VcsException) {
            throw RuntimeException(ExceptionUtils.getRootCauseMessage(e))
        } catch (e: ProcessCanceledException) {
            throw RuntimeException(ExceptionUtils.getRootCauseMessage(e))
        }
    }

    fun log(msg: String) {
        log(project, msg)
    }

    val remoteUrl: String get() = repository.remotes.flatMap { it.pushUrls }.first { it.isNotBlank() }

    val currentBranchName: String get() = repository.currentBranchName.toString()

    companion object {
        private val logger = logger<GitCmd>()

        fun clear() {
            ToolWindowConsole.clear()
        }

        @JvmStatic
        fun log(p: Project?, msg: String) {
            try {
                val project = p ?: ProjectManager.getInstance().defaultProject
                val toolWindow = ToolWindowManager.getInstance(project).getToolWindow("77tool") ?: return
                ApplicationManager.getApplication().invokeLater {
                    toolWindow.activate {
                        ToolWindowConsole.show()
                        ToolWindowConsole.log(project, msg)
                    }
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }
}
