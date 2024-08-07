package com.github.linrol.tool.lang

import com.github.linrol.tool.model.GitCmd
import com.github.linrol.tool.utils.*
import com.google.common.hash.Hashing
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.command.WriteCommandAction
import com.intellij.openapi.diagnostic.logger
import com.intellij.openapi.project.Project
import com.intellij.usages.Usage
import com.intellij.usages.UsageInfo2UsageAdapter
import org.apache.commons.lang3.exception.ExceptionUtils
import java.nio.charset.StandardCharsets
import java.nio.file.Files
import java.nio.file.Paths
import java.util.concurrent.atomic.AtomicInteger

class FrontLangAction : AbstractLangAction() {

    companion object {
        private val logger = logger<FrontLangAction>()
    }

    override fun update(e: AnActionEvent) {
        val project = e.project ?: return
        val front = GitLabUtil.getRepositories(project).any { it.remotes.first()?.firstUrl?.contains("front") ?: false }
        val backend = GitLabUtil.getRepositories(project).any { it.remotes.first()?.firstUrl?.contains("backend") ?: false }
        if (!(front or backend)) {
            e.presentation.isEnabledAndVisible = true
        } else {
            e.presentation.isEnabledAndVisible = front
        }
    }

    override fun actionPerformed(event: AnActionEvent) {
        val project = event.project ?: return
        try {
            when (event.place) { // ProjectViewPopup EditorPopup
                "ProjectViewPopup" -> projectViewProcess(event, project)  // 对目录下的csv文件或选中的csv文件整体翻译没有被翻译的中文
                "UsageViewPopup" -> async(project) { searchProcessor(event, project) } // 对搜索结果中的中文翻译
            }
        } catch (e: Exception) {
            e.printStackTrace()
            logger.error(e)
            GitCmd.log(project, e.stackTraceToString())
            GitCmd.log(project, ExceptionUtils.getRootCauseMessage(e))
        }
    }

    private fun searchProcessor(event: AnActionEvent, project: Project) {
        val usages: Array<Usage> = getUsages(event)
        if(usages.isEmpty()) {
            return
        }
        try {
            val exist = ShimApi(project).getText("5rk9KBxvZQH78g3x")
            val csvData = mutableListOf<String>()
            val keyCache = mutableMapOf<String, String>()
            val translater = LangTranslater(project).printUse()
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
                val wrappedInQuote = it.document.wrappedInQuote(it.startOffset(), it.endOffset())
                if (wrappedInQuote) {
                    start -= 1
                    end += 1
                }
                var replaceText = "i18n('${codeResKey}')/*${searchText}*/"
                val equalsSing = it.document.getString(start - 1, start).equals("=")
                if (!wrappedInQuote || equalsSing) {
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

    override fun rowTranslateAsync(header: Map<String, Int>, row: Array<String>, translater: LangTranslater, count: AtomicInteger): Array<String> {
        val idIdx = header.getOrDefault("reskey", header["resKey"]) ?: return row
        val chineseIdx = header["zh-ch"] ?: return row
        val englishIdx = header["en"] ?: return row

        val rowList = row.toMutableList()
        val id = row.getOrNull(idIdx); val chinese = row.getOrNull(chineseIdx); val english = row.getOrElse(englishIdx) {""}
        if (english.isNotBlank()) return row
        if (id.isNullOrBlank() && chinese.isNullOrBlank()) return arrayOf()
        if (id.isNullOrBlank() || chinese.isNullOrBlank()) return row

        val supressIndex = header.getOrDefault("supressTrans", -1)
        val supress = supressIndex != -1 && row.getOrElse(supressIndex) {""} == "true"
        if (supress) return row

        val updateEnglish = translater.translateFixed(chinese).let {
            if (it.isNotEmpty()) count.incrementAndGet()
            WordCapitalizeUtils.apply(id, chinese, it)/* 翻译后的英文处理大小写 */
        }
        return rowList.apply { add(englishIdx, updateEnglish) }.toTypedArray()
    }
}
