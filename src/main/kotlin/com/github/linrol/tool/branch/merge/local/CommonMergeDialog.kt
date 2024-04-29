package com.github.linrol.tool.branch.merge.local

import com.google.common.collect.Sets
import com.intellij.ide.ui.laf.darcula.ui.DarculaComboBoxUI
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.diagnostic.logger
import com.intellij.openapi.editor.event.DocumentEvent
import com.intellij.openapi.editor.event.DocumentListener
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.DialogWrapper
import com.intellij.openapi.ui.ValidationInfo
import com.intellij.openapi.vcs.AbstractVcsHelper
import com.intellij.ui.MutableCollectionComboBoxModel
import com.intellij.util.ui.JBUI
import git4idea.branch.GitBrancher
import git4idea.repo.GitRepository
import git4idea.ui.ComboBoxWithAutoCompletion
import net.miginfocom.swing.MigLayout
import org.apache.commons.lang3.exception.ExceptionUtils
import com.github.linrol.tool.branch.update.UpdateAction
import com.github.linrol.tool.branch.version.ChangeVersion
import com.github.linrol.tool.extend.vcs.AbstractVcsHelperImplEx
import com.github.linrol.tool.model.GitCmd
import com.github.linrol.tool.utils.GitLabUtil
import java.awt.Insets
import javax.swing.JLabel
import javax.swing.JPanel
import net.miginfocom.layout.AC as AxisConstraint
import net.miginfocom.layout.CC as ComponentConstraint
import net.miginfocom.layout.LC as LayoutConstraint

/**
 * This class has been inspired by [git4idea.merge.GitMergeDialog].
 * If you see any non-trivial pieces of code,
 * please take a look to that class as a reference.
 */
