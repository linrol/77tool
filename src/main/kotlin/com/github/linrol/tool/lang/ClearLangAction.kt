package com.github.linrol.tool.lang

import com.github.linrol.tool.model.GitCmd
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.diagnostic.logger
import org.apache.commons.lang3.exception.ExceptionUtils
import java.util.concurrent.atomic.AtomicInteger

class ClearLangAction : AbstractLangAction() {

    companion object {
        private val logger = logger<ClearLangAction>()
    }

    override fun actionPerformed(event: AnActionEvent) {
        val project = event.project ?: return
        try {
            projectViewProcess(event, project)  // 清除英文列
        } catch (e: Exception) {
            e.printStackTrace()
            logger.error(e)
            GitCmd.log(project, e.stackTraceToString())
            GitCmd.log(project, ExceptionUtils.getRootCauseMessage(e))
        }
    }


    override fun rowTranslateAsync(header: Map<String, Int>, row: Array<String>, translater: LangTranslater, count: AtomicInteger): Array<String> {
        val englishIdx = header["content"] ?: return row
        return row.apply { set(englishIdx, "") }
    }
}