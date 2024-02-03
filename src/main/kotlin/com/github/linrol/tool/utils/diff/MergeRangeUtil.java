// Copyright 2000-2021 JetBrains s.r.o. and contributors. Use of this source code is governed by the Apache 2.0 license.
package com.github.linrol.tool.utils.diff;

import static com.github.linrol.tool.utils.diff.DiffRangeUtil.getLinesContent;

import com.intellij.diff.comparison.ComparisonMergeUtil;
import com.intellij.diff.comparison.ComparisonPolicy;
import com.intellij.diff.comparison.ComparisonUtil;
import com.intellij.diff.fragments.MergeLineFragment;
import com.intellij.diff.tools.util.text.LineOffsets;
import com.intellij.diff.util.TextDiffType;
import com.intellij.diff.util.ThreeSide;
import com.intellij.openapi.util.BooleanGetter;
import com.intellij.openapi.util.Condition;
import java.util.List;
import java.util.function.BiPredicate;
import org.jetbrains.annotations.NotNull;
import org.jetbrains.annotations.Nullable;

public class MergeRangeUtil {
  @NotNull
  public static MergeConflictType getMergeType(@NotNull Condition<? super ThreeSide> emptiness,
      @NotNull BiPredicate<? super ThreeSide, ? super ThreeSide> equality,
      @Nullable BiPredicate<? super ThreeSide, ? super ThreeSide> trueEquality,
      @NotNull BooleanGetter conflictResolver) {
    boolean isLeftEmpty = emptiness.value(ThreeSide.LEFT);
    boolean isBaseEmpty = emptiness.value(ThreeSide.BASE);
    boolean isRightEmpty = emptiness.value(ThreeSide.RIGHT);
    assert !isLeftEmpty || !isBaseEmpty || !isRightEmpty;

    if (isBaseEmpty) {
      if (isLeftEmpty) { // --=
        return new MergeConflictType(TextDiffType.INSERTED, false, true);
      }
      else if (isRightEmpty) { // =--
        return new MergeConflictType(TextDiffType.INSERTED, true, false);
      }
      else { // =-=
        boolean equalModifications = equality.test(ThreeSide.LEFT, ThreeSide.RIGHT);
        if (equalModifications) {
          return new MergeConflictType(TextDiffType.INSERTED, true, true);
        }
        else {
          return new MergeConflictType(TextDiffType.CONFLICT, true, true, false);
        }
      }
    }
    else {
      if (isLeftEmpty && isRightEmpty) { // -=-
        return new MergeConflictType(TextDiffType.DELETED, true, true);
      }
      else { // -==, ==-, ===
        boolean unchangedLeft = equality.test(ThreeSide.BASE, ThreeSide.LEFT);
        boolean unchangedRight = equality.test(ThreeSide.BASE, ThreeSide.RIGHT);

        if (unchangedLeft && unchangedRight) {
          assert trueEquality != null;
          boolean trueUnchangedLeft = trueEquality.test(ThreeSide.BASE, ThreeSide.LEFT);
          boolean trueUnchangedRight = trueEquality.test(ThreeSide.BASE, ThreeSide.RIGHT);
          assert !trueUnchangedLeft || !trueUnchangedRight;
          return new MergeConflictType(TextDiffType.MODIFIED, !trueUnchangedLeft, !trueUnchangedRight);
        }

        if (unchangedLeft) return new MergeConflictType(isRightEmpty ? TextDiffType.DELETED : TextDiffType.MODIFIED, false, true);
        if (unchangedRight) return new MergeConflictType(isLeftEmpty ? TextDiffType.DELETED : TextDiffType.MODIFIED, true, false);

        boolean equalModifications = equality.test(ThreeSide.LEFT, ThreeSide.RIGHT);
        if (equalModifications) {
          return new MergeConflictType(TextDiffType.MODIFIED, true, true);
        }
        else {
          boolean canBeResolved = !isLeftEmpty && !isRightEmpty && conflictResolver.get();
          return new MergeConflictType(TextDiffType.CONFLICT, true, true, canBeResolved);
        }
      }
    }
  }

  @NotNull
  public static MergeConflictType getLineMergeType(@NotNull MergeLineFragment fragment,
                                                   @NotNull List<? extends CharSequence> sequences,
                                                   @NotNull List<? extends LineOffsets> lineOffsets,
                                                   @NotNull ComparisonPolicy policy) {
    return getMergeType((side) -> isLineMergeIntervalEmpty(fragment, side),
                        (side1, side2) -> compareLineMergeContents(fragment, sequences, lineOffsets, policy, side1, side2),
                        (side1, side2) -> compareLineMergeContents(fragment, sequences, lineOffsets, ComparisonPolicy.DEFAULT, side1, side2),
                        () -> canResolveLineConflict(fragment, sequences, lineOffsets));
  }

  private static boolean canResolveLineConflict(@NotNull MergeLineFragment fragment,
                                                @NotNull List<? extends CharSequence> sequences,
                                                @NotNull List<? extends LineOffsets> lineOffsets) {
    List<? extends CharSequence> contents = ThreeSide.map(side -> getLinesContent(side.select(sequences), side.select(lineOffsets), fragment.getStartLine(side), fragment.getEndLine(side)));
    return ComparisonMergeUtil.tryResolveConflict(contents.get(0), contents.get(1), contents.get(2)) != null;
  }

  private static boolean compareLineMergeContents(@NotNull MergeLineFragment fragment,
                                                  @NotNull List<? extends CharSequence> sequences,
                                                  @NotNull List<? extends LineOffsets> lineOffsets,
                                                  @NotNull ComparisonPolicy policy,
                                                  @NotNull ThreeSide side1,
                                                  @NotNull ThreeSide side2) {
    int start1 = fragment.getStartLine(side1);
    int end1 = fragment.getEndLine(side1);
    int start2 = fragment.getStartLine(side2);
    int end2 = fragment.getEndLine(side2);

    if (end2 - start2 != end1 - start1) return false;

    CharSequence sequence1 = side1.select(sequences);
    CharSequence sequence2 = side2.select(sequences);
    LineOffsets offsets1 = side1.select(lineOffsets);
    LineOffsets offsets2 = side2.select(lineOffsets);

    for (int i = 0; i < end1 - start1; i++) {
      int line1 = start1 + i;
      int line2 = start2 + i;

      CharSequence content1 = getLinesContent(sequence1, offsets1, line1, line1 + 1);
      CharSequence content2 = getLinesContent(sequence2, offsets2, line2, line2 + 1);
      if (!ComparisonUtil.isEquals(content1, content2, policy)) return false;
    }

    return true;
  }

  private static boolean isLineMergeIntervalEmpty(@NotNull MergeLineFragment fragment, @NotNull ThreeSide side) {
    return fragment.getStartLine(side) == fragment.getEndLine(side);
  }


}
