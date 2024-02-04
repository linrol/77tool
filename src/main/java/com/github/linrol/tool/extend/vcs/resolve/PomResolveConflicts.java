package com.github.linrol.tool.extend.vcs.resolve;

import com.intellij.diff.fragments.MergeLineFragment;
import com.intellij.diff.util.DiffUtil;
import com.intellij.diff.util.ThreeSide;
import com.intellij.openapi.diagnostic.Logger;
import com.intellij.openapi.editor.Document;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import org.apache.commons.lang3.StringUtils;

public class PomResolveConflicts extends ResolveConflicts {

  private static final Logger LOG = Logger.getInstance(PomResolveConflicts.class);

  public static final List<String> NODE_NAMES = new ArrayList<>();

  static {
    NODE_NAMES.add("initDataVersion");

    NODE_NAMES.add("version.framework");
    NODE_NAMES.add("version.framework.app-build-plugins");
    NODE_NAMES.add("version.framework.app-common");
    NODE_NAMES.add("version.framework.app-common-api");
    NODE_NAMES.add("version.framework.common-base");
    NODE_NAMES.add("version.framework.common-base-api");
    NODE_NAMES.add("version.framework.graphql-api");
    NODE_NAMES.add("version.framework.graphql-impl");
    NODE_NAMES.add("version.framework.json-schema-plugin");
    NODE_NAMES.add("version.framework.mbg-plugins");
    NODE_NAMES.add("version.framework.metadata-api");
    NODE_NAMES.add("version.framework.metadata-impl");
    NODE_NAMES.add("version.framework.sql-parser");
  }

  @Override
  List<String> getNewContentOfConflict(MergeLineFragment fragment) {
    ThreeSide sourceSide;
    int leftStartLine = fragment.getStartLine(ThreeSide.LEFT);
    int leftEndLine = fragment.getEndLine(ThreeSide.LEFT);
    Document leftDocument = getRequest().getContents().get(ThreeSide.LEFT.getIndex()).getDocument();

    int rightStartLine = fragment.getStartLine(ThreeSide.RIGHT);
    int rightEndLine = fragment.getEndLine(ThreeSide.RIGHT);
    Document rightDocument = getRequest().getContents().get(ThreeSide.RIGHT.getIndex())
        .getDocument();

    if (leftEndLine - leftStartLine != rightEndLine - rightStartLine
        || leftEndLine - leftStartLine != 1) {
      //行数不一样，需要人工确认，行数超过一行，人工确认
      return null;
    }
    Map<String, String> leftVersion = getVersion(leftDocument, leftStartLine, leftEndLine);
    Map<String, String> rightVersion = getVersion(rightDocument, rightStartLine, rightEndLine);
    if (leftVersion.isEmpty() || rightVersion.isEmpty()) {
      return null;
    }
    String left = leftVersion.values().iterator().next();
    String right = rightVersion.values().iterator().next();
    if (isRelease(left)) {
      if (isRelease(right)) {
        //检查版本号大小
        sourceSide = versionToInt(left).compareTo(versionToInt(right)) > 0 ? ThreeSide.LEFT
            : ThreeSide.RIGHT;
      } else {
        //来源分支不是release版本，目标分支是release版本，则需要人工确认
        return null;
      }
    } else {
      //目标分支不是release版本，则取目标分支数据
      sourceSide = ThreeSide.LEFT;
    }

    int sourceStartLine = fragment.getStartLine(sourceSide);
    int sourceEndLine = fragment.getEndLine(sourceSide);
    Document sourceDocument = getRequest().getContents().get(sourceSide.getIndex()).getDocument();

    return DiffUtil.getLines(sourceDocument, sourceStartLine, sourceEndLine);
  }

  public static String versionToInt(String version) {
    String[] str = version.split("\\.");
    StringBuilder seqBuilder = new StringBuilder();
    for (Integer index = 0; index < 6; index++) {
      if (str.length > index) {
        seqBuilder.append(String.format("%05d", Integer.valueOf(str[index])));
      } else {
        seqBuilder.append("00000");
      }
    }
    return seqBuilder.toString();
  }

  private Boolean isRelease(String version) {
    String pattern = "^([0-9]+.){2,}[0-9]+$";

    Pattern r = Pattern.compile(pattern);
    Matcher m = r.matcher(version);
    return m.matches();
  }

  private Map<String, String> getVersion(Document document, int startLine, int endLine) {
    List<String> lines = DiffUtil.getLines(document, startLine, endLine);
    Map<String, String> versionMap = new HashMap<>();
    if (lines.size() == 1) {
      String version = getNodeValue("version", lines.get(0));
      if (!StringUtils.isBlank(version)) {
        if (isQ7linkVersion(document, startLine - 2, startLine, 0)) {
          versionMap.put("version", version);
        }
        return versionMap;
      }
    }

    for (String line : lines) {
      String version = null;
      String node = null;
      for (String nodeName : NODE_NAMES) {
        version = getNodeValue(nodeName, line);
        if (!StringUtils.isBlank(version)) {
          node = nodeName;
          break;
        }
      }
      if (StringUtils.isBlank(version)) {
        versionMap.clear();
        break;
      }
      versionMap.put(node, version);
    }
    return versionMap;
  }

  private Boolean isQ7linkVersion(Document document, int startLine, int endLine,
      Integer effectiveLine) {
    List<String> lines = DiffUtil.getLines(document, startLine, endLine);
    if (startLine < 0 || effectiveLine > 3) {
      return false;
    }
    int offset = 0;
    for (String line : lines) {
      if (line.trim().startsWith("<groupId>com.q7link.")) {
        return true;
      }
      if (line.trim().startsWith("<!--") || StringUtils.isBlank(line)) {
        offset += 1;
      } else {
        effectiveLine += 1;
      }
    }
    if (offset > 0) {
      return isQ7linkVersion(document, startLine - offset, startLine, effectiveLine);
    }
    return false;
  }

  private String getNodeValue(String node, String text) {
    String pattern = String.format("(?<=(?:<%s>))[\\s\\S]+(?=(?:</%s>))", node, node);

    Pattern r = Pattern.compile(pattern);
    Matcher m = r.matcher(text);
    return m.find() ? m.group() : null;
  }
}
