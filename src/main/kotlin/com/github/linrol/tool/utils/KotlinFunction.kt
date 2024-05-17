package com.github.linrol.tool.utils

import com.google.gson.JsonElement
import com.google.gson.JsonObject
import com.intellij.openapi.editor.Document
import com.intellij.openapi.util.TextRange
import com.intellij.usages.UsageInfo2UsageAdapter
import org.apache.commons.lang3.StringUtils

fun Document.getString(start: Int, end: Int): String? {
    val minEnd = 0
    val maxEnd = textLength
    if (start < minEnd || end > maxEnd) {
        return null
    }
    return getText(TextRange(start, end))
}

fun Document.wrappedInQuote(start: Int, end: Int): Boolean {
    val minEnd = 0
    val maxEnd = textLength
    if (start <= minEnd || end >= maxEnd) {
        return false
    }
    val left = getString(start - 1, start)
    val right = getString(end, end + 1)
    return StringUtils.equalsAny(left, "'", "\"").and(StringUtils.equalsAny(right, "'", "\""))
}

fun UsageInfo2UsageAdapter.searchText(): String? {
    val first = getMergedInfos().first()
    val last = getMergedInfos().last()
    if (first.navigationRange == null) {
        return null
    }
    if (last.navigationRange == null) {
        return null
    }
    val startOffset = first.navigationRange.startOffset
    val endOffset = last.navigationRange.endOffset
    return document.getString(startOffset, endOffset)
}

fun UsageInfo2UsageAdapter.startOffset(): Int {
    return getMergedInfos().first().navigationRange.startOffset
}

fun UsageInfo2UsageAdapter.endOffset(): Int {
    return getMergedInfos().last().navigationRange.endOffset
}

fun JsonElement?.getValue(path: String): JsonElement? {
    if (this == null) return null

    val keys = path.split(".")
    var currentElement: JsonElement? = this

    for (key in keys) {
        currentElement = when {
            key.contains("[") && key.contains("]") -> {
                val arrayKey = key.substringBefore("[")
                val index = key.substringAfter("[").substringBefore("]").toIntOrNull()
                if (currentElement is JsonObject && currentElement.has(arrayKey) && index != null) {
                    val jsonArray = currentElement.getAsJsonArray(arrayKey)
                    if (index >= 0 && index < jsonArray.size()) {
                        jsonArray[index]
                    } else null
                } else null
            }
            currentElement is JsonObject && currentElement.has(key) -> {
                currentElement.getAsJsonObject().get(key)
            }
            else -> null
        }
    }
    return currentElement
}