package com.github.linrol.tool.lang

import com.github.linrol.tool.model.GitCmd
import com.google.gson.GsonBuilder
import com.google.gson.reflect.TypeToken
import com.intellij.json.JsonFileType
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.command.WriteCommandAction
import com.intellij.openapi.diagnostic.logger
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.progress.EmptyProgressIndicator
import com.intellij.openapi.progress.ProgressIndicator
import com.intellij.openapi.progress.ProgressManager
import com.intellij.openapi.progress.Task
import com.intellij.openapi.project.DumbAwareAction
import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.LocalFileSystem
import com.intellij.openapi.vfs.VirtualFile
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

class BackendLangAction : DumbAwareAction() {

    companion object {
        private val logger = logger<BackendLangAction>()
    }

    override fun actionPerformed(event: AnActionEvent) {
        val project = event.project ?: return
        try {
            async(project) {
                when (event.place) { // ProjectViewPopup EditorPopup
                    "EditorPopup" -> editorSelectedProcessor(event, project)  // 代码中选中的文本翻译
                    "ProjectViewPopup" -> csvTranslateProcessor(event, project)  // 对csv文件整体翻译没有被翻译的中文
                }
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
        val document = editor.document
        val selectedText = editor.selectionModel.selectedText ?: return
        // 翻译
        val translater = LangTranslater()
        if (translater.canProxy) {
            GitCmd.log(project, "使用谷歌翻译")
        } else {
            GitCmd.log(project, "使用百度翻译")
        }
        val translateText: String = translater.translate(selectedText)
        if (selectedText == translateText) {
            return
        }
        val repository = GitRepositoryManager.getInstance(project).getRepositoryForFileQuick(virtualFile)?: return
        val modulePath = repository.root.path
        val csvData = getCsvData(modulePath)
        // 准备替换内容
        val resourceKey = if (csvData.containsValue(selectedText)) {
            csvData.filter { f -> f.value == selectedText }.first().key.replace(".", "_").uppercase(Locale.getDefault())
        } else {
            val toRemove = setOf('-', ',', '，', '。', '.', '!', '！')
            translateText.filterNot { it in toRemove }.replace(" ", "_").uppercase(Locale.getDefault())
        }
        val replaceText = "StrResUtils.getCurrentAppStr(StrResConstants.${resourceKey})"
        val documentText = document.text
        val newText = documentText.replace("\"${selectedText}\"", replaceText)
        WriteCommandAction.runWriteCommandAction(event.project) {
            document.setText(newText)
            val key = resourceKey.replace("_", ".").lowercase()
            appendResJson(modulePath, Pair(key, selectedText))
        }
    }

    private fun csvTranslateProcessor(event: AnActionEvent, project: Project) {
        val virtualFile = event.getData(CommonDataKeys.VIRTUAL_FILE)

        if (virtualFile == null || !virtualFile.name.endsWith(".csv")) {
            GitCmd.log(project, "选中的文件不是.csv文件，请重新选择")
            return
        }
        val translater = LangTranslater()
        if (translater.canProxy) {
            GitCmd.log(project, "使用谷歌翻译")
        } else {
            GitCmd.log(project, "使用百度翻译")
        }
        WriteCommandAction.runWriteCommandAction(event.project) {
            updateCsvFile(virtualFile, translater)
        }
    }

    private fun updateCsvFile(file: VirtualFile, translater: LangTranslater) {
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
            try {
                reader.close()
                writer.close()
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    private fun appendResJson(path: String, entry: Pair<String, String>) {
        val virtualFile = LocalFileSystem.getInstance().findFileByPath("${path}/src/main/resources/string-res.json")
        if (virtualFile == null || virtualFile.fileType !is JsonFileType) {
            logger.error("string-res.json文件未找到或不是json类型的文件")
            return
        }
        val file = Paths.get(virtualFile.path)
        val gson = GsonBuilder().setPrettyPrinting().create()
        val map: MutableMap<String, String> = gson.fromJson<MutableMap<String, String>?>(Files.readString(file), object : TypeToken<MutableMap<String, Any>>() {}.type).apply {
            put(entry.first, entry.second)
        }
        val toJson = gson.toJson(map)
        Files.write(file, toJson.toByteArray(StandardCharsets.UTF_8))
    }

    private fun getCsvData(path: String): MutableMap<String, String> {
        val virtualFile = LocalFileSystem.getInstance().findFileByPath("${path}/src/main/resources/string-res.json")
        if (virtualFile == null || virtualFile.fileType !is JsonFileType) {
            logger.error("string-res.json文件未找到或不是json类型的文件")
            return mutableMapOf()
        }
        val file = Paths.get(virtualFile.path)
        val gson = GsonBuilder().setPrettyPrinting().create()
        return gson.fromJson(Files.readString(file), object : TypeToken<MutableMap<String, Any>>() {}.type)
    }

    private fun async(project: Project, runnable: Runnable) {
        ProgressManager.getInstance().runProcessWithProgressAsynchronously(object : Task.Backgroundable(project, "多语翻译中") {
            override fun run(indicator: ProgressIndicator) {
                runnable.run()
            }
        }, EmptyProgressIndicator())
    }
}