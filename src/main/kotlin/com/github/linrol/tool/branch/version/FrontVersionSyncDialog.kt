package com.github.linrol.tool.branch.version

import com.github.linrol.tool.constants.GIT_BUILD_PATH
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
import com.intellij.util.ui.JBUI
import git4idea.GitUserRegistry
import git4idea.ui.ComboBoxWithAutoCompletion
import net.miginfocom.layout.AC
import net.miginfocom.layout.CC
import net.miginfocom.layout.LC
import net.miginfocom.swing.MigLayout
import java.awt.Insets
import javax.swing.JLabel
import javax.swing.JPanel

class FrontVersionSyncDialog(
    private val project: Project,
    private val action: AnActionEvent,
) : DialogWrapper(project, /* canBeParent */ true) {

    private val branch = createComboBoxWithAutoCompletion("请选择被同步的后端分支")
    private val version = createComboBoxWithAutoCompletion("请选择同步到后端的版本号")
    private val innerPanel = createInnerPanel()
    private val panel = createPanel()
    private val buildBranches = GitLabUtil.getRepositoryBranches(GIT_BUILD_PATH)
    private val frontGoServer = GitLabUtil.getRepository(project, "front-goserver")
    companion object {
        val log = logger<FrontVersionSyncDialog>()
    }

    init {
        title = "前端版本号同步"
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

            add(JLabel("被同步分支"), CC().gapAfter("0").minWidth("${JBUI.scale(90)}px"))
            add(branch, CC().minWidth("${JBUI.scale(250)}px").growX().wrap())

            add(JLabel("同步版本号"), CC().gapAfter("0").minWidth("${JBUI.scale(90)}px"))
            add(version, CC().minWidth("${JBUI.scale(250)}px").growX().wrap())
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
        val branchModel = branch.model as? MutableCollectionComboBoxModel
        branchModel?.update(buildBranches.keys.sortedBy { calBranchWeight(it) })
        branch.addItemListener {
            val branchName = it.item.toString()
            version.setPlaceholder("后端分支版本为(${getBuildFrontVersion(branchName)})")

            val versionModel = version.model as? MutableCollectionComboBoxModel
            versionModel?.update(GitLabUtil.getFrontLocalXmlVersions(frontGoServer))
        }
        branch.selectAll()
        branch.selectedIndex = 0
    }

    private fun validates(): List<ValidationInfo> {
        val validators = mutableListOf<ValidationInfo>()
        val branchName = branch.getText()
        if (branchName.isNullOrBlank()) {
            validators.add(ValidationInfo("被同步的分支必填", branch))
            return validators
        }
        if (listOf("master", "stage", "perform").contains(branchName)) {
            validators.add(ValidationInfo("不允许操作基准分支", branch))
            return validators
        }
        val versionNo = version.item
        if (versionNo.isNullOrBlank()) {
            validators.add(ValidationInfo("被同步的版本号必填", version))
            return validators
        }
        if (versionNo == getBuildFrontVersion(branchName)) {
            validators.add(ValidationInfo("被同步的版本号和后端版本号一致，无需同步", version))
            return validators
        }
        return validators
    }

    override fun doOKAction() {
        val branchName = branch.getText()!!
        val versionNo = version.item
        BackgroundTaskUtil.executeOnPooledThread(project) {
            GitCmd.clear()
            val gitUserName = frontGoServer?.root?.let {
                GitUserRegistry.getInstance(project).getUser(it)?.name
            } ?: ""
            GitLabUtil.updateBuildVersion(GIT_BUILD_PATH, branchName, "reimburse", versionNo, gitUserName).takeIf { ret -> ret }?.let {
                GitCmd.log(project, "分支(${branchName})预制数据版本号(front-apps.reimburse)成功更新为:$versionNo")
            }
        }
        super.doOKAction()
    }

    private fun getBuildFrontVersion(branchName: String): String {
        return GitLabUtil.getBuildVersion(GIT_BUILD_PATH, branchName, "reimburse")
    }

    private fun calBranchWeight(branch: String): Int {
        if (branch == frontGoServer?.currentBranchName) {
            return 0
        }
        if (branch.startsWith("feature")) {
            return 1
        }
        if (branch.startsWith("sprint") || branch.startsWith("release")) {
            val date = branch.replace("sprint", "").replace("release", "")
            if (date.length == 8) {
                return 2
            }
        }
        if (branch.startsWith("stage-patch") || branch.startsWith("emergency")) {
            return 3
        }
        return 4
    }
}