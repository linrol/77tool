package com.github.linrol.tool.utils

import com.intellij.concurrency.JobScheduler
import com.intellij.openapi.progress.ProgressIndicator
import com.intellij.openapi.progress.ProgressManager
import com.intellij.openapi.progress.Task
import com.intellij.openapi.project.Project
import com.intellij.openapi.roots.ProjectRootManager
import com.intellij.openapi.ui.Messages
import com.intellij.openapi.util.Ref
import com.intellij.openapi.util.ThrowableComputable
import com.intellij.openapi.vcs.changes.Change
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.util.ThrowableConvertor
import com.intellij.util.containers.Convertor
import git4idea.GitUtil
import git4idea.commands.Git
import git4idea.commands.GitCommand
import git4idea.commands.GitLineHandler
import git4idea.config.GitExecutableManager
import git4idea.fetch.GitFetchResult
import git4idea.fetch.GitFetchSupport
import git4idea.repo.GitRepository
import com.github.linrol.tool.model.RepositoryChange
import java.io.IOException
import java.net.URI
import java.util.*
import java.util.concurrent.ScheduledFuture
import java.util.concurrent.TimeUnit
import java.util.regex.Pattern

/**
 * GitLab specific untils
 *
 * @author ppolivka
 * @since 28.10.2015
 */
object GitLabUtil {
    fun getGitRepository(project: Project, file: VirtualFile): GitRepository? {
        val manager = GitUtil.getRepositoryManager(project)
        val repositories = manager.repositories
        if (repositories.isEmpty()) {
            return null
        }
        if (repositories.size == 1) {
            return repositories[0]
        }
        val repository = manager.getRepositoryForFile(file)
        if (repository != null) {
            return repository
        }
        ProjectRootManager.getInstance(project).fileIndex.getContentRootForFile(file)?.let {
            manager.getRepositoryForFile(it)
        }
        return null
    }

    fun groupByRepository(project: Project, files: List<Change>): List<RepositoryChange> {
        val manager = GitUtil.getRepositoryManager(project)
        val repoFilesMap: MutableMap<GitRepository, MutableList<Change>> = HashMap()
        files.forEach { change ->
            change.virtualFile?.let { virtualFile ->
                manager.getRepositoryForFile(virtualFile)?.let { repository ->
                    repoFilesMap.compute(repository) { _, v ->
                        v?.apply { add(change) } ?: mutableListOf(change)
                    }
                }
            }
        }
        return repoFilesMap.entries.map { RepositoryChange(it.key, it.value) }
    }

    fun getRepositories(project: Project): List<GitRepository> {
        val manager = GitUtil.getRepositoryManager(project)
        return manager.repositories
    }

    fun getCommonRepositories(project: Project, vararg branch: String): List<GitRepository> {
        return getRepositories(project).filter { f -> f.branches.remoteBranches.map { it.nameForRemoteOperations }.toSet().containsAll(branch.toSet()) }
    }

    fun getRepositories(project: Project, files: List<Change>): List<GitRepository> {
        val manager = GitUtil.getRepositoryManager(project)
        return files.filter { it.virtualFile != null }.map { manager.getRepositoryForFile(it.virtualFile!!) }.filterNotNull().distinct()
    }

    fun isGitLabUrl(testUrl: String, url: String): Boolean {
        try {
            val fromSettings = URI(testUrl)
            val fromSettingsHost = fromSettings.host

            val patternString = "(\\w+://)(.+@)*([\\w\\d\\.\\-]+)(:[\\d]+){0,1}/*(.*)|(.+@)*([\\w\\d\\.\\-]+):(.*)"
            val pattern = Pattern.compile(patternString)
            val matcher = pattern.matcher(url)
            var fromUrlHost = ""
            if (matcher.matches()) {
                val group3 = matcher.group(3)
                val group7 = matcher.group(7)
                if (group3.isNotBlank()) {
                    fromUrlHost = group3
                } else if (group7.isNotBlank()) {
                    fromUrlHost = group7
                }
            }
            return fromSettingsHost != null && removeNotAlpha(fromSettingsHost) == removeNotAlpha(fromUrlHost)
        } catch (e: Exception) {
            return false
        }
    }

    private fun removeNotAlpha(input: String): String {
        return input.replace("[^a-zA-Z0-9]".toRegex(), "").lowercase(Locale.getDefault())
    }

