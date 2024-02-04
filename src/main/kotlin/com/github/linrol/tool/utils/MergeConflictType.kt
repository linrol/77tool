package com.github.linrol.tool.utils

import com.intellij.diff.util.Side
import com.intellij.diff.util.TextDiffType
import com.intellij.diff.util.ThreeSide

class MergeConflictType @JvmOverloads constructor(
    val diffType: TextDiffType,
    private val leftChange: Boolean,
    private val rightChange: Boolean,
    private val canBeResolved: Boolean = true
) {
    fun canBeResolved(): Boolean {
        return canBeResolved
    }

    fun isChange(side: Side): Boolean {
        return if (side.isLeft) leftChange else rightChange
    }

    fun isChange(side: ThreeSide): Boolean {
        return when (side) {
            ThreeSide.LEFT -> leftChange
            ThreeSide.BASE -> true
            ThreeSide.RIGHT -> rightChange
            else -> throw IllegalArgumentException(side.toString())
        }
    }
}
