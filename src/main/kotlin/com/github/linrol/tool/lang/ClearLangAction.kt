package com.github.linrol.tool.lang

import com.github.linrol.tool.model.GitCmd
import com.github.linrol.tool.state.ToolSettingsState
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
import kotlinx.coroutines.asCoroutineDispatcher
import org.apache.commons.lang3.exception.ExceptionUtils
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.nio.charset.StandardCharsets
import java.nio.file.Files
import java.nio.file.Paths
import java.util.*
import java.util.concurrent.Executors
import kotlinx.coroutines.*
import java.util.concurrent.atomic.AtomicInteger

class ClearLangAction : AbstractLangAction() {

    companion object {
        private val logger = logger<ClearLangAction>()
    }

    override fun actionPerformed(event: AnActionEvent) {
        val project = event.project ?: return
        try {
            csvTranslateProcessor(event, project)  // 对csv文件整体翻译没有被翻译的中文
        } catch (e: Exception) {
            e.printStackTrace()
            logger.error(e)
            GitCmd.log(project, e.stackTraceToString())
            GitCmd.log(project, ExceptionUtils.getRootCauseMessage(e))
        }
    }


    private fun csvTranslateProcessor(event: AnActionEvent, project: Project) {
        val virtualFile = event.getData(CommonDataKeys.VIRTUAL_FILE) ?: return
        if (!virtualFile.name.endsWith(".csv") && !virtualFile.isDirectory) {
            GitCmd.log(project, "选中的文件不是.csv文件，请重新选择")
        }

        async(project) { indicator ->
            if (virtualFile.isDirectory) {
                processDirectory(project, indicator, virtualFile)
            } else {
                updateCsvFile(project, virtualFile)
            }
        }
    }

    private fun processDirectory(project: Project, indicator: ProgressIndicator, directory: VirtualFile) {
        val files = directory.children
        for (file in files) {
            if (file.isDirectory) {
                // 递归处理子目录
                processDirectory(project, indicator, file)
            } else if (file.name.endsWith(".csv")) {
                // 处理 CSV 文件
                updateCsvFile(project, file)
            }
        }
    }

    private fun updateCsvFile(project: Project, file: VirtualFile) {
        val inputStream = file.inputStream
        val outputStream = file.getOutputStream(this)
        val csvParser = RFC4180ParserBuilder().build()
        val reader = CSVReaderBuilder(InputStreamReader(inputStream, StandardCharsets.UTF_8)).withCSVParser(csvParser).build()
        val writer = CSVWriter(OutputStreamWriter(outputStream, StandardCharsets.UTF_8))
        var line: Array<String>?

        try {
            // 读取 CSV 文件头（假设有头）
            val header = reader.readNext()
            val allLine = Collections.synchronizedList(mutableListOf<Array<String>>())
            allLine.add(header)
            // 遍历文件每一行，进行更新
            while (reader.readNext().also { line = it } != null) {
                val id = line!![0]
                val chinese = line!![1]
                if (id.isEmpty() || chinese.isEmpty()) {
                    continue
                }
                // 写入更新后的行数据
                allLine.add(arrayOf(id, chinese, ""))
            }
            writer.writeAll(allLine)
            GitCmd.log(project, "文件:${file.name}清除多语翻译完成")
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
}