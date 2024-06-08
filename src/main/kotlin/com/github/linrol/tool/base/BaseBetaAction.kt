package com.github.linrol.tool.base

import com.github.linrol.tool.state.ToolSettingsState
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.project.DumbAwareAction

abstract class BaseBetaAction : DumbAwareAction(){

    override fun update(e: AnActionEvent) {
        e.project ?: return
        val isBetaUser = listOf("罗林").contains(ToolSettingsState.instance.buildUser)
        e.presentation.isEnabledAndVisible = isBetaUser
    }
}