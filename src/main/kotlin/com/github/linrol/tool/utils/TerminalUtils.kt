package com.github.linrol.tool.utils

import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.ToolWindowManager
import org.jetbrains.plugins.terminal.ShellTerminalWidget
import org.jetbrains.plugins.terminal.TerminalToolWindowFactory
import org.jetbrains.plugins.terminal.TerminalView

class TerminalUtils(val project: Project) {

    companion object {
        const val TAB_NAME = "Build"
    }

    fun run(command: String) {
        val terminalView = TerminalView.getInstance(project)
        val window = ToolWindowManager.getInstance(project).getToolWindow(TerminalToolWindowFactory.TOOL_WINDOW_ID) ?: return
        val content = window.contentManager.findContent((TAB_NAME))

        val widget = if (content == null) {
            terminalView.createLocalShellWidget(project.basePath, TAB_NAME)
        } else {
            TerminalView.getWidgetByContent(content) as ShellTerminalWidget
        }
        widget.executeCommand(command)
    }
}