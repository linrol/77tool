package com.github.linrol.tool.utils

import com.github.linrol.tool.state.ToolSettingsState
import com.google.gson.JsonParser
import com.intellij.openapi.diagnostic.logger
import com.intellij.openapi.project.Project
import okhttp3.Headers
import org.apache.poi.ss.usermodel.WorkbookFactory
import java.io.File
import java.io.FileOutputStream
import java.nio.file.Files

class ShimApi(val project: Project) {

    private val sid = ToolSettingsState.instance.shimoSid
    private val headers: Headers = Headers.Builder().add("referer", "https://shimo.im/desktop").add("Cookie", "shimo_sid=${sid}").build()

    private fun export(uid: String): String? {
        val url = "https://shimo.im/lizard-api/office-gw/files/export?fileGuid=${uid}"
        return runCatching {
            OkHttpClientUtils().get(url, headers) {
                val response = JsonParser.parseString(it.string()).asJsonObject
                response.get("taskId").asString
            }
        }.getOrNull()
    }

    /**
     * 获取石墨文档下载地址
     */
    private fun getExportDownloadUrl(uid: String): String? {
        val taskId = export(uid) ?: return null
        val url = "https://shimo.im/lizard-api/office-gw/files/export/progress?taskId=$taskId"
        return runCatching {
            OkHttpClientUtils().get(url, headers) {
                val response = JsonParser.parseString(it.string()).asJsonObject
                val progress = response.getAsJsonObject("data").get("progress").asInt
                if (progress != 100) {
                    Thread.sleep(1000)
                    getExportDownloadUrl(taskId)
                }
                response.getAsJsonObject("data").get("downloadUrl").asString
            }
        }.getOrNull()
    }

    fun getText(uid: String): List<Map<String, String>> {
        val downloadUrl = getExportDownloadUrl(uid) ?: return emptyList()
        return runCatching {
            OkHttpClientUtils().get(downloadUrl) {
                val tempFile: File = Files.createTempFile("tempFile", ".xlsx").toFile()
                val fos = FileOutputStream(tempFile)
                fos.use { output ->
                    it.byteStream().use { input ->
                        input.copyTo(output)
                    }
                }
                return@get toJson(tempFile)
            }
        }.getOrElse { emptyList() }
    }

    private fun toJson(file: File): List<Map<String, String>> {
        val workbook = WorkbookFactory.create(file)
        val sheet = workbook.getSheetAt(0)

        val headerRow = sheet.getRow(0)
        val headers = mutableListOf<String>()
        for (cell in headerRow) {
            headers.add(cell.stringCellValue)
        }
        val data = mutableListOf<Map<String, String>>()
        for (rowIndex in 1 until sheet.physicalNumberOfRows) {
            val row = sheet.getRow(rowIndex)
            val rowMap = mutableMapOf<String, String>()
            for (cellIndex in headers.indices) {
                val cell = row.getCell(cellIndex) ?: continue
                val key = headers[cellIndex]
                val value = cell.stringCellValue
                rowMap[key] = value
            }
            data.add(rowMap)
        }
        workbook.close()
        return data
    }


    companion object {
        private val logger = logger<ShimApi>()
    }
}