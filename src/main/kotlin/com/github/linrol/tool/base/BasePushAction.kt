package com.github.linrol.tool.base

import com.intellij.dvcs.push.ui.VcsPushUi
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.project.Project
import org.jetbrains.annotations.Nls
import org.jetbrains.annotations.NotNull
import org.jetbrains.annotations.Nullable

abstract class BasePushAction(actionName:String) : AbstractDumbAction(actionName) {
    abstract fun isEnabled(dialog: VcsPushUi): Boolean

    @Nls
    @Nullable
    protected abstract fun getDescription(@NotNull dialog: VcsPushUi, enabled: Boolean): String

    protected abstract fun actionPerformed(@NotNull project: Project, @NotNull dialog: VcsPushUi)

    override fun actionPerformed(e: AnActionEvent) {
        actionPerformed(e.getRequiredData(CommonDataKeys.PROJECT), e.getRequiredData(VcsPushUi.VCS_PUSH_DIALOG))
    }

    override fun update(e: AnActionEvent) {
        val dialog = e.getData(VcsPushUi.VCS_PUSH_DIALOG)
        if (dialog == null || e.project == null) {
            e.presentation.isEnabledAndVisible = false
            return
        }
        e.presentation.isVisible = true

        val enabled = isEnabled(dialog)
        e.presentation.isEnabled = enabled
        e.presentation.description = getDescription(dialog, enabled)
    }
}