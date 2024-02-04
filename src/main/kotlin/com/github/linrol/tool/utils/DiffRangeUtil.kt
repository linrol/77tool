package com.github.linrol.tool.utils

import com.intellij.diff.tools.util.text.LineOffsets
import com.intellij.openapi.util.TextRange

object DiffRangeUtil {
    fun getLinesContent(
        sequence: CharSequence,
        lineOffsets: LineOffsets,
        line1: Int,
        line2: Int
    ): CharSequence {
        return getLinesContent(sequence, lineOffsets, line1, line2, false)
    }

    private fun getLinesContent(
        sequence: CharSequence, lineOffsets: LineOffsets, line1: Int, line2: Int,
        includeNewline: Boolean
    ): CharSequence {
        assert(sequence.length == lineOffsets.textLength)
        return getLinesRange(lineOffsets, line1, line2, includeNewline).subSequence(sequence)
    }

    private fun getLinesRange(
        lineOffsets: LineOffsets,
        line1: Int,
        line2: Int,
        includeNewline: Boolean
    ): TextRange {
        if (line1 == line2) {
            val lineStartOffset =
                if (line1 < lineOffsets.lineCount) lineOffsets.getLineStart(line1) else lineOffsets.textLength
            return TextRange(lineStartOffset, lineStartOffset)
        } else {
            val startOffset = lineOffsets.getLineStart(line1)
            var endOffset = lineOffsets.getLineEnd(line2 - 1)
            if (includeNewline && endOffset < lineOffsets.textLength) endOffset++
            return TextRange(startOffset, endOffset)
        }
    }
}
