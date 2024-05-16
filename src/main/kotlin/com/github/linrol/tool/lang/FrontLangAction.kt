package com.github.linrol.tool.lang

import com.github.linrol.tool.model.GitCmd
import com.github.linrol.tool.utils.*
import com.google.common.hash.Hashing
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.command.WriteCommandAction
import com.intellij.openapi.diagnostic.logger
import com.intellij.usages.Usage
import com.intellij.usages.UsageInfo2UsageAdapter
import org.apache.commons.lang3.exception.ExceptionUtils
import java.nio.charset.StandardCharsets
import java.nio.file.Files
import java.nio.file.Paths

class FrontLangAction : AbstractLangAction() {

    companion object {
        private val logger = logger<FrontLangAction>()
    }

    override fun actionPerformed(event: AnActionEvent) {
        val project = event.project ?: return
        val usages: Array<Usage> = getUsages(event)
        if(usages.isEmpty()) {
            return
        }
        try {
            async(project) {
                val exist = ShimApi(project).getText("5rk9KBxvZQH78g3x")
                val csvData = mutableListOf<String>()
                val keyCache = mutableMapOf<String, String>()
                val translater = LangTranslater().printUse(project)
                usages.filterIsInstance<UsageInfo2UsageAdapter>().forEach {
                    val searchText = it.searchText() ?: return@forEach
                    val match = exist.find { m -> m["zh-ch"].equals(searchText) }
                    // 翻译
                    val translateText: String = if (match != null) {
                        "common.${match["reskey"].toString()}"
                    } else {
                        translater.translate(text = searchText)
                    }
                    if (searchText == translateText) {
                        return@forEach
                    }
                    // 准备替换内容
                    val resourceKey = translateText.replace(" ", "-")
                    val codeResKey = if (resourceKey.startsWith("common.")) {
                        resourceKey
                    } else {
                        val tmp = "${resourceKey}.${TimeUtils.getCurrentTime("yyyyMMddHHmmss")}"
                        val hash = Hashing.murmur3_32_fixed().hashString(tmp, StandardCharsets.UTF_8).toString()
                        if (keyCache[searchText] == null) "multilang.${hash}" else "multilang.${keyCache[searchText]}"
                    }
                    // 判断中文是否被单引号或双引号包裹
                    var start = it.startOffset()
                    var end = it.endOffset()
                    val quotedString = it.quotedString(it.startOffset(), it.endOffset())
                    if (quotedString) {
                        start -= 1
                        end += 1
                    }
                    var replaceText = "i18n('${codeResKey}')/*${searchText}*/"
                    val equalsSing = it.document.getString(start - 1, start).equals("=")
                    if (!quotedString || equalsSing) {
                        // 不是字符串包裹的中文或在中文首字母-2的位置为=号
                        replaceText = "{${replaceText}}"
                    }
                    WriteCommandAction.runWriteCommandAction(event.project) {
                        it.document.replaceString(start, end, replaceText)
                        val csvExist = csvData.any { f -> f.split(",")[1] == searchText }
                        if (!csvExist && !codeResKey.startsWith("common.")) {
                            csvData.add("${codeResKey.replace("multilang.", "")},${searchText},${translateText}")
                            keyCache[searchText] = codeResKey.replace("multilang.", "")
                        }
                    }
                }
                writeCsv(event, csvData)
            }
        } catch (e: Exception) {
            e.printStackTrace()
            logger.error(e)
            GitCmd.log(project, e.stackTraceToString())
            GitCmd.log(project, ExceptionUtils.getRootCauseMessage(e))
        }
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
}
