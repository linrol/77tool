package com.github.linrol.tool.lang

import com.github.linrol.tool.model.GitCmd
import com.github.linrol.tool.state.ToolSettingsState
import com.github.linrol.tool.utils.OkHttpClientUtils
import com.github.linrol.tool.utils.getValue
import com.google.gson.JsonParser
import com.intellij.openapi.diagnostic.logger
import com.intellij.openapi.project.Project
import okhttp3.Headers
import okhttp3.MediaType
import okhttp3.RequestBody
import java.util.concurrent.TimeUnit

class LangTranslater(val project: Project) {

    private val cache = mutableMapOf<String, String>()

    private var printUse = false

    private val canProxy = canProxy()

    companion object {
        private val logger = logger<FrontLangAction>()
    }

    fun translate(text: String): String {
        // 过滤除纯中文以外的内容
        val api = ToolSettingsState.instance.translaterApi
        return when {
            api == "baidu" -> translateUseBaidu(text)
            api == "chatgpt" -> translateUseChatgpt(text)
            api == "google" && canProxy -> translateUseGoogle(text)
            else -> translateUseBaidu(text)
        }
    }

    fun printUse(): LangTranslater {
        printUse = true
        return this
    }

    private fun translateUseGoogle(text: String): String {
        val key = "AIzaSyBuRCQkN72SAkmQ0CT3fK4mJIEg_ZCqUd8"
        val params = "q=${text}&source=zh&target=en&key=${key}"
        val url = "https://translation.googleapis.com/language/translate/v2?${params}"

        return runCatching {
            OkHttpClientUtils().get(url) {
                val translatedText = JsonParser.parseString(it.string()).getValue("data.translations[0].translatedText")
                return@get if (translatedText != null) {
                    if (printUse) GitCmd.log(project, "使用谷歌翻译【${text}】:【${translatedText.asString}】")
                    translatedText.asString.apply {
                        cache[text] = it.toString()
                    }
                } else {
                    logger.error(it.string())
                    translateUseBaidu(text)
                }
            }
        }.getOrElse { translateUseBaidu(text) }
    }

    private fun translateUseBaidu(text: String): String {
        Thread.sleep(13)
        val appId = "20240513002050659"
        val appKey = "Y6ZoTVT8oDBsF_MzBcIE"
        val salt = System.currentTimeMillis().toString()
        val sign = md5("$appId$text$salt$appKey")
        val params = "q=${text}&from=zh&to=en&appid=${appId}&salt=${salt}&sign=${sign}"
        val url = "https://api.fanyi.baidu.com/api/trans/vip/translate?${params}"

        return runCatching {
            return OkHttpClientUtils().get(url) {
                val dst = JsonParser.parseString(it.string()).getValue("trans_result[0].dst")
                return@get if (dst != null) {
                    if (printUse) GitCmd.log(project, "使用百度翻译【${text}】:【${dst.asString}】")
                    dst.asString.replaceFirstChar { char ->
                        if (char.isLowerCase()) char.titlecase() else char.toString()
                    }.apply {
                        cache[text] = it.toString()
                    }.replace("% s", "%s")
                } else {
                    logger.error(it.string())
                    GitCmd.log(project, it.toString())
                    text
                }
            }
        }.getOrElse { text }
    }

    private fun translateUseChatgpt(text: String): String {
        val url = "https://api.chatanywhere.tech/v1/chat/completions"
        val key = ToolSettingsState.instance.chatgptKey
        val headers: Headers = Headers.Builder().add("Content-Type", "application/json").add("Authorization", "Bearer $key").build()
        // 构建请求体
        val params = "{\"model\": \"gpt-3.5-turbo\",\"messages\": [{\"role\": \"user\",\"content\": \"翻译:${text}\"}]}"
        val request = RequestBody.create(MediaType.parse("application/json; charset=utf-8"), params)
        return runCatching {
            return OkHttpClientUtils().post(url, headers, request) {
                val content = JsonParser.parseString(it.string()).getValue("choices[0].message.content")
                return@post if (content != null) {
                    if (printUse) GitCmd.log(project, "使用chatgpt翻译【${text}】:【${content.asString}】")
                    content.asString.replace("\"", "").apply {
                        cache[text] = it.toString()
                    }
                } else {
                    logger.error(it.string())
                    GitCmd.log(project, it.string())
                    text
                }
            }
        }.getOrElse {
            it.message?.also { error ->
                GitCmd.log(project, error)
            }
            text
        }
    }

    private fun canProxy(): Boolean {
        return runCatching {
            val test = "https://translate.google.com/"
            OkHttpClientUtils().connectTimeout(1, TimeUnit.SECONDS).get(test) {
                true
            }
        }.getOrElse { false }
    }

    private fun md5(input: String): String {
        val md = java.security.MessageDigest.getInstance("MD5")
        val byteArray = input.toByteArray()
        val mdBytes = md.digest(byteArray)
        return mdBytes.joinToString("") { "%02x".format(it) }
    }
}