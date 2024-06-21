package com.github.linrol.tool.branch.delete

import com.github.linrol.tool.branch.merge.local.CommonMergeDialog
import com.github.linrol.tool.model.GitCmd
import com.github.linrol.tool.utils.GitLabUtil
import com.intellij.ide.ui.laf.darcula.ui.DarculaComboBoxUI
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.diagnostic.logger
import com.intellij.openapi.editor.event.DocumentEvent
import com.intellij.openapi.editor.event.DocumentListener
import com.intellij.openapi.progress.util.BackgroundTaskUtil
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.DialogWrapper
import com.intellij.openapi.ui.ValidationInfo
import com.intellij.ui.MutableCollectionComboBoxModel
import com.intellij.ui.components.JBCheckBox
import com.intellij.util.ui.JBUI
import git4idea.branch.GitBrancher
import git4idea.ui.ComboBoxWithAutoCompletion
import net.miginfocom.layout.AC
import net.miginfocom.layout.CC
import net.miginfocom.layout.LC
import net.miginfocom.swing.MigLayout
import java.awt.Insets
import javax.swing.JLabel
import javax.swing.JPanel

class DeleteBranchDialog(
    private val project: Project,
    private val action: AnActionEvent,
) : DialogWrapper(project, /* canBeParent */ true) {

    private val branch = createComboBoxWithAutoCompletion("请选择被删除的分支")
    private val deleteRemote = JBCheckBox()
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
        title = "分支删除"
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
                AC().grow(20f, 1)
            )

            add(JLabel("分支名称"), CC().gapAfter("0").minWidth("${JBUI.scale(60)}px"))
            add(branch, CC().minWidth("${JBUI.scale(100)}px").growX().wrap())

            add(JLabel("删除远程"), CC().gapAfter("0").minWidth("${JBUI.scale(60)}px").gapY("${JBUI.scale(10)}px", "0"))
            add(deleteRemote, CC().minWidth("${JBUI.scale(100)}px").growX().gapY("${JBUI.scale(10)}px", "0"))
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
        if (branchName.isNullOrBlank()) {
            validators.add(ValidationInfo("分支必填", branch))
            return validators
        }
        return validators
    }

    override fun doOKAction() {
        val branchName = branch.getText()!!
        BackgroundTaskUtil.executeOnPooledThread(project) {
            GitCmd.clear()
            val repos = GitLabUtil.getCommonRepositories(project, branchName)
            if (repos.isEmpty()) return@executeOnPooledThread
            val brancher = GitBrancher.getInstance(project)
            brancher.deleteBranch(branchName, repos)
            if (deleteRemote.isSelected) {
                brancher.deleteRemoteBranch("origin/$branchName", repos)
            }
            repos.forEach {
                GitCmd.log(project, "工程【${it}】本地分支【${branchName}】删除成功")
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