class CommonMergeDialog(
        private val project: Project,
        private val action: AnActionEvent,
) : DialogWrapper(project, /* canBeParent */ true) {


    private val branchSource = createComboBoxWithAutoCompletion("请选择来源分支")
    private val branchTarget = createComboBoxWithAutoCompletion("请选择目标分支")
    private val moduleBox = createComboBoxWithAutoCompletion("请选择工程模块")
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
        title = "分支合并"
        setCancelButtonText("取消")
        setOKButtonText("合并")
        comboBoxBindDatas()
        init()
        render()
    }

    override fun createCenterPanel() = panel

    override fun getPreferredFocusedComponent() = branchSource

    override fun doValidateAll(): List<ValidationInfo> = validates(false)

    private fun createPanel() =
            JPanel().apply {
                layout = MigLayout(LayoutConstraint().insets("0").hideMode(3), AxisConstraint().grow())

                add(innerPanel, ComponentConstraint().growX().wrap())

                // add(JCheckBox("合并后执行ChangeVersion？"))
            }

    private fun createInnerPanel(): JPanel {
        return JPanel().apply {
            layout = MigLayout(
                    LayoutConstraint().fillX().insets("0").gridGap("0", "0").noVisualPadding(),
                    AxisConstraint().grow(100f, 1)
            )

            add(JLabel("来源分支"), ComponentConstraint().gapAfter("0").minWidth("${JBUI.scale(60)}px"))
            add(branchSource, ComponentConstraint().minWidth("${JBUI.scale(250)}px").growX().wrap())

            add(JLabel("目标分支"), ComponentConstraint().gapAfter("0").minWidth("${JBUI.scale(60)}px"))
            add(branchTarget, ComponentConstraint().minWidth("${JBUI.scale(250)}px").growX().wrap())

            add(JLabel("工程模块"), ComponentConstraint().gapAfter("0").minWidth("${JBUI.scale(60)}px"))
            add(moduleBox, ComponentConstraint().minWidth("${JBUI.scale(250)}px").growX().wrap())
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
        val sourcesModel = branchSource.model as? MutableCollectionComboBoxModel
        sourcesModel?.update(branches.keys.sortedBy { calSourceWeight(it) })
        branchSource.selectAll()
        branchSource.setSelectedIndex(0)

        val targetModel = branchTarget.model as? MutableCollectionComboBoxModel
        targetModel?.update(branches.keys.sortedBy { calTargetWeight(it) })
        branchTarget.selectAll()
        branchTarget.setSelectedIndex(0)

        val list = repos.map { p: GitRepository -> p.root.name }.distinct().toMutableList()
        list.addAll(0, listOf("交集分支的全部工程", "来源分支的全部工程"))
        val moduleModel = moduleBox.model as? MutableCollectionComboBoxModel
        moduleModel?.update(list)
        moduleBox.selectAll()
        moduleBox.setSelectedIndex(0)
        moduleBox.addPropertyChangeListener {
            validates(true)
        }
    }

    private fun validates(tiggerListener: Boolean): List<ValidationInfo> {
        val validators = mutableListOf<ValidationInfo>()
        val source = branchSource.getText()
        val target = branchTarget.getText()
        if (source.isNullOrBlank()) {
            validators.add(ValidationInfo("来源分支名必填", branchSource))
            return validators
        }
        if (target.isNullOrBlank()) {
            validators.add(ValidationInfo("目标分支名必填", branchTarget))
            return validators
        }
        if (source == target) {
            validators.add(ValidationInfo("来源分支和目标分支不允许相同", branchTarget))
        }
        val module = moduleBox.getText()
        if (module.isNullOrBlank()) {
            validators.add(ValidationInfo("工程模块必填", moduleBox))
        }
        val commonRepos = GitLabUtil.getCommonRepositories(project, source, target).filter {
            module?.endsWith("全部工程") ?: false || module == it.root.name
        }
        if (commonRepos.isEmpty()) {
            validators.add(ValidationInfo("来源和目标分支不存在交集工程", moduleBox))
        }
        if (module == "来源分支的全部工程") {
            val sourceRepos = repos.filter { it.branches.remoteBranches.any { branch -> branch.nameForRemoteOperations == source } }
            val diffRepos = Sets.difference(sourceRepos.map { it.root.name }.toSet(), commonRepos.map { it.root.name }.toSet())
            if (!diffRepos.isEmpty()) {
                if (tiggerListener) {
                    GitCmd.clear()
                    GitCmd.log(project, "目标分支缺少工程模块【${diffRepos.joinToString(",")}】")
                }
                validators.add(ValidationInfo("目标分支缺少工程模块【${diffRepos.joinToString(",")}】", moduleBox))
            }
        }
        return validators
    }

    override fun doOKAction() {
        val brancher = GitBrancher.getInstance(project)
        val source = branchSource.getText()!!
        val target = branchTarget.getText()!!
        val module = moduleBox.getText()
        val commonRepos = GitLabUtil.getCommonRepositories(project, source, target).filter {
            module?.endsWith("全部工程") ?: false || module == it.root.name
        }
        val callInAwtLater = Runnable {
            withExceptionRun {
                val checkoutRet = assertRepoBranch(commonRepos, target)
                if (checkoutRet) {
                    val updateAction = action.actionManager.getAction("com.github.linrol.tool.branch.update.UpdateAction") as UpdateAction
                    updateAction.success {
                        commonRepos.find { it.root.name == "build" } ?.let {
                            val vcsHelper = AbstractVcsHelper.getInstance(project) as AbstractVcsHelperImplEx
                            vcsHelper.apply {
                                setCallAfterMerged {
                                    val changeRet = ChangeVersion(project).run(target)
                                    GitCmd.log(project, "分支【${target}】根据配置定义重刷版本号【${changeRet}】")
                                }
                            }
                        }
                        brancher.merge(branches[source].toString(), GitBrancher.DeleteOnMergeOption.NOTHING, commonRepos)
                    }.actionPerformed(action)
                }
            }
        }
        brancher.checkout(target, false, commonRepos, callInAwtLater)
        super.doOKAction()
    }

    private fun assertRepoBranch(repositories: List<GitRepository>, branchName: String): Boolean {
        return repositories.map { repo ->
            val branch = repo.currentBranch
            val ret = branch != null && branch.name == branchName
            if (!ret) {
                val module = repo.root.name
                GitCmd.log(project, "工程【${module}】切换分支到【${branchName}】失败，终止合并！！！")
            }
            ret
        }.reduce { r1, r2 -> r1 && r2 }.or(false)
    }

    private fun withExceptionRun(runnable: Runnable) {
        try {
            runnable.run()
        } catch (e: RuntimeException) {
            GitCmd.log(project, ExceptionUtils.getRootCauseMessage(e))
        } catch (e: Throwable) {
            e.printStackTrace()
            GitCmd.log(project, ExceptionUtils.getRootCauseMessage(e))
            log.error("GitMergeRequestAction execute failed", e)
        }
    }

    private fun calSourceWeight(branch: String): Int {
        if (branch == "stage") {
            return 0
        }
        if (branch == "master") {
            return 1
        }
        if (branch.startsWith("sprint") || branch.startsWith("release")) {
            val date = branch.replace("sprint", "").replace("release", "")
            if (date.length == 8) {
                return 2
            }
        }
        if (branch.startsWith("feature")) {
            return 3
        }
        if (branch.startsWith("stage-patch") || branch.startsWith("emergency")) {
            return 4
        }
        return 5
    }

    private fun calTargetWeight(branch: String): Int {
        if (branch.startsWith("feature")) {
            return 0
        }
        if (branch.startsWith("sprint") || branch.startsWith("release")) {
            val date = branch.replace("sprint", "").replace("release", "")
            if (date.length == 8) {
                return 1
            }
        }
        if (branch == "stage" || branch == "master") {
            return 2
        }
        if (branch.startsWith("stage-patch") || branch.startsWith("emergency")) {
            return 3
        }
        return 4
    }
}