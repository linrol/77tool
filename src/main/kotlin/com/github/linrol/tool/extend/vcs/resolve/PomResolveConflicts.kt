package com.github.linrol.tool.extend.vcs.resolve

import com.intellij.diff.fragments.MergeLineFragment
import com.intellij.diff.util.DiffUtil
import com.intellij.diff.util.ThreeSide
import com.intellij.openapi.editor.Document
import org.apache.commons.lang3.StringUtils
import java.util.regex.Pattern

class PomResolveConflicts : ResolveConflicts() {
    override fun getNewContentOfConflict(fragment: MergeLineFragment): MutableList<String>? {
        val sourceSide: ThreeSide
        val leftStartLine = fragment.getStartLine(ThreeSide.LEFT)
        val leftEndLine = fragment.getEndLine(ThreeSide.LEFT)
        val leftDocument = request.contents[ThreeSide.LEFT.index].document

        val rightStartLine = fragment.getStartLine(ThreeSide.RIGHT)
        val rightEndLine = fragment.getEndLine(ThreeSide.RIGHT)
        val rightDocument = request.contents[ThreeSide.RIGHT.index].document

        if (leftEndLine - leftStartLine != rightEndLine - rightStartLine || leftEndLine - leftStartLine != 1) {
            //行数不一样，需要人工确认，行数超过一行，人工确认
            return null
        }
        val leftVersion = getVersion(leftDocument, leftStartLine, leftEndLine)
        val rightVersion = getVersion(rightDocument, rightStartLine, rightEndLine)
        if (leftVersion.isEmpty() || rightVersion.isEmpty()) {
            return null
        }
        val left = leftVersion.values.iterator().next()
        val right = rightVersion.values.iterator().next()
        sourceSide = if (isRelease(left)) {
            if (!isRelease(right)) {
                // 来源分支不是release版本，目标分支是release版本，则需要人工确认
                return null
            } else {
                // 检查版本号大小
                if (versionToInt(left) > versionToInt(right)) ThreeSide.LEFT else ThreeSide.RIGHT
            }
        } else {
            //目标分支不是release版本，则取目标分支数据
            ThreeSide.LEFT
        }
        val sourceStartLine = fragment.getStartLine(sourceSide)
        val sourceEndLine = fragment.getEndLine(sourceSide)
        val sourceDocument = request.contents[sourceSide.index].document
        return DiffUtil.getLines(sourceDocument, sourceStartLine, sourceEndLine)
    }

    private fun isRelease(version: String): Boolean {
        val pattern = "^([0-9]+.){2,}[0-9]+$"

        val r = Pattern.compile(pattern)
        val m = r.matcher(version)
        return m.matches()
    }

    private fun getVersion(document: Document, startLine: Int, endLine: Int): Map<String, String> {
        val lines = DiffUtil.getLines(document, startLine, endLine)
        val versionMap: MutableMap<String, String> = HashMap()
        if (lines.size == 1) {
            val version = getNodeValue("version", lines[0])
            if (StringUtils.isNotBlank(version)) {
                if (isQ7linkVersion(document, startLine - 2, startLine, 0)) {
                    versionMap["version"] = version
                }
                return versionMap
            }
        }

        for (line in lines) {
            var version = ""
            var node = ""
            for (nodeName in NODE_NAMES) {
                version = getNodeValue(nodeName, line)
                if (StringUtils.isNotBlank(version)) {
                    node = nodeName
                    break
                }
            }
            if (StringUtils.isBlank(version)) {
                versionMap.clear()
                break
            }
            versionMap[node] = version
        }
        return versionMap
    }

    private fun isQ7linkVersion(document: Document, startLine: Int, endLine: Int, effectiveLine: Int): Boolean {
        var mutableEffectiveLine = effectiveLine
        val lines = DiffUtil.getLines(document, startLine, endLine)
        if (startLine < 0 || mutableEffectiveLine > 3) {
            return false
        }
        var offset = 0
        for (line in lines) {
            if (line.trim { it <= ' ' }.startsWith("<groupId>com.q7link.")) {
                return true
            }
            if (line.trim { it <= ' ' }.startsWith("<!--") || StringUtils.isBlank(line)) {
                offset += 1
            } else {
                mutableEffectiveLine += 1
            }
        }
        if (offset > 0) {
            return isQ7linkVersion(document, startLine - offset, startLine, mutableEffectiveLine)
        }
        return false
    }

    private fun getNodeValue(node: String, text: String): String {
        val pattern = String.format("(?<=(?:<%s>))[\\s\\S]+(?=(?:</%s>))", node, node)
        val r = Pattern.compile(pattern)
        val m = r.matcher(text)
        return if (m.find()) m.group() else ""
    }

    companion object {
        val NODE_NAMES: MutableList<String> = ArrayList()
        init {
            NODE_NAMES.add("initDataVersion")
            NODE_NAMES.add("version.framework")
            NODE_NAMES.add("version.framework.app-build-plugins")
            NODE_NAMES.add("version.framework.app-common")
            NODE_NAMES.add("version.framework.app-common-api")
            NODE_NAMES.add("version.framework.common-base")
            NODE_NAMES.add("version.framework.common-base-api")
            NODE_NAMES.add("version.framework.graphql-api")
            NODE_NAMES.add("version.framework.graphql-impl")
            NODE_NAMES.add("version.framework.json-schema-plugin")
            NODE_NAMES.add("version.framework.mbg-plugins")
            NODE_NAMES.add("version.framework.metadata-api")
            NODE_NAMES.add("version.framework.metadata-impl")
            NODE_NAMES.add("version.framework.sql-parser")
        }

        fun versionToInt(version: String?): String {
            val str = version!!.split("\\.".toRegex()).dropLastWhile { it.isEmpty() }.toTypedArray()
            val seqBuilder = StringBuilder()
            for (index in 0..5) {
                if (str.size > index) {
                    seqBuilder.append(String.format("%05d", str[index].toInt()))
                } else {
                    seqBuilder.append("00000")
                }
            }
            return seqBuilder.toString()
        }
    }
}
