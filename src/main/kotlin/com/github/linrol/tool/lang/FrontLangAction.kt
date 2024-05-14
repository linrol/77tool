package com.github.linrol.tool.lang

import com.github.linrol.tool.utils.TimeUtils
import com.google.gson.JsonParser
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.command.WriteCommandAction
import com.intellij.openapi.diagnostic.logger
import com.intellij.openapi.editor.Document
import com.intellij.openapi.project.DumbAwareAction
import com.intellij.openapi.util.TextRange
import com.intellij.usages.Usage
import com.intellij.usages.UsageInfo2UsageAdapter
import com.intellij.usages.UsageView
import okhttp3.OkHttpClient
import okhttp3.Request
import java.nio.file.Files
import java.nio.file.Paths

class FrontLangAction : DumbAwareAction() {

    private val cache = mutableMapOf<String, String>()

    override fun actionPerformed(event: AnActionEvent) {
//        val editor: Editor = event.dataContext.getData("editor") as? Editor ?: return
//        val document = editor.document
//        val selectedText = editor.selectionModel.selectedText ?: return
//        val replaceText = "i18n('${translateUseBaidu(selectedText)}')"
//
//        val documentText = document.text
//        val newText = documentText.replace(selectedText, replaceText)
//        document.setText(newText)

        val usages: Array<Usage> = getUsages(event)
        if(usages.isEmpty()) {
            return
        }
        val csvData = mutableListOf<String>()
        usages.filterIsInstance<UsageInfo2UsageAdapter>().forEach {
            var startOffset = it.getMergedInfos().first().navigationRange.startOffset
            var endOffset = it.getMergedInfos().last().navigationRange.endOffset
            val searchText = it.document.getText(TextRange(startOffset, endOffset))
            // 翻译
            val translateText = translateUseBaidu(searchText)
            if (searchText == translateText) {
                return
            }
            // 准备替换内容
            val resourceKey = translateText.replace(" ", "-")
            // 判断中文是否被单引号或双引号选中
            val quotedString = quotedString(it.document, startOffset, endOffset)
            var replaceText = "i18n('${resourceKey}')/*${searchText}*/"
            if (quotedString) {
                startOffset -= 1
                endOffset += 1
            } else {
                replaceText = "{${replaceText}}"
            }
            WriteCommandAction.runWriteCommandAction(event.project) {
                it.document.replaceString(startOffset, endOffset, replaceText)
                csvData.add("${resourceKey},${translateText},${searchText}")
            }
        }
        writeCsv(event, csvData)
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

    companion object {
        private val logger = logger<FrontLangAction>()
    }

    private fun getUsages(event: AnActionEvent): Array<Usage> {
        ApplicationManager.getApplication().assertIsDispatchThread()
        event.getData(UsageView.USAGE_VIEW_KEY) ?: return Usage.EMPTY_ARRAY
        return event.getData(UsageView.USAGES_KEY) ?: Usage.EMPTY_ARRAY
    }

    private fun writeCsv(event: AnActionEvent, data: List<String>) {
        val project = event.project ?: return
        project.basePath ?.let { path ->
            val csvFile = Paths.get(path, "multilang-${TimeUtils.getCurrentTime("yyyyMMddHHmmss")}.csv")
            if (!Files.exists(csvFile)) {
                Files.createFile(csvFile)
            }
            csvFile.toFile().bufferedWriter().use { out ->
                data.forEach { row ->
                    out.write(row)
                    out.newLine()
                }
            }
        }
    }

    private fun quotedString(document: Document, start: Int, end: Int): Boolean {
        val minEnd = 0
        val maxEnd = document.textLength
        if (start <= minEnd || end >= maxEnd) {
            return false
        }
        val leftCharacter = document.getText(TextRange(start - 1, start))
        val rightCharacter = document.getText(TextRange(end, end + 1))
        if (leftCharacter.equalsAny("'", "\"") && rightCharacter.equalsAny("'", "\"")) {
            return true
        }
        return false
    }
}

fun md5(input: String): String {
    val md = java.security.MessageDigest.getInstance("MD5")
    val byteArray = input.toByteArray()
    val mdBytes = md.digest(byteArray)
    return mdBytes.joinToString("") { "%02x".format(it) }
}

fun String.equalsAny(vararg others: String): Boolean {
    return others.any { it == this }
}