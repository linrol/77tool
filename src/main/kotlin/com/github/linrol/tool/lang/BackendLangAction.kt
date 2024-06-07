package com.github.linrol.tool.lang

import com.github.linrol.tool.model.GitCmd
import com.github.linrol.tool.utils.*
import com.google.common.hash.Hashing
import com.google.gson.GsonBuilder
import com.google.gson.reflect.TypeToken
import com.intellij.json.JsonFileType
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.command.WriteCommandAction
import com.intellij.openapi.diagnostic.logger
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.progress.ProgressIndicator
import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.usages.Usage
import com.intellij.usages.UsageInfo2UsageAdapter
import com.jetbrains.rd.util.first
import com.opencsv.*
import git4idea.repo.GitRepositoryManager
import org.apache.commons.lang3.exception.ExceptionUtils
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.nio.charset.StandardCharsets
import java.nio.file.Files
import java.nio.file.Paths
import java.util.*

class BackendLangAction : AbstractLangAction() {

    companion object {
        private val logger = logger<BackendLangAction>()
    }

    data class Code(val resPath: String,val resKey: String, val segment: String, val isTypeJava: Boolean)

    override fun actionPerformed(event: AnActionEvent) {
        val project = event.project ?: return
        try {
            when (event.place) { // ProjectViewPopup EditorPopup
                "EditorPopup" -> editorSelectedProcessor(event, project)  // 代码中选中的文本翻译
                "ProjectViewPopup" -> csvTranslateProcessor(event, project)  // 对csv文件整体翻译没有被翻译的中文
                "UsageViewPopup" -> async(project) { searchProcessor(event, project) } // 对搜索结果中的中文翻译
            }
        } catch (e: Exception) {
            e.printStackTrace()
            logger.error(e)
            GitCmd.log(project, e.stackTraceToString())
            GitCmd.log(project, ExceptionUtils.getRootCauseMessage(e))
        }
    }

    private fun editorSelectedProcessor(event: AnActionEvent, project: Project) {
        val editor: Editor = event.dataContext.getData("editor") as? Editor ?: return
        val virtualFile = event.getData(CommonDataKeys.VIRTUAL_FILE) ?: return
        val selectedText = editor.selectionModel.selectedText ?: return
        // 翻译
        val translateText: String = LangTranslater(project).printUse().translate(selectedText)
        if (selectedText == translateText) {
            return
        }
        val code = generateCode(project, virtualFile, selectedText, translateText) ?: return
        var start = editor.caretModel.currentCaret.selectionStart
        var end = editor.caretModel.currentCaret.selectionEnd
        // 判断中文是否被单引号或双引号包裹
        val wrappedInQuote = editor.document.wrappedInQuote(start, end)
        if (wrappedInQuote && code.isTypeJava) {
            start -= 1
            end += 1
        }
        WriteCommandAction.runWriteCommandAction(event.project) {
            appendResJson(code.resPath, code.resKey, selectedText)
            editor.document.replaceString(start, end, code.segment)
        }
    }

    private fun searchProcessor(event: AnActionEvent, project: Project) {
        val usages: Array<Usage> = getUsages(event)
        if (usages.isEmpty()) {
            return
        }
        // 翻译
        val translater = LangTranslater(project).printUse()
        usages.filterIsInstance<UsageInfo2UsageAdapter>().forEach {
            val searchText = it.searchText() ?: return@forEach
            // 翻译
            val translateText: String = translater.translate(searchText)
            if (searchText == translateText) {
                return@forEach
            }
            // 判断搜索结果中被翻译的内容是否被单引号或双引号包裹
            val wrappedInQuote = it.document.wrappedInQuote(it.startOffset(), it.endOffset())
            if (!wrappedInQuote) {
                logger.error("翻译的内容:${searchText}不是一个字符串")
                return@forEach
            }
            val code = generateCode(project, it.file, searchText, translateText) ?: return
            val start = if (code.isTypeJava) (it.startOffset() - 1) else it.startOffset()
            val end = if (code.isTypeJava) (it.endOffset() + 1) else it.endOffset()
            WriteCommandAction.runWriteCommandAction(event.project) {
                appendResJson(code.resPath, code.resKey, searchText)
                it.document.replaceString(start, end, code.segment)
            }
        }
    }

    private fun csvTranslateProcessor(event: AnActionEvent, project: Project) {
        val virtualFile = event.getData(CommonDataKeys.VIRTUAL_FILE)

        if (virtualFile == null || !virtualFile.name.endsWith(".csv")) {
            GitCmd.log(project, "选中的文件不是.csv文件，请重新选择")
            return
        }
        async(project) { indicator ->
            updateCsvFile(project, indicator, virtualFile, LangTranslater(project).printUse())
        }
    }

