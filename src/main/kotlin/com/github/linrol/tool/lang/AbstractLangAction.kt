package com.github.linrol.tool.lang

import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.progress.EmptyProgressIndicator
import com.intellij.openapi.progress.ProgressIndicator
import com.intellij.openapi.progress.ProgressManager
import com.intellij.openapi.progress.Task
import com.intellij.openapi.project.DumbAwareAction
import com.intellij.openapi.project.Project
import com.intellij.usages.Usage
import com.intellij.usages.UsageView

abstract class AbstractLangAction : DumbAwareAction() {

    fun getUsages(event: AnActionEvent): Array<Usage> {
        event.getData(UsageView.USAGE_VIEW_KEY) ?: return Usage.EMPTY_ARRAY
        return event.getData(UsageView.USAGES_KEY) ?: Usage.EMPTY_ARRAY
    }

    fun async(project: Project, runnable: Runnable) {
        ProgressManager.getInstance().runProcessWithProgressAsynchronously(object : Task.Backgroundable(project, "多语翻译中") {
            override fun run(indicator: ProgressIndicator) {
                runnable.run()
            }
        }, EmptyProgressIndicator())
    }

}