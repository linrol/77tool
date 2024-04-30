package com.github.linrol.tool.extend.vcs

import com.github.linrol.tool.extend.vcs.resolve.ResolveConflicts
import com.intellij.notification.NotificationType
import com.intellij.openapi.progress.ProgressManager
import com.intellij.openapi.project.Project
import com.intellij.openapi.vcs.FilePath
import com.intellij.openapi.vcs.VcsBundle
import com.intellij.openapi.vcs.VcsException
import com.intellij.openapi.vcs.VcsNotifier
import com.intellij.openapi.vcs.impl.AbstractVcsHelperImpl
import com.intellij.openapi.vcs.merge.MergeDialogCustomizer
import com.intellij.openapi.vcs.merge.MergeProvider
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.vcsUtil.VcsUtil
import git4idea.util.GitFileUtils

open class AbstractVcsHelperImplEx protected constructor(private val project: Project) : AbstractVcsHelperImpl(project) {
    private var callAfterMerged: Runnable? = null


    override fun showMergeDialog(files: List<VirtualFile>, provider: MergeProvider, mergeDialogCustomizer: MergeDialogCustomizer): List<VirtualFile> {
        val conflictFiles = try {
            autoResolve(files, provider)
        } catch (e: Throwable) {
            e.printStackTrace()
            VcsNotifier.getInstance(project).notify(VcsNotifier.STANDARD_NOTIFICATION.createNotification(e.toString(), NotificationType.ERROR))
            files
        }
        val resolvedFiles = if (conflictFiles.isEmpty()) emptyList() else super.showMergeDialog(conflictFiles, provider, mergeDialogCustomizer)
        changeVersionAfterMerged(conflictFiles, resolvedFiles)
        return resolvedFiles
    }

    private fun autoResolve(files: List<VirtualFile>, provider: MergeProvider) :List<VirtualFile> {
        if (files.isEmpty()) return emptyList()
        val toAddMap: MutableMap<VirtualFile, MutableList<FilePath>> = HashMap()
        val conflictFiles = files.filter { file ->
            val conflicts = ResolveConflicts.getInstance(project, provider, file)
            conflicts?.let {
                val isResolve = conflicts.resolveChangeAuto()
                takeIf { isResolve } ?.run {
                    val root = VcsUtil.getVcsRootFor(project, file)!!
                    val toAdds = toAddMap.getOrDefault(root, ArrayList())
                    toAdds.add(VcsUtil.getFilePath(file))
                    toAddMap[root] = toAdds
                }
                !isResolve
            } ?: true
        }
        ProgressManager.getInstance().runProcessWithProgressSynchronously({
            toAddMap.forEach { (root: VirtualFile, toAdd: List<FilePath>) ->
                try {
                    GitFileUtils.addPathsForce(project, root, toAdd)
                } catch (e: VcsException) {
                    throw RuntimeException(e)
                }
            } }, VcsBundle.message("multiple.file.merge.dialog.progress.title.resolving.conflicts"), true, project
        )
        return conflictFiles
    }

    private fun changeVersionAfterMerged(conflictFiles: List<VirtualFile>, resolvedFiles: List<VirtualFile>) {
        if (conflictFiles.size == resolvedFiles.size) {
            if (callAfterMerged != null) {
                callAfterMerged!!.run()
            }
        }
        clearCallAfterMerged()
    }

    fun setCallAfterMerged(callAfterMerged: Runnable?) {
        this.callAfterMerged = callAfterMerged
    }

    private fun clearCallAfterMerged() {
        callAfterMerged = null
    }
}

fun test () {
    val a = null;
    println(a==true)
}
