package com.github.linrol.tool.build

import com.github.linrol.tool.base.BaseBetaAction
import com.github.linrol.tool.utils.TerminalUtils
import com.intellij.openapi.actionSystem.AnActionEvent
import org.jetbrains.idea.maven.project.MavenProjectsManager

class MavenBuildAction: BaseBetaAction() {

    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val mavenProjectsManager = MavenProjectsManager.getInstance(project)
        val projects = mavenProjectsManager.projects.joinToString(",") { m -> m.directory.substringAfterLast("/") }
        TerminalUtils(project).run("./build-all.sh -p $projects")
    }

}