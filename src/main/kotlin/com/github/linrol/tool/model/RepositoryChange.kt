package com.github.linrol.tool.model

import com.intellij.openapi.vcs.changes.Change
import git4idea.repo.GitRepository

class RepositoryChange(var repository: GitRepository, var changeFileList: List<Change>) {
    var commitMessage: String? = null
}
