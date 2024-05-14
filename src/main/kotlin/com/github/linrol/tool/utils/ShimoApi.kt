package com.github.linrol.tool.utils

import com.google.gson.JsonParser
import com.intellij.openapi.diagnostic.logger
import okhttp3.OkHttpClient
import okhttp3.Request

class ShimoApi {
    private fun export(uid: String): String? {
        val url = "https://shimo.im/lizard-api/office-gw/files/export?fileGuid=${uid}"
        val client = OkHttpClient()
        val request = Request.Builder().url(url).get().build()
        return client.newCall(request).execute().let {
            if (it.isSuccessful) {
                val response = JsonParser.parseString(it.body().string()).asJsonObject
                response.get("taskId").asString
            } else {
                logger.info("Response Error: ${it.code()} - ${it.message()}")
                null
            }
        }
    }

    /**
     * 获取石墨文档下载地址
     */
    private fun getExportDownloadUrl(uid: String): String? {
        val taskId = export(uid) ?: return null
        val url = "https://shimo.im/lizard-api/office-gw/files/export/progress?taskId=$taskId"
        val client = OkHttpClient()
        val request = Request.Builder().url(url).get().build()
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
                null
            }
        }
    }

    companion object {
        private val logger = logger<ShimoApi>()
    }
}