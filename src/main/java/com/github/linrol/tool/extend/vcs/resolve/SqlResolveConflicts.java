package com.github.linrol.tool.extend.vcs.resolve;

import com.intellij.diff.fragments.MergeLineFragment;
import com.intellij.diff.util.DiffUtil;
import com.intellij.diff.util.ThreeSide;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import java.util.List;
import org.apache.commons.lang3.StringUtils;

public class SqlResolveConflicts extends ResolveConflicts {

  private static final Logger LOG = Logger.getInstance(SqlResolveConflicts.class);

  @Override
  List<String> getNewContentOfConflict(MergeLineFragment fragment) {
    int rightStartLine = fragment.getStartLine(ThreeSide.RIGHT);
    int rightEndLine = fragment.getEndLine(ThreeSide.RIGHT);
    Document rightDocument = getRequest().getContents().get(ThreeSide.RIGHT.getIndex()).getDocument();

    if (!canIgnore(DiffUtil.getLines(rightDocument, rightStartLine, rightEndLine))) {
      return null;
    }

    ThreeSide sourceSide = ThreeSide.LEFT;
    int sourceStartLine = fragment.getStartLine(sourceSide);
    int sourceEndLine = fragment.getEndLine(sourceSide);
    Document sourceDocument = getRequest().getContents().get(sourceSide.getIndex()).getDocument();

    return DiffUtil.getLines(sourceDocument, sourceStartLine, sourceEndLine);
  }

  private Boolean canIgnore(List<String> lines) {
    Boolean ignore = true;
    for (String line : lines) {
      if (!StringUtils.isBlank(line) && !line.trim().startsWith("--")) {
        ignore = false;
        break;
      }
    }
    return ignore;
  }
}
