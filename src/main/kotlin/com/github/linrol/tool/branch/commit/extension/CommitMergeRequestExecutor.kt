package com.github.linrol.tool.branch.commit.extension

import com.intellij.openapi.project.Project
import com.intellij.openapi.vcs.changes.CommitContext
import com.intellij.openapi.vcs.changes.CommitSession
import com.intellij.openapi.vcs.changes.LocalCommitExecutor

class CommitMergeRequestExecutor(private val project: Project) : LocalCommitExecutor() {
    override fun getHelpId(): String {
        return "Commit And Merge Request"
    }

    override fun getActionText(): String {
        return "Commit And Merge Request"
    }

    override fun createCommitSession(commitContext: CommitContext): CommitSession {
        return CommitMergeRequestSession(project)
    }
}
