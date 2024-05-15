package com.github.linrol.tool.lang

import com.github.linrol.tool.model.GitCmd
import com.github.linrol.tool.utils.ShimApi
import com.github.linrol.tool.utils.TimeUtils
import com.google.common.hash.Hashing
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
import java.nio.charset.StandardCharsets
import java.nio.file.Files
import java.nio.file.Paths

class FrontLangAction : DumbAwareAction() {



    override fun actionPerformed(event: AnActionEvent) {
//        val editor: Editor = event.dataContext.getData("editor") as? Editor ?: return
//        val document = editor.document
//        val selectedText = editor.selectionModel.selectedText ?: return
//        val replaceText = "i18n('${translateUseBaidu(selectedText)}')"
//
//        val documentText = document.text
//        val newText = documentText.replace(selectedText, replaceText)
//        document.setText(newText)

        val project = event.project ?: return
        val usages: Array<Usage> = getUsages(event)
        if(usages.isEmpty()) {
            return
        }
        val exist = ShimApi(project).getText("5rk9KBxvZQH78g3x")
        val csvData = mutableListOf<String>()
        val translater = LangTranslater()
        if (translater.canProxy) {
            GitCmd.log(project, "使用谷歌翻译")
        } else {
            GitCmd.log(project, "使用百度翻译")
        }
        usages.filterIsInstance<UsageInfo2UsageAdapter>().forEach {
            val first = it.getMergedInfos().first()
            val last = it.getMergedInfos().last()
            if (first.navigationRange == null) {
                return
            }
            if (last.navigationRange == null) {
                return
            }
            var startOffset = first.navigationRange.startOffset
            var endOffset = last.navigationRange.endOffset
            val searchText = it.document.getText(TextRange(startOffset, endOffset))
            val match = exist.find { m -> m["zh-ch"].equals(searchText) }

            // 翻译
            val translateText: String = if (match != null) {
                "common.${match["reskey"].toString()}"
            } else {
                translater.translate(text = searchText)
            }
            if (searchText == translateText) {
                return
            }
            // 准备替换内容
            val resourceKey = translateText.replace(" ", "-")
            val codeResKey = if (resourceKey.startsWith("common.")) {
                resourceKey
            } else {
                val tmp = "${resourceKey}.${TimeUtils.getCurrentTime("yyyyMMddHHmmss")}"
                val hash = Hashing.murmur3_32().hashString(tmp, StandardCharsets.UTF_8).toString()
                "multilang.${hash}"
            }
            var replaceText = "i18n('${codeResKey}')/*${searchText}*/"
            // 判断中文是否被单引号或双引号包裹
            val quotedString = quotedString(it.document, startOffset, endOffset)
            if (quotedString) {
                startOffset -= 1
                endOffset += 1
            }
            val equalSignChar = getStr(it.document, startOffset - 1, startOffset).equals("=")
            if (!quotedString || equalSignChar) {
                // 不是字符串包裹的中文或在中文首字母-2的位置为=号
                replaceText = "{${replaceText}}"
            }
            WriteCommandAction.runWriteCommandAction(event.project) {
                it.document.replaceString(startOffset, endOffset, replaceText)
                val csvExist = csvData.any { f -> f.split(",")[1] == searchText }
                if (!csvExist && !codeResKey.startsWith("common.")) {
                    csvData.add("${codeResKey.replace("multilang.", "")},${searchText},${translateText}")
                }
            }
        }
        writeCsv(event, csvData)
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

    private fun getStr(document: Document, start: Int, end: Int): String? {
        val minEnd = 0
        val maxEnd = document.textLength
        if (start < minEnd || end > maxEnd) {
            return null
        }
        return document.getText(TextRange(start, end))
    }
}

fun String.equalsAny(vararg others: String): Boolean {
    return others.any { it == this }
}
