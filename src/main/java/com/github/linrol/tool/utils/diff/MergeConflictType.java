package com.github.linrol.tool.utils.diff;

import com.intellij.diff.util.Side;
import com.intellij.diff.util.TextDiffType;
import com.intellij.diff.util.ThreeSide;
import org.jetbrains.annotations.NotNull;

public class MergeConflictType {
  @NotNull private final TextDiffType myType;
  private final boolean myLeftChange;
  private final boolean myRightChange;
  private final boolean myCanBeResolved;

  public MergeConflictType(@NotNull TextDiffType type, boolean leftChange, boolean rightChange) {
    this(type, leftChange, rightChange, true);
  }

  public MergeConflictType(@NotNull TextDiffType type, boolean leftChange, boolean rightChange, boolean canBeResolved) {
    myType = type;
    myLeftChange = leftChange;
    myRightChange = rightChange;
    myCanBeResolved = canBeResolved;
  }

  @NotNull
  public TextDiffType getDiffType() {
    return myType;
  }

  public boolean canBeResolved() {
    return myCanBeResolved;
  }

  public boolean isChange(@NotNull Side side) {
    return side.isLeft() ? myLeftChange : myRightChange;
  }

  public boolean isChange(@NotNull ThreeSide side) {
    switch (side) {
      case LEFT:
        return myLeftChange;
      case BASE:
        return true;
      case RIGHT:
        return myRightChange;
      default:
        throw new IllegalArgumentException(side.toString());
    }
  }
}
