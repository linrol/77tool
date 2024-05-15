package com.github.linrol.tool.lang

import com.github.linrol.tool.model.GitCmd
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.command.WriteCommandAction
import com.intellij.openapi.diagnostic.logger
import com.intellij.openapi.editor.Editor
import com.intellij.openapi.project.DumbAwareAction
import com.intellij.openapi.vfs.VirtualFile
import com.opencsv.*
import org.apache.commons.lang3.exception.ExceptionUtils
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.util.*

class BackendLangAction : DumbAwareAction() {

    companion object {
        private val logger = logger<BackendLangAction>()
    }

    override fun actionPerformed(event: AnActionEvent) {
        val project = event.project ?: return
        try {
            val place = event.place // ProjectViewPopup EditorPopup
            if (place == "EditorPopup") {
                // 代码中选中的文本翻译
                editorSelectedProcessor(event)
            }
            if (place == "ProjectViewPopup") {
                // 对csv文件整体翻译没有被翻译的中文
                csvTranslateProcessor(event)
            }
        } catch (e: Exception) {
            e.printStackTrace()
            logger.error(e)
            GitCmd.log(project, e.stackTraceToString())
            GitCmd.log(project, ExceptionUtils.getRootCauseMessage(e))
        }
    }

    private fun editorSelectedProcessor(event: AnActionEvent) {
        val editor: Editor = event.dataContext.getData("editor") as? Editor ?: return
        val document = editor.document
        val selectedText = editor.selectionModel.selectedText ?: return
        // 翻译
        val translater = LangTranslater()
        if (translater.canProxy) {
            GitCmd.log(event.project!!, "使用谷歌翻译")
        } else {
            GitCmd.log(event.project!!, "使用百度翻译")
        }
        val translateText: String = translater.translate(selectedText)
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

    private fun csvTranslateProcessor(event: AnActionEvent) {
        val project = event.project!!
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
                val updatedEnglish = if (english.isNullOrBlank()) {
                    translater.translate(chinese)   // 更新英文列
                } else {
                    english
                }
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
}