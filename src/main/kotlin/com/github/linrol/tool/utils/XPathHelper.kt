package com.github.linrol.tool.utils

import org.jdom2.Element
import org.jdom2.Namespace
import org.jdom2.filter.Filters
import org.jdom2.xpath.XPathFactory

object XPathHelper {

    fun getElement(document: Any, xpathExpression: String?): Element? {
        val elements = getElements(document, xpathExpression)
        if (elements.isEmpty()) {
            return null
        }
        return elements[0]
    }

    fun getElements(document: Any, xpathExpression: String?): List<Element> {
        try {
            // 定义命名空间
            val namespace = Namespace.getNamespace("ns", "http://maven.apache.org/POM/4.0.0")

            // 使用 Jaxen XPath 引擎
            val xPathFactory = XPathFactory.instance()
            val expression = xPathFactory.compile(xpathExpression, Filters.element(), null, namespace)

            // 执行 XPath 查询
            return expression.evaluate(document)
        } catch (e: Exception) {
            e.printStackTrace()
            return emptyList()
        }
    }
}
