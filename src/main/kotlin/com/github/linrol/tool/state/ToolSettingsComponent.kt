package com.github.linrol.tool.state

import com.intellij.ui.components.JBCheckBox
import com.intellij.util.ui.FormBuilder
import javax.swing.JComponent
import javax.swing.JLabel
import javax.swing.JPanel
import javax.swing.JTextField

class ToolSettingsComponent {
    val panel: JPanel
    private val buildAfterPush = JBCheckBox("Enable ops build after successful push? ")
    private val buildUrl = JTextField("http://ops.q7link.com:8000/qqdeploy/projectbuild/")
    private val buildUser = JTextField("77tool")

    init {
        panel = FormBuilder.createFormBuilder()
                .addComponent(buildAfterPush, 1)
                .addLabeledComponent(JLabel("Build url"), buildUrl, 1)
                .addLabeledComponent(JLabel("Build user"), buildUser, 1)
                .addComponentFillVertically(JPanel(), 0)
                .panel
    }

    val preferredFocusedComponent: JComponent get() = buildAfterPush

    fun getBuildAfterPush(): Boolean {
        return buildAfterPush.isSelected
    }

    fun getBuildUrl(): String {
        return buildUrl.text
    }

    fun getBuildUser(): String {
        return buildUser.text
    }

    fun setBuildAfterPush(newStatus: Boolean) {
        buildAfterPush.isSelected = newStatus
    }

    fun setBuildUrl(newUrl: String) {
        buildUrl.text = newUrl
    }

    fun setBuildUser(newUser: String) {
        buildUser.text = newUser
    }

    fun isModified(): Boolean {
        val enable = getBuildAfterPush() != ToolSettingsState.instance.buildAfterPush
        val urlModified = getBuildUrl() != ToolSettingsState.instance.buildUrl
        val userModified = getBuildUser() != ToolSettingsState.instance.buildUser
        return enable || urlModified || userModified
    }
}
