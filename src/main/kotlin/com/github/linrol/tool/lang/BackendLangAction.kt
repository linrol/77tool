package com.github.linrol.tool.lang

import com.github.linrol.tool.model.GitCmd
import com.google.gson.JsonParser
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.command.WriteCommandAction
import com.intellij.openapi.diagnostic.logger
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.project.DumbAwareAction
import okhttp3.OkHttpClient
import okhttp3.Request
import java.net.SocketTimeoutException
import java.util.*
import java.util.concurrent.TimeUnit

class BackendLangAction : DumbAwareAction() {

    private val cache = mutableMapOf<String, String>()

    override fun actionPerformed(event: AnActionEvent) {
        val project = event.project ?: return
        val editor: Editor = event.dataContext.getData("editor") as? Editor ?: return
        val document = editor.document
        val selectedText = editor.selectionModel.selectedText ?: return
        // 翻译
        val translateText: String = if (canProxy()) {
            GitCmd.log(project, "使用谷歌翻译")
            translateUseGoogle(selectedText)
        } else {
            GitCmd.log(project, "使用百度翻译")
            translateUseBaidu(selectedText)
        }
        if (selectedText == translateText) {
            return
        }
        // 准备替换内容
        val resourceKey = translateText.replace(" ", "_").uppercase(Locale.getDefault())
        val replaceText = "StrResUtils.getCurrentAppStr(StrResConstants.${resourceKey})"
        val documentText = document.text
        val newText = documentText.replace("\"${selectedText}\"", replaceText)
        WriteCommandAction.runWriteCommandAction(event.project) {
            document.setText(newText)
        }
    }

    private fun translateUseBaidu(text: String): String {
        val ret = cache[text]
        if (ret != null) {
            return ret
        }
        val appId = "20240513002050659"
        val appKey = "Y6ZoTVT8oDBsF_MzBcIE"
        val salt = System.currentTimeMillis().toString()
        val sign = md5("$appId$text$salt$appKey")
        val params = "q=${text}&from=zh&to=en&appid=${appId}&salt=${salt}&sign=${sign}"
        val url = "https://api.fanyi.baidu.com/api/trans/vip/translate?${params}"

        val client = OkHttpClient()
        val request = Request.Builder().url(url).get().build()
        return client.newCall(request).execute().let {
            if (it.isSuccessful) {
                val response = JsonParser.parseString(it.body().string()).asJsonObject
                val translateText = response.getAsJsonArray("trans_result").get(0).asJsonObject.get("dst").asString
                cache[text] = translateText
                translateText
            } else {
                logger.info("Response Error: ${it.code()} - ${it.message()}")
                text
            }
        }
    }

    private fun translateUseGoogle(text: String): String {
        val ret = cache[text]
        if (ret != null) {
            return ret
        }
        val key = "AIzaSyBuRCQkN72SAkmQ0CT3fK4mJIEg_ZCqUd8"
        val params = "q=${text}&source=zh&target=en&key=${key}"
        val url = "https://translation.googleapis.com/language/translate/v2?${params}"

        val client = OkHttpClient()
        val request = Request.Builder().url(url).get().build()
        return client.newCall(request).execute().let {
            if (it.isSuccessful) {
                val response = JsonParser.parseString(it.body().string()).asJsonObject
                val translateText = response.getAsJsonObject("data").getAsJsonArray("translations").get(0).asJsonObject.get("translatedText").asString
                cache[text] = translateText
                translateText
            } else {
                logger.info("Response Error: ${it.code()} - ${it.message()}")
                text
            }
        }
    }

    companion object {
        private val logger = logger<BackendLangAction>()
    }

    private fun canProxy(): Boolean {
        val client = OkHttpClient().newBuilder().connectTimeout(2, TimeUnit.SECONDS).build()
        return try {
            client.newCall(Request.Builder().url("https://translate.google.com/").get().build()).execute().let {
                it.isSuccessful
            }
        } catch (e: SocketTimeoutException) {
            false
        }
    }
}