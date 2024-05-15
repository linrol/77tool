package com.github.linrol.tool.lang

import com.github.linrol.tool.utils.OkHttpClientUtils
import com.google.gson.JsonParser
import com.intellij.openapi.diagnostic.logger
import java.util.concurrent.TimeUnit

class LangTranslater {

    private val cache = mutableMapOf<String, String>()

    val canProxy = canProxy()

    fun translate(text: String): String {
        return cache[text] ?: if (canProxy) {
            translateUseGoogle(text)
        } else {
            translateUseBaidu(text)
        }
    }

    private fun translateUseGoogle(text: String): String {
        val key = "AIzaSyBuRCQkN72SAkmQ0CT3fK4mJIEg_ZCqUd8"
        val params = "q=${text}&source=zh&target=en&key=${key}"
        val url = "https://translation.googleapis.com/language/translate/v2?${params}"

        return runCatching {
            OkHttpClientUtils().get(url) {
                val response = JsonParser.parseString(it.string()).asJsonObject
                val translateText = response.getAsJsonObject("data").getAsJsonArray("translations").get(0).asJsonObject.get("translatedText").asString
                cache[text] = translateText
                translateText
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
                val response = JsonParser.parseString(it.string()).asJsonObject ?: return@get text
                val transResult = response.getAsJsonArray("trans_result") ?: return@get text
                if (transResult.isEmpty) {
                    return@get text
                }
                val dst = transResult.get(0).asJsonObject.get("dst") ?: return@get text
                val translateText = dst.asString.replaceFirstChar { char ->
                    if (char.isLowerCase()) char.titlecase() else char.toString()
                }
                cache[text] = translateText
                return@get translateText
            }
        }.getOrElse { text }
    }

    private fun canProxy(): Boolean {
        return runCatching {
            val test = "https://translate.google.com/"
            OkHttpClientUtils().connectTimeout(2, TimeUnit.SECONDS).get(test) {
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

    companion object {
        private val logger = logger<FrontLangAction>()
    }

}

fun String.equalsAny(vararg others: String): Boolean {
    return others.any { it == this }
}