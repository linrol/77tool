package com.github.linrol.tool.branch.version

import com.intellij.openapi.diagnostic.logger
import com.intellij.openapi.project.Project
import com.intellij.util.io.write
import com.github.linrol.tool.utils.GitLabUtil
import com.github.linrol.tool.utils.XPathHelper
import org.jdom2.Document
import org.jdom2.input.SAXBuilder
import org.jdom2.output.Format
import org.jdom2.output.XMLOutputter
import org.yaml.snakeyaml.Yaml
import java.io.File
import java.io.FileInputStream
import java.io.FileWriter
import java.io.InputStream
import java.nio.file.Paths
import java.util.*
import kotlin.io.path.readText


class ChangeVersion(val project: Project) {

    private val versions = getConfigVersion()

    private val ignore = listOf("autotest-frame-starter", "dbtools", "grpc-clients")

    companion object {
        val log = logger<ChangeVersion>()
    }

    private fun getConfigVersion(): MutableMap<Any, Any> {
        val yaml = Yaml()
        val configFile: File = Paths.get("${project.basePath}/apps/build", "config.yaml").toFile()
        return try {
            val input: InputStream = FileInputStream(configFile)
            (yaml.load(input) as Map<String, Any>).values.flatMap { (it as Map<*, *>).toList() }.associateBy ( { it.first!! }, {it.second!!} ).toMutableMap().apply {
                this["base-common"]?.let {
                    this["base-common-test"] = it
                    this["base-common-test-api"] = it
                }
                this["framework"]?.let {
                    this["testapp"] = it
                    this["testapp-api"] = it
                    this["version.framework"] = it
                }
            }
        } catch (e: Exception) {
            Collections.emptyMap()
        }
    }

    fun run(branch: String):Boolean {
        try {
            val repos = GitLabUtil.getCommonRepositories(project, branch).associateBy ( {it.root.name}, {it.root.path})
            repos.filter { it.value.contains("platform") }.keys.filter { !versions.containsKey(it) }.forEach { name ->
                versions["framework"] ?.let { versions["version.framework.${name}"] = it }
            }
            repos.forEach { (name, path) ->
                val poms = searchPoms(path, 0)
                poms.forEach { changeVersion(name, it) }
            }
            return true
        } catch (e: Throwable) {
            log.error(e)
            return false
        }
    }

    private fun searchPoms(path: String, level: Int): List<File> {
        val files = File(path).listFiles()
        if (files == null || level > 3) {
            return emptyList()
        }
        return files.filter { it.isDirectory || it.name.contains("pom.xml") }.flatMap {
            if (it.isDirectory) {
                searchPoms(it.path, level + 1)
            } else{
                listOf(it)
            }
        }.toList()
    }

    private fun changeVersion(module: String, file: File) {
        // 1. 使用 SAXBuilder 创建 Document 对象
        val saxBuilder = SAXBuilder()
        val document = saxBuilder.build(file)

        val name = module.takeIf { !file.path.contains("platform") } ?: "framework"
        if (updateParent(document) or updateSelf(document, name) or updateProperties(document) or updateDependencies(document) or updatePlugins(document)) {
            writeFile(document, file)
        }
    }

    private fun updateParent(document: Document) :Boolean {
        val group = XPathHelper.getElement(document, "/ns:project/ns:parent/ns:groupId") ?: return false
        val version = XPathHelper.getElement(document, "/ns:project/ns:parent/ns:version") ?: return false
        takeIf { group.text.contains("com.q7link") } ?. let {
           version.run {
               versions["framework"]?.let {
                   if (this.text != it.toString()) {
                       this.setText(it.toString())
                       return true
                   }
               }
           }
        }
        return false
    }

    private fun updateSelf(document: Document, module: String) :Boolean {
        val version = XPathHelper.getElement(document, "/ns:project/ns:version") ?: return false
        version.run {
            versions[module]?.let {
                if (this.text != it.toString()) {
                    this.setText(it.toString())
                    return true
                }
            }
        }
        return false
    }

