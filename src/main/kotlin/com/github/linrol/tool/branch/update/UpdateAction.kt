package com.github.linrol.tool.branch.update

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.vcs.update.CommonUpdateProjectAction

class UpdateAction : CommonUpdateProjectAction() {

    private lateinit var callback: () -> Unit

    override fun filterRootsBeforeAction(): Boolean {
        return false
    }

    fun success(callback: () -> Unit): AnAction {
        this.callback = callback
        return this
    }

    override fun onSuccess() {
        callback.invoke()
    }
}
