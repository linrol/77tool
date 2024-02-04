package com.github.linrol.tool.extend.vcs.resolve

import com.intellij.diff.fragments.MergeLineFragment
import com.intellij.diff.util.DiffUtil
import com.intellij.diff.util.ThreeSide
import org.apache.commons.lang3.StringUtils

class SqlResolveConflicts : ResolveConflicts() {
    override fun getNewContentOfConflict(fragment: MergeLineFragment): MutableList<String>? {
        val rightStartLine = fragment.getStartLine(ThreeSide.RIGHT)
        val rightEndLine = fragment.getEndLine(ThreeSide.RIGHT)
        val rightDocument = request.contents[ThreeSide.RIGHT.index].document

        if (!canIgnore(DiffUtil.getLines(rightDocument, rightStartLine, rightEndLine))) {
            return null
        }

        val sourceSide = ThreeSide.LEFT
        val sourceStartLine = fragment.getStartLine(sourceSide)
        val sourceEndLine = fragment.getEndLine(sourceSide)
        val sourceDocument = request.contents[sourceSide.index].document

        return DiffUtil.getLines(sourceDocument, sourceStartLine, sourceEndLine)
    }

    private fun canIgnore(lines: List<String>): Boolean {
        var ignore = true
        for (line in lines) {
            if (!StringUtils.isBlank(line) && !line.trim { it <= ' ' }.startsWith("--")) {
                ignore = false
                break
            }
        }
        return ignore
    }
}
