package com.github.linrol.tool.console

import com.intellij.execution.filters.TextConsoleBuilderFactory
import com.intellij.execution.ui.ConsoleView
import com.intellij.execution.ui.ConsoleViewContentType
import com.intellij.openapi.project.Project
import com.github.linrol.tool.utils.TimeUtils

object ToolWindowConsole {
    private var console: ConsoleView? = null
    private var isShow: Boolean = false

    fun register(console: ConsoleView) {
        ToolWindowConsole.console = console
    }

    fun show() {
        isShow = true
    }

    fun clear() {
        console?.clear()
    }

    fun log(project: Project, s: String) {
        (console ?: TextConsoleBuilderFactory.getInstance().createBuilder(project).console).let {
            val time = TimeUtils.getCurrentTime(null)
            it.print("$time $s\n", ConsoleViewContentType.NORMAL_OUTPUT)
        }
    }
}
