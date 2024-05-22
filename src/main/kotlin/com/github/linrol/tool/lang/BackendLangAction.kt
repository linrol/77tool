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
        val repository = GitRepositoryManager.getInstance(project).getRepositoryForFileQuick(virtualFile)?: return
        val rootPath = repository.root.path
        val variable = generateVariable(rootPath, selectedText, translateText)
        val replaceText = "StrResUtils.getCurrentAppStr(StrResConstants.${variable})"
        var start = editor.caretModel.currentCaret.selectionStart
        var end = editor.caretModel.currentCaret.selectionEnd
        // 判断中文是否被单引号或双引号包裹
        val wrappedInQuote = editor.document.wrappedInQuote(start, end)
        if (wrappedInQuote) {
            start -= 1
            end += 1
        }
        WriteCommandAction.runWriteCommandAction(event.project) {
            editor.document.replaceString(start, end, replaceText)
            val key = variable.replace("_", ".").lowercase()
            appendResJson(rootPath, key, selectedText)
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
            val repository = GitRepositoryManager.getInstance(project).getRepositoryForFileQuick(it.file) ?: return@forEach
            val rootPath = repository.root.path
            val variable = generateVariable(rootPath, searchText, translateText)
            val replaceText = "StrResUtils.getCurrentAppStr(StrResConstants.${variable})"
            // 判断中文是否被单引号或双引号包裹
            val wrappedInQuote = it.document.wrappedInQuote(it.startOffset(), it.endOffset())
            if (!wrappedInQuote) {
                logger.error("翻译的内容:${searchText}不是一个字符串")
                return@forEach
            }
            val start = it.startOffset() - 1
            val end = it.endOffset() + 1
            WriteCommandAction.runWriteCommandAction(event.project) {
                it.document.replaceString(start, end, replaceText)
                val key = variable.replace("_", ".").lowercase()
                appendResJson(rootPath, key, searchText)
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
                val updatedEnglish = english.ifBlank { translater.translate(chinese)/* 更新英文列 */ }
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

    private fun generateVariable (path: String, chineseText: String, englishText: String): String {
        val csvData = getResData(path)
        // 准备替换内容
        return if (csvData.containsValue(chineseText)) {
            csvData.filter { f -> f.value == chineseText }.first().key.replace(".", "_").uppercase(Locale.getDefault())
        } else {
            english2UpperSnakeCase(englishText)
        }
    }

    private fun english2UpperSnakeCase(text: String): String {
        return (if (text.contains("%s") || text.length > 128) {
            "message template ${Hashing.murmur3_32_fixed().hashString(text, StandardCharsets.UTF_8)}"
        } else {
            text
        }).replace(Regex("[^a-zA-Z\\s]"), "").replace(Regex("\\s+"), "_").uppercase(Locale.getDefault())
    }
}