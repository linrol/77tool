package com.github.linrol.tool.state

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.PersistentStateComponent
import com.intellij.openapi.components.State
import com.intellij.openapi.components.Storage
import com.intellij.util.xmlb.XmlSerializerUtil

@State(name = "org.intellij.tool.state.ToolSettingsStat", storages = [Storage("77toolSettingsPlugin.xml")])
class ToolSettingsState : PersistentStateComponent<ToolSettingsState?> {
    // push后触发编译
    var buildAfterPush: Boolean = true

    var buildUrl: String = "http://ops.q7link.com:8000/qqdeploy/projectbuild/"

    var buildUser: String = "77tool"

    override fun getState(): ToolSettingsState {
        return this
    }

    override fun loadState(state: ToolSettingsState) {
        XmlSerializerUtil.copyBean(state, this)
    }

    companion object {
        val instance: ToolSettingsState = ApplicationManager.getApplication().getService(ToolSettingsState::class.java)
    }
}
