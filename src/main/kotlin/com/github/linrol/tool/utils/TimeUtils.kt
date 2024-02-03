package com.github.linrol.tool.utils

import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

object TimeUtils {
    private var defaultPattern: String = "yyyy-MM-dd HH:mm:ss.SSS"

    fun getCurrentTime(pattern: String?): String {
        return LocalDateTime.now().format(DateTimeFormatter.ofPattern(pattern ?: defaultPattern))
    }
}
