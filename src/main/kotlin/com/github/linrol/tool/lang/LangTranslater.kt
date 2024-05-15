package com.github.linrol.tool.lang

import com.google.gson.JsonParser
import com.intellij.openapi.diagnostic.logger
import okhttp3.OkHttpClient
import okhttp3.Request
import java.net.SocketTimeoutException
import java.util.concurrent.TimeUnit

class LangTranslater {

    private val cache = mutableMapOf<String, String>()

    val canProxy = canProxy()

    fun translate(text: String): String {
        val ret = cache[text]
        if (ret != null) {
            return ret
        }
        return if (canProxy) {
            translateUseGoogle(text)
        } else{
            translateUseBaidu(text)
        }
    }

    private fun translateUseGoogle(text: String): String {
        val key = "AIzaSyBuRCQkN72SAkmQ0CT3fK4mJIEg_ZCqUd8"
        val params = "q=${text}&source=zh&target=en&key=${key}"
        val url = "https://translation.googleapis.com/language/translate/v2?${params}"

        val client = OkHttpClient()
        val request = Request.Builder().url(url).get().build()
        return client.newCall(request).execute().let {
            if (it.isSuccessful) {
                val response = JsonParser.parseString(it.body().string()).asJsonObject
                val translateText = response.getAsJsonObject("data").getAsJsonArray("translations").get(0).asJsonObject.get("translatedText").asString
                cache[text] = translateText
                translateText
            } else {
                logger.info("Response Error: ${it.code()} - ${it.message()}")
                text
            }
        }
    }

    private fun translateUseBaidu(text: String): String {
        Thread.sleep(13)
        val appId = "20240513002050659"
        val appKey = "Y6ZoTVT8oDBsF_MzBcIE"
        val salt = System.currentTimeMillis().toString()
        val sign = md5("$appId$text$salt$appKey")
        val params = "q=${text}&from=zh&to=en&appid=${appId}&salt=${salt}&sign=${sign}"
        val url = "https://api.fanyi.baidu.com/api/trans/vip/translate?${params}"

        val client = OkHttpClient()
        val request = Request.Builder().url(url).get().build()
        return client.newCall(request).execute().let { it ->
            if (it.isSuccessful) {
                val response = JsonParser.parseString(it.body().string()).asJsonObject ?: return text
                val transResult = response.getAsJsonArray("trans_result") ?: return text
                if (transResult.isEmpty) {
                    return text
                }
                val dst = transResult.get(0).asJsonObject.get("dst") ?: return text
                val translateText = dst.asString.replaceFirstChar { char ->
                    if (char.isLowerCase()) char.titlecase() else char.toString()
                }
                cache[text] = translateText
                return translateText
            } else {
                logger.info("Response Error: ${it.code()} - ${it.message()}")
                text
            }
        }
    }

    private fun canProxy(): Boolean {
        val client = OkHttpClient().newBuilder().connectTimeout(2, TimeUnit.SECONDS).build()
        return try {
            client.newCall(Request.Builder().url("https://translate.google.com/").get().build()).execute().let {
                it.isSuccessful
            }
        } catch (e: SocketTimeoutException) {
            false
        }
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