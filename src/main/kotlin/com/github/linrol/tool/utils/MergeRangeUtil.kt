// Copyright 2000-2021 JetBrains s.r.o. and contributors. Use of this source code is governed by the Apache 2.0 license.
package com.github.linrol.tool.utils

import com.intellij.diff.comparison.ComparisonMergeUtil
import com.intellij.diff.comparison.ComparisonPolicy
import com.intellij.diff.comparison.ComparisonUtil
import com.intellij.diff.fragments.MergeLineFragment
import com.intellij.diff.tools.util.text.LineOffsets
import com.intellij.diff.util.TextDiffType
import com.intellij.diff.util.ThreeSide
import com.intellij.openapi.util.BooleanGetter
import com.intellij.openapi.util.Condition
import java.util.function.BiPredicate

object MergeRangeUtil {
    private fun getMergeType(
        emptiness: Condition<in ThreeSide>,
        equality: BiPredicate<in ThreeSide, in ThreeSide>,
        trueEquality: BiPredicate<in ThreeSide, in ThreeSide>?,
        conflictResolver: BooleanGetter
    ): MergeConflictType {
        val isLeftEmpty = emptiness.value(ThreeSide.LEFT)
        val isBaseEmpty = emptiness.value(ThreeSide.BASE)
        val isRightEmpty = emptiness.value(ThreeSide.RIGHT)
        assert(!isLeftEmpty || !isBaseEmpty || !isRightEmpty)
        if (isBaseEmpty) {
            if (isLeftEmpty) { // --=
                return MergeConflictType(TextDiffType.INSERTED, leftChange = false, rightChange = true)
            } else if (isRightEmpty) { // =--
                return MergeConflictType(TextDiffType.INSERTED, leftChange = true, rightChange = false)
            } else { // =-=
                val equalModifications = equality.test(ThreeSide.LEFT, ThreeSide.RIGHT)
                return if (equalModifications) {
                    MergeConflictType(TextDiffType.INSERTED, leftChange = true, rightChange = true)
                } else {
                    MergeConflictType(TextDiffType.CONFLICT, leftChange = true, rightChange = true, canBeResolved = false)
                }
            }
        } else {
            if (isLeftEmpty && isRightEmpty) { // -=-
                return MergeConflictType(TextDiffType.DELETED, leftChange = true, rightChange = true)
            } else { // -==, ==-, ===
                val unchangedLeft = equality.test(ThreeSide.BASE, ThreeSide.LEFT)
                val unchangedRight = equality.test(ThreeSide.BASE, ThreeSide.RIGHT)

                if (unchangedLeft && unchangedRight) {
                    assert(trueEquality != null)
                    val trueUnchangedLeft = trueEquality!!.test(ThreeSide.BASE, ThreeSide.LEFT)
                    val trueUnchangedRight = trueEquality.test(ThreeSide.BASE, ThreeSide.RIGHT)
                    assert(!trueUnchangedLeft || !trueUnchangedRight)
                    return MergeConflictType(
                        TextDiffType.MODIFIED,
                        !trueUnchangedLeft,
                        !trueUnchangedRight
                    )
                }

                if (unchangedLeft) return MergeConflictType(
                    if (isRightEmpty) TextDiffType.DELETED else TextDiffType.MODIFIED,
                    leftChange = false,
                    rightChange = true
                )
                if (unchangedRight) return MergeConflictType(
                    if (isLeftEmpty) TextDiffType.DELETED else TextDiffType.MODIFIED,
                    leftChange = true,
                    rightChange = false
                )

                val equalModifications = equality.test(ThreeSide.LEFT, ThreeSide.RIGHT)
                if (equalModifications) {
                    return MergeConflictType(TextDiffType.MODIFIED, leftChange = true, rightChange = true)
                } else {
                    val canBeResolved = !isLeftEmpty && !isRightEmpty && conflictResolver.get()
                    return MergeConflictType(TextDiffType.CONFLICT, leftChange = true, rightChange = true, canBeResolved)
                }
            }
        }
    }

    fun getLineMergeType(
        fragment: MergeLineFragment,
        sequences: List<CharSequence>,
        lineOffsets: List<LineOffsets>,
        policy: ComparisonPolicy
    ): MergeConflictType {
        return getMergeType(
            { side: ThreeSide -> isLineMergeIntervalEmpty(fragment, side) },
            { side1: ThreeSide, side2: ThreeSide ->
                compareLineMergeContents(
                    fragment,
                    sequences,
                    lineOffsets,
                    policy,
                    side1,
                    side2
                )
            },
            { side1: ThreeSide, side2: ThreeSide ->
                compareLineMergeContents(
                    fragment,
                    sequences,
                    lineOffsets,
                    ComparisonPolicy.DEFAULT,
                    side1,
                    side2
                )
            },
            { canResolveLineConflict(fragment, sequences, lineOffsets) })
    }

    private fun canResolveLineConflict(
        fragment: MergeLineFragment,
        sequences: List<CharSequence>,
        lineOffsets: List<LineOffsets>
    ): Boolean {
        val contents = ThreeSide.map { side: ThreeSide ->
            DiffRangeUtil.getLinesContent(
                side.select(sequences),
                side.select(lineOffsets),
                fragment.getStartLine(side),
                fragment.getEndLine(side)
            )
        }
        return ComparisonMergeUtil.tryResolveConflict(
            contents[0]!!,
            contents[1]!!,
            contents[2]!!
        ) != null
    }

    private fun compareLineMergeContents(
        fragment: MergeLineFragment,
        sequences: List<CharSequence>,
        lineOffsets: List<LineOffsets>,
        policy: ComparisonPolicy,
        side1: ThreeSide,
        side2: ThreeSide
    ): Boolean {
        val start1 = fragment.getStartLine(side1)
        val end1 = fragment.getEndLine(side1)
        val start2 = fragment.getStartLine(side2)
        val end2 = fragment.getEndLine(side2)

        if (end2 - start2 != end1 - start1) return false

        val sequence1 = side1.select(sequences)
        val sequence2 = side2.select(sequences)
        val offsets1 = side1.select(lineOffsets)
        val offsets2 = side2.select(lineOffsets)

        for (i in 0 until end1 - start1) {
            val line1 = start1 + i
            val line2 = start2 + i

            val content1 = DiffRangeUtil.getLinesContent(sequence1, offsets1, line1, line1 + 1)
            val content2 = DiffRangeUtil.getLinesContent(sequence2, offsets2, line2, line2 + 1)
            if (!ComparisonUtil.isEquals(content1, content2, policy)) return false
        }

        return true
    }

    private fun isLineMergeIntervalEmpty(fragment: MergeLineFragment, side: ThreeSide): Boolean {
        return fragment.getStartLine(side) == fragment.getEndLine(side)
    }
}