    private fun updateProperties(document: Document) :Boolean {
        var update = false
        XPathHelper.getElements(document, "/ns:project/ns:properties/*").forEach {
            val elementName: String = if (it.name.endsWith("Version")) {
                toHyphen(it.name.replace("Version",""))
            } else{
                it.name
            }
            versions[elementName]?.let { version ->
                if (it.text != version.toString()) {
                    it.setText(version.toString())
                    update = true
                }
            }
        }
        return update
    }

    private fun updateDependencies(document: Document) :Boolean {
        var update = false
        XPathHelper.getElements(document, "/ns:project/ns:dependencies/ns:dependency").forEach {
            val groupNode = it.getChild("groupId", it.namespace) ?: return@forEach
            val artifactNode = it.getChild("artifactId", it.namespace) ?: return@forEach
            val versionNode = it.getChild("version", it.namespace) ?: return@forEach
            val scopeNode = it.getChild("scope", it.namespace)
            if (scopeNode != null && scopeNode.text == "test") {
                return@forEach
            }
            if (groupNode.text != "com.q7link.application") {
                return@forEach
            }
            val artifactId = artifactNode.text.replace("-private", "")
            if (ignore.contains(artifactId)) {
                return@forEach
            }
            if (versionNode.text.startsWith("\${")) {
                return@forEach
            }
            versions[artifactId]?.let { version ->
                if (versionNode.text != version.toString()) {
                    versionNode.setText(version.toString())
                    update = true
                }
            }
        }
        return update
    }

    private fun updatePlugins(document: Document) :Boolean {
        var update = false
        XPathHelper.getElements(document, "/ns:project/ns:build/ns:plugins/ns:plugin").forEach {
            val groupNode = it.getChild("groupId", it.namespace) ?: return@forEach
            val versionNode = it.getChild("version", it.namespace) ?: return@forEach
            val artifactNode = it.getChild("artifactId", it.namespace) ?: return@forEach
            if (groupNode.text != "com.q7link.framework") {
                return@forEach
            }
            if (versionNode.text.startsWith("\${")) {
                return@forEach
            }
            versions[artifactNode.text]?.let { version ->
                if (versionNode.text != version.toString()) {
                    versionNode.setText(version.toString())
                    update = true
                }
            }
        }
        return update
    }

    private fun writeFile(document: Document, file: File) {
        XMLOutputter(Format.getRawFormat()).output(document, FileWriter(file.path))

        val content = Paths.get(file.path).readText(Charsets.UTF_8).replace("""<?xml version="1.0" encoding="UTF-8"?>""", """<?xml version='1.0' encoding='UTF-8'?>""")
        Paths.get(file.path).write(content, Charsets.UTF_8)
    }

    private fun toCamelCase(input: String): String {
        // Use regular expression to match spaces, underscores, or hyphens
        val regexPattern = """[\s_-]"""

        // Split the input string using the regex pattern
        val words = input.split(regexPattern)

        // Capitalize the first letter of each word (except the first word)
        val camelCaseBuilder = StringBuilder(words[0])
        for (i in 1 until words.size) {
            camelCaseBuilder.append(words[i].replaceFirstChar { if (it.isLowerCase()) it.titlecase(Locale.getDefault()) else it.toString() })
        }

        return camelCaseBuilder.toString()
    }

    private fun toHyphen(camelCase: String): String {
        // Use regular expression to match camel case
        val regexPattern = "([a-z0-9])([A-Z])"

        // Replace camel case with lower-hyphen
        val hyphenString = camelCase.replace(Regex(regexPattern)) {
            "${it.groupValues[1]}-${it.groupValues[2].lowercase(Locale.getDefault())}"
        }

        return hyphenString.lowercase(Locale.getDefault())
    }
}