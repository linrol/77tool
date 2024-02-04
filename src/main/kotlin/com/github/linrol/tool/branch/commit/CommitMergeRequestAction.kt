package com.github.linrol.tool.branch.commit

import com.github.linrol.tool.branch.commit.extension.CommitMergeRequestExecutor
import com.intellij.openapi.project.Project
import com.intellij.openapi.vcs.changes.CommitExecutor
import com.intellij.openapi.vcs.changes.actions.AbstractCommitChangesAction

class CommitMergeRequestAction : AbstractCommitChangesAction() {
    override fun getExecutor(project: Project): CommitExecutor {
        return CommitMergeRequestExecutor(project)
    }
}
