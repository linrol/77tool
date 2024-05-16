package com.github.linrol.tool.utils

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

fun UsageInfo2UsageAdapter.quotedString(start: Int, end: Int): Boolean {
    val minEnd = 0
    val maxEnd = document.textLength
    if (start <= minEnd || end >= maxEnd) {
        return false
    }
    val left = document.getString(start - 1, start)
    val right = document.getString(end, end + 1)
    return StringUtils.equalsAny(left, "'", "\"").and(StringUtils.equalsAny(right, "'", "\""))
}