package com.github.linrol.tool.state

import com.intellij.openapi.ui.ComboBox
import com.intellij.ui.components.JBCheckBox
import com.intellij.ui.layout.selectedValueIs
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
    private val shimoSid = JTextField("s%3A9e1d2ddd1970404b81e4fcf2b7182aed.gzbpB8BH75NkR7W87Tz1FKrR67A4L20vrkQgbcrGTHA")
    private val translaterApi = ComboBox(arrayOf("baidu", "google", "chatgpt"))

    init {
        panel = FormBuilder.createFormBuilder()
                .addComponent(buildAfterPush, 1)
                .addLabeledComponent(JLabel("编译地址"), buildUrl, 1)
                .addLabeledComponent(JLabel("编译人"), buildUser, 1)
                .addLabeledComponent(JLabel("石墨sid"), shimoSid, 1)
                .addLabeledComponent(JLabel("翻译api"), translaterApi, 1)
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

    fun getShimoSid(): String {
        return shimoSid.text
    }

    fun getTranslaterApi(): String {
        return translaterApi.selectedItem as String
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

    fun setShimoSid(newShimoSid: String) {
        shimoSid.text = newShimoSid
    }

    fun setTranslaterApi(api: String) {
        translaterApi.selectedItem = api
    }

    fun isModified(): Boolean {
        val enable = getBuildAfterPush() != ToolSettingsState.instance.buildAfterPush
        val urlModified = getBuildUrl() != ToolSettingsState.instance.buildUrl
        val userModified = getBuildUser() != ToolSettingsState.instance.buildUser
        val shimoSidModified = getShimoSid() != ToolSettingsState.instance.shimoSid
        val translaterApiModified = getTranslaterApi() != ToolSettingsState.instance.translaterApi
        return enable || urlModified || userModified || shimoSidModified || translaterApiModified
    }
}
