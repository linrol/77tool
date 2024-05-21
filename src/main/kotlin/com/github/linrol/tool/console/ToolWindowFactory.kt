package com.github.linrol.tool.console

import com.intellij.execution.filters.TextConsoleBuilderFactory
import com.intellij.execution.ui.ConsoleView
import com.intellij.openapi.project.Project
import com.intellij.openapi.wm.ToolWindow
import com.intellij.openapi.wm.ToolWindowFactory
import com.github.linrol.tool.console.ToolWindowConsole.register
import java.awt.BorderLayout
import javax.swing.JComponent
import javax.swing.JPanel

class ToolWindowFactory : ToolWindowFactory {
    override fun shouldBeAvailable(project: Project): Boolean {
        return true
    }

    override fun createToolWindowContent(project: Project, toolWindow: ToolWindow) {
        val consoleBuilder = TextConsoleBuilderFactory.getInstance().createBuilder(project)
        val console = consoleBuilder.console
        val consolePanel = createConsolePanel(console)
        val content = toolWindow.contentManager.factory.createContent(consolePanel, "控制台", false)
        toolWindow.contentManager.addContent(content)
        // console.print("------------after add consoleView to tool------------" + "\n", ConsoleViewContentType.LOG_INFO_OUTPUT);
        register(console)
        //PropertiesCenter.init(project);
        //console.setOutputPaused(true);
    }


    companion object {
        fun createConsolePanel(view: ConsoleView): JComponent {
            val panel = JPanel()
            panel.layout = BorderLayout()
            panel.add(view.component, BorderLayout.CENTER)
            return panel
        }
    }
}