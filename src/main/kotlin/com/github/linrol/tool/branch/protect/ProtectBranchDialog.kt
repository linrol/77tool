package com.github.linrol.tool.branch.protect

import com.github.linrol.tool.branch.merge.local.CommonMergeDialog
import com.github.linrol.tool.constants.GITLAB_URL
import com.github.linrol.tool.model.GitCmd
import com.github.linrol.tool.utils.GitLabUtil
import com.intellij.ide.ui.laf.darcula.ui.DarculaComboBoxUI
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.diagnostic.logger
import com.intellij.openapi.editor.event.DocumentEvent
import com.intellij.openapi.editor.event.DocumentListener
import com.intellij.openapi.progress.util.BackgroundTaskUtil
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.ComboBox
import com.intellij.openapi.ui.DialogWrapper
import com.intellij.openapi.ui.ValidationInfo
import com.intellij.ui.MutableCollectionComboBoxModel
import com.intellij.util.ui.JBUI
import git4idea.ui.ComboBoxWithAutoCompletion
import net.miginfocom.layout.AC
import net.miginfocom.layout.CC
import net.miginfocom.layout.LC
import net.miginfocom.swing.MigLayout
import java.awt.Insets
import javax.swing.JLabel
import javax.swing.JPanel

class ProtectBranchDialog(
    private val project: Project,
    private val action: AnActionEvent,
) : DialogWrapper(project, /* canBeParent */ true) {

    private val branch = createComboBoxWithAutoCompletion("请选择被保护的分支")
    private val branchLevel = createComboBox("请选择被保护的分支权限")
    private val innerPanel = createInnerPanel()
    private val panel = createPanel()

    private val repos = GitLabUtil.getRepositories(project)
    private val branches = repos.flatMap { it.branches.remoteBranches }
        .distinct()
        .filter { it.name.isNotBlank() && it.nameForRemoteOperations.isNotBlank() }
        .associateBy ( {it.nameForRemoteOperations}, {it.name} )

    companion object {
        val log = logger<CommonMergeDialog>()
    }

    init {
        title = "分支保护"
        setCancelButtonText("取消")
        setOKButtonText("确定")
        comboBoxBindDatas()
        init()
        render()
    }

    override fun createCenterPanel() = panel

    override fun getPreferredFocusedComponent() = branch

    override fun doValidateAll(): List<ValidationInfo> = validates()

    private fun createPanel() =
        JPanel().apply {
            layout = MigLayout(LC().insets("0").hideMode(3), AC().grow())

            add(innerPanel, CC().growX().wrap())
        }

    private fun createInnerPanel(): JPanel {
        return JPanel().apply {
            layout = MigLayout(
                LC().fillX().insets("0").gridGap("0", "0").noVisualPadding(),
                AC().grow(100f, 1)
            )

            add(JLabel("保护分支"), CC().gapAfter("0").minWidth("${JBUI.scale(60)}px"))
            add(branch, CC().minWidth("${JBUI.scale(250)}px").growX().wrap())

            add(JLabel("权限级别"), CC().gapAfter("0").minWidth("${JBUI.scale(60)}px"))
            add(branchLevel, CC().minWidth("${JBUI.scale(250)}px").growX().wrap())
        }
    }

    private fun createComboBoxWithAutoCompletion(placeholder: String): ComboBoxWithAutoCompletion<String> =
        ComboBoxWithAutoCompletion(MutableCollectionComboBoxModel(mutableListOf<String>()), project)
            .apply {
                prototypeDisplayValue = "origin/long-enough-branch-name"
                setPlaceholder(placeholder)
                setUI(DarculaComboBoxUI(/* arc */ 0f, Insets(1, 0, 1, 0), /* paintArrowButton */false))
                addDocumentListener(
                    object : DocumentListener {
                        override fun documentChanged(event: DocumentEvent) {
                            startTrackingValidation()
                        }
                    },
                )
            }

    private fun createComboBox(placeholder: String) = ComboBox(arrayOf("Noone", "Hotfix", "Release", "Dev", "Delete"))

    private fun render() {
        window.pack()
        window.revalidate()
        pack()
        repaint()
    }

    private fun comboBoxBindDatas() {
        val boxModel = branch.model as? MutableCollectionComboBoxModel
        boxModel?.update(branches.keys.sortedBy { calBranchWeight(it) })
        branch.selectAll()
        branch.selectedIndex = 0
    }

    private fun validates(): List<ValidationInfo> {
        val validators = mutableListOf<ValidationInfo>()
        val branchName = branch.getText()
        val level = branchLevel.item
        if (branchName.isNullOrBlank()) {
            validators.add(ValidationInfo("被保护的分支必填", branch))
            return validators
        }
        if (level.isNullOrBlank()) {
            validators.add(ValidationInfo("被保护的分支权限必选", branchLevel))
            return validators
        }
        return validators
    }

    override fun doOKAction() {
        val branchName = branch.getText()!!
        val protectLevel = ProtectLevel.valueOf(branchLevel.item)
        BackgroundTaskUtil.executeOnPooledThread(project) {
            GitCmd.clear()
            GitLabUtil.getCommonRepositories(project, branchName).forEach {
                it.remotes.first().firstUrl?.takeIf { url -> url.contains(GITLAB_URL) }?.replace(GITLAB_URL, "")?.replace(".git", "")?.run {
                    GitLabUtil.protectBranch(this, branchName, protectLevel).takeIf { ret -> ret }?.let {
                        GitCmd.log(project, "工程【${this}】分支【${branchName}】设置保护权限【${protectLevel.desc}】")
                    }
                }
            }
        }
        super.doOKAction()
    }

    private fun calBranchWeight(branch: String): Int {
        if (branch.startsWith("sprint") || branch.startsWith("release")) {
            val date = branch.replace("sprint", "").replace("release", "")
            if (date.length == 8) {
                return 0
            }
        }
        if (branch.startsWith("stage-patch") || branch.startsWith("emergency")) {
            return 1
        }
        if (branch.startsWith("feature")) {
            return 2
        }
        return 3
    }
}