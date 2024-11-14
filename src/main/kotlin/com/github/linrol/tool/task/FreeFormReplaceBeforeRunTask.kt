package com.github.linrol.tool.task

import com.intellij.execution.BeforeRunTask
import com.intellij.openapi.util.Key

class FreeFormReplaceBeforeRunTask : BeforeRunTask<FreeFormReplaceBeforeRunTask>(TASK_KEY) {
    // 构造函数，设置任务描述
    init {
        isEnabled = true
    }

    override fun clone(): BeforeRunTask<FreeFormReplaceBeforeRunTask> {
        return FreeFormReplaceBeforeRunTask()
    }

    companion object {
        val TASK_KEY: Key<FreeFormReplaceBeforeRunTask> = Key.create("FreeFormReplaceTask")
    }
}
