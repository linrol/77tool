package com.github.linrol.tool.lang

import com.github.linrol.tool.base.AbstractDumbAction
import com.github.linrol.tool.model.GitCmd
import com.github.linrol.tool.state.ToolSettingsState
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.command.WriteCommandAction
import com.intellij.openapi.progress.ProgressIndicator
import com.intellij.openapi.progress.ProgressManager
import com.intellij.openapi.progress.Task
import com.intellij.openapi.project.Project
import com.intellij.openapi.vfs.VirtualFile
import com.intellij.usages.Usage
import com.intellij.usages.UsageView
import com.opencsv.CSVReaderBuilder
import com.opencsv.CSVWriter
import com.opencsv.RFC4180ParserBuilder
import kotlinx.coroutines.*
import java.io.InputStreamReader
import java.io.OutputStreamWriter
import java.lang.Runnable
import java.nio.charset.StandardCharsets
import java.util.*
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicInteger

abstract class AbstractLangAction : AbstractDumbAction() {

    fun getUsages(event: AnActionEvent): Array<Usage> {
        event.getData(UsageView.USAGE_VIEW_KEY) ?: return Usage.EMPTY_ARRAY
        return event.getData(UsageView.USAGES_KEY) ?: Usage.EMPTY_ARRAY
    }

    fun async(project: Project, runnable: Runnable) {
        ProgressManager.getInstance().run(object : Task.Backgroundable(project, "多语翻译中"){
            override fun run(indicator: ProgressIndicator) {
                runnable.run()
            }
        })
    }

    fun async(project: Project, runnable: (ProgressIndicator) -> Unit) {
        ProgressManager.getInstance().run(object : Task.Backgroundable(project, "多语翻译中"){
            override fun run(indicator: ProgressIndicator) {
                runnable.invoke(indicator)
            }
        })
    }

    fun projectViewProcess(event: AnActionEvent, project: Project) {
        val virtualFile = event.getData(CommonDataKeys.VIRTUAL_FILE) ?: return
        if (!virtualFile.name.endsWith(".csv") && !virtualFile.isDirectory) {
            GitCmd.log(project, "当前选中不是目录或.csv文件，请重新选择")
        }

        async(project) { indicator ->
            fileTranslate(project, indicator, virtualFile)
        }
    }

    private fun fileTranslate(project: Project, indicator: ProgressIndicator, virtualFile: VirtualFile) {
        if (!virtualFile.isDirectory && virtualFile.name.endsWith(".csv")) {
            // 是一个csv文件
            csvBatchTranslate(project, indicator, virtualFile)
        } else {
            // 递归处理子目录
            virtualFile.children.forEach { children ->
                fileTranslate(project, indicator, children)
            }
        }
    }

    private fun csvBatchTranslate(project: Project, indicator: ProgressIndicator, file: VirtualFile) {
        val batchNum = 100
        val count = csvTranslate(project, indicator, file, LangTranslater(project).printUse().batch(), batchNum)
        if (count > batchNum) {
            csvBatchTranslate(project, indicator, file)
        }
    }

    private fun csvTranslate(project: Project, indicator: ProgressIndicator, file: VirtualFile, translater: LangTranslater, batchNum: Int): Int {
        val inputStream = file.inputStream
        val outputStream = file.getOutputStream(this)
        val csvParser = RFC4180ParserBuilder().build()
        val reader = CSVReaderBuilder(InputStreamReader(inputStream, StandardCharsets.UTF_8)).withCSVParser(csvParser).build()
        val writer = CSVWriter(OutputStreamWriter(outputStream, StandardCharsets.UTF_8))
        var line: Array<String>?

        val jobs = mutableListOf<Deferred<Array<String>>>()
        val count = AtomicInteger(0)
        val nThreads = ToolSettingsState.instance.nThreads.toIntOrNull() ?: 1
        val dispatcher = Executors.newFixedThreadPool(nThreads).asCoroutineDispatcher()
        try {
            // 读取 CSV 文件头（假设有头）
            val header = reader.readNext()
            val headerMap = header.mapIndexed { index, title -> title to index }.toMap()
            val allLine = Collections.synchronizedList(mutableListOf<Array<String>>())
            allLine.add(header)
            // 遍历文件每一行，进行更新
            while (reader.readNext().also { line = it } != null) {
                val row  = line!!
                val deferred = CoroutineScope(Dispatchers.Default).async(dispatcher) {
                    if (indicator.isCanceled || count.get() >= batchNum) {
                        return@async row
                    } else {
                        return@async rowTranslateAsync(headerMap, row, translater, count)
                    }
                }
                jobs.add(deferred)
            }
            runBlocking {
                jobs.forEach { job ->
                    allLine.add(job.await()) //获取异步任务的结果
                }
            }
            writer.writeAll(allLine)
            if (indicator.isCanceled) GitCmd.log(project, "多语翻译任务被终止")
            GitCmd.log(project, "本批次总共翻译：${count.get()}条")
            return count.get()
        } catch (e: Exception) {
            e.printStackTrace()
            return count.get()
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

    open fun rowTranslateAsync(header: Map<String, Int>, row: Array<String>, translater: LangTranslater, count: AtomicInteger): Array<String> {
        return row
    }
}