    fun addGitLabRemote(project: Project,
                        repository: GitRepository,
                        remote: String,
                        url: String): Boolean {
        val handler = GitLineHandler(project, repository.root, GitCommand.REMOTE)
        handler.setSilent(true)
        handler.addParameters("add", remote, url)
        val result = Git.getInstance().runCommand(handler)
        if (result.exitCode != 0) {
            // showErrorDialog(project, "New remote origin cannot be added to this project.", "Cannot Add New Remote");
            return false
        }
        // catch newly added remote
        repository.update()
        return true
    }

    /**
     * use getSavedPathToGit() to get the path from settings if there's any or use GitExecutableManager.getPathToGit()/GitExecutableManager.getPathToGit(Project) to get git executable with auto-detection
     *
     * @param project
     * @return
     */
    fun testGitExecutable(project: Project): Boolean {
        val manager = GitExecutableManager.getInstance()
        // val executable = manager.getPathToGit(project)
        // val version: GitVersion
        return try {
            manager.getVersion(project).isSupported
        } catch (e: Exception) {
            // showErrorDialog(project, "Cannot find git executable.", "Cannot Find Git");
            false
        }
    }

    @Throws(IOException::class)
    fun <T> computeValueInModal(project: Project,
                                caption: String,
                                task: ThrowableConvertor<ProgressIndicator?, T, IOException?>): T {
        val dataRef = Ref<T>()
        val exceptionRef = Ref<Throwable>()
        ProgressManager.getInstance().run(object : Task.Modal(project, caption, true) {
            override fun run(indicator: ProgressIndicator) {
                try {
                    dataRef.set(task.convert(indicator))
                } catch (e: Throwable) {
                    exceptionRef.set(e)
                }
            }
        })
        if (!exceptionRef.isNull) {
            val e = exceptionRef.get()
            if (e is IOException) {
                throw (e)
            }
            if (e is RuntimeException) {
                throw (e)
            }
            if (e is Error) {
                throw (e)
            }
            throw RuntimeException(e)
        }
        return dataRef.get()
    }

    fun <T> computeValueInModal(project: Project,
                                caption: String,
                                task: Convertor<ProgressIndicator?, T>): T {
        return computeValueInModal(project, caption, true, task)
    }

    private fun <T> computeValueInModal(project: Project,
                                        caption: String,
                                        canBeCancelled: Boolean,
                                        task: Convertor<ProgressIndicator?, T>): T {
        val dataRef = Ref<T>()
        val exceptionRef = Ref<Throwable>()
        ProgressManager.getInstance().run(object : Task.Modal(project, caption, canBeCancelled) {
            override fun run(indicator: ProgressIndicator) {
                try {
                    dataRef.set(task.convert(indicator))
                } catch (e: Throwable) {
                    exceptionRef.set(e)
                }
            }
        })
        if (!exceptionRef.isNull) {
            val e = exceptionRef.get()
            if (e is RuntimeException) {
                throw (e)
            }
            if (e is Error) {
                throw (e)
            }
            throw RuntimeException(e)
        }
        return dataRef.get()
    }

    @Throws(IOException::class)
    fun <T> runInterruptable(indicator: ProgressIndicator,
                             task: ThrowableComputable<T, IOException?>): T {
        var future: ScheduledFuture<*>? = null
        try {
            val thread = Thread.currentThread()
            future = addCancellationListener(indicator, thread)

            return task.compute()
        } finally {
            future?.cancel(true)
            Thread.interrupted()
        }
    }

    private fun addCancellationListener(indicator: ProgressIndicator,
                                        thread: Thread): ScheduledFuture<*> {
        return addCancellationListener {
            if (indicator.isCanceled) {
                thread.interrupt()
            }
        }
    }

    private fun addCancellationListener(run: Runnable): ScheduledFuture<*> {
        return JobScheduler.getScheduler().scheduleWithFixedDelay(run, 1000, 300, TimeUnit.MILLISECONDS)
    }

    @Messages.YesNoResult
    fun showYesNoDialog(project: Project?, title: String, message: String): Boolean {
        return Messages.YES == Messages.showYesNoDialog(project, message, title, Messages.getQuestionIcon())
    }

    @JvmOverloads
    fun fetch(project: Project, repositories: Collection<GitRepository?>? = GitUtil.getRepositories(project)): GitFetchResult {
        return GitFetchSupport.fetchSupport(project).fetchAllRemotes(repositories!!)
    }
}