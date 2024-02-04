package com.github.linrol.tool.utils.diff;

import com.intellij.diff.tools.util.text.LineOffsets;
import com.intellij.openapi.util.TextRange;
import org.jetbrains.annotations.NotNull;

public class DiffRangeUtil {
  public static CharSequence getLinesContent(@NotNull CharSequence sequence, @NotNull LineOffsets lineOffsets, int line1, int line2) {
    return getLinesContent(sequence, lineOffsets, line1, line2, false);
  }

  @NotNull
  public static CharSequence getLinesContent(@NotNull CharSequence sequence, @NotNull LineOffsets lineOffsets, int line1, int line2,
      boolean includeNewline) {
    assert sequence.length() == lineOffsets.getTextLength();
    return getLinesRange(lineOffsets, line1, line2, includeNewline).subSequence(sequence);
  }

  @NotNull
  public static TextRange getLinesRange(@NotNull LineOffsets lineOffsets, int line1, int line2, boolean includeNewline) {
    if (line1 == line2) {
      int lineStartOffset = line1 < lineOffsets.getLineCount() ? lineOffsets.getLineStart(line1) : lineOffsets.getTextLength();
      return new TextRange(lineStartOffset, lineStartOffset);
    }
    else {
      int startOffset = lineOffsets.getLineStart(line1);
      int endOffset = lineOffsets.getLineEnd(line2 - 1);
      if (includeNewline && endOffset < lineOffsets.getTextLength()) endOffset++;
      return new TextRange(startOffset, endOffset);
    }
  }
}
