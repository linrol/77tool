package com.github.linrol.tool.utils

import com.github.linrol.tool.model.GitCmd
import com.github.linrol.tool.state.ToolSettingsState
import com.google.gson.JsonParser
import com.intellij.openapi.diagnostic.logger
import com.intellij.openapi.project.Project
import okhttp3.OkHttpClient
import okhttp3.Request
import org.apache.poi.ss.usermodel.WorkbookFactory
import java.io.File
import java.io.FileOutputStream
import java.nio.file.Files

class ShimApi(val project: Project) {
    private fun export(uid: String): String? {
        val sid = ToolSettingsState.instance.shimoSid
        val url = "https://shimo.im/lizard-api/office-gw/files/export?fileGuid=${uid}"
        val client = OkHttpClient()
        val request = Request.Builder().url(url)
            .addHeader("referer", "https://shimo.im/desktop")
            .addHeader("Cookie", "shimo_sid=${sid}")
            .get().build()
        return client.newCall(request).execute().let {
            if (it.isSuccessful) {
                val response = JsonParser.parseString(it.body().string()).asJsonObject
                response.get("taskId").asString
            } else {
                logger.info("Response Error: ${it.code()} - ${it.message()}")
                GitCmd.log(project, "石墨 api 请求错误: ${it.message()}，请检查Setting->77tool->shimo_sid的配置")
                null
            }
        }
    }

    /**
     * 获取石墨文档下载地址
     */
    private fun getExportDownloadUrl(uid: String): String? {
        val taskId = export(uid) ?: return null
        val sid = "s%3A9e1d2ddd1970404b81e4fcf2b7182aed.gzbpB8BH75NkR7W87Tz1FKrR67A4L20vrkQgbcrGTHA"
        val url = "https://shimo.im/lizard-api/office-gw/files/export/progress?taskId=$taskId"
        val client = OkHttpClient()
        val request = Request.Builder().url(url)
            .addHeader("referer", "https://shimo.im/desktop")
            .addHeader("Cookie", "shimo_sid=${sid}")
            .get().build()
        return client.newCall(request).execute().let {
            if (it.isSuccessful) {
                val response = JsonParser.parseString(it.body().string()).asJsonObject
                val progress = response.getAsJsonObject("data").get("progress").asInt
                if (progress != 100) {
                    Thread.sleep(1000)
                    return getExportDownloadUrl(taskId)
                }
                return response.getAsJsonObject("data").get("downloadUrl").asString
            } else {
                GitCmd.log(project, "石墨 api 请求错误: ${it.message()}，请检查Setting->77tool->shimo_sid的配置")
                null
            }
        }
    }

    fun getText(uid: String): List<Map<String, String>> {
        val exportDownloadUrl = getExportDownloadUrl(uid) ?: return emptyList()

        // 创建请求对象
        val request = Request.Builder().url(exportDownloadUrl).build()
        val client = OkHttpClient()

        // 发送请求并获取响应
        client.newCall(request).execute().let { response ->
            if (!response.isSuccessful) {
                return emptyList()
            }
            val body = response.body() ?: return emptyList()
            val tempFile: File = Files.createTempFile("tempFile", ".xlsx").toFile()
            val fos = FileOutputStream(tempFile)
            fos.use { output ->
                body.byteStream().use { input ->
                    input.copyTo(output)
                }
            }
            return toJson(tempFile)
        }
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