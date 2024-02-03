package com.github.linrol.tool.branch.commit

import com.intellij.openapi.project.Project
import com.intellij.openapi.vcs.changes.CommitExecutor
import com.intellij.openapi.vcs.changes.actions.AbstractCommitChangesAction
import com.github.linrol.tool.branch.commit.extension.CommitMergeRequestExecutor.Companion.getInstance

class CommitMergeRequestAction : AbstractCommitChangesAction() {
    override fun getExecutor(project: Project): CommitExecutor {
        return getInstance()
    }
}
