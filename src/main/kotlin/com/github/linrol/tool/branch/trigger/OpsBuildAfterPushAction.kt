package com.github.linrol.tool.branch.trigger

import com.google.gson.JsonParser
import com.intellij.dvcs.push.ui.VcsPushDialog
import com.intellij.dvcs.push.ui.VcsPushUi
import com.intellij.dvcs.repo.Repository
import com.intellij.notification.Notification
import com.intellij.openapi.diagnostic.logger
import com.intellij.openapi.project.Project
import com.intellij.openapi.ui.DialogWrapper
import git4idea.repo.GitRepository
import okhttp3.FormBody
import okhttp3.OkHttpClient
import okhttp3.Request
import org.apache.commons.lang3.exception.ExceptionUtils
import com.github.linrol.tool.base.BasePushAction
import com.github.linrol.tool.model.GitCmd
import com.github.linrol.tool.state.ToolSettingsState
import com.intellij.dvcs.push.ui.PushActionBase

class OpsBuildAfterPushAction: PushActionBase("Push And Build") {
    override fun actionPerformed(project: Project, dialog: VcsPushUi) {
        try {
            GitCmd.clear()
            val repos: List<Repository> = dialog.selectedPushSpecs.values.flatMap { it.map { obj -> obj.repository } }
            dialog.push(false)
            if (dialog.canPush()) {
                Thread.sleep(5000)
                reposBuild(project, repos)
            }
        } catch (e: RuntimeException) {
            e.printStackTrace()
            GitCmd.log(project, ExceptionUtils.getRootCauseMessage(e))
        } catch (e: Throwable) {
            close(dialog, DialogWrapper.OK_EXIT_CODE)
            e.printStackTrace()
            GitCmd.log(project, ExceptionUtils.getRootCauseMessage(e))
            logger.error("PushAndBuildAction execute failed", e)
        }
    }

    override fun isEnabled(dialog: VcsPushUi): Boolean {
        return ToolSettingsState.instance.buildAfterPush
    }

    override fun getDescription(dialog: VcsPushUi, enabled: Boolean): String {
        return "Push And Build"
    }

    private fun close(dialog: VcsPushUi, exitCode: Int) {
        if (dialog is VcsPushDialog) {
            // 关闭push窗口
            dialog.close(exitCode)
        }
    }

    private fun reposBuild(project: Project, repos: List<Repository>) {
        val branch2Paths: Map<String, String> = repos.groupBy { (it as GitRepository).currentBranchName.toString() }.mapValues {
            it.value.filter { repo -> (repo as GitRepository).root.name != "build" }.joinToString(",") { repo ->
                val gitRepo = repo as GitRepository
                gitRepo.remotes.first().firstUrl?.substringAfter("com/")?.substringBefore(".git") ?: gitRepo.root.name
            }
        }
        branch2Paths.forEach { opsBuild(project, it.key, it.value) }
        /* subscribe GitPusher Notifications
        project.messageBus.connect().subscribe(Notifications.TOPIC, object : Notifications {
            override fun notify(notification: Notification) {
                if (!isVcsNotification(notification)) return
                if (matchTitleOf(notification, "Push successful", "Push failed", "Push partially failed", "Push rejected", "Push partially rejected")) {

                }
            }
        }) */
    }

    private fun opsBuild(project: Project, branch: String, paths: String) {
        val client = OkHttpClient()
        val body = FormBody.Builder()
                .add("branch", branch)
                .add("projects", paths)
                .add("byCaller", ToolSettingsState.instance.buildUser)
                .build()
        val request = Request.Builder().url(ToolSettingsState.instance.buildUrl).post(body).build()
        client.newCall(request).execute().let {
            if (it.isSuccessful) {
                val jsonResponse = JsonParser.parseString(it.body().string()).asJsonObject
                val responseData = jsonResponse.get("data")
                if (responseData != null) {
                    val taskId = responseData.asJsonObject.getAsJsonPrimitive("taskid").asString
                    GitCmd.log(project,"项目:${paths}触发独立编译成功，编译任务ID:${taskId}")
                }
            } else {
                logger.info("Response Error: ${it.code()} - ${it.message()}")
                GitCmd.log(project,"Response Error: ${it.code()} - ${it.message()}")
            }
        }
    }

    companion object {
        private val logger = logger<OpsBuildAfterPushAction>()

        fun isVcsNotification(notification: Notification): Boolean {
            return  notification.groupId == "Vcs Notifications" ||
                    notification.groupId == "Vcs Messages" ||
                    notification.groupId == "Vcs Important Messages" ||
                    notification.groupId == "Vcs Minor Notifications" ||
                    notification.groupId == "Vcs Silent Notifications"
        }

        fun matchTitleOf(notification: Notification, vararg expectedTitles: String): Boolean {
            for (title in expectedTitles) {
                if (notification.title.startsWith(title)) return true
            }
            return false
        }
    }

}