    private fun updateCsvFile(project: Project, indicator: ProgressIndicator, file: VirtualFile, translater: LangTranslater) {
        val inputStream = file.inputStream
        val outputStream = file.getOutputStream(this)
        val csvParser = RFC4180ParserBuilder().build()
        val reader = CSVReaderBuilder(InputStreamReader(inputStream)).withCSVParser(csvParser).build()
        val writer = CSVWriter(OutputStreamWriter(outputStream))
        var line: Array<String>?

        try {
            // 读取 CSV 文件头（假设有头）
            val header = reader.readNext()
            writer.writeNext(header)

            // 遍历文件每一行，进行更新
            while (reader.readNext().also { line = it } != null) {
                if (indicator.isCanceled) {
                    GitCmd.log(project, "多语翻译任务终止")
                    return
                }
                val id = line!![0]
                val chinese = line!![2]
                val english = line!![1]
                val updatedEnglish = english.ifBlank { WordCapitalizeUtils.apply(id, chinese, translater.translate(chinese))/* 更新英文列 */ }
                // 写入更新后的行数据
                val updatedLine = arrayOf(id, updatedEnglish, chinese)
                writer.writeNext(updatedLine)
            }
        } catch (e: Exception) {
            e.printStackTrace()
        } finally {
            WriteCommandAction.runWriteCommandAction(project) {
                try {
                    reader.close()
                    writer.close()
                } catch (e: Exception) {
                    e.printStackTrace()
                }
            }
        }
    }

    private fun appendResJson(path: String, key: String, value: String) {
        val virtualFile = LocalFileSystem.getInstance().findFileByPath("${path}/src/main/resources/string-res.json")
        if (virtualFile == null || virtualFile.fileType !is JsonFileType) {
            logger.error("string-res.json文件未找到或不是json类型的文件")
            return
        }
        val file = Paths.get(virtualFile.path)
        val gson = GsonBuilder().setPrettyPrinting().create()
        val map: MutableMap<String, String> = gson.fromJson<MutableMap<String, String>?>(Files.readString(file), object : TypeToken<MutableMap<String, Any>>() {}.type).apply {
            put(key, value)
        }
        val toJson = gson.toJson(map)
        Files.write(file, toJson.toByteArray(StandardCharsets.UTF_8))
    }

    private fun getResData(path: String): MutableMap<String, String> {
        val virtualFile = LocalFileSystem.getInstance().findFileByPath("${path}/src/main/resources/string-res.json")
        if (virtualFile == null || virtualFile.fileType !is JsonFileType) {
            logger.error("string-res.json文件未找到或不是json类型的文件")
            return mutableMapOf()
        }
        val file = Paths.get(virtualFile.path)
        val gson = GsonBuilder().setPrettyPrinting().create()
        return gson.fromJson(Files.readString(file), object : TypeToken<MutableMap<String, Any>>() {}.type)
    }

    private fun generateCode(project:Project, virtualFile: VirtualFile, chineseText: String, englishText: String): Code? {
        val repository = GitRepositoryManager.getInstance(project).getRepositoryForFileQuick(virtualFile) ?: return null
        val resPath = repository.root.path.replace("-api", "")
        val moduleName = repository.root.name.replace("-api", "")
        val csvData = getResData(resPath)
        // 准备替换内容
        val variable = if (csvData.containsValue(chineseText)) {
            csvData.filter { f -> f.value == chineseText }.first().key.replace(".", "_").uppercase(Locale.getDefault())
        } else {
            english2UpperSnakeCase(englishText)
        }
        val isTypeJson = virtualFile.extension == "json"
        val resKey = variable.replace("_", ".").lowercase()
        val segment = if (isTypeJson) {
            "\$str.${moduleName}\$${resKey}"
        } else {
            "StrResUtils.getCurrentAppStr(StrResConstants.${variable})"
        }
        return Code(resPath, resKey, segment, !isTypeJson)
    }

    private fun english2UpperSnakeCase(text: String): String {
        return (if (text.contains("%s") || text.length > 64) {
            "message template ${Hashing.murmur3_32_fixed().hashString(text, StandardCharsets.UTF_8)}"
        } else {
            text
        }).replace(Regex("[^a-zA-Z1-9\\s]"), "")
          .replace(Regex("\\s+"), "_")
          .replace(Regex("_$"), "")
          .uppercase(Locale.getDefault())
    